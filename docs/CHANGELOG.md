# Changelog

What changed in each phase, based on the git history of this repository. Dates are the commit dates. Within a phase, items that came from the project owner's feedback (rather than the original spec) are marked **(owner request)**, and fixes for problems found during testing are marked **(fix)**. Back to the [README](../README.md).

## Phase 5: Documentation (this change; not yet committed when this was written)

- Added `README.md` and the `docs/` folder: ARCHITECTURE, AGENT, FUNCTION_REFERENCE, DATA_MODEL, KPIS, VALIDATION_LOG, CHANGELOG, GLOSSARY.
- Rewrote the docstrings of every function and class (purpose, inputs, output, short example). The code's logic was not touched; this was checked by comparing each file's syntax tree with docstrings removed, before and after.
- **(fix)** Dashboard empty-state message still said "Process a discharge"; now says to start a follow-up.
- **(fix)** `config.py`: removed a stale "TODO: fill in prices" comment.
- **(fix)** `.env.example`: the model-name line now says to use the exact name from `list_gateway_models.py`, with `anthropic.claude-sonnet-5-5` as the example, since the gateway uses prefixed names.
- Re-seeded FHIR from scratch while re-running the tests, so the five HL7 files in `hl7_messages/` carry new discharge times matching the new data.

## Phase 4: Streamlit app (`ed7f32c`, 2026-11-01)

- Added `app.py` with two pages built on `st.navigation`.
- **Page 1, Patient follow-up:** a table of the five discharged patients, a per-patient chat with the agent, an HL7 and FHIR IDs expander, an End conversation button with outcome tiles, and a "Behind the scenes" sidebar listing each tool call with its input and result.
- **Page 2, Dashboard:** seven KPI tiles (some from the log, some live from FHIR), a table of recent conversations, and a "Statistics from this hospital" section.
- **(owner request)** Replaced the planned ROI calculator panel with the "Statistics from this hospital" section, read from a new `HOSPITAL_STATS` block in `config.py`; placeholders display as "Not filled in yet". The owner later filled in WellSpan York Hospital heart failure figures from the CMS Hospital Readmissions Reduction Program data.
- **(owner request)** Patient list redesigned as a table with one row per patient.
- **(owner request)** "Process discharge" button renamed "Start follow-up" (then "Resume chat" and "View chat"), because the discharge has already happened.
- **(owner request, fix)** Each patient now keeps their own conversation, so switching patients and coming back resumes the chat instead of restarting. Completed chats reopen read-only.
- Added `fhir_client.count` (counts matches with `_summary=count`) and `logger.conversation_cost` (prices a conversation from its token counts, including cache tokens).
- Updated `.gitignore` for Streamlit skill folders, and `SPEC.md` for the new pages.

## Phase 3: Agent and tools (`4d8e1bd`, 2026-11-01)

- Added `tools.py` with the three tools (`get_patient_context`, `book_followup`, `escalate_to_nurse`), their validation, and `run_tool`, which never raises and rejects any patient other than the conversation's own.
- Added `agent.py`: the tool-use loop, the hidden `[DISCHARGE EVENT]` first message, the end-of-conversation JSON summary, and a command-line chat that prints every tool call.
- Added `logger.py` (JSONL conversation log) and `claude_client.py` (one shared Claude client).
- **(owner request)** Added `test_gateway.py` and `ANTHROPIC_BASE_URL` to `.env.example` to check the Open WebUI gateway supports tool use before building the agent. Added `list_gateway_models.py` after the first run failed with "Model not found" (the gateway uses its own model names).
- **(owner request)** The Claude client is created in one shared place that every file uses.
- **(fix)** Seeded appointments were at 10:00 UTC, which the agent saw as 05:00 and escalated as odd. They are now 10:00 in the hospital timezone (new `HOSPITAL_TZ` constant), and re-seeding corrects existing ones.
- **(fix)** System prompt: while escalating an ibuprofen question the model said "please don't start ibuprofen on your own". Added a rule that an escalation says only that a nurse will follow up. Also defined `routine` versus `urgent`, because the ibuprofen question was marked urgent.
- **(fix)** Token counts: the gateway caches prompts automatically, so `input_tokens` was tiny. The agent now also tracks cache-write and cache-read tokens, and `config.py` gained the two cache price multipliers.
- The code corrects two summary fields from the tool log (`escalated`, and `followup` when a booking succeeded) and removes the patient's first name from the stored summary.
- Added per-patient booking limits: one upcoming booked appointment at a time.

## Phase 2: HL7 messages and parser (`bd1eab4`, 2026-11-01)

- Added `hl7_parser.py`: `parse_adt` (rejects anything that is not an inpatient ADT A03), `find_patient`, a plain-language header explaining each HL7 segment and field, and a command line.
- Added five ADT A03 messages in `hl7_messages/` and **(owner request)** one invalid ADT A01 message in `hl7_messages/invalid/` to confirm rejection.
- **(owner request)** The messages carry a DG1 diagnosis segment with the same ICD-10-CM code as the FHIR Condition, and the parser cross-checks them.
- **(owner request, fix)** Discharge time mismatch: the seed script became the single source of discharge times and now writes the HL7 files from the Encounter's stored end time, with a UTC offset (`YYYYMMDDHHMMSS+ZZZZ`). The parser checks the message time against the Encounter end within 5 minutes, reported the same way as the diagnosis check.
- `SPEC.md` updated for all of the above.

## Phase 1: FHIR server and seed data (`b613313`, 2026-11-01)

- Added `config.py` (settings and constants), `fhir_client.py` (get, search, create, conditional update, update), `seed_fhir.py`, `requirements.txt`, `.gitignore` (excludes `.env`, `.venv/`, `__pycache__/`, `data/conversations.jsonl`) and `.env.example`.
- The seed script creates five synthetic patients with an Encounter, medications and (for MRN1002 and MRN1004) an Appointment, and is idempotent: conditional update on the MRN for Patients, search-before-create for everything else.
- **(owner request)** Medications carry an RxNorm code for the exact drug, strength and form, with every code verified against NLM's RxNav service and listed for review.
- **(owner request)** Each patient has one ICD-10-CM discharge diagnosis stored as a Condition linked to the Patient and the Encounter, and referenced from `Encounter.diagnosis` with role `DD`. The agent never sees these codes.
- **(fix)** HAPI caches identical searches for about a minute, which made the second seed run create duplicates. Searches now send `Cache-Control: no-cache`.
- `SPEC.md` updated for the codes and diagnoses.

## Before Phase 1: the spec (`586c7d1`, 2026-10-31)

- Added `SPEC.md`: the build plan for the five phases.
