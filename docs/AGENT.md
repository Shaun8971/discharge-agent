# The Agent

How the AI agent works: the loop that moves messages between our code and the model, the instructions it is given, the three tools it can use, and what is recorded. Terms are defined where they first appear; see [GLOSSARY.md](GLOSSARY.md). Back to the [README](../README.md). The code is in `agent.py` and `tools.py`.

## 1. What "agent" means here

A *large language model* (LLM) such as Claude reads text and writes text. On its own it cannot look anything up or change anything. An *agent* is an LLM that has been given **tools**: named actions it can ask for. The model never runs a tool itself. It replies "I would like to run tool X with these inputs", our code decides whether to run it, runs it, and hands back the result. That arrangement is called **tool use** (or function calling), and the whole back-and-forth is the **agentic loop**.

In this project the model can ask for only three tools (section 3). Everything else it does is write text to the patient.

## 2. The agentic loop, step by step

The conversation is a list of *messages*. Each message has a *role*: `user` (input to the model, which includes tool results) or `assistant` (what the model said). Content is either plain text or a list of typed *blocks*:

| Block | Who creates it | Meaning |
|-------|----------------|---------|
| `text` | model | Words for the patient. |
| `tool_use` | model | "Please run tool `name` with this `input`." It carries a unique `id`. |
| `tool_result` | our code | The tool's output, tied to the request by `tool_use_id`. |

Every call also carries the **system prompt** (fixed instructions, section 4) and the **tool definitions** (the names, descriptions and input shapes of the three tools). A model response also has a `stop_reason`: `tool_use` means "I am waiting for a tool result", and `end_turn` means "I am done, here is my text".

### Starting a conversation (`Conversation.start`)

1. The code adds one hidden user message. The patient never sees it:
   ```
   [DISCHARGE EVENT] patient_id=1000, discharged=2026-10-31T23:26:38+00:00. Begin the follow-up check-in.
   ```
2. It runs the loop (below).

### The loop (`Conversation._run_loop`)

Repeat, at most 6 times (`MAX_TOOL_ROUNDS`) for each patient message:

1. **Call Claude** with the system prompt, the tool definitions and the full message list. Record how long it took and how many tokens it used.
2. **Save the reply** as an `assistant` message (its text and any tool requests).
3. **If `stop_reason` is not `tool_use`:** the model has finished its turn. Return its text. Done.
4. **Otherwise** run every `tool_use` block through `tools.run_tool`. For each one: store the call record, call the optional UI hook (so the sidebar or terminal can show it), and, if it was `get_patient_context` and succeeded, remember the first name in memory (used later only to scrub the summary).
5. **Send the results back** as one `user` message made of `tool_result` blocks (each marked `is_error` if the tool failed), then go to step 1.

If six rounds pass without a plain answer, the loop returns a fixed line: "Sorry, I'm having trouble right now. A nurse will follow up with you."

### What the messages look like

The first turn of the MRN1001 demo produced these messages (roles and block types, taken from a real run):

```
1. user       "[DISCHARGE EVENT] patient_id=1000, discharged=... Begin the follow-up check-in."
2. assistant  [tool_use  get_patient_context {"patient_id": "1000"}]
3. user       [tool_result  {"first_name": "Alice", "discharge_date": "2026-10-31", "medications": [...], ...}]
4. assistant  [text  "Hi Alice, this is Demo General Hospital checking in ..."]
```

Then the patient types "yes I have them all" (message 5, `user`, plain text), and the model answers (message 6) with text. When the model needs a tool, an extra `assistant` tool request and a `user` tool result sit in between, just like messages 2 and 3. A single patient message can therefore cost more than one Claude call. The complete MRN1001 demo (3 patient messages, one booking, one summary) used **7 Claude calls**: 2 to start, 1 for the first reply, 2 for the booking, 1 for the closing reply, and 1 for the summary.

### Counting turns, tokens and time

Each `Conversation` tracks:

- `turns`: patient messages sent (the hidden discharge event does not count).
- `latencies_ms`: seconds of waiting, one number per Claude call.
- Four token counts. A *token* is a chunk of text, roughly three-quarters of a word, and is the unit AI usage is billed in. The gateway caches the repeated start of each prompt automatically, so there are three input counts: `input_tokens` (new, uncached), `cache_write_tokens` (stored for reuse) and `cache_read_tokens` (reused at a discount), plus `output_tokens` (what the model wrote). Cost needs all four ([KPIS.md](KPIS.md)).
- `tool_calls`: the list of tool call records.

## 3. The three tools

All tools live in `tools.py`. **Every tool call goes through `run_tool(name, input, expected_patient_id)`**, which:

1. rejects an unknown tool name;
2. rejects any `patient_id` other than the conversation's own (so the model can never read or write a different patient);
3. calls the tool and catches problems: a broken rule becomes an error message the model can read; a missing or extra argument becomes "Invalid tool arguments."; a FHIR failure becomes "FHIR request failed."; anything unexpected becomes "Internal error.";
4. returns the result and a record `{tool, input, ok, error, ms}`.

`run_tool` never raises, so a bad tool call cannot crash a conversation. The model sees the error and can adjust.

Every tool first checks the patient ID is well formed (letters, digits, `-` or `.`, up to 64 characters) and that the patient exists.

### 3.1 `get_patient_context`

| | |
|---|---|
| **Purpose** | Give the model the minimum it needs to run the check-in. This is the **PHI minimization point**: the only patient data the model ever sees. |
| **Input** | `patient_id` (string, required) |
| **Validation** | Well-formed, existing patient ID. |
| **FHIR reads** | `Patient/<id>` (existence and first name); `Encounter` for the patient with status `finished` (latest `period.end`, converted to a local date); `MedicationRequest` for the patient with status `active` (name from `medicationCodeableConcept.text`, instruction from `dosageInstruction[0].text`); `Appointment` for the patient with status `booked`, keeping only those that start in the future. |
| **FHIR writes** | None. |
| **Returns** | `first_name`, `discharge_date`, `medications` (name and instruction), `upcoming_appointments` (date, local time, status). |
| **Never returned** | Last name, address, phone, birth date, diagnosis, RxNorm or ICD-10 codes, any full FHIR resource. |

Real request and result (MRN1002, who has a seeded appointment):

```
get_patient_context {"patient_id": "1006"}
```
```json
{"first_name": "Ben", "discharge_date": "2026-10-31",
 "medications": [
   {"name": "Carvedilol 6.25 mg tablet", "instruction": "Take 1 tablet by mouth twice daily with food"},
   {"name": "Spironolactone 25 mg tablet", "instruction": "Take 1 tablet by mouth once daily"}],
 "upcoming_appointments": [{"date": "2026-11-06", "time": "10:00", "status": "booked"}]}
```

### 3.2 `book_followup`

| | |
|---|---|
| **Purpose** | Book a 30-minute post-discharge follow-up. |
| **Input** | `patient_id` (string); `date` (string, ISO date `YYYY-MM-DD`); `time_of_day` (`"morning"` or `"afternoon"`). All required. |
| **Validation** | `time_of_day` must be `morning` (09:00) or `afternoon` (14:00), in the hospital's timezone (America/New_York). `date` must parse as a date and fall between tomorrow and 14 days from today. The patient must have no other *upcoming booked* Appointment (any appointment, not only follow-ups). |
| **FHIR reads** | `Patient/<id>`; `Appointment` search for the patient's booked appointments. |
| **FHIR writes** | One `Appointment`: status `booked`, description "Post-discharge follow-up", `start` and `end` (30 minutes) with a timezone offset, the patient as a participant with status `accepted`, and the tag `urn:demo:source|discharge-agent`. |
| **Returns** | `appointment_id`, `date`, `time`, `status`. |

Real request and result:

```
book_followup {"patient_id": "1000", "date": "2026-11-02", "time_of_day": "afternoon"}
```
```json
{"appointment_id": "1029", "date": "2026-11-02", "time": "14:00", "status": "booked"}
```

Real rejection (a second booking for the same patient). The model receives this as an error result:

```json
{"error": "The patient already has an upcoming booked appointment; do not book another."}
```

The other messages: "date must be between 2026-11-02 and 2026-11-15 (1 to 14 days from today).", "date must be an ISO date like 2026-11-05.", "time_of_day must be 'morning' or 'afternoon'."

### 3.3 `escalate_to_nurse`

| | |
|---|---|
| **Purpose** | Ask a nurse to follow up. The model's route for anything it should not handle itself. |
| **Input** | `patient_id` (string); `reason` (string, a short factual note); `urgency` (`"routine"` or `"urgent"`). All required. |
| **Validation** | `urgency` is one of the two values. `reason` is not empty or just spaces and is at most 300 characters. |
| **FHIR reads** | `Patient/<id>`. |
| **FHIR writes** | One `Task`: status `requested`, intent `order`, priority equal to the urgency, `description` equal to the reason, `for` the patient, `authoredOn` now (UTC), and the agent tag. |
| **Returns** | `task_id`, `urgency`, `status`. |

Real request and result:

```
escalate_to_nurse {"patient_id": "1012", "reason": "Patient asked about a rash", "urgency": "routine"}
```
```json
{"task_id": "1038", "urgency": "routine", "status": "requested"}
```

A real urgent Task as stored in FHIR (from the chest pain demo, MRN1005) is shown in [DATA_MODEL.md](DATA_MODEL.md).

### A tool that is not exposed to the model: `write_summary`

`tools.write_summary` creates the end-of-conversation `Communication`. It is **not** in the tool list the model receives. Only `Conversation.end` calls it, once.

## 4. The system prompt, section by section

The system prompt is the standing instruction Claude receives with every call. It lives in `agent.py` as `SYSTEM_PROMPT`. Each part, and the reason it exists:

> **You are a post-discharge follow-up assistant for Demo General Hospital. You are chatting by text with a patient who went home in the last two days.**

*Why:* sets the role, the setting and the tone. "In the last two days" keeps the check-in about recent discharge.

> **Your job is logistics only:**
> 1. Confirm they have picked up their medications. Read the names from the patient context. Do not explain what the medications are for.
> 2. Make sure they have a follow-up appointment. If none exists, offer to book one within the next 14 days.
> 3. Ask if they have any other questions.

*Why:* a short, checkable list. These two checklist items are exactly what the summary later judges "completed" against. "Do not explain what the medications are for" prevents the model drifting into medical education. "Within the next 14 days" matches the tool's limit.

> **Never give medical advice, diagnose, interpret symptoms, or suggest changing a medication or dose.**

*Why:* the core safety rule. The agent is not a clinician and has no clinical oversight.

> **If the patient mentions any symptom, side effect, or medical question, call escalate_to_nurse with a short factual reason and tell them a nurse will follow up.**

*Why:* gives the model a safe action instead of leaving it to improvise an answer. "Short factual reason" keeps the nurse's task note useful and brief.

> **If the patient describes something that sounds like an emergency, tell them to call 911 now, and call escalate_to_nurse with urgency "urgent".**

*Why:* an emergency cannot wait for a nurse's queue. This is the only case where the agent may tell a patient to do something.

> **If the patient is confused or you are unsure, escalate with urgency "routine".**

*Why:* when the model is out of its depth, handing over to a human is the safe default.

> **When you escalate, say only that a nurse will follow up. Do not tell the patient to take, avoid, stop, wait on, or change any medication or activity (the only exception is telling them to call 911 in an emergency).**

*Why:* added after a test in which the model, while escalating a question about ibuprofen, told the patient "please don't start ibuprofen on your own". That is advice. This rule closes the gap.

> **Use urgency "routine" for medication questions, side effects, mild symptoms, confusion, and anything else a nurse can handle during the day. Use "urgent" only for an emergency (the 911 case).**

*Why:* also added after testing, when the ibuprofen question was marked `urgent`. Without a definition, the two levels drift. Keeping `urgent` for emergencies keeps the urgent queue meaningful.

> **Keep messages short and friendly. Ask one question at a time.**

*Why:* people reading a text message answer one short question better than a long list.

> **Use only information from get_patient_context. Never invent appointment times or medications.**

*Why:* stops the model making things up. It can only talk about the medications and appointments the tool returned.

> **Practical notes:** pass the `patient_id` from the discharge event to every tool call; today's date is *(filled in by the code)*; appointments can be booked as morning (9:00) or afternoon (14:00).

*Why:* the model does not know today's date, and it needs the date to turn "tomorrow" into `2026-11-02`. The ID note keeps tool calls pointing at the right patient. These notes are not part of the original spec; the code adds them.

A caution: a prompt is guidance, not a guarantee. The code enforces some rules itself (the patient-ID check, date and urgency validation) but cannot, for example, verify that the model said "call 911". That is why the rollout plan in the [README](../README.md#rollout-plan) has nurses review conversations.

## 5. Escalation rules in one place

| Patient says | Agent should | Tool call | Observed in testing |
|--------------|--------------|-----------|---------------------|
| A medication question ("Can I take this with ibuprofen?") | Say a nurse will follow up. No advice. | `escalate_to_nurse` with `urgency: "routine"` | Routine task created; reply: "I can't answer medication questions ... I've asked a nurse to follow up with you." |
| A mild symptom or side effect | Same as above | `escalate_to_nurse`, `routine` | Not specifically tested |
| Something that sounds like an emergency ("chest pain and my left arm feels numb") | Tell them to call 911 now | `escalate_to_nurse` with `urgency: "urgent"` | Urgent task created; reply: "could be an emergency. Please call 911 now." |
| Confusion, or the agent is unsure | Escalate | `escalate_to_nurse`, `routine` | Not specifically tested |
| Has not picked up medications | Note it (a logistics matter) | Model's choice. It sometimes escalates, sometimes just records it | Varied between runs |

An escalation creates a `Task` in FHIR that a nurse would work from. This prototype has no nurse screen; you can see tasks with `curl` (see [VALIDATION_LOG.md](VALIDATION_LOG.md)).

## 6. The end-of-conversation summary

Triggered by typing `end` in the CLI or clicking **End conversation** in the app (`Conversation.end`).

1. **Build a plain transcript.** The chat is turned into lines like `PATIENT: ...` and `ASSISTANT: ...`, with tool calls shown briefly and `patient_id` removed. The hidden discharge event is skipped. A plain-text transcript is used because the conversation's tool blocks would require passing the tool list again.
2. **Ask Claude for JSON only**, using a separate `SUMMARY_PROMPT`. The expected shape:
   ```json
   {"completed": true, "meds_confirmed": "yes|no|unclear",
    "followup": "booked|already_scheduled|declined|not_discussed",
    "escalated": false, "summary": "2-3 sentences"}
   ```
   The prompt defines `completed` as "both the medication check and the follow-up were covered" and asks the model never to include a patient name.
3. **Parse and validate** (`_parse_outcome`). It finds the JSON object even if the model wraps it in code fences or extra words, replaces an out-of-range `meds_confirmed` with `unclear` and an out-of-range `followup` with `not_discussed`, and cuts the summary at 1,000 characters. If no JSON is found it uses safe values (not completed, `unclear`, `not_discussed`, "Summary unavailable").
4. **Correct two fields from facts.** The model's guess is overridden by the tool log: `escalated` is true only if `escalate_to_nurse` succeeded, and `followup` becomes `booked` if `book_followup` succeeded. The model is not trusted for things the code knows.
5. **Scrub the first name.** If the summary contains the patient's first name, it is replaced with "the patient". (The last name was never given to the model.)
6. **Write a `Communication` to FHIR** (status `completed`, the patient, the encounter, now, the summary as `payload[0].contentString`, agent tag).
7. **Append the log record** (next section) and return the outcome.

## 7. What gets logged

One JSON line is appended to `data/conversations.jsonl` per **finished** conversation. Closing the window or pressing Ctrl+C before `end` logs nothing. Example values from real runs:

| Field | Example | Meaning |
|-------|---------|---------|
| `started`, `ended` | `2026-11-01T19:00:24+00:00` | UTC timestamps. |
| `message_control_id` | `CTRL-MRN1001-001` | The HL7 message that triggered it. |
| `mrn`, `patient_id`, `encounter_id`, `communication_id` | `MRN1001`, `1000`, `1001`, `1030` | Identifiers, not names. |
| `model` | `anthropic.claude-sonnet-5-5` | Model name the gateway used. |
| `turns` | `3` | Patient messages. |
| `input_tokens`, `cache_write_tokens`, `cache_read_tokens`, `output_tokens` | `24`, `6086`, `5717`, `551` | Usage, for cost. |
| `claude_calls`, `latencies_ms`, `avg_latency_ms` | `7`, `[...]`, `...` | How many model calls and how long each took. |
| `tool_calls` | `[{"tool": "get_patient_context", "input": {...}, "ok": true, "error": null, "ms": 150}, ...]` | The audit trail: every tool call with its input, success, error and duration. |
| `outcome` | `{"completed": true, "meds_confirmed": "yes", ...}` | The validated outcome JSON, including the summary. |

**Deliberately not logged:** the chat transcript, the patient's name, and the tool *results* (which would repeat medication lists). **Be aware:** the tool call `input` includes the `reason` text the agent wrote for a nurse. That can describe a symptom (for example "chest pain and left arm numbness"), though it contains no name. The same text is stored in the FHIR Task. Treat the log as sensitive.

The file is in `.gitignore`, so it is never committed.
