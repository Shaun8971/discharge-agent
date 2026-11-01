"""The one place the Claude client is created. Every file that talks to Claude imports from here.

Settings come from .env: ANTHROPIC_BASE_URL (the Open WebUI gateway), ANTHROPIC_API_KEY.
Same settings test_gateway.py verified: custom base URL, 60-second timeout.
"""
import os

import anthropic
from dotenv import load_dotenv

load_dotenv()

_client = None


def get_client() -> anthropic.Anthropic:
    """Return the one shared Anthropic client, creating it on first use.

    Reads ANTHROPIC_BASE_URL (the Open WebUI gateway) and ANTHROPIC_API_KEY from the environment
    (loaded from .env). The same client object is returned on every later call.

    Returns:
        anthropic.Anthropic: client with the gateway base URL and a 60-second timeout.

    Raises:
        RuntimeError: if either setting is missing or the key still starts with "your-".

    Example:
        >>> client = get_client()
        >>> get_client() is client
        True
    """
    global _client
    if _client is None:
        base_url = os.getenv("ANTHROPIC_BASE_URL")
        api_key = os.getenv("ANTHROPIC_API_KEY")
        if not base_url or not api_key or api_key.startswith("your-"):
            raise RuntimeError("Set ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY in .env (see .env.example).")
        _client = anthropic.Anthropic(base_url=base_url, api_key=api_key, timeout=60)
    return _client
