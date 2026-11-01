# Post-Discharge Follow-up Agent: Build Spec

## What we're building

A 1-day prototype (5 to 6 hours). An HL7 v2 ADT A03 (discharge) message triggers a Claude agent that chats by text with the discharged patient. The agent reads and writes a FHIR R4 server through three tools. A Streamlit dashboard shows KPIs and a simple ROI estimate.

Flow: HL7 ADT A03 message -> parser -> FHIR patient lookup -> Claude agent chat -> tools write to FHIR -> dashboard

All data is synthetic. No real patient data anywhere.

## Instructions for Claude Code

- Build one phase at a time. After each phase, stop, tell me exactly how to test it, and wait for me to confirm before moving on.
- Keep it simple. No auth, no message queues, no extra databases. FHIR is the system of record; one JSONL file holds conversation logs.
- Python 3.11+. Use only the dependencies listed below unless you ask first.
- Explain each new FHIR or HL7 concept in one or two plain sentences as you use it. I am using this project to learn.
- Never print or log full patient records. Log IDs, not names, wherever possible.

## Stack

- FHIR server: HAPI FHIR R4 in Docker
  - `docker run -d --name hapi -p 8080:8080 hapiproject/hapi:latest`
  - Base URL: `http://localhost:8080/fhir`
  - Fallback if Docker is unavailable: public test server `https://hapi.fhir.org/baseR4` (slower, shared, data may be reset)
- Python packages: `anthropic`, `requests`, `hl7`, `streamlit`, `pandas`, `python-dotenv`
- Claude model: read from env var `CLAUDE_MODEL`, default `claude-sonnet-5-5`
- Secrets: `ANTHROPIC_API_KEY` in `.env` (never committed; provide `.env.example`)
- Token prices: constants in `config.py`, filled in from Anthropic's pricing page

## Project structure

```
discharge-agent/
├── .env.example
├── .gitignore
├── requirements.txt
├── README.md
├── config.py            # base URL, model, price constants, tag constants
├── fhir_client.py       # thin wrapper: get, search, create, conditional update
├── seed_fhir.py         # loads 5 synthetic patients
├── hl7_messages/        # 5 sample ADT A03 files
├── hl7_parser.py        # parse ADT A03, look up patient in FHIR
├── tools.py             # the agent's 3 tools + input validation
├── agent.py             # Claude tool-use loop + end-of-chat summary
├── logger.py            # JSONL conversation log
├── app.py               # Streamlit: chat page + dashboard page
└── data/conversations.jsonl
```

## Shared conventions

- Patient identifier: system `urn:demo:mrn`, values `MRN1001` to `MRN1005`.
- Every resource the agent creates gets a `meta.tag` with system `urn:demo:source` and code `discharge-agent`. The dashboard uses this tag to count agent activity.
- All FHIR requests use `Content-Type: application/fhir+json`.
- Code systems: drugs use RxNorm (`http://www.nlm.nih.gov/research/umls/rxnorm`); diagnoses use ICD-10-CM (`http://hl7.org/fhir/sid/icd-10-cm`).
- Seeded Encounter, Condition, MedicationRequest and Appointment resources carry an identifier in system `urn:demo:seed-id` (e.g. `MRN1001-ENC`) so the seed script can find them on re-run.
- Searches send `Cache-Control: no-cache` (HAPI caches identical searches for about a minute).

---

## Phase 1: FHIR server and seed data (about 45 min)

`seed_fhir.py` creates, for each of 5 patients:

- **Patient**: identifier (MRN), name, birthDate, phone (555 numbers), address in a made-up town.
- **Encounter**: status `finished`, class `IMP` (inpatient), period start and end (end = discharge time, within the last 2 days), subject reference to the Patient.
- **MedicationRequest** (2 or 3 each): status `active`, intent `order`, `medicationCodeableConcept` with both `text` (plain name and strength, e.g. "Metoprolol 25 mg tablet") and one RxNorm `coding` (system, code, display) for the exact drug, strength and form (RxNorm "clinical drug" level, TTY `SCD`; codes verified against NLM RxNav), plus `dosageInstruction[0].text` (e.g. "Take 1 tablet by mouth twice daily").
- **Condition** (1 each): the discharge diagnosis, coded in ICD-10-CM (conditions from the CMS readmission program: heart failure, AMI, pneumonia, COPD). `subject` = Patient, `encounter` = the Encounter, category `encounter-diagnosis`, clinicalStatus `active`. The Encounter links back to it via `Encounter.diagnosis` with `use` = `DD` (discharge diagnosis, system `http://terminology.hl7.org/CodeSystem/diagnosis-role`) and `rank` 1.
- **Appointment**: only for MRN1002 and MRN1004 (they already have a follow-up booked). The others have none, so the agent can book one.

Requirements:

- Idempotent: running the script twice must not create duplicates. Use conditional update on identifier for Patient (`PUT /Patient?identifier=urn:demo:mrn|MRN1001`), and search-before-create for the other resources. If a resource already exists but differs from the seed definition (e.g. it predates the codes), update it in place; relative times (discharge time, appointment time) are kept from the first run.
- The agent never sees RxNorm or ICD-10 codes (see `get_patient_context` in Phase 3). The codes exist so the FHIR data is realistic and the ADT message can be cross-checked against it.
- Print a short table at the end: MRN, FHIR Patient ID, number of meds, has appointment, discharge diagnosis code.

Test:

- `curl "http://localhost:8080/fhir/Patient?identifier=urn:demo:mrn|MRN1001"`
- `curl "http://localhost:8080/fhir/MedicationRequest?subject=Patient/<id>"` (each has an RxNorm coding)
- `curl "http://localhost:8080/fhir/Condition?subject=Patient/<id>"` (one ICD-10-CM code)
- `curl "http://localhost:8080/fhir/Encounter?subject=Patient/<id>"` (`diagnosis[0].use` = DD)
- Resource counts after running the seed twice: 5 Patient, 5 Encounter, 5 Condition, 12 MedicationRequest, 2 Appointment.

## Phase 2: HL7 ADT A03 messages and parser (about 45 min)

Create 5 files in `hl7_messages/`, one per patient (`adt_a03_MRN1001.hl7`, etc.). HL7 v2.5 with segments MSH, EVN, PID, PV1, DG1:

- MSH-9 = `ADT^A03`, MSH-10 = unique message control ID
- PID-3 = MRN (must match the FHIR identifier), PID-5 = name, PID-7 = birth date
- PV1-2 = `I` (inpatient), PV1-45 = discharge date/time
- DG1 (diagnosis segment): DG1-1 = 1, DG1-2 = `I10` (ICD-10 coding method), DG1-3 = ICD-10-CM code (same as the seeded Condition for that patient, e.g. `I50.9^Heart failure, unspecified^I10`), DG1-6 = `F` (final diagnosis)

`hl7_parser.py`:

- `parse_adt(text) -> dict` returning `message_control_id`, `event_type`, `mrn`, `patient_name`, `discharge_time`, `diagnosis_code`.
- Normalize line endings to `\r` before parsing (the `hl7` library expects `\r` segment separators).
- Reject anything that is not ADT A03 with a clear error.
- `find_patient(mrn) -> (patient_id, encounter_id)` using FHIR search by identifier, then the most recent finished Encounter. A check (CLI and tests) confirms the DG1 code matches the code on the patient's FHIR Condition.
- CLI: `python hl7_parser.py hl7_messages/adt_a03_MRN1001.hl7` prints the parsed fields and matching FHIR IDs.

Add a short comment block at the top of the file explaining each segment and field used, in plain language.

## Phase 3: Claude agent and tools (about 2 hours)

### tools.py

Three tools. Each one validates its input, calls FHIR, returns a small JSON result, and records `{tool, input, ok, error, ms}` for the log. The agent never touches FHIR directly; it only calls these tools.

1. `get_patient_context(patient_id)`
   - Returns ONLY: first name, discharge date, list of meds (name + instruction text), upcoming appointments (date + status).
   - No address, phone, birth date, or full resources. This is the PHI minimization point.
   - Also excludes diagnosis (ICD-10) and drug (RxNorm) codes: the model gets plain-language medication names and instructions only. The agent's job is logistics, so it has no need for the diagnosis.
2. `book_followup(patient_id, date, time_of_day)`
   - `date`: ISO date, 1 to 14 days from today. `time_of_day`: `morning` or `afternoon` (map to 09:00 or 14:00, 30 min slot).
   - Creates Appointment: status `booked`, description "Post-discharge follow-up", start/end, participant actor = Patient (status `accepted`), agent tag.
   - Reject if the patient already has an upcoming booked follow-up.
3. `escalate_to_nurse(patient_id, reason, urgency)`
   - `urgency`: `routine` or `urgent`. `reason`: non-empty, max 300 characters.
   - Creates Task: status `requested`, intent `order`, priority `routine` or `urgent`, description = reason, `for` = Patient, `authoredOn` = now, agent tag.

### agent.py

- Uses the Anthropic Python SDK with tool use. Loop: send messages + tools, run any `tool_use` blocks, return `tool_result` blocks, repeat until the model stops calling tools.
- Start of conversation: the first user-role message is a system event, not shown in the UI: `[DISCHARGE EVENT] patient_id=<id>, discharged=<time>. Begin the follow-up check-in.` The agent should call `get_patient_context` first, then greet the patient.
- Track per conversation: turns, input/output tokens (from `response.usage`), latency per Claude call, tool calls.

System prompt (starting version, can be refined):

```
You are a post-discharge follow-up assistant for Demo General Hospital. You are
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
- Keep messages short and friendly. Ask one question at a time.
- Use only information from get_patient_context. Never invent appointment
  times or medications.
```

### End of conversation

When I click "End conversation", make one extra Claude call that returns JSON only:

```json
{"completed": true, "meds_confirmed": "yes|no|unclear", "followup": "booked|already_scheduled|declined|not_discussed", "escalated": false, "summary": "2-3 sentences"}
```

- `completed` = both checklist items (meds, follow-up) were covered.
- Write a Communication resource: status `completed`, subject = Patient, sent = now, `payload[0].contentString` = summary, agent tag.
- Append the full log record to `data/conversations.jsonl` (no patient names).

## Phase 4: Streamlit app (about 1 hour)

### Page 1: Discharges and chat

- List the files in `hl7_messages/` with a "Process discharge" button for each.
- On click: parse, look up the patient, start the agent. Show the parsed HL7 fields in an expander.
- Chat UI with `st.chat_message` and `st.chat_input`. I type as the patient.
- Sidebar "Behind the scenes" panel: live list of tool calls with inputs and results, so viewers can see FHIR reads and writes happening.
- "End conversation" button runs the summary step and shows the outcome.

### Page 2: Dashboard

KPI tiles:

- Discharges processed (count of log records)
- Completion rate (completed / processed)
- Follow-ups booked (Appointments with the agent tag, queried from FHIR)
- Escalation rate (conversations with escalated = true), with a routine vs urgent split from FHIR Tasks
- Average cost per conversation (tokens x price constants in `config.py`)
- Average Claude response latency
- Table of recent conversations: time, MRN, outcome fields, cost

ROI panel (inputs in a form; everything except the CMS figures is labeled as an assumption):

- Inputs:
  - Hospital name and condition (e.g. heart failure)
  - Discharges and readmissions for that condition, from the CMS Hospital Readmissions Reduction Program dataset (check the dataset's performance period and convert to annual)
  - Cost per readmission (assumption)
  - Expected relative reduction in readmissions from follow-up (assumption, default 10%)
  - Agent cost per conversation (default = measured average from the log)
- Outputs:
  - Baseline readmissions per year and readmissions avoided per year
  - Gross savings per year, agent cost per year, net savings
  - Break-even reduction % (the reduction needed for savings to equal agent cost)
- Note under the panel: "Directional estimate. HRRP penalty effects not modeled."

## Phase 5: README and demo (about 1 hour)

`README.md` sections:

1. Problem (3 to 4 sentences)
2. Architecture: Mermaid diagram of the flow
3. How to run (Docker, seed script, `streamlit run app.py`)
4. Design decisions:
   - PHI minimization: the model sees only the fields returned by `get_patient_context`
   - The model never writes to the EHR directly; validated tools do
   - Every tool call is logged (audit trail)
   - Secrets in `.env`; synthetic data only
   - Logistics-only scope; anything clinical routes to a human
5. What changes in production: BAA with the LLM vendor; ADT feed from the hospital's interface engine (e.g. Mirth) instead of files; EHR vendor FHIR APIs (Epic, Cerner) with SMART on FHIR auth; monitoring and alerting
6. Rollout plan: pilot on one discharge unit; 30/60/90 day phases with KPI gates (completion rate, follow-up booking rate, escalations reviewed by nursing) before expanding
7. Limitations and next steps (voice, multiple agents, Star Ratings use case)

Demo script (5 conversations I will run):

1. MRN1001: meds picked up, books a follow-up (happy path)
2. MRN1002: already has a follow-up, agent confirms it
3. MRN1003: has not picked up meds yet, books a follow-up
4. MRN1004: asks "Can I take this with ibuprofen?" -> routine escalation, no advice given
5. MRN1005: says they have chest pain -> 911 instruction + urgent escalation

## Definition of done

- [ ] Seed script runs twice with no duplicates
- [ ] All 5 HL7 messages parse and match a FHIR patient
- [ ] Agent books appointments and creates Tasks that are visible in FHIR via curl
- [ ] Agent gives no medical advice in demo conversations 4 and 5
- [ ] Dashboard KPIs match what is in FHIR
- [ ] ROI panel works with one real hospital's CMS numbers
- [ ] README complete and 2-minute demo recorded
