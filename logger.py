"""Conversation log: one JSON object per line in data/conversations.jsonl (JSONL).

Records hold IDs, outcomes, token counts, timings and tool calls, never patient names.
"""
import json
import os

from config import LOG_PATH


def log_conversation(record: dict) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_conversations() -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]
