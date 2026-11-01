"""Conversation log: one JSON object per line in data/conversations.jsonl (JSONL).

Records hold IDs, outcomes, token counts, timings and tool calls, never patient names.
"""
import json
import os

from config import CACHE_READ_MULTIPLIER, CACHE_WRITE_MULTIPLIER, LOG_PATH, PRICE_INPUT_PER_MTOK, PRICE_OUTPUT_PER_MTOK


def log_conversation(record: dict) -> None:
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_conversations() -> list[dict]:
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def conversation_cost(record: dict) -> float:
    """USD cost of one logged conversation: tokens x per-million-token prices from config.py.
    Cache writes and reads are billed at multiples of the input price."""
    input_cost = PRICE_INPUT_PER_MTOK * (
        record.get("input_tokens", 0)
        + record.get("cache_write_tokens", 0) * CACHE_WRITE_MULTIPLIER
        + record.get("cache_read_tokens", 0) * CACHE_READ_MULTIPLIER
    )
    return (input_cost + PRICE_OUTPUT_PER_MTOK * record.get("output_tokens", 0)) / 1_000_000
