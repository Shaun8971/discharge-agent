"""Streamlit app: page 1 = patient list + follow-up chat with the agent, page 2 = dashboard.

Run:  streamlit run app.py
"""
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

import fhir_client as fhir
import hl7_parser
from agent import Conversation
from config import AGENT_TAG_CODE, HOSPITAL_STATS, HOSPITAL_TZ, SOURCE_TAG_SYSTEM
from logger import conversation_cost, read_conversations

HL7_DIR = Path(__file__).parent / "hl7_messages"
AGENT_TAG = f"{SOURCE_TAG_SYSTEM}|{AGENT_TAG_CODE}"
NOT_FILLED = "Not filled in yet"

st.set_page_config(page_title="Discharge Follow-up Agent", layout="wide")


# ---------------------------------------------------------------- page 1: patients and follow-up chat
# Each patient has their own saved conversation in st.session_state["patients"][mrn], so
# switching between patients (or coming back later) resumes exactly where you left off.
# This lives in the browser session only: reloading the page clears the chat transcripts
# (the FHIR records and the log file are kept).
LOCAL_TZ = ZoneInfo(HOSPITAL_TZ)


def load_patients() -> list[dict]:
    """Parse every HL7 file into one row per patient (local files only; no FHIR call)."""
    rows = []
    for f in sorted(HL7_DIR.glob("*.hl7")):
        try:
            rows.append({"file": f, "parsed": hl7_parser.parse_adt(f.read_text()), "error": None})
        except (hl7_parser.HL7Error, OSError) as e:
            rows.append({"file": f, "parsed": None, "error": str(e)})
    return rows


def status_of(mrn: str) -> str:
    p = st.session_state.patients.get(mrn)
    if p is None:
        return "Not contacted"
    return "Completed" if p["outcome"] else "In progress"


def start_followup(mrn: str, parsed: dict):
    """Look the patient up in FHIR, start the agent, and save the conversation under their MRN."""
    try:
        patient_id, encounter_id = hl7_parser.find_patient(parsed["mrn"])
    except hl7_parser.HL7Error as e:
        st.error(str(e))
        return
    except Exception:
        st.error("Could not reach the FHIR server. Is it running?")
        return
    events: list[dict] = []
    convo = Conversation(parsed, patient_id, encounter_id, on_tool_call=lambda rec, res: events.append({"record": rec, "result": res}))
    try:
        with st.spinner("Agent is starting the follow-up..."):
            greeting = convo.start()
    except Exception as e:
        st.error(f"The agent could not start ({type(e).__name__}). Check the gateway settings in .env.")
        return
    st.session_state.patients[mrn] = {
        "convo": convo, "history": [("assistant", greeting)], "events": events,
        "outcome": None, "ids": (patient_id, encounter_id), "parsed": parsed,
    }


def discharges_page():
    ss = st.session_state
    ss.setdefault("patients", {})   # mrn -> saved conversation
    ss.setdefault("selected", None)  # mrn currently open
    ss.setdefault("to_start", None)  # mrn waiting for its conversation to be started

    st.title("Patient follow-up")
    st.caption("Recently discharged patients, from incoming HL7 ADT A03 (discharge) messages. Start a follow-up chat to check in with a patient after they go home.")

    rows = load_patients()
    by_mrn = {r["parsed"]["mrn"]: r["parsed"] for r in rows if r["parsed"]}

    # A "Start follow-up" click only records the request; the agent is started here, before
    # the table is drawn, so the table always shows up-to-date statuses.
    if ss.to_start:
        mrn, ss.to_start = ss.to_start, None
        start_followup(mrn, by_mrn[mrn])
        ss.selected = mrn if mrn in ss.patients else None

    widths = [1.1, 1.8, 2.2, 1.6, 1.6]
    head = st.columns(widths)
    for col, label in zip(head, ["MRN", "Patient", "Discharged", "Follow-up status", ""]):
        col.markdown(f"**{label}**")
    if not rows:
        st.warning("No HL7 files found. Run seed_fhir.py first.")
    for r in rows:
        c = st.columns(widths, vertical_alignment="center")
        if r["error"]:
            c[0].write(r["file"].name)
            c[1].error(r["error"])
            continue
        p = r["parsed"]
        mrn = p["mrn"]
        discharged = datetime.fromisoformat(p["discharge_time"]).astimezone(LOCAL_TZ).strftime("%b %d, %Y %H:%M")
        c[0].write(("▶ " if ss.selected == mrn else "") + mrn)
        c[1].write(p["patient_name"])
        c[2].write(discharged)
        c[3].write(status_of(mrn))
        state = status_of(mrn)
        label = {"Not contacted": "Start follow-up", "In progress": "Resume chat", "Completed": "View chat"}[state]
        if c[4].button(label, key=f"open_{mrn}", type="primary" if ss.selected == mrn else "secondary"):
            ss.selected = mrn
            if state == "Not contacted":
                ss.to_start = mrn
            st.rerun()

    st.divider()
    mrn = ss.selected
    saved = ss.patients.get(mrn) if mrn else None
    if saved is None:
        st.info("Choose a patient above and click Start follow-up. You type as the patient.")
    else:
        convo, outcome = saved["convo"], saved["outcome"]
        st.subheader(f"Follow-up chat: {mrn}")
        with st.expander("Discharge message (HL7) and matching FHIR IDs", expanded=len(saved["history"]) <= 1):
            patient_id, encounter_id = saved["ids"]
            st.json({**saved["parsed"], "fhir_patient_id": patient_id, "fhir_encounter_id": encounter_id})
        for role, text in saved["history"]:
            with st.chat_message(role):
                st.write(text)

        user_text = st.chat_input("Reply as the patient...", disabled=outcome is not None)
        if user_text:
            saved["history"].append(("user", user_text))
            with st.chat_message("user"):
                st.write(user_text)
            try:
                with st.chat_message("assistant"), st.spinner("Agent is typing..."):
                    reply = convo.send(user_text)
                    st.write(reply)
                saved["history"].append(("assistant", reply))
            except Exception as e:
                st.error(f"The agent failed ({type(e).__name__}). Try again.")

        if outcome is None:
            if st.button("End conversation", type="primary"):
                try:
                    with st.spinner("Summarizing..."):
                        saved["outcome"] = convo.end()
                    st.rerun()  # refresh the table's status
                except Exception as e:
                    st.error(f"Could not finish the conversation ({type(e).__name__}).")
        else:
            st.success("Conversation ended and logged.")
            m = st.columns(4)
            m[0].metric("Completed", "Yes" if outcome["completed"] else "No")
            m[1].metric("Meds confirmed", outcome["meds_confirmed"])
            m[2].metric("Follow-up", outcome["followup"])
            m[3].metric("Escalated", "Yes" if outcome["escalated"] else "No")
            st.write(outcome["summary"])
            if st.button("Start a new follow-up with this patient"):
                del ss.patients[mrn]
                ss.to_start = mrn
                st.rerun()

    # Sidebar rendered last so it includes tool calls from this run.
    with st.sidebar:
        st.header("Behind the scenes")
        st.caption("Every tool call the agent makes for the selected patient, with its FHIR result.")
        events = saved["events"] if saved else []
        if not events:
            st.write("No tool calls yet.")
        for ev in events:
            rec = ev["record"]
            label = f"{'OK' if rec['ok'] else 'ERROR'} · {rec['tool']} · {rec['ms']} ms"
            with st.expander(label, expanded=not rec["ok"]):
                st.json({"input": rec["input"], "result": ev["result"]})
        if saved:
            st.caption(f"Claude calls: {len(saved['convo'].latencies_ms)} · output tokens: {saved['convo'].output_tokens}")


# ---------------------------------------------------------------- page 2: dashboard
def pct(n, d):
    return f"{n / d:.0%}" if d else "n/a"


def fhir_counts():
    """Agent activity as recorded in FHIR (resources carrying the agent tag)."""
    try:
        return {
            "appointments": fhir.count("Appointment", {"_tag": AGENT_TAG}),
            "tasks_routine": fhir.count("Task", {"_tag": AGENT_TAG, "priority": "routine"}),
            "tasks_urgent": fhir.count("Task", {"_tag": AGENT_TAG, "priority": "urgent"}),
        }
    except Exception:
        return None


def stat_value(key):
    v = HOSPITAL_STATS.get(key)
    return NOT_FILLED if v in (None, "", "REPLACE_ME") else f"{v:,}" if isinstance(v, (int, float)) else str(v)


def dashboard_page():
    st.title("Dashboard")
    st.button("Refresh")
    records = read_conversations()
    n = len(records)
    counts = fhir_counts()
    if counts is None:
        st.warning("Could not read FHIR; FHIR-based tiles show n/a.")

    completed = sum(r["outcome"]["completed"] for r in records)
    escalated = sum(r["outcome"]["escalated"] for r in records)
    latencies = [ms for r in records for ms in r.get("latencies_ms", [])]
    costs = [conversation_cost(r) for r in records]

    st.caption("Tiles marked (log) come from data/conversations.jsonl; tiles marked (FHIR) are queried live from the server.")
    r1 = st.columns(3)
    r1[0].metric("Discharges processed (log)", n)
    r1[1].metric("Completion rate (log)", pct(completed, n), help="Conversations where both the medication check and the follow-up were covered.")
    r1[2].metric("Follow-ups booked (FHIR)", counts["appointments"] if counts else "n/a", help="Appointments created by the agent (tagged discharge-agent).")
    r2 = st.columns(3)
    r2[0].metric("Escalation rate (log)", pct(escalated, n))
    r2[1].metric("Escalations: routine / urgent (FHIR)", f"{counts['tasks_routine']} / {counts['tasks_urgent']}" if counts else "n/a", help="Nurse Tasks created by the agent, by priority.")
    r2[2].metric("Avg cost per conversation (log)", f"${sum(costs) / n:.4f}" if n else "n/a", help="Tokens x the price constants in config.py (cache writes and reads priced separately).")
    st.metric("Avg Claude response latency (log)", f"{sum(latencies) / len(latencies) / 1000:.1f} s" if latencies else "n/a", help="Mean time per Claude call.")

    st.subheader("Recent conversations")
    if not records:
        st.info("No conversations logged yet. Process a discharge and click End conversation.")
    else:
        rows = [{
            "Time": datetime.fromisoformat(r["ended"]).astimezone().strftime("%Y-%m-%d %H:%M"),
            "MRN": r["mrn"],
            "Completed": r["outcome"]["completed"],
            "Meds confirmed": r["outcome"]["meds_confirmed"],
            "Follow-up": r["outcome"]["followup"],
            "Escalated": r["outcome"]["escalated"],
            "Cost (USD)": round(conversation_cost(r), 4),
        } for r in reversed(records[-20:])]
        st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")

    st.divider()
    st.subheader("Statistics from this hospital")
    st.table(pd.DataFrame(
        {"Value": [stat_value(k) for k in ("hospital_name", "condition", "annual_discharges", "annual_readmissions", "source")]},
        index=["Hospital", "Condition", "Annual discharges", "Annual readmissions", "Source"],
    ))


pages = [
    st.Page(discharges_page, title="Patient follow-up", url_path="chat", default=True),
    st.Page(dashboard_page, title="Dashboard", url_path="dashboard"),
]
st.navigation(pages).run()
