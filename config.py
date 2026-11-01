"""Shared configuration and constants."""
import os

from dotenv import load_dotenv

load_dotenv()

# FHIR server (HAPI in Docker by default; public test server is the fallback)
FHIR_BASE_URL = os.getenv("FHIR_BASE_URL", "http://localhost:8080/fhir")
FHIR_HEADERS = {
    "Content-Type": "application/fhir+json",
    "Accept": "application/fhir+json",
}

# Claude, reached through the Open WebUI gateway (see claude_client.py).
# CLAUDE_MODEL must be the model name the gateway lists (run list_gateway_models.py).
ANTHROPIC_BASE_URL = os.getenv("ANTHROPIC_BASE_URL")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

# Hospital local timezone: appointment times (09:00 / 14:00) are in this zone.
HOSPITAL_TZ = "America/New_York"

# Token prices in USD per million tokens. TODO: fill in from Anthropic's pricing page (Phase 4).
PRICE_INPUT_PER_MTOK = 2
PRICE_OUTPUT_PER_MTOK = 10
# Prompt-cache pricing relative to the input price (Anthropic's standard multipliers; verify on the pricing page)
CACHE_WRITE_MULTIPLIER = 1.25
CACHE_READ_MULTIPLIER = 0.10

# Identifier / tag conventions
MRN_SYSTEM = "urn:demo:mrn"
SOURCE_TAG_SYSTEM = "urn:demo:source"
AGENT_TAG_CODE = "discharge-agent"
SEED_TAG_CODE = "seed"
# Used only to make seeded Encounters/Medications/Appointments findable on re-run
SEED_ID_SYSTEM = "urn:demo:seed-id"

LOG_PATH = "data/conversations.jsonl"
