"""Claude tool-use loop for the post-discharge check-in, plus the end-of-chat summary.

Tool use, in short: we send Claude the conversation plus a list of tools. If it wants one it
replies with stop_reason "tool_use" and a tool_use block (name + input). We run the tool, send
the output back as a tool_result block, and call Claude again, until it answers in plain text.

Command-line chat for testing:  python agent.py hl7_messages/adt_a03_MRN1001.hl7
"""
import json
import re
import sys
import time
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import hl7_parser
import tools
from claude_client import get_client
from config import CLAUDE_MODEL, HOSPITAL_TZ
from logger import log_conversation

MAX_TOOL_ROUNDS = 6  # safety stop for one patient message

SYSTEM_PROMPT = """You are a post-discharge follow-up assistant for Demo General Hospital. You are
chatting by text with a patient who went home in the last two days.

Your job is logistics only:
1. Confirm they have picked up their medications. Read the names from the
   patient context. Do not explain what the medications are for.
2. Make sure they have a follow-up appointment. If none exists, offer to book
   one within the next 14 days.
3. Ask if they have any other questions.

Rules:
- Never give medical advice, diagnose, interpret symptoms, or suggest changing
  a medication or dose.
- If the patient mentions any symptom, side effect, or medical question, call
  escalate_to_nurse with a short factual reason and tell them a nurse will
  follow up.
- If the patient describes something that sounds like an emergency, tell them
  to call 911 now, and call escalate_to_nurse with urgency "urgent".
- If the patient is confused or you are unsure, escalate with urgency "routine".
- When you escalate, say only that a nurse will follow up. Do not tell the
  patient to take, avoid, stop, wait on, or change any medication or activity
  (the only exception is telling them to call 911 in an emergency).
- Use urgency "routine" for medication questions, side effects, mild symptoms,
  confusion, and anything else a nurse can handle during the day. Use "urgent"
  only for an emergency (the 911 case).
- Keep messages short and friendly. Ask one question at a time.
- Use only information from get_patient_context. Never invent appointment
  times or medications.

Practical notes:
- Pass the patient_id from the discharge event to every tool call.
- Today's date is {today}. Appointments can be booked as morning (9:00) or afternoon (14:00)."""

SUMMARY_PROMPT = """You review a finished post-discharge check-in chat and reply with JSON only
(no other text, no code fences) in exactly this shape:
{"completed": true, "meds_confirmed": "yes|no|unclear", "followup": "booked|already_scheduled|declined|not_discussed", "escalated": false, "summary": "2-3 sentences"}
- completed: true only if BOTH the medication check and the follow-up appointment were covered.
- meds_confirmed: did the patient say they have their medications?
- followup: booked = the assistant booked one; already_scheduled = one already existed; declined = patient said no.
- escalated: true if the assistant escalated to a nurse.
- summary: 2-3 plain sentences. Do not include any patient name; say "the patient"."""


class Conversation:
    """One post-discharge check-in between the agent and one patient.

    Holds the message history sent to Claude, token and latency counters, and the tool-call
    record. Typical use: Conversation(...).start(), then .send(text) for each patient message,
    then .end() to summarize, write to FHIR and log.

    Args:
        parsed (dict): output of hl7_parser.parse_adt.
        patient_id (str): FHIR Patient ID.
        encounter_id (str): FHIR Encounter ID.
        on_tool_call (callable | None): called as on_tool_call(record, result) after each tool
            runs, so a UI can show it.
    """
    def __init__(self, parsed: dict, patient_id: str, encounter_id: str, on_tool_call=None):
        self.parsed, self.patient_id, self.encounter_id = parsed, patient_id, encounter_id
        self.on_tool_call = on_tool_call or (lambda record, result: None)
        self.client = get_client()
        self.messages: list[dict] = []
        self.started = datetime.now(timezone.utc)
        self.turns = 0
        # The gateway caches prompts automatically, so usage has three input counts:
        # fresh input, cache writes, and cache reads. All are billed (at different rates).
        self.input_tokens = self.output_tokens = self.cache_write_tokens = self.cache_read_tokens = 0
        self.latencies_ms: list[int] = []
        self.tool_calls: list[dict] = []
        self.first_name = None  # kept in memory only, to scrub it from the stored summary
        self.system = SYSTEM_PROMPT.format(today=datetime.now(ZoneInfo(HOSPITAL_TZ)).date().isoformat())

    # --- Claude calls ---
    def _call_claude(self, **kwargs):
        """Make one Claude request and update the counters (latency, tokens, cache tokens).

        Args:
            **kwargs: passed to client.messages.create (system, tools, messages).

        Returns:
            anthropic.types.Message: the model response.

        Raises:
            anthropic.APIError: if the gateway or model call fails.
        """
        t0 = time.perf_counter()
        response = self.client.messages.create(model=CLAUDE_MODEL, max_tokens=600, **kwargs)
        self.latencies_ms.append(round((time.perf_counter() - t0) * 1000))
        self.input_tokens += response.usage.input_tokens
        self.output_tokens += response.usage.output_tokens
        self.cache_write_tokens += getattr(response.usage, "cache_creation_input_tokens", 0) or 0
        self.cache_read_tokens += getattr(response.usage, "cache_read_input_tokens", 0) or 0
        return response

    def _run_loop(self) -> str:
        """The agentic loop: call Claude, run any tools it asks for, send the results back, and repeat
        until it answers in plain text (at most MAX_TOOL_ROUNDS times).

        Returns:
            str: the assistant's text reply, or a fixed apology if the round limit is hit.

        Raises:
            anthropic.APIError: if a Claude call fails.
        """
        for _ in range(MAX_TOOL_ROUNDS):
            response = self._call_claude(system=self.system, tools=tools.TOOL_SPECS, messages=self.messages)
            blocks = [
                {"type": "tool_use", "id": b.id, "name": b.name, "input": b.input} if b.type == "tool_use"
                else {"type": "text", "text": b.text}
                for b in response.content if b.type in ("tool_use", "text")
            ]
            self.messages.append({"role": "assistant", "content": blocks})
            if response.stop_reason != "tool_use":
                return "\n".join(b["text"] for b in blocks if b["type"] == "text").strip()
            results = []
            for b in (x for x in blocks if x["type"] == "tool_use"):
                result, record = tools.run_tool(b["name"], b["input"], self.patient_id)
                self.tool_calls.append(record)
                if b["name"] == "get_patient_context" and record["ok"]:
                    self.first_name = result.get("first_name")
                self.on_tool_call(record, result)
                results.append({"type": "tool_result", "tool_use_id": b["id"], "content": json.dumps(result), "is_error": not record["ok"]})
            self.messages.append({"role": "user", "content": results})
        return "Sorry, I'm having trouble right now. A nurse will follow up with you."

    # --- conversation ---
    def start(self) -> str:
        """Begin the conversation. The first user-role message is a system event that is not shown to the
        patient: "[DISCHARGE EVENT] patient_id=..., discharged=.... Begin the follow-up check-in."

        Returns:
            str: the agent's greeting (it normally calls get_patient_context first).

        Example:
            >>> convo.start()
            'Hi Alice, this is Demo General Hospital checking in after your discharge. ...'
        """
        self.messages.append({
            "role": "user",
            "content": f"[DISCHARGE EVENT] patient_id={self.patient_id}, discharged={self.parsed['discharge_time']}. Begin the follow-up check-in.",
        })
        return self._run_loop()

    def send(self, text: str) -> str:
        """Send one patient message and return the agent's reply.

        Args:
            text (str): what the patient typed.

        Returns:
            str: the agent's reply.

        Example:
            >>> convo.send("yes I have them all")
            'Great, thanks for confirming. I do not see a follow-up appointment ...'
        """
        self.turns += 1
        self.messages.append({"role": "user", "content": text})
        return self._run_loop()

    def _transcript(self) -> str:
        """Build a plain-text transcript (PATIENT / ASSISTANT lines plus short tool notes, patient_id
        removed) for the summary call.

        Returns:
            str: the transcript, without the hidden discharge event.
        """
        lines = []
        for m in self.messages[1:]:  # skip the discharge event
            if isinstance(m["content"], str):
                lines.append(f"PATIENT: {m['content']}")
                continue
            for b in m["content"]:
                if b["type"] == "text":
                    lines.append(f"ASSISTANT: {b['text']}")
                elif b["type"] == "tool_use":
                    lines.append(f"[assistant used tool {b['name']} {json.dumps({k: v for k, v in b['input'].items() if k != 'patient_id'})}]")
                elif b["type"] == "tool_result":
                    lines.append(f"[tool result {'ERROR ' if b.get('is_error') else ''}{b['content'][:300]}]")
        return "\n".join(lines)

    def end(self) -> dict:
        """Finish the conversation: ask Claude for the JSON outcome, correct two fields from the tool log,
        scrub the first name, write a FHIR Communication, and append the log record.

        Returns:
            dict: {"completed", "meds_confirmed", "followup", "escalated", "summary"}.

        Raises:
            anthropic.APIError: if the summary call fails.
            fhir_client.FhirError: if the Communication cannot be written.

        Example:
            >>> convo.end()["followup"]
            'booked'
        """
        response = self._call_claude(
            system=SUMMARY_PROMPT,
            messages=[{"role": "user", "content": "Chat transcript:\n" + self._transcript()}],
        )
        raw = "".join(b.text for b in response.content if b.type == "text")
        outcome = _parse_outcome(raw)
        # Ground truth from the tool log beats the model's guess for these fields.
        ok_tools = {r["tool"] for r in self.tool_calls if r["ok"]}
        outcome["escalated"] = "escalate_to_nurse" in ok_tools
        if "book_followup" in ok_tools:
            outcome["followup"] = "booked"
        if self.first_name:
            outcome["summary"] = re.sub(rf"\b{re.escape(self.first_name)}\b", "the patient", outcome["summary"], flags=re.I)
        comm_id = tools.write_summary(self.patient_id, outcome["summary"], self.encounter_id)
        self.on_tool_call({"tool": "write_summary (Communication)", "input": {"patient_id": self.patient_id}, "ok": True, "error": None, "ms": 0}, {"communication_id": comm_id})
        log_conversation({
            "started": self.started.isoformat(), "ended": datetime.now(timezone.utc).isoformat(),
            "message_control_id": self.parsed["message_control_id"], "mrn": self.parsed["mrn"],
            "patient_id": self.patient_id, "encounter_id": self.encounter_id, "communication_id": comm_id,
            "model": CLAUDE_MODEL, "turns": self.turns,
            "input_tokens": self.input_tokens, "output_tokens": self.output_tokens,
            "cache_write_tokens": self.cache_write_tokens, "cache_read_tokens": self.cache_read_tokens,
            "claude_calls": len(self.latencies_ms), "latencies_ms": self.latencies_ms,
            "avg_latency_ms": round(sum(self.latencies_ms) / len(self.latencies_ms)),
            "tool_calls": self.tool_calls, "outcome": outcome,
        })
        return outcome


def _parse_outcome(raw: str) -> dict:
    """Parse and validate the summary JSON from the model, falling back to safe values.

    Args:
        raw (str): the model's reply text (may include code fences or extra words).

    Returns:
        dict: completed (bool), meds_confirmed (yes/no/unclear), followup
            (booked/already_scheduled/declined/not_discussed), escalated (bool), summary (str).
            If no JSON object is found: completed False, "unclear", "not_discussed", and a notice.

    Example:
        >>> _parse_outcome("I cannot do that")["summary"]
        'Summary unavailable: the model did not return valid JSON.'
    """
    safe = {"completed": False, "meds_confirmed": "unclear", "followup": "not_discussed", "escalated": False,
            "summary": "Summary unavailable: the model did not return valid JSON."}
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        data = json.loads(m.group(0))
    except (AttributeError, json.JSONDecodeError):
        return safe
    if data.get("meds_confirmed") not in ("yes", "no", "unclear"):
        data["meds_confirmed"] = "unclear"
    if data.get("followup") not in ("booked", "already_scheduled", "declined", "not_discussed"):
        data["followup"] = "not_discussed"
    return {
        "completed": bool(data.get("completed")), "meds_confirmed": data["meds_confirmed"], "followup": data["followup"],
        "escalated": bool(data.get("escalated")), "summary": str(data.get("summary") or safe["summary"])[:1000],
    }


def print_tool_call(record: dict, result: dict) -> None:
    """Print one tool call and its result to the terminal (used by the command-line chat).

    Args:
        record (dict): {"tool", "input", "ok", "error", "ms"}.
        result (dict): what the tool returned.

    Example output:
          [TOOL] book_followup {"patient_id": "1000", "date": "2026-11-02", "time_of_day": "afternoon"}
          [RESULT] ok (176 ms) {"appointment_id": "1032", ...}
    """
    status = "ok" if record["ok"] else f"ERROR: {record['error']}"
    print(f"\n  [TOOL] {record['tool']} {json.dumps(record['input'])}")
    print(f"  [RESULT] {status} ({record['ms']} ms) {json.dumps(result)}")


def main(path: str) -> int:
    """Command-line chat: parse the file, find the patient, start the agent, let you type replies as
    the patient, and run the summary when you type "end".

    Args:
        path (str): path to an .hl7 file.

    Returns:
        int: 0 on a normal exit, 1 if the file cannot be parsed or the patient is not found.
            Ctrl+C or Ctrl+D exits without a summary and logs nothing.
    """
    try:
        with open(path, newline="") as f:
            parsed = hl7_parser.parse_adt(f.read())
        patient_id, encounter_id = hl7_parser.find_patient(parsed["mrn"])
    except (hl7_parser.HL7Error, OSError) as e:
        print(f"ERROR: {e}")
        return 1
    print(f"Discharge {parsed['message_control_id']}: {parsed['mrn']} -> Patient/{patient_id}, Encounter/{encounter_id}")
    print("You are the patient. Type a reply, or 'end' to finish and summarize.\n")
    convo = Conversation(parsed, patient_id, encounter_id, on_tool_call=print_tool_call)
    print(f"\nAgent: {convo.start()}")
    while True:
        try:
            text = input("\nPatient> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExited without a summary (nothing logged).")
            return 0
        if not text:
            continue
        if text.lower() == "end":
            break
        print(f"\nAgent: {convo.send(text)}")
    outcome = convo.end()
    print("\n--- Outcome ---")
    print(json.dumps(outcome, indent=2))
    print(f"Tokens: input={convo.input_tokens}, cache_write={convo.cache_write_tokens}, cache_read={convo.cache_read_tokens}, output={convo.output_tokens}; Claude calls={len(convo.latencies_ms)}; logged to data/conversations.jsonl")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python agent.py hl7_messages/<file>.hl7")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
