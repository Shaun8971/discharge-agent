"""Check that the Claude gateway supports tool use, the loop the agent in Phase 3 depends on.

Run:  python test_gateway.py
Needs ANTHROPIC_BASE_URL, ANTHROPIC_API_KEY and CLAUDE_MODEL in .env (see .env.example).
Makes two small API calls. Sends no patient data; the tool here is a made-up weather tool.
"""
import os
import sys

import anthropic
from dotenv import load_dotenv

# Step 0: read settings from .env. (The key is never printed.)
load_dotenv()
BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL = os.getenv("CLAUDE_MODEL")
missing = [n for n, v in [("ANTHROPIC_BASE_URL", BASE_URL), ("ANTHROPIC_API_KEY", API_KEY), ("CLAUDE_MODEL", MODEL)] if not v]
if missing:
    sys.exit(f"Missing in .env: {', '.join(missing)}")
if API_KEY.startswith("your-"):
    sys.exit("ANTHROPIC_API_KEY in .env is still the placeholder value.")

from claude_client import get_client  # the same shared client the agent uses

client = get_client()

# A fake tool. We describe it to the model; the model never runs it, it only asks us to.
TOOLS = [{
    "name": "get_weather",
    "description": "Get the current weather for a city.",
    "input_schema": {
        "type": "object",
        "properties": {"city": {"type": "string", "description": "City name"}},
        "required": ["city"],
    },
}]


def show_usage(label, response):
    # Tokens are what the API bills for: input = what we sent, output = what the model wrote.
    """Print the token counts of one response (input = what we sent, output = what the model wrote).

    Args:
        label (str): name of the test, e.g. "test 1".
        response: an Anthropic message response.
    """
    print(f"  usage ({label}): input_tokens={response.usage.input_tokens}, output_tokens={response.usage.output_tokens}")


def fail(msg):
    """Print "FAIL: <msg>" and exit the script with status 1.

    Args:
        msg (str): why the test failed.
    """
    print(f"FAIL: {msg}")
    sys.exit(1)


print(f"Model: {MODEL}")
print(f"Gateway host: {anthropic.Anthropic(base_url=BASE_URL, api_key='x').base_url.host}")

messages = [{"role": "user", "content": "What is the weather in Paris right now? Use the tool."}]

try:
    # Test 1: ask a question that needs the tool. A gateway that supports tool use should
    # answer with stop_reason "tool_use" and a tool_use block naming the tool and its input.
    print("\nTest 1: model should ask to call the tool")
    r1 = client.messages.create(model=MODEL, max_tokens=300, tools=TOOLS, messages=messages)
    show_usage("test 1", r1)
    print(f"  stop_reason: {r1.stop_reason}")
    if r1.stop_reason != "tool_use":
        fail(f"expected stop_reason 'tool_use', got {r1.stop_reason!r}. The gateway may be dropping the tools parameter.")
    tool_call = next((b for b in r1.content if b.type == "tool_use"), None)
    if tool_call is None or tool_call.name != "get_weather":
        fail("no tool_use block for get_weather in the response.")
    print(f"  tool requested: {tool_call.name}({tool_call.input})")
    print("PASS: tool use request")

    # Test 2: play the part of our code. We "ran" the tool and send back its result as a
    # tool_result block, tied to the request by tool_use_id. We first echo the model's own
    # message (its tool_use block) so the conversation stays valid.
    print("\nTest 2: send the tool result back; model should answer in plain text")
    assistant_blocks = [
        {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input} if b.type == "tool_use"
        else {"type": "text", "text": b.text}
        for b in r1.content if b.type in ("tool_use", "text")
    ]
    messages += [
        {"role": "assistant", "content": assistant_blocks},
        {"role": "user", "content": [{
            "type": "tool_result",
            "tool_use_id": tool_call.id,
            "content": '{"city": "Paris", "temp_c": 18, "conditions": "light rain"}',
        }]},
    ]
    r2 = client.messages.create(model=MODEL, max_tokens=300, tools=TOOLS, messages=messages)
    show_usage("test 2", r2)
    print(f"  stop_reason: {r2.stop_reason}")
    text = " ".join(b.text for b in r2.content if b.type == "text").strip()
    if r2.stop_reason != "end_turn" or not text:
        fail(f"expected a final text answer with stop_reason 'end_turn', got {r2.stop_reason!r}.")
    print(f"  answer: {text[:200]}")
    print("PASS: final answer after tool result")

except anthropic.APIStatusError as e:
    fail(f"gateway returned HTTP {e.status_code}: {str(e.message)[:200]}")
except anthropic.APIConnectionError as e:
    fail(f"could not reach the gateway ({type(e.__cause__).__name__}). Check ANTHROPIC_BASE_URL.")

print("\nAll tests passed: the gateway supports tool use.")
