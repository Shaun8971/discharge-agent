"""Conversation log: one JSON object per line in data/conversations.jsonl (JSONL).

Records hold IDs, outcomes, token counts, timings and tool calls, never patient names.
"""
import json
import os

from config import CACHE_READ_MULTIPLIER, CACHE_WRITE_MULTIPLIER, LOG_PATH, PRICE_INPUT_PER_MTOK, PRICE_OUTPUT_PER_MTOK


def log_conversation(record: dict) -> None:
    """Append one conversation record as a single JSON line to data/conversations.jsonl.
    Creates the data/ folder if needed. Records hold IDs, outcomes, token counts, timings and
    tool calls, never patient names.

    Args:
        record (dict): the log record built by Conversation.end().

    Returns:
        None

    Example:
        >>> log_conversation({"mrn": "MRN1001", "outcome": {"completed": True}})
    """
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(record) + "\n")


def read_conversations() -> list[dict]:
    """Read every record from data/conversations.jsonl.

    Returns:
        list[dict]: one dict per logged conversation, oldest first; [] if the file does not exist.

    Example:
        >>> len(read_conversations())
        5
    """
    if not os.path.exists(LOG_PATH):
        return []
    with open(LOG_PATH) as f:
        return [json.loads(line) for line in f if line.strip()]


def conversation_cost(record: dict) -> float:
    """Work out the USD cost of one logged conversation from its token counts.

    Cost = (input + 1.25 x cache-write + 0.10 x cache-read tokens) x input price
           + output tokens x output price, with prices per million tokens from config.py.
    Missing token fields count as 0, so older records still work.

    Args:
        record (dict): a log record with input_tokens, cache_write_tokens, cache_read_tokens
            and output_tokens.

    Returns:
        float: cost in US dollars.

    Example:
        >>> conversation_cost({"input_tokens": 18, "cache_write_tokens": 5824,
        ...                    "cache_read_tokens": 1708, "output_tokens": 401})
        0.0189476
    """
    input_cost = PRICE_INPUT_PER_MTOK * (
        record.get("input_tokens", 0)
        + record.get("cache_write_tokens", 0) * CACHE_WRITE_MULTIPLIER
        + record.get("cache_read_tokens", 0) * CACHE_READ_MULTIPLIER
    )
    return (input_cost + PRICE_OUTPUT_PER_MTOK * record.get("output_tokens", 0)) / 1_000_000
