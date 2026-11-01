"""Print the model IDs your gateway accepts, so you can set CLAUDE_MODEL correctly.

Run:  python list_gateway_models.py
Reads ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY from .env. Prints model IDs only; never the key.
"""
import os
import sys

import anthropic
import requests
from dotenv import load_dotenv

load_dotenv()
base = os.getenv("ANTHROPIC_BASE_URL")
key = os.getenv("ANTHROPIC_API_KEY")
if not base or not key:
    sys.exit("Set ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY in .env first.")

found = []

# Attempt 1: the Anthropic-style list (GET <base>/v1/models), via the SDK.
try:
    found = [m.id for m in anthropic.Anthropic(base_url=base, api_key=key, timeout=30).models.list(limit=1000)]
    print("(listed via the Anthropic-style endpoint)")
except Exception as e:
    print(f"Anthropic-style listing failed: {type(e).__name__}")

# Attempt 2: the OpenAI-style list that Open WebUI-type gateways usually offer (GET <base>/models).
if not found:
    for url in (base.rstrip("/") + "/models", base.rstrip("/") + "/v1/models"):
        try:
            r = requests.get(url, headers={"Authorization": f"Bearer {key}"}, timeout=30)
            if r.ok:
                found = [m.get("id") for m in r.json().get("data", [])]
                print(f"(listed via {url.replace(base.rstrip('/'), '<base>')})")
                break
            print(f"{url.replace(base.rstrip('/'), '<base>')} -> HTTP {r.status_code}")
        except Exception as e:
            print(f"{url.replace(base.rstrip('/'), '<base>')} failed: {type(e).__name__}")

if not found:
    sys.exit("Could not list models. Check the gateway's docs or model picker for the exact IDs.")
claude = [m for m in found if m and "claude" in m.lower()]
print(f"\n{len(found)} models available. Claude models:" if claude else f"\n{len(found)} models available (none contain 'claude'):")
for m in sorted(claude or found):
    print("  ", m)
