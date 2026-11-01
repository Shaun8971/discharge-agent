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

# Claude
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-5-5")

# Token prices in USD per million tokens. TODO: fill in from Anthropic's pricing page (Phase 4).
PRICE_INPUT_PER_MTOK = 0.0
PRICE_OUTPUT_PER_MTOK = 0.0

# Identifier / tag conventions
MRN_SYSTEM = "urn:demo:mrn"
SOURCE_TAG_SYSTEM = "urn:demo:source"
AGENT_TAG_CODE = "discharge-agent"
SEED_TAG_CODE = "seed"
# Used only to make seeded Encounters/Medications/Appointments findable on re-run
SEED_ID_SYSTEM = "urn:demo:seed-id"

LOG_PATH = "data/conversations.jsonl"
