# Function Reference

Every function and class in the project, grouped by file: what it is for, what goes in, the steps it takes, what comes out, what can go wrong, and a real example. Examples are real output from the running system on 2026-11-01 (synthetic data; server-assigned IDs such as `1000` differ on other machines). The same information, in short form, is in each function's docstring. New terms are defined where they first appear; see [GLOSSARY.md](GLOSSARY.md). Back to the [README](../README.md).

## Component tracker

**Tested** means a test in [VALIDATION_LOG.md](VALIDATION_LOG.md) exercises the function, directly or as part of a flow. It does not mean every branch is covered; uncovered branches are noted in each function's section. There is no automated test suite; all tests were run by hand or by script.

| File | Function | Purpose | Tested |
|------|----------|---------|--------|
| `fhir_client.py` | `FhirError` | Error for a failed FHIR request | yes |
| `fhir_client.py` | `_check` | Return JSON or raise `FhirError` | yes |
| `fhir_client.py` | `get` | Read one resource by ID | yes |
| `fhir_client.py` | `search` | Search and return a list of resources | yes |
| `fhir_client.py` | `create` | Create a resource | yes |
| `fhir_client.py` | `conditional_update` | Create-or-replace by search | yes |
| `fhir_client.py` | `update` | Replace a resource by ID | yes |
| `fhir_client.py` | `count` | Count matching resources | yes |
| `claude_client.py` | `get_client` | The one shared Claude client | yes |
| `logger.py` | `log_conversation` | Append a record to the log | yes |
| `logger.py` | `read_conversations` | Read all log records | yes |
| `logger.py` | `conversation_cost` | Price a conversation | yes |
| `tools.py` | `ToolError` | Error the model should be told about | yes |
| `tools.py` | `_patient_ref` | Validate a patient ID, build a reference | yes |
| `tools.py` | `_upcoming_booked` | Future booked appointments | yes |
| `tools.py` | `get_patient_context` | Tool 1: minimal patient facts | yes |
| `tools.py` | `book_followup` | Tool 2: book an appointment | yes |
| `tools.py` | `escalate_to_nurse` | Tool 3: create a nurse task | yes |
| `tools.py` | `write_summary` | Store the end-of-chat summary | yes |
| `tools.py` | `run_tool` | Run any tool safely, record the call | yes |
| `hl7_parser.py` | `HL7Error` | Error for bad or unmatched messages | yes |
| `hl7_parser.py` | `_field` | Read one HL7 field | yes |
| `hl7_parser.py` | `_to_iso` | HL7 timestamp to ISO 8601 | yes |
| `hl7_parser.py` | `parse_adt` | Parse a discharge message | yes |
| `hl7_parser.py` | `find_patient` | MRN to FHIR Patient and Encounter | yes |
| `hl7_parser.py` | `fhir_diagnosis_code` | ICD-10 code of an Encounter's Condition | yes |
| `hl7_parser.py` | `fhir_discharge_time` | Encounter end time | yes |
| `hl7_parser.py` | `_as_utc` | ISO string to UTC datetime | yes |
| `hl7_parser.py` | `discharge_times_match` | Compare two times within 5 minutes | yes |
| `hl7_parser.py` | `main` | Command-line parser with cross-checks | yes |
| `seed_fhir.py` | `iso` | Datetime to FHIR UTC string | yes |
| `seed_fhir.py` | `hl7_ts` | Datetime to HL7 timestamp | yes |
| `seed_fhir.py` | `write_hl7` | Write a discharge message file | yes |
| `seed_fhir.py` | `find_or_create` | Idempotent create-or-update | yes |
| `seed_fhir.py` | `seed_patient` | Seed one patient's records | yes |
| `seed_fhir.py` | `main` | Seed all patients, print a table | yes |
| `agent.py` | `Conversation.__init__` | Set up a conversation | yes |
| `agent.py` | `Conversation._call_claude` | One Claude request with counters | yes |
| `agent.py` | `Conversation._run_loop` | The agentic loop | yes |
| `agent.py` | `Conversation.start` | Begin the check-in | yes |
| `agent.py` | `Conversation.send` | Send one patient message | yes |
| `agent.py` | `Conversation._transcript` | Plain-text transcript for the summary | yes |
| `agent.py` | `Conversation.end` | Summarize, write FHIR, log | yes |
| `agent.py` | `_parse_outcome` | Validate the summary JSON | yes |
| `agent.py` | `print_tool_call` | Print a tool call to the terminal | yes |
| `agent.py` | `main` | Command-line chat | yes |
| `app.py` | `load_patients` | One row per HL7 file | yes |
| `app.py` | `status_of` | Follow-up status of a patient | yes |
| `app.py` | `start_followup` | Start and save a conversation | yes |
| `app.py` | `discharges_page` | Page 1 | yes |
| `app.py` | `pct` | Percentage formatting | yes |
| `app.py` | `fhir_counts` | Agent activity counts from FHIR | yes |
| `app.py` | `stat_value` | Format a hospital statistic | yes |
| `app.py` | `dashboard_page` | Page 2 | yes |
| `test_gateway.py` | `show_usage` | Print token usage | yes |
| `test_gateway.py` | `fail` | Print FAIL and exit | no |
| `list_gateway_models.py` | (script, no functions) | List the gateway's model names | yes |

---

## `config.py`

Constants only, no functions. Values are read from `.env` or fixed here.

| Name | Value | Meaning |
|------|-------|---------|
| `FHIR_BASE_URL` | env `FHIR_BASE_URL`, default `http://localhost:8080/fhir` | Where the FHIR server is. |
| `FHIR_HEADERS` | `Content-Type` and `Accept` of `application/fhir+json` | Sent with every FHIR request. |
| `ANTHROPIC_BASE_URL` | env | The gateway address (read here for reference; `claude_client.py` reads it directly). |
| `CLAUDE_MODEL` | env `CLAUDE_MODEL`, default `claude-sonnet-5-5` | The model name sent to the gateway. The gateway needs its own exact name (for example `anthropic.claude-sonnet-5-5`), so set it in `.env`. |
| `HOSPITAL_TZ` | `America/New_York` | Timezone for appointment times. |
| `PRICE_INPUT_PER_MTOK`, `PRICE_OUTPUT_PER_MTOK` | 2, 10 | USD per million tokens. |
| `CACHE_WRITE_MULTIPLIER`, `CACHE_READ_MULTIPLIER` | 1.25, 0.10 | Cache token price as a multiple of the input price. |
| `MRN_SYSTEM`, `SOURCE_TAG_SYSTEM`, `AGENT_TAG_CODE`, `SEED_TAG_CODE`, `SEED_ID_SYSTEM` | `urn:demo:mrn`, `urn:demo:source`, `discharge-agent`, `seed`, `urn:demo:seed-id` | Identifier and tag names (see [DATA_MODEL.md](DATA_MODEL.md)). |
| `LOG_PATH` | `data/conversations.jsonl` | The conversation log. |
| `HOSPITAL_STATS` | a dict of five values | The dashboard's hospital statistics. |

---

## `fhir_client.py`

A thin helper over FHIR's web interface. Each function makes one HTTP request with a 15-second timeout.

### `FhirError` (class)

An exception raised when the FHIR server answers with an error status (anything but 2xx). **Message:** the HTTP method, URL, status and the first 300 characters of the reply.

### `_check(resp)`

- **Purpose:** turn a response into its JSON, or raise `FhirError` if the status is not 2xx.
- **Inputs:** `resp` (`requests.Response`): the response to inspect.
- **Process:** 1. If the status is an error, raise `FhirError` with the method, URL, status code and reply text cut to 300 characters (error bodies can echo parts of a resource). 2. Otherwise return the parsed JSON, or `{}` if the body is empty.
- **Output:** `dict`.
- **Errors:** `FhirError`.
- **Example:** called by every function below. A missing resource produces:
  ```
  GET http://localhost:8080/fhir/Patient/does-not-exist -> 404: { "resourceType": "OperationOutcome", ... "diagnostics": "HAPI-2001: Resource Patient/does-not-exist is not known" ...
  ```

### `get(resource_type, resource_id)`

- **Purpose:** read one resource by its server-assigned ID (`GET /Type/id`).
- **Inputs:** `resource_type` (`str`): such as `"Patient"`. `resource_id` (`str`): such as `"1000"`.
- **Process:** 1. Request `{base}/{type}/{id}`. 2. Pass the response through `_check`.
- **Output:** the full resource as a `dict`.
- **Errors:** `FhirError` (404 if it does not exist). Network errors from `requests` (for example a refused connection) are not caught here.
- **Example:**
  ```python
  >>> sorted(get("Patient", "1000"))
  ['address', 'birthDate', 'id', 'identifier', 'meta', 'name', 'resourceType', 'telecom']
  ```

### `search(resource_type, params)`

- **Purpose:** search one resource type and return a plain list. FHIR answers a search with a *Bundle*, a wrapper holding a list of entries; this unwraps it.
- **Inputs:** `resource_type` (`str`). `params` (`dict`): search parameters, such as `{"subject": "Patient/1000", "status": "finished"}`.
- **Process:** 1. Add the header `Cache-Control: no-cache`, because HAPI caches identical searches for about a minute and would otherwise return stale answers. 2. Request `{base}/{type}` with the parameters. 3. Return the `resource` of each entry in the bundle (empty list if none).
- **Output:** `list[dict]`. Only the first page of results (HAPI's default page size).
- **Errors:** `FhirError`.
- **Example:**
  ```python
  >>> [p["id"] for p in search("Patient", {"identifier": "urn:demo:mrn|MRN1001"})]
  ['1000']
  >>> [e["id"] for e in search("Encounter", {"subject": "Patient/1000", "status": "finished"})]
  ['1001']
  ```

### `create(resource)`

- **Purpose:** create a new resource (`POST /Type`); the server assigns the ID.
- **Inputs:** `resource` (`dict`): must contain `"resourceType"`.
- **Process:** 1. POST the JSON to `{base}/{resourceType}`. 2. Return the stored resource.
- **Output:** `dict` including the new `id`.
- **Errors:** `FhirError` if the server rejects it.
- **Example:**
  ```python
  >>> create({"resourceType": "Patient", "name": [{"family": "Created"}]})["id"]
  '1045'
  ```

### `conditional_update(resource, params)`

- **Purpose:** `PUT /Type?search`. A *conditional update* replaces the one resource matching the search, or creates the resource if none matches. This is what makes seeding safe to repeat.
- **Inputs:** `resource` (`dict`). `params` (`dict`): search that identifies the existing resource, such as `{"identifier": "urn:demo:mrn|MRN1001"}`.
- **Process:** 1. PUT to `{base}/{resourceType}` with the parameters. 2. Return the stored resource.
- **Output:** `dict`.
- **Errors:** `FhirError` (for example if several resources match).
- **Example:** two calls with the same resource and search returned the same ID, `1044`, so the second call changed nothing:
  ```python
  >>> a = conditional_update(tmp, {"identifier": "urn:demo:doc-example|X1"})
  >>> b = conditional_update(tmp, {"identifier": "urn:demo:doc-example|X1"})
  >>> (a["id"], b["id"])
  ('1044', '1044')
  ```

### `update(resource)`

- **Purpose:** replace an existing resource whose ID is known (`PUT /Type/id`).
- **Inputs:** `resource` (`dict`): the full new version, containing `"resourceType"` and `"id"`.
- **Process:** 1. PUT to `{base}/{resourceType}/{id}`. 2. Return the stored resource.
- **Output:** `dict`.
- **Errors:** `FhirError`.
- **Example:**
  ```python
  >>> update({**b, "name": [{"family": "Changed"}]})["name"][0]["family"]
  'Changed'
  ```

### `count(resource_type, params)`

- **Purpose:** count matches without downloading them (`_summary=count`).
- **Inputs:** `resource_type` (`str`). `params` (`dict`).
- **Process:** 1. Add `_summary=count` and `Cache-Control: no-cache`. 2. Request the search. 3. Return the bundle's `total` (0 if absent).
- **Output:** `int`.
- **Errors:** `FhirError`.
- **Example:**
  ```python
  >>> count("Appointment", {})
  2
  >>> count("MedicationRequest", {"subject": "Patient/1000"})
  3
  ```

---

## `claude_client.py`

### `get_client()`

- **Purpose:** return the one shared Anthropic client that talks to the Claude gateway, creating it the first time.
- **Inputs:** none. Reads `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY` from the environment (loaded from `.env`).
- **Process:** 1. If a client already exists, return it. 2. Read the two settings. 3. If either is missing, or the key still starts with `your-`, raise an error. 4. Create `anthropic.Anthropic(base_url=..., api_key=..., timeout=60)`, remember it, and return it.
- **Output:** `anthropic.Anthropic`.
- **Errors:** `RuntimeError("Set ANTHROPIC_BASE_URL and ANTHROPIC_API_KEY in .env (see .env.example).")`.
- **Example:**
  ```python
  >>> client = get_client()
  >>> type(client).__name__, get_client() is client
  ('Anthropic', True)
  ```
- **Not covered by a test:** the error branch.

---

## `logger.py`

### `log_conversation(record)`

- **Purpose:** append one conversation record to the log file.
- **Inputs:** `record` (`dict`): the record built by `Conversation.end`.
- **Process:** 1. Create the `data/` folder if needed. 2. Append the record as one line of JSON.
- **Output:** `None`.
- **Errors:** file errors (`OSError`) if the folder cannot be written.
- **Example:** after logging one record, `len(read_conversations())` was `1` (tested against a temporary file so the real log was untouched).

### `read_conversations()`

- **Purpose:** read every record from the log.
- **Inputs:** none.
- **Process:** 1. If the file does not exist, return an empty list. 2. Parse each non-empty line as JSON.
- **Output:** `list[dict]`, oldest first.
- **Errors:** `json.JSONDecodeError` if a line is not valid JSON.
- **Example:**
  ```python
  >>> read_conversations()      # no file yet
  []
  ```

### `conversation_cost(record)`

- **Purpose:** the estimated USD cost of one logged conversation.
- **Inputs:** `record` (`dict`): uses `input_tokens`, `cache_write_tokens`, `cache_read_tokens`, `output_tokens`. Missing fields count as 0.
- **Process:** 1. Input-side tokens = `input_tokens + cache_write_tokens x 1.25 + cache_read_tokens x 0.10`. 2. Multiply by the input price. 3. Add output tokens x the output price. 4. Divide by 1,000,000.
- **Output:** `float`, US dollars.
- **Errors:** none for normal input.
- **Example:**
  ```python
  >>> conversation_cost({"input_tokens": 18, "cache_write_tokens": 5824,
  ...                    "cache_read_tokens": 1708, "output_tokens": 401})
  0.0189476
  >>> conversation_cost({})
  0.0
  ```

---

## `tools.py`

The agent's three tools and the safety wrapper around them. Constants: `TZ` (hospital timezone), `AGENT_TAG` (the tag on everything the agent creates), `SLOTS` (`morning` = 09:00, `afternoon` = 14:00), `TOOL_SPECS` (the tool definitions shown to the model), `_FUNCS` (name to function lookup).

### `ToolError` (class)

An exception for problems the model should be told about (bad input, a broken rule). `run_tool` catches it and passes the message to the model.

### `_patient_ref(patient_id)`

- **Purpose:** check an ID is well formed and exists, and build a FHIR reference to it.
- **Inputs:** `patient_id` (`str`): letters, digits, `-` or `.`, 1 to 64 characters.
- **Process:** 1. Check the format. 2. Read `Patient/<id>` from FHIR. 3. Return `{"reference": "Patient/<id>"}`.
- **Output:** `dict`.
- **Errors:** `ToolError("patient_id must be the patient ID from the discharge event.")` for a bad format; `ToolError("No patient with ID 99999.")` if not found.
- **Example:**
  ```python
  >>> _patient_ref("1000")
  {'reference': 'Patient/1000'}
  >>> _patient_ref("../x")
  ToolError: patient_id must be the patient ID from the discharge event.
  >>> _patient_ref("99999")
  ToolError: No patient with ID 99999.
  ```

### `_upcoming_booked(patient_id)`

- **Purpose:** the patient's booked appointments that start in the future.
- **Inputs:** `patient_id` (`str`).
- **Process:** 1. Search Appointments for this patient with status `booked`. 2. Keep those with a `start` after now. 3. Sort soonest first.
- **Output:** `list[dict]` of Appointment resources (any appointment, not only follow-ups).
- **Errors:** `FhirError`.
- **Example:**
  ```python
  >>> [a["start"] for a in _upcoming_booked("1006")]
  ['2026-11-06T15:00:00Z']
  ```

### `get_patient_context(patient_id)`

- **Purpose:** tool 1, and the **PHI minimization point**: the only patient data the model sees.
- **Inputs:** `patient_id` (`str`).
- **Process:** 1. Validate the patient (`_patient_ref`). 2. Read the Patient and take the first given name. 3. Search finished Encounters; take the latest `period.end`, convert it to a local date. 4. Search active MedicationRequests; keep the plain `text` name and the dosage instruction (not the RxNorm code). 5. List upcoming booked appointments (`_upcoming_booked`), with local date, local time and status.
- **Output:** `{"first_name", "discharge_date", "medications", "upcoming_appointments"}`. Never returned: last name, address, phone, birth date, diagnosis, any codes.
- **Errors:** `ToolError` (bad or unknown patient); `FhirError`.
- **Example:**
  ```python
  >>> get_patient_context("1006")
  {'first_name': 'Ben', 'discharge_date': '2026-10-31',
   'medications': [{'name': 'Carvedilol 6.25 mg tablet', 'instruction': 'Take 1 tablet by mouth twice daily with food'},
                   {'name': 'Spironolactone 25 mg tablet', 'instruction': 'Take 1 tablet by mouth once daily'}],
   'upcoming_appointments': [{'date': '2026-11-06', 'time': '10:00', 'status': 'booked'}]}
  ```

### `book_followup(patient_id, date, time_of_day)`

- **Purpose:** tool 2: book a 30-minute post-discharge follow-up.
- **Inputs:** `patient_id` (`str`). `date` (`str`): ISO date `YYYY-MM-DD`. `time_of_day` (`str`): `"morning"` (09:00) or `"afternoon"` (14:00).
- **Process:** 1. Validate the patient. 2. Check `time_of_day`. 3. Parse `date`. 4. Check the date is between tomorrow and 14 days from today in the hospital timezone. 5. Refuse if the patient has any upcoming booked appointment. 6. Build the start time in the hospital timezone and create an Appointment (status `booked`, 30 minutes, patient participant `accepted`, agent tag).
- **Output:** `{"appointment_id", "date", "time", "status": "booked"}`.
- **Errors (`ToolError`):** `time_of_day must be 'morning' or 'afternoon'.` / `date must be an ISO date like 2026-11-05.` / `date must be between 2026-11-02 and 2026-11-15 (1 to 14 days from today).` / `The patient already has an upcoming booked appointment; do not book another.` Also `FhirError`.
- **Example:**
  ```python
  >>> book_followup("1024", "2026-11-04", "morning")
  {'appointment_id': '1046', 'date': '2026-11-04', 'time': '09:00', 'status': 'booked'}
  >>> book_followup("1024", "2026-11-04", "afternoon")        # immediately after
  ToolError: The patient already has an upcoming booked appointment; do not book another.
  ```

### `escalate_to_nurse(patient_id, reason, urgency)`

- **Purpose:** tool 3: ask a nurse to follow up.
- **Inputs:** `patient_id` (`str`). `reason` (`str`): short, factual, not blank, at most 300 characters. `urgency` (`str`): `"routine"` or `"urgent"`.
- **Process:** 1. Validate the patient. 2. Check `urgency`, then that `reason` is a non-blank string, then its length. 3. Create a Task: status `requested`, intent `order`, priority = urgency, description = reason (trimmed), `for` = patient, `authoredOn` = now in UTC, agent tag.
- **Output:** `{"task_id", "urgency", "status": "requested"}`.
- **Errors (`ToolError`):** `urgency must be 'routine' or 'urgent'.` / `reason must be a non-empty string.` / `reason must be at most 300 characters.` Also `FhirError`.
- **Example:**
  ```python
  >>> escalate_to_nurse("1024", "Patient asked about a rash", "routine")
  {'task_id': '1047', 'urgency': 'routine', 'status': 'requested'}
  ```

### `write_summary(patient_id, summary, encounter_id=None)`

- **Purpose:** store the end-of-conversation summary as a FHIR Communication. **Not a model tool**: `Conversation.end` calls it.
- **Inputs:** `patient_id` (`str`). `summary` (`str`). `encounter_id` (`str | None`): the stay to link.
- **Process:** 1. Build a Communication (status `completed`, subject, `sent` = now in UTC, `payload[0].contentString` = summary, agent tag). 2. Add the encounter reference if given. 3. Create it.
- **Output:** the new Communication's ID (`str`).
- **Errors:** `FhirError`. It does not validate the patient ID; the caller has already checked it.
- **Example:**
  ```python
  >>> write_summary("1024", "Example summary.")
  '1048'
  ```

### `run_tool(name, tool_input, expected_patient_id)`

- **Purpose:** run one tool call the model asked for, safely, and record it. **Never raises.**
- **Inputs:** `name` (`str`): tool name. `tool_input` (`dict`): the model's input. `expected_patient_id` (`str`): this conversation's patient.
- **Process:** 1. Start a timer. 2. Reject an unknown tool name. 3. Reject if `tool_input` is not a dict or its `patient_id` differs from the conversation's. 4. Call the tool with the input as keyword arguments. 5. Translate failures: `ToolError` to its own message; wrong or missing arguments to "Invalid tool arguments."; `FhirError` to "FHIR request failed."; anything else to "Internal error." 6. Build the record.
- **Output:** `(result, record)`. `result` is the tool's output, or `{"error": message}`. `record` is `{"tool", "input", "ok", "error", "ms"}`.
- **Errors:** none raised. (Network errors that are not `FhirError` are reported as "Internal error.")
- **Example:**
  ```python
  >>> run_tool("book_followup", {"patient_id": "1024", "date": "2026-11-04", "time_of_day": "afternoon"}, "1024")
  ({'error': 'The patient already has an upcoming booked appointment; do not book another.'},
   {'tool': 'book_followup', 'input': {...}, 'ok': False,
    'error': 'The patient already has an upcoming booked appointment; do not book another.', 'ms': 34})
  >>> run_tool("get_patient_context", {"patient_id": "1006"}, "1000")      # a different patient
  ({'error': "patient_id does not match this conversation's patient."}, {... 'ok': False ...})
  ```

---

## `hl7_parser.py`

Reads HL7 v2 discharge messages. A message is lines called *segments*; each is split into numbered *fields* by `|`, and fields into *components* by `^`. The file header explains every field it uses. A segment-and-field name is written like `PV1-45` (field 45 of the PV1 segment).

### `HL7Error` (class)

Subclass of `ValueError`. Raised when a message is malformed, is not an ADT A03, or does not match a FHIR patient.

### `_field(msg, segment, index, required=True)`

- **Purpose:** read one field of a parsed message as trimmed text.
- **Inputs:** `msg` (parsed `hl7.Message`). `segment` (`str`): such as `"PV1"`. `index` (`int`): field number. `required` (`bool`).
- **Process:** 1. Look up the segment and field. 2. If the segment is absent, raise. 3. If the field index is beyond the segment's length, treat it as empty. 4. If required and empty, raise.
- **Output:** `str`.
- **Errors:** `HL7Error("Missing required segment ZZZ.")`, `HL7Error("Missing required field EVN-9.")`.
- **Example:**
  ```python
  >>> _field(msg, "MSH", 10)
  'CTRL-MRN1001-001'
  >>> _field(msg, "PV1", 45)
  '20261031232638+0000'
  ```

### `_to_iso(ts)`

- **Purpose:** convert an HL7 timestamp `YYYYMMDD[HHMM[SS]][+/-ZZZZ]` to ISO 8601.
- **Inputs:** `ts` (`str`).
- **Process:** 1. Match the pattern (8, 12 or 14 digits, optional offset). 2. Parse with the matching format. 3. Return `isoformat()`. Without an offset the result has no timezone.
- **Output:** `str`.
- **Errors:** `HL7Error("Invalid HL7 timestamp: ...")`.
- **Example:**
  ```python
  >>> _to_iso("20261031232638+0000")
  '2026-10-31T23:26:38+00:00'
  >>> _to_iso("20261031232638-0500")
  '2026-10-31T23:26:38-05:00'
  >>> _to_iso("202610312326"), _to_iso("20261031")
  ('2026-10-31T23:26:00', '2026-10-31T00:00:00')
  >>> _to_iso("2026-10-31")
  HL7Error: Invalid HL7 timestamp: '2026-10-31'.
  ```

### `parse_adt(text)`

- **Purpose:** parse an ADT^A03 discharge message into a dict.
- **Inputs:** `text` (`str`): the raw message, with any line ending.
- **Process:** 1. Trim, and convert `\r\n` and `\n` to `\r` (the HL7 library needs carriage returns). 2. Require that it starts with `MSH`. 3. Parse it. 4. Require MSH-9 to be `ADT` then `A03`. 5. Require PV1-2 to be `I` (inpatient). 6. Require a PID-3 (the MRN) and read the name from PID-5. 7. Read the discharge time from PV1-45 and the diagnosis code from DG1-3 if a DG1 segment exists.
- **Output:** `{"message_control_id", "event_type", "mrn", "patient_name", "discharge_time" (ISO 8601), "diagnosis_code" (or None)}`.
- **Errors:** `HL7Error` for each failed requirement.
- **Example:**
  ```python
  >>> parse_adt(open("hl7_messages/adt_a03_MRN1001.hl7", newline="").read())
  {'message_control_id': 'CTRL-MRN1001-001', 'event_type': 'ADT^A03', 'mrn': 'MRN1001',
   'patient_name': 'Alice Morgan', 'discharge_time': '2026-10-31T23:26:38+00:00', 'diagnosis_code': 'I50.9'}
  >>> parse_adt("garbage")
  HL7Error: Not an HL7 v2 message: it must start with an MSH segment.
  ```
- **Not covered by a test:** wrong visit class, a missing PID or PV1 segment, a missing DG1 segment.

### `find_patient(mrn)`

- **Purpose:** find the FHIR Patient for an MRN and their most recent finished Encounter.
- **Inputs:** `mrn` (`str`).
- **Process:** 1. Search Patients by `urn:demo:mrn|<mrn>`. 2. Fail if none, or if more than one. 3. Search the patient's finished Encounters. 4. Fail if none. 5. Pick the one with the latest `period.end`.
- **Output:** `(patient_id, encounter_id)`, both `str`.
- **Errors:** `HL7Error("No FHIR Patient found with MRN MRN9999.")`, `HL7Error("2 FHIR Patients share MRN ...; expected exactly one.")`, `HL7Error("Patient/<id> has no finished Encounter.")`; `FhirError`.
- **Example:**
  ```python
  >>> find_patient("MRN1001")
  ('1000', '1001')
  ```

### `fhir_diagnosis_code(encounter_id)`

- **Purpose:** the ICD-10-CM code of the Condition attached to an Encounter, to cross-check the message's DG1-3.
- **Inputs:** `encounter_id` (`str`).
- **Process:** 1. Search Conditions with `encounter=Encounter/<id>`. 2. Return the first coding in the ICD-10-CM system.
- **Output:** `str` or `None`.
- **Errors:** `FhirError`.
- **Example:** `fhir_diagnosis_code("1001")` returns `'I50.9'`.

### `fhir_discharge_time(encounter_id)`

- **Purpose:** the discharge time FHIR holds (`Encounter.period.end`).
- **Inputs:** `encounter_id` (`str`).
- **Process:** 1. Read the Encounter. 2. Return `period.end` if present.
- **Output:** `str` or `None`.
- **Errors:** `FhirError`.
- **Example:** `fhir_discharge_time("1001")` returns `'2026-10-31T23:26:38Z'`.

### `_as_utc(iso)`

- **Purpose:** turn an ISO 8601 string into a timezone-aware UTC datetime.
- **Inputs:** `iso` (`str`), with `Z` or an offset.
- **Process:** 1. Replace a trailing `Z` with `+00:00` and parse. 2. If it has a timezone, convert to UTC. 3. If it has none, assume it is already UTC.
- **Output:** `datetime` in UTC.
- **Errors:** `ValueError` for invalid text.
- **Example:**
  ```python
  >>> _as_utc("2026-10-31T18:26:38-05:00")
  datetime.datetime(2026, 10, 31, 23, 26, 38, tzinfo=datetime.timezone.utc)
  >>> _as_utc("2026-10-31T18:26:38")           # no offset: assumed UTC
  datetime.datetime(2026, 10, 31, 18, 26, 38, tzinfo=datetime.timezone.utc)
  ```

### `discharge_times_match(hl7_iso, fhir_iso, tolerance_minutes=5)`

- **Purpose:** are the message's discharge time and FHIR's within a tolerance?
- **Inputs:** `hl7_iso` (`str`). `fhir_iso` (`str | None`): `None` counts as no match. `tolerance_minutes` (`int`, default 5).
- **Process:** 1. Return False if `fhir_iso` is empty. 2. Compare the two instants in UTC. 3. True if the difference is at most the tolerance.
- **Output:** `bool`.
- **Errors:** `ValueError` for invalid time text.
- **Example:**
  ```python
  >>> discharge_times_match("2026-10-31T23:26:38+00:00", "2026-10-31T23:26:38Z")
  True
  >>> discharge_times_match("2026-10-31T23:46:38+00:00", "2026-10-31T23:26:38Z")    # 20 minutes apart
  False
  >>> discharge_times_match("2026-10-31T23:26:38+00:00", None)
  False
  ```

### `main(path)`

- **Purpose:** the command-line tool: `python hl7_parser.py <file>`.
- **Inputs:** `path` (`str`).
- **Process:** 1. Read and parse the file. 2. Find the patient and Encounter. 3. Read FHIR's diagnosis code and discharge time. 4. Print the parsed fields and FHIR values. 5. Print the diagnosis check and the discharge time check ("matches" or "DOES NOT MATCH").
- **Output:** exit code `int`: 0 if both checks pass, 1 for any error or failed check. (Running with no argument prints usage and exits 2.)
- **Errors:** every error is printed as `ERROR: ...` and returns 1. **Known gap:** an unreachable FHIR server is caught by the `OSError` clause, so the message is the raw network error, not the friendly "is the FHIR server running?" one ([VALIDATION_LOG.md](VALIDATION_LOG.md), P2.10).
- **Example:** see the output in [ARCHITECTURE.md](ARCHITECTURE.md#step-3-the-code-looks-the-patient-up-in-fhir-a-pull); in short:
  ```
  $ python hl7_parser.py hl7_messages/adt_a03_MRN1001.hl7
  ...
  Diagnosis check: DG1 matches FHIR Condition.
  Discharge time check: PV1-45 matches FHIR Encounter end (within 5 minutes).
  ```

---

## `seed_fhir.py`

Creates the five synthetic patients. Constants: `PATIENTS` (the five patient definitions: MRN, names, birth date, phone, street, hours since discharge, whether to seed an appointment, ICD-10 code and text, and medications with RxNorm codes), `TAG` (the `seed` source tag), `HL7_DIR`.

### `iso(dt)`

- **Purpose:** format a datetime as a UTC FHIR instant.
- **Inputs:** `dt` (`datetime`, timezone-aware).
- **Process:** convert to UTC and format as `YYYY-MM-DDTHH:MM:SSZ`.
- **Output:** `str`.
- **Errors:** none (a naive datetime would be treated as local time).
- **Example:**
  ```python
  >>> iso(datetime(2026, 11, 1, 12, 0, tzinfo=ZoneInfo("America/New_York")))
  '2026-11-01T17:00:00Z'
  ```

### `hl7_ts(dt)`

- **Purpose:** format a datetime as an HL7 timestamp with a UTC offset.
- **Inputs:** `dt` (`datetime`, timezone-aware).
- **Process:** convert to UTC and format as `YYYYMMDDHHMMSS+0000`.
- **Output:** `str`.
- **Example:**
  ```python
  >>> hl7_ts(datetime(2026, 11, 1, 12, 0, tzinfo=ZoneInfo("America/New_York")))
  '20261101170000+0000'
  ```

### `write_hl7(mrn, first, last, dob, icd, icd_text, discharge)`

- **Purpose:** write one patient's ADT^A03 message to `hl7_messages/adt_a03_<MRN>.hl7`.
- **Inputs:** `mrn`, `first`, `last` (`str`); `dob` (`str`, `YYYY-MM-DD`); `icd` and `icd_text` (`str`): diagnosis code and description; `discharge` (`datetime`).
- **Process:** 1. Format the timestamp. 2. Build the five segments: MSH (control ID `CTRL-<MRN>-001`), EVN, PID, PV1 (46 fields, with PV1-45 the discharge time) and DG1, all carrying the same timestamp. 3. Create the folder if needed. 4. Write the file with CRLF line endings.
- **Output:** `None`.
- **Errors:** file errors (`OSError`).
- **Example:** the file for MRN1001 is shown in full in [DATA_MODEL.md](DATA_MODEL.md#4-the-hl7-adta03-message). The first line:
  ```
  MSH|^~\&|DEMO_EHR|DEMO_GENERAL|DISCHARGE_AGENT|DEMO_GENERAL|20261031232638+0000||ADT^A03^ADT_A03|CTRL-MRN1001-001|P|2.5
  ```

### `find_or_create(resource, seed_id, keep=())`

- **Purpose:** create a resource only if it does not already exist, so re-running the seed adds nothing. If it exists but differs, update it in place.
- **Inputs:** `resource` (`dict`). `seed_id` (`str`): such as `"MRN1001-ENC"`. `keep` (`tuple`): field names never overwritten on an existing resource (times that are relative to "now").
- **Process:** 1. Set the resource's identifier to the seed ID in system `urn:demo:seed-id`. 2. Search for that identifier. 3. If none found, create it. 4. If found, compare the wanted fields (except those in `keep`, and ignoring `meta`) with the stored ones. 5. If all equal, return the stored resource. 6. Otherwise update it, merging the wanted fields over the stored ones.
- **Output:** the stored `dict`.
- **Errors:** `FhirError`.
- **Example:** run against an Encounter that already existed:
  ```python
  >>> r = find_or_create({"resourceType": "Encounter", "status": "finished"}, "MRN1001-ENC", keep=("period",))
  >>> (r["id"], r["period"]["end"], r["status"])
  ('1001', '2026-10-31T23:26:38Z', 'finished')        # same record, discharge time untouched
  ```

### `seed_patient(mrn, first, last, dob, phone, street, hours_ago, has_appt, icd, icd_text, meds)`

- **Purpose:** create or update everything for one synthetic patient.
- **Inputs:** the fields of one `PATIENTS` entry (see the constant above).
- **Process:** 1. Conditional-update the Patient on its MRN. 2. Create or find the Encounter, with discharge time `now - hours_ago` on the first run only. 3. Write the HL7 file from the Encounter's stored end time. 4. Create or find the Condition (ICD-10-CM). 5. Update the Encounter to point to the Condition as the discharge diagnosis. 6. Create or find each MedicationRequest (RxNorm code plus plain text). 7. If `has_appt`, create or find an Appointment at 10:00 hospital time five days out, correcting old seeds stored at the wrong hour.
- **Output:** the Patient's FHIR ID (`str`).
- **Errors:** `FhirError`, `OSError`.
- **Example:**
  ```python
  >>> seed_patient(*PATIENTS[0])
  '1000'                       # same ID on every run
  ```

### `main()`

- **Purpose:** seed all five patients and print a summary table.
- **Inputs:** none.
- **Process:** 1. Seed each patient. 2. Count that patient's MedicationRequests and Appointments. 3. Print a table.
- **Output:** printed table; returns `None`.
- **Errors:** `FhirError`, and network errors if the server is not up.
- **Note:** the "Has appointment" column counts **any** Appointment for the patient, including ones the agent booked in earlier conversations.
- **Example:**
  ```
  $ python seed_fhir.py
  MRN      Patient ID    Meds  Has appointment  Discharge dx (ICD-10-CM)
  MRN1001  1000          3     no               I50.9
  MRN1002  1006          2     yes              I50.22
  MRN1003  1012          3     no               I21.4
  MRN1004  1018          2     yes              J18.9
  MRN1005  1024          2     no               J44.1
  ```

---

## `agent.py`

The conversation engine. Constants: `MAX_TOOL_ROUNDS = 6`; `SYSTEM_PROMPT` and `SUMMARY_PROMPT` (see [AGENT.md](AGENT.md)).

### `Conversation` (class)

One check-in with one patient. Typical use: create it, call `start()`, call `send(text)` for each patient message, then `end()`.

#### `Conversation.__init__(parsed, patient_id, encounter_id, on_tool_call=None)`

- **Purpose:** set up an empty conversation.
- **Inputs:** `parsed` (`dict`): output of `parse_adt`. `patient_id`, `encounter_id` (`str`). `on_tool_call` (callable or `None`): called as `on_tool_call(record, result)` after each tool runs, so a UI can display it.
- **Process:** 1. Store the inputs. 2. Get the shared Claude client. 3. Zero the counters (turns, four token counts, latencies, tool calls). 4. Build the system prompt with today's date in the hospital timezone filled in.
- **Output:** a `Conversation`.
- **Errors:** `RuntimeError` if the Claude settings are missing.
- **Example:**
  ```python
  >>> c = Conversation(parsed, "1000", "1001", on_tool_call=lambda rec, res: events.append((rec, res)))
  >>> c.system.splitlines()[-1]
  "- Today's date is 2026-11-01. Appointments can be booked as morning (9:00) or afternoon (14:00)."
  ```

#### `Conversation._call_claude(**kwargs)`

- **Purpose:** make one Claude request and update the counters.
- **Inputs:** keyword arguments passed to `client.messages.create` (`system`, `tools`, `messages`). The model name comes from `CLAUDE_MODEL`; `max_tokens` is 600.
- **Process:** 1. Start a timer. 2. Make the request. 3. Record the elapsed milliseconds. 4. Add input, output, cache-write and cache-read token counts.
- **Output:** the response message.
- **Errors:** `anthropic.APIError` subclasses if the gateway or model fails (not caught here).
- **Example:** after a greeting and one reply, one conversation had `latencies_ms = [1206, 2029, 1769]` and tokens `{"in": 10, "cache_write": 2036, "cache_read": 2842, "out": 225}`.

#### `Conversation._run_loop()`

- **Purpose:** the agentic loop (explained in [AGENT.md](AGENT.md#2-the-agentic-loop-step-by-step)).
- **Inputs:** none (uses the stored messages).
- **Process:** repeat up to 6 times: 1. Call Claude with the system prompt, tools and messages. 2. Store the reply as an assistant message. 3. If it is not a tool request, return its text. 4. Otherwise run each requested tool through `run_tool`, record it, notify `on_tool_call`, and remember the first name after a successful `get_patient_context`. 5. Append the tool results as a user message.
- **Output:** the assistant's text (`str`), or the fixed line "Sorry, I'm having trouble right now. A nurse will follow up with you." after 6 rounds.
- **Errors:** `anthropic.APIError` from the Claude call.
- **Example:** after `start()` the stored message roles were `user` (text), `assistant` (tool request), `user` (tool result), `assistant` (text).
- **Not covered by a test:** the six-round fallback.

#### `Conversation.start()`

- **Purpose:** begin the check-in.
- **Inputs:** none.
- **Process:** 1. Append the hidden first message `[DISCHARGE EVENT] patient_id=<id>, discharged=<time>. Begin the follow-up check-in.` 2. Run the loop.
- **Output:** the agent's greeting (`str`).
- **Errors:** `anthropic.APIError`.
- **Example:**
  ```python
  >>> c.start()
  'Hi Alice, this is Demo General Hospital checking in after your discharge. I'm here to help with a few logistics.\nHave you been able to pick up your medications: Metoprolol 25 mg, Furosemide 40 mg, and Lisinopril 10 mg?'
  ```

#### `Conversation.send(text)`

- **Purpose:** send one patient message and get the reply.
- **Inputs:** `text` (`str`).
- **Process:** 1. Add 1 to `turns`. 2. Append the text as a user message. 3. Run the loop.
- **Output:** the agent's reply (`str`).
- **Errors:** `anthropic.APIError`.
- **Example:**
  ```python
  >>> c.send("yes I have them all")
  "Great, thanks for confirming. I don't see a follow-up appointment on your record yet. Would you like me to book one in the next 14 days? If so, what day works for you, and do you prefer morning (9:00) or afternoon (14:00)?"
  ```

#### `Conversation._transcript()`

- **Purpose:** a plain-text version of the chat for the summary call.
- **Inputs:** none.
- **Process:** 1. Skip the hidden discharge event. 2. For plain-text user messages write `PATIENT: ...`. 3. For assistant text write `ASSISTANT: ...`. 4. For tool requests write a short note (without `patient_id`) and for tool results a note cut to 300 characters.
- **Output:** `str`.
- **Example:** (lines from a real run)
  ```
  [assistant used tool get_patient_context {}]
  [tool result {"first_name": "Alice", "discharge_date": "2026-10-31", "medications": [...
  ASSISTANT: Hi Alice, this is Demo General Hospital checking in after your discharge. ...
  PATIENT: yes I have them all
  ASSISTANT: Great, thanks for confirming. ...
  ```

#### `Conversation.end()`

- **Purpose:** finish the conversation: summary, FHIR record, log line.
- **Inputs:** none.
- **Process:** 1. Ask Claude for the JSON outcome from the transcript. 2. Validate it (`_parse_outcome`). 3. Set `escalated` from the tool log, and `followup` to `booked` if a booking succeeded. 4. Replace the patient's first name in the summary with "the patient". 5. Write a Communication to FHIR (`tools.write_summary`) and notify `on_tool_call`. 6. Append the log record. 7. Return the outcome.
- **Output:** `{"completed", "meds_confirmed", "followup", "escalated", "summary"}`.
- **Errors:** `anthropic.APIError`; `FhirError` if the Communication cannot be written (then nothing is logged).
- **Example:** from the MRN1001 demo:
  ```python
  >>> c.end()
  {'completed': True, 'meds_confirmed': 'yes', 'followup': 'booked', 'escalated': False,
   'summary': 'The patient confirmed they had picked up all three of their prescribed medications. The assistant booked a follow-up appointment for the afternoon of November 2 at 2:00 PM, and the patient had no further questions. No escalation to a nurse was needed.'}
  ```

### `_parse_outcome(raw)`

- **Purpose:** turn the model's summary reply into a validated dict, with safe fallbacks.
- **Inputs:** `raw` (`str`): the model's reply, possibly with code fences or extra words.
- **Process:** 1. Find the first `{` to the last `}`. 2. Parse as JSON; if that fails return the safe default. 3. Replace an out-of-range `meds_confirmed` with `unclear` and an out-of-range `followup` with `not_discussed`. 4. Convert `completed` and `escalated` to booleans. 5. Cut `summary` to 1,000 characters, or use the default text if empty.
- **Output:** `dict`.
- **Errors:** none; it falls back to safe values instead.
- **Example:**
  ```python
  >>> _parse_outcome('{"completed": 1, "meds_confirmed": "maybe", "followup": "later", "escalated": true, "summary": "S"}')
  {'completed': True, 'meds_confirmed': 'unclear', 'followup': 'not_discussed', 'escalated': True, 'summary': 'S'}
  >>> _parse_outcome("I cannot do that")
  {'completed': False, 'meds_confirmed': 'unclear', 'followup': 'not_discussed', 'escalated': False,
   'summary': 'Summary unavailable: the model did not return valid JSON.'}
  ```

### `print_tool_call(record, result)`

- **Purpose:** show a tool call and its result in the terminal.
- **Inputs:** `record` (`dict`): `{"tool", "input", "ok", "error", "ms"}`. `result` (`dict`).
- **Process:** print a `[TOOL]` line with the name and input, then a `[RESULT]` line with `ok` or the error, the time, and the result.
- **Output:** `None` (prints).
- **Example:**
  ```
    [TOOL] book_followup {"patient_id": "1000", "date": "2026-11-02", "time_of_day": "afternoon"}
    [RESULT] ok (154 ms) {"appointment_id": "1029", "date": "2026-11-02", "time": "14:00", "status": "booked"}
  ```

### `main(path)`

- **Purpose:** the command-line chat: `python agent.py hl7_messages/<file>.hl7`.
- **Inputs:** `path` (`str`).
- **Process:** 1. Parse the file and find the patient. 2. Print the IDs and start a `Conversation` with `print_tool_call` as the hook. 3. Print the greeting. 4. Loop: read a line; `end` leaves the loop; anything else is sent and the reply printed. Ctrl+C or Ctrl+D exits without a summary and logs nothing. 5. On `end`, call `Conversation.end` and print the outcome and token totals.
- **Output:** exit code `int`: 0 normally, 1 if the file cannot be parsed or the patient is not found. (No argument: usage, exit 2.)
- **Errors:** `HL7Error` and `OSError` are reported as `ERROR: ...`. **Known gap:** like `hl7_parser.main`, an unreachable FHIR server shows the raw network error. Errors from Claude during the chat are not caught and end the program with a traceback.
- **Example:** a full real transcript is in [ARCHITECTURE.md](ARCHITECTURE.md#one-discharge-end-to-end) and [VALIDATION_LOG.md](VALIDATION_LOG.md).

---

## `app.py`

The Streamlit web app. Streamlit re-runs the whole script whenever you click or type, so the app keeps its memory (open chats, which patient is selected) in `st.session_state`, a dictionary that lasts until the browser page is reloaded. Constants: `HL7_DIR`, `AGENT_TAG` (as a search string), `NOT_FILLED` ("Not filled in yet"), `LOCAL_TZ`. At the bottom, `st.navigation` registers the two pages.

### `load_patients()`

- **Purpose:** one row per HL7 file for the patient table. Reads local files only; no FHIR call.
- **Inputs:** none.
- **Process:** 1. List `hl7_messages/*.hl7` in name order. 2. Parse each with `parse_adt`. 3. On a parse or file error, keep the row with the error text.
- **Output:** `list[dict]`, each `{"file": Path, "parsed": dict or None, "error": str or None}`.
- **Errors:** none raised.
- **Example:**
  ```python
  >>> rows = load_patients(); len(rows), rows[0]["parsed"]["mrn"], rows[0]["error"]
  (5, 'MRN1001', None)
  ```

### `status_of(mrn)`

- **Purpose:** the follow-up status shown in the table.
- **Inputs:** `mrn` (`str`).
- **Process:** 1. No saved conversation: "Not contacted". 2. A conversation with an outcome: "Completed". 3. Otherwise "In progress".
- **Output:** `str`.
- **Example:** in the UI test, MRN1003 was "Not contacted", became "In progress" as soon as Start follow-up was clicked, and became "Completed" after End conversation.

### `start_followup(mrn, parsed)`

- **Purpose:** look the patient up, start the agent, and save the conversation under the MRN.
- **Inputs:** `mrn` (`str`). `parsed` (`dict`).
- **Process:** 1. `find_patient`; on failure show an error and stop. 2. Create a `Conversation` whose tool-call hook appends to a list kept for the sidebar. 3. Call `start()` under a spinner; on failure show an error and stop. 4. Save the conversation, the greeting, the tool-call list and the IDs in `st.session_state["patients"][mrn]`.
- **Output:** `None` (saves state or shows an error).
- **Errors:** shown in the page, not raised.
- **Example:** clicking Start follow-up on MRN1003 saved a conversation with one greeting message, and the sidebar showed `OK · get_patient_context · 101 ms`.
- **Not covered by a test:** the two failure branches.

### `discharges_page()`

- **Purpose:** page 1.
- **Inputs:** none (reads session state).
- **Process:** 1. Set up session state. 2. Parse all HL7 files. 3. If a start was requested, start that patient's conversation now (so the table shows current statuses). 4. Draw the table: MRN, patient, discharge time (hospital time), status and one button each. A click selects the patient and, if new, asks for a start, then re-runs. 5. For the selected patient, draw the parsed-fields expander and the saved chat. 6. Handle a new chat message. 7. Show End conversation (or, for a completed chat, the outcome tiles, summary and "Start a new follow-up with this patient"). 8. Draw the Behind the scenes sidebar with each tool call.
- **Output:** `None` (draws the page).
- **Errors:** shown in the page.
- **Example:** results of driving it in the UI test: 5 rows with "Start follow-up"; after one chat "Resume chat"; after ending "View chat"; reopening a completed chat gave a disabled chat box.

### `pct(n, d)`

- **Purpose:** format a fraction as a whole-number percentage.
- **Inputs:** `n` (`int`), `d` (`int`).
- **Process:** if `d` is 0 return `"n/a"`, otherwise `n / d` formatted as a whole percentage.
- **Output:** `str`.
- **Example:**
  ```python
  >>> pct(6, 7), pct(0, 0)
  ('86%', 'n/a')
  ```

### `fhir_counts()`

- **Purpose:** the agent's activity as stored in FHIR.
- **Inputs:** none.
- **Process:** count Appointments tagged `urn:demo:source|discharge-agent`, and Tasks with that tag and priority `routine`, and with priority `urgent`. If any call fails, return `None`.
- **Output:** `{"appointments", "tasks_routine", "tasks_urgent"}` or `None`.
- **Example:**
  ```python
  >>> fhir_counts()
  {'appointments': 0, 'tasks_routine': 0, 'tasks_urgent': 0}      # on a freshly cleaned server
  ```
- **Not covered by a test:** the `None` branch.

### `stat_value(key)`

- **Purpose:** format one hospital statistic for display.
- **Inputs:** `key` (`str`): a key of `HOSPITAL_STATS`.
- **Process:** 1. Look up the value. 2. If it is `None`, empty or `"REPLACE_ME"`, return "Not filled in yet". 3. If it is a number, format with thousands separators. 4. Otherwise return it as text.
- **Output:** `str`.
- **Example:**
  ```python
  >>> stat_value("hospital_name"), stat_value("annual_discharges")
  ('WellSpan York Hospital', '334')
  >>> # with annual_readmissions set to None:
  >>> stat_value("annual_readmissions")
  'Not filled in yet'
  ```

### `dashboard_page()`

- **Purpose:** page 2: the KPI tiles, recent conversations and hospital statistics.
- **Inputs:** none.
- **Process:** 1. Read the log and the FHIR counts. 2. Compute and show each tile ([KPIS.md](KPIS.md) has every formula). 3. Show the 20 most recent conversations, newest first. 4. Show the "Statistics from this hospital" table.
- **Output:** `None` (draws the page).
- **Errors:** a warning if FHIR cannot be read; FHIR tiles show `n/a`.
- **Example:** real tiles from the test: `Discharges processed (log) 7`, `Completion rate (log) 86%`, `Follow-ups booked (FHIR) 1`, `Escalation rate (log) 43%`, `Escalations: routine / urgent (FHIR) 1 / 0`, `Avg cost per conversation (log) $0.0196`, `Avg Claude response latency (log) 1.7 s`.

---

## `test_gateway.py`

A script (runs when called, not a library). Reads the three settings, then runs two tests: the model asks for a fake `get_weather` tool, then answers after being sent the tool result. See [VALIDATION_LOG.md](VALIDATION_LOG.md) P3.1.

### `show_usage(label, response)`

- **Purpose:** print the token counts of one response.
- **Inputs:** `label` (`str`): such as `"test 1"`. `response`: an Anthropic message.
- **Process:** print `usage (<label>): input_tokens=..., output_tokens=...`.
- **Output:** `None` (prints).
- **Example:**
  ```
    usage (test 1): input_tokens=391, output_tokens=50
  ```

### `fail(msg)`

- **Purpose:** report a failed check and stop.
- **Inputs:** `msg` (`str`): why it failed.
- **Process:** print `FAIL: <msg>` and exit with status 1.
- **Output:** never returns.
- **Tested:** no, because every run passed, so the function never ran.

## `list_gateway_models.py`

A script with no functions. Reads `ANTHROPIC_BASE_URL` and `ANTHROPIC_API_KEY`, asks the gateway for its model list (first in Anthropic style, then in OpenAI style), and prints the model IDs, Claude ones first. It never prints the key. Real output (abridged):

```
(listed via gateway)

50 models available. Claude models:
   anthropic.claude-fable-5
   anthropic.claude-haiku-4-5-20251001
   anthropic.claude-haiku-5-5
   ...
```
