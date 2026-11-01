# Dashboard KPIs

A KPI (key performance indicator) is a number that tells you how well something is working. This document defines every number on the dashboard page of the app: what it means, the exact formula, and where the data comes from. Back to the [README](../README.md). Code: `dashboard_page`, `fhir_counts` and `stat_value` in `app.py`; `read_conversations` and `conversation_cost` in `logger.py`.

## Two data sources

| Source | What it is | Strengths and weaknesses |
|--------|-----------|--------------------------|
| **The log** | `data/conversations.jsonl`: one JSON line per conversation that was ended with **End conversation** (or `end` in the CLI). Details in [AGENT.md](AGENT.md#7-what-gets-logged). | Holds outcomes, tokens and timing. Only conversations that were ended appear. It is a local file, so it is not reset when FHIR is reset. |
| **FHIR** | The live FHIR server. The dashboard counts resources tagged `urn:demo:source\|discharge-agent`, which only the agent creates (seeded data is tagged `seed`). | The authoritative record of what the agent actually did. Includes records from conversations that were never ended, and loses everything if the server is reset. |

Each tile on the dashboard is labelled **(log)** or **(FHIR)**. Because the two sources are independent, they can disagree (see "When the numbers differ" at the end).

The dashboard has a **Refresh** button that re-reads both sources. If FHIR cannot be reached, the FHIR tiles show `n/a` and a warning appears.

## The tiles

In the examples below, "the sample" is a real dashboard state with **7 logged conversations** and a FHIR server holding **1 agent appointment and 1 routine task**.

### 1. Discharges processed (log)

- **Definition:** how many conversations have been completed and logged.
- **Formula:** `n = number of records in the log`.
- **Source:** log.
- **Caveats:** despite the name, this is not the number of HL7 messages received. It counts *finished follow-up conversations*. A conversation that is never ended is not counted, and following up twice with the same patient counts twice.
- **Sample:** `7`.

### 2. Completion rate (log)

- **Definition:** the share of conversations in which both checklist items were covered: the medication check and the follow-up appointment.
- **Formula:** `completed / n`, where `completed` is the number of records whose `outcome.completed` is true. Shown as a whole-number percentage; `n/a` if `n` is 0.
- **Source:** log. The `completed` value comes from the end-of-conversation summary the model produced ([AGENT.md](AGENT.md#6-the-end-of-conversation-summary)), so it reflects the model's judgment of "both items covered".
- **Sample:** `6 / 7 = 86%`.

### 3. Follow-ups booked (FHIR)

- **Definition:** how many follow-up appointments the agent has booked.
- **Formula:** `count of Appointment resources with tag urn:demo:source|discharge-agent` (a FHIR search with `_summary=count`).
- **Source:** FHIR.
- **Caveats:** counts appointments of any status and any date. It does not count the two seeded appointments, which carry the `seed` tag. A conversation that booked an appointment but was never ended is counted here and not in the log.
- **Sample:** `1`.

### 4. Escalation rate (log)

- **Definition:** the share of conversations in which the agent escalated to a nurse.
- **Formula:** `escalated / n`, where `escalated` is the number of records whose `outcome.escalated` is true. Percentage; `n/a` if `n` is 0.
- **Source:** log. This flag is not the model's opinion: the code sets it true only if an `escalate_to_nurse` call actually succeeded ([AGENT.md](AGENT.md#6-the-end-of-conversation-summary), step 4).
- **Sample:** `3 / 7 = 43%`.

### 5. Escalations: routine / urgent (FHIR)

- **Definition:** how many nurse Tasks the agent created, split by priority.
- **Formula:** `routine = count of Task with the agent tag and priority=routine`; `urgent = count of Task with the agent tag and priority=urgent`. Shown as `routine / urgent`.
- **Source:** FHIR.
- **Caveats:** one conversation can create several Tasks, so these counts can exceed the number of escalated conversations.
- **Sample:** `1 / 0`.

### 6. Average cost per conversation (log)

- **Definition:** the average estimated price of the AI usage for one conversation.
- **Formula, per conversation:**

  ```
  cost = ( (input_tokens
            + cache_write_tokens x 1.25
            + cache_read_tokens  x 0.10) x PRICE_INPUT_PER_MTOK
           + output_tokens x PRICE_OUTPUT_PER_MTOK ) / 1,000,000
  ```

  The tile shows the mean: `sum of cost over all records / n`, formatted to four decimal places, or `n/a` if `n` is 0.
- **Source:** log (token counts) and `config.py` (prices).
- **Inputs explained:** a *token* is a chunk of text, about three-quarters of a word, and AI usage is billed per token, with prices quoted per million tokens. The gateway automatically *caches* the repeated start of each prompt, which splits input into three kinds: fresh input, cache writes (billed at 1.25 times the input price) and cache reads (billed at 0.10 times). Output is billed at its own, higher price. The multipliers `CACHE_WRITE_MULTIPLIER` and `CACHE_READ_MULTIPLIER` are Anthropic's standard figures but are assumptions in this project: verify them, and the prices, against your provider.
- **Current prices in `config.py`:** $2 per million input tokens, $10 per million output tokens (set by the project owner).
- **Worked example (the MRN1001 demo):** 24 fresh input, 6,086 cache write, 5,717 cache read, 551 output. Input side: 24 + 6,086 x 1.25 + 5,717 x 0.10 = 24 + 7,607.5 + 571.7 = 8,203.2 token-equivalents, times $2 per million = $0.016406. Output: 551 x $10 per million = $0.00551. Total **$0.0219**.
- **Sample:** `$0.0196` (average over 7).
- **Caveat:** the dashboard counts every Claude call in the conversation, including the summary call, because the counters accumulate across all of them.

### 7. Avg Claude response latency (log)

- **Definition:** how long, on average, one call to the model takes to return.
- **Formula:** `sum of all latencies_ms / number of Claude calls`, over every call in every logged conversation, shown in seconds with one decimal. `n/a` if there are none.
- **Source:** log. Each record stores one latency per Claude call, measured around the request in `Conversation._call_claude`.
- **Caveats:** it is the mean over *calls*, not over conversations, so a conversation with more calls weighs more. It is the model call only; the time to run FHIR tools is not included (those take roughly 25 to 500 milliseconds and are in each `tool_calls` record).
- **Sample:** `1.7 s`.

### 8. Recent conversations (table)

- **Definition:** the 20 most recent logged conversations, newest first.
- **Columns:** *Time* (when it ended, shown in your computer's local timezone), *MRN*, *Completed*, *Meds confirmed*, *Follow-up*, *Escalated*, and *Cost (USD)* for that conversation (the same cost formula, rounded to four decimals).
- **Source:** log.

## Statistics from this hospital (not a KPI)

The last section of the page shows five values copied from the `HOSPITAL_STATS` block in `config.py`: hospital name, condition, annual discharges, annual readmissions, and source. **Nothing is calculated.** A value left as a placeholder (`None` or `"REPLACE_ME"`) is shown as "Not filled in yet". Numbers get thousands separators.

As configured: WellSpan York Hospital, heart failure, 334 discharges and 56 readmissions per year, from the CMS Hospital Readmissions Reduction Program, Medicare patients, July 2021 to June 2024, averaged per year. How those were derived, and what they mean, is explained in the [README](../README.md#statistics-from-this-hospital).

## When the numbers differ

- **FHIR was reset but the log was not** (or the reverse): the log may show conversations whose appointments and tasks no longer exist in FHIR. After a reset, delete `data/conversations.jsonl` too for a clean dashboard.
- **A conversation was not ended:** the appointment or task exists in FHIR (counted by the FHIR tiles) but there is no log record (not counted by the log tiles).
- **Follow-ups booked (FHIR) versus conversations with `followup = booked` in the log:** these should match in a clean run, since each booking comes from one conversation, but they can differ for the reasons above.
- **Cost is an estimate** based on token counts and the prices in `config.py`, not an invoice.
