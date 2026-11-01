# Glossary

Plain-language definitions of the technical terms used in this project's documentation, in alphabetical order. Back to the [README](../README.md).

**A01.** The HL7 event code for "patient admitted". The project's invalid test message is an A01, to prove the parser accepts only discharges. See *ADT*, *A03*.

**A03.** The HL7 event code for "patient discharged". The only message type the parser accepts.

**ADT.** "Admit, Discharge, Transfer": the family of HL7 messages that announce a patient arriving, leaving or moving within a hospital.

**Agent.** An AI model that has been given tools so it can take actions, not just write text. Here, Claude with three tools. See *Tool*, *Agentic loop*.

**Agentic loop.** The repeated cycle: send the conversation to the model, run any tool it asks for, send the result back, and repeat until the model answers in plain text. Explained in [AGENT.md](AGENT.md).

**API.** Application programming interface: a way for one program to ask another to do something over the network, with a defined format for requests and replies.

**API key.** A secret password-like string that proves you may use an API. Kept in `.env`, never in code or git.

**Appointment.** The FHIR resource for a scheduled visit.

**Audit trail.** A record of what happened and who or what did it, kept so it can be reviewed later. Here, every tool call is logged with its input, success and duration.

**BAA (business associate agreement).** A contract required in the US by HIPAA before a vendor, such as an AI provider, may handle patient data on a hospital's behalf.

**Bundle.** The FHIR wrapper a search returns: a list of matching resources plus a total count.

**Cache (prompt caching).** The AI service remembering the repeated start of your requests (the system prompt, tool list and earlier messages) so it does not reprocess them each time. Cached input is cheaper to read, slightly dearer to store. See *Cache-read tokens*, *Cache-write tokens*.

**Cache-Control: no-cache.** A web request header asking the server for a fresh answer, not a stored one. The FHIR client sends it because HAPI would otherwise return stale search results for about a minute.

**Cache-read tokens / cache-write tokens.** Input tokens that were reused from the cache (read) or stored into it (write). Billed at different rates from fresh input. See *Token*.

**Cerner.** A large electronic health record vendor (now Oracle Health). Mentioned as an example of a real system a production version would connect to.

**CLI (command-line interface).** Using a program by typing commands in a terminal, for example `python agent.py ...`.

**CMS.** The Centers for Medicare & Medicaid Services, the US agency that runs Medicare. It publishes the hospital readmission data used for the statistics section.

**Communication.** The FHIR resource for a record that a message or contact took place. Here: the conversation summary.

**Component.** A piece of an HL7 field, separated from its neighbours by `^`. For example the name `Morgan^Alice` has two components.

**Condition.** The FHIR resource for a diagnosis or health problem.

**Conditional update.** A FHIR request that replaces the one resource matching a search, or creates it if none matches. Used to keep the seed script from creating duplicates.

**Container.** A self-contained, ready-to-run package of software started by Docker. The FHIR server runs in one.

**Control ID (message control ID).** A unique ID in HL7 field MSH-10 that identifies one message, so receivers can detect duplicates.

**curl.** A command-line tool that makes web requests. Used in the docs to look at FHIR directly.

**Dashboard.** A page of summary numbers and tables. Here, page 2 of the app.

**DD.** The code for "discharge diagnosis" in FHIR's diagnosis-role list, used to mark which Condition is the main diagnosis of a stay.

**Docker.** Software that runs other software in isolated containers. Used to run the FHIR server without installing it.

**Docker volume.** Storage that outlives a container. This project's FHIR container has none, so resetting it erases its data.

**.env.** A local text file of settings and secrets (API key, gateway address, model name). Ignored by git. `.env.example` is the committed template.

**EHR (electronic health record).** The hospital's computer system holding patient records. Epic and Cerner are well-known vendors.

**Encounter.** The FHIR resource for one visit or stay. Here, the hospital stay that just ended.

**Epic.** A large electronic health record vendor. Mentioned as an example of a real system.

**Escalation.** Handing something to a human. Here, the agent creating a nurse Task.

**Excess readmission ratio (ERR).** A CMS number for one hospital and one condition: the hospital's predicted readmission rate divided by the rate expected at an average hospital with similar patients. Above 1.0 means more readmissions than expected (counts toward a penalty); below 1.0 means fewer.

**Exit code.** The number a command-line program returns when it finishes: 0 usually means success, anything else means a problem.

**Field.** One numbered piece of an HL7 segment, separated by `|`. Written as the segment name and number, for example `PV1-45`.

**FHIR (Fast Healthcare Interoperability Resources).** The modern standard for representing health records as JSON and exchanging them over the web. This project uses version R4.

**Fee-for-service.** The traditional form of Medicare in which the program pays providers per service. The CMS readmission measures cover these patients.

**Function calling.** Another name for *tool use*.

**Gateway.** A web service in front of the AI model that accepts your requests, checks your key and forwards them. This project uses an Open WebUI gateway that speaks Anthropic's API.

**git.** The version control system that records the history of the code.

**HAPI FHIR.** A free, open-source FHIR server. Run here in Docker as the project's system of record.

**HIPAA.** The US law that protects patient health information and governs how it may be used and shared.

**HL7 v2.** An older text message standard that hospital systems use to announce events. Messages are lines of pipe-separated fields. This project uses version 2.5.

**HRRP (Hospital Readmissions Reduction Program).** A US Medicare program that reduces payments to hospitals whose 30-day readmission rates for certain conditions (such as heart failure) are higher than expected.

**HTTP.** The protocol web browsers and APIs use to send requests and receive replies.

**ICD-10-CM.** The US diagnosis code set (for example `I50.9` = heart failure, unspecified).

**Identifier.** A labelled ID on a FHIR resource: a *system* (which numbering scheme) and a *value*. The MRN is one.

**Idempotent.** Safe to repeat: doing it twice has the same effect as doing it once. The seed script is idempotent, so running it again creates no duplicates.

**IMP.** The code for "inpatient" in FHIR's encounter class list: the patient was admitted to the hospital.

**Inpatient.** A patient admitted to a hospital for at least one night. HL7 marks this with `I` in PV1-2.

**Interface engine.** Software (such as Mirth Connect) that receives, translates and forwards HL7 messages between hospital systems.

**ISO 8601.** The standard way to write dates and times, for example `2026-10-31T23:26:38+00:00`.

**JSON.** A text format for structured data, using braces, brackets and key-value pairs. FHIR resources and tool inputs are JSON.

**JSONL (JSON Lines).** A file with one JSON object per line. The conversation log uses this.

**JSON Schema.** A way of describing what shape a JSON object must have. The tool definitions use it to describe each tool's inputs.

**KPI (key performance indicator).** A number that shows how well something is working, such as the completion rate.

**Latency.** How long something takes to respond. Here, the time for one call to the AI model.

**LLM (large language model).** An AI model trained to read and write text, such as Claude.

**Medicare.** The US government health insurance program for people 65 and older and some younger people with disabilities.

**MedicationRequest.** The FHIR resource for a prescription order.

**Mermaid.** A text-based way to draw diagrams. GitHub turns the Mermaid blocks in these docs into pictures.

**Message (in an AI conversation).** One turn in the history sent to the model, with a role (`user` or `assistant`) and content (text or blocks).

**Mirth Connect.** A well-known interface engine for HL7 messages. Mentioned as an example of how a hospital would feed discharge messages in.

**MRN (medical record number).** A hospital's ID for a patient. Here `MRN1001` to `MRN1005`.

**Open WebUI.** A web application that can act as a gateway to AI models. This project reaches Claude through one.

**Parser.** Code that reads text in a defined format and turns it into structured data. `hl7_parser.py` parses HL7 messages.

**Patient (FHIR resource).** The FHIR record of a person receiving care.

**PHI (protected health information).** Information that identifies a patient and relates to their health or care. HIPAA protects it.

**PHI minimization.** Sharing only the smallest amount of patient information needed. The model sees only first name, discharge date, medications and appointments.

**Placeholder.** A stand-in value, such as `REPLACE_ME`, to be replaced with the real one.

**Prompt.** The text given to an AI model. See *System prompt*.

**Readmission.** A patient returning to a hospital soon after leaving, usually counted within 30 days.

**Reference (FHIR).** A link from one resource to another, written like `Patient/1000`.

**Resource (FHIR).** One kind of record in FHIR, such as Patient or Appointment, with its own web address and JSON shape.

**REST.** The style of web interface FHIR uses: each resource has an address, and you read, create, update or search it with standard web requests.

**Role (in an AI conversation).** Who a message is from: `user` (input to the model, including tool results) or `assistant` (the model).

**RxNorm / RxCUI / SCD.** RxNorm is the US National Library of Medicine's drug vocabulary. An RxCUI is one RxNorm code. SCD ("semantic clinical drug") is the level that names an exact ingredient, strength and form, which is what this project uses.

**Seed (seeding).** Loading starting data into a system. `seed_fhir.py` seeds FHIR with the five synthetic patients.

**Segment (HL7).** One line of an HL7 message, named by its first three letters: MSH, EVN, PID, PV1, DG1.

**Sequence diagram.** A diagram showing who sends what to whom, in order, over time.

**Session state.** Memory a Streamlit app keeps for one browser tab. It is cleared when the page is reloaded.

**SMART on FHIR.** The standard way for an app to sign in to a hospital's records system and get limited, per-patient access.

**SMS.** Text messaging over the phone network.

**Star Ratings.** CMS's Overall Hospital Quality Star Ratings, which include readmission measures.

**`stop_reason`.** A field on an AI model's reply saying why it stopped. `tool_use` means it is waiting for a tool result; `end_turn` means it has finished.

**Streamlit.** A Python library that turns a script into an interactive web page.

**Synthetic data.** Made-up data that looks realistic but describes no real person. All patient data here is synthetic.

**System of record.** The one system treated as the source of truth for some data. Here, FHIR.

**System prompt.** Standing instructions given to the AI model with every request, defining its role and rules.

**Tag (FHIR).** A label in a resource's `meta.tag` that you can search by. The agent tags everything it creates with `urn:demo:source|discharge-agent`.

**Task (FHIR resource).** A request for someone to do something. Here, "a nurse should follow up with this patient".

**Timeout.** How long a program waits for a reply before giving up. The Claude client waits up to 60 seconds; FHIR requests wait up to 15.

**Timezone offset.** The difference from UTC, such as `-05:00`. Times with an offset name an exact instant.

**Token.** A chunk of text (roughly three-quarters of a word) that AI models read and write. Usage is billed per token, with separate prices for input and output.

**Tool.** A named action given to an AI model. The model can ask for it, but our code runs it. See *Agent*.

**Tool call / tool use.** The model asking for a tool (a `tool_use` block), our code running it, and the output going back as a `tool_result` block.

**Tool result.** The output of a tool, sent back to the model as a `tool_result` block tied to the request by its ID.

**Transcript.** The text record of a conversation.

**URN.** A name-style identifier, such as `urn:demo:mrn`, used here as the name of a numbering scheme.

**UTC.** Coordinated Universal Time, the world's reference timezone. Times stored in FHIR here end in `Z`, meaning UTC.

**Validation.** Checking that input is acceptable before using it, for example that a date is within the allowed range.

**Virtual environment (`.venv`).** A private folder of Python packages for one project, so it does not interfere with other projects.
