"""The agent's three tools. The model never touches FHIR itself; it can only ask for these.

Each tool validates its input, calls FHIR, and returns a small JSON-able dict. run_tool()
wraps them, never raises, and records {tool, input, ok, error, ms} for the audit log.
"""
import re
import time
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import fhir_client as fhir
from config import AGENT_TAG_CODE, HOSPITAL_TZ, SOURCE_TAG_SYSTEM

TZ = ZoneInfo(HOSPITAL_TZ)
# Every resource the agent creates carries this tag so the dashboard can count agent activity.
AGENT_TAG = {"tag": [{"system": SOURCE_TAG_SYSTEM, "code": AGENT_TAG_CODE}]}
SLOTS = {"morning": (9, 0), "afternoon": (14, 0)}


class ToolError(Exception):
    """A problem the model should be told about (bad input, rule violation)."""


def _patient_ref(patient_id) -> dict:
    if not isinstance(patient_id, str) or not re.fullmatch(r"[A-Za-z0-9\-.]{1,64}", patient_id):
        raise ToolError("patient_id must be the patient ID from the discharge event.")
    try:
        fhir.get("Patient", patient_id)  # exists?
    except fhir.FhirError:
        raise ToolError(f"No patient with ID {patient_id}.") from None
    return {"reference": f"Patient/{patient_id}"}


def _upcoming_booked(patient_id: str) -> list[dict]:
    now = datetime.now(timezone.utc)
    appts = fhir.search("Appointment", {"actor": f"Patient/{patient_id}", "status": "booked"})
    return sorted(
        (a for a in appts if a.get("start") and datetime.fromisoformat(a["start"].replace("Z", "+00:00")) > now),
        key=lambda a: a["start"],
    )


def get_patient_context(patient_id: str) -> dict:
    """PHI minimization point: returns ONLY first name, discharge date, meds (name +
    instruction) and upcoming appointments (date, time, status). No address, phone, birth date,
    diagnosis or drug codes, and never a full FHIR resource."""
    _patient_ref(patient_id)
    patient = fhir.get("Patient", patient_id)
    given = (patient.get("name") or [{}])[0].get("given") or [""]
    encounters = fhir.search("Encounter", {"subject": f"Patient/{patient_id}", "status": "finished"})
    ends = [e["period"]["end"] for e in encounters if e.get("period", {}).get("end")]
    discharge = max(ends) if ends else None
    meds = [
        {
            "name": m.get("medicationCodeableConcept", {}).get("text", ""),
            "instruction": (m.get("dosageInstruction") or [{}])[0].get("text", ""),
        }
        for m in fhir.search("MedicationRequest", {"subject": f"Patient/{patient_id}", "status": "active"})
    ]
    appts = []
    for a in _upcoming_booked(patient_id):
        local = datetime.fromisoformat(a["start"].replace("Z", "+00:00")).astimezone(TZ)
        appts.append({"date": local.date().isoformat(), "time": local.strftime("%H:%M"), "status": a["status"]})
    return {
        "first_name": given[0],
        "discharge_date": datetime.fromisoformat(discharge.replace("Z", "+00:00")).astimezone(TZ).date().isoformat() if discharge else None,
        "medications": meds,
        "upcoming_appointments": appts,
    }


def book_followup(patient_id: str, date: str, time_of_day: str) -> dict:
    ref = _patient_ref(patient_id)
    if time_of_day not in SLOTS:
        raise ToolError("time_of_day must be 'morning' or 'afternoon'.")
    try:
        day = datetime.strptime(date, "%Y-%m-%d").date()
    except (TypeError, ValueError):
        raise ToolError("date must be an ISO date like 2026-11-05.") from None
    today = datetime.now(TZ).date()
    if not (today + timedelta(days=1) <= day <= today + timedelta(days=14)):
        raise ToolError(f"date must be between {today + timedelta(days=1)} and {today + timedelta(days=14)} (1 to 14 days from today).")
    if _upcoming_booked(patient_id):
        raise ToolError("The patient already has an upcoming booked appointment; do not book another.")
    hour, minute = SLOTS[time_of_day]
    start = datetime(day.year, day.month, day.day, hour, minute, tzinfo=TZ)
    appt = fhir.create({
        "resourceType": "Appointment", "meta": AGENT_TAG, "status": "booked",
        "description": "Post-discharge follow-up",
        "start": start.isoformat(), "end": (start + timedelta(minutes=30)).isoformat(),
        "participant": [{"actor": ref, "status": "accepted"}],
    })
    return {"appointment_id": appt["id"], "date": day.isoformat(), "time": start.strftime("%H:%M"), "status": "booked"}


def escalate_to_nurse(patient_id: str, reason: str, urgency: str) -> dict:
    ref = _patient_ref(patient_id)
    if urgency not in ("routine", "urgent"):
        raise ToolError("urgency must be 'routine' or 'urgent'.")
    if not isinstance(reason, str) or not reason.strip():
        raise ToolError("reason must be a non-empty string.")
    if len(reason) > 300:
        raise ToolError("reason must be at most 300 characters.")
    task = fhir.create({
        "resourceType": "Task", "meta": AGENT_TAG, "status": "requested", "intent": "order",
        "priority": urgency, "description": reason.strip(), "for": ref,
        "authoredOn": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    })
    return {"task_id": task["id"], "urgency": urgency, "status": "requested"}


def write_summary(patient_id: str, summary: str, encounter_id: str | None = None) -> str:
    """Not a model tool: the agent code calls this once, at end of conversation, to store the
    summary as a FHIR Communication (a record that a message/contact took place)."""
    comm = {
        "resourceType": "Communication", "meta": AGENT_TAG, "status": "completed",
        "subject": {"reference": f"Patient/{patient_id}"},
        "sent": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "payload": [{"contentString": summary}],
    }
    if encounter_id:
        comm["encounter"] = {"reference": f"Encounter/{encounter_id}"}
    return fhir.create(comm)["id"]


# Tool definitions shown to the model (JSON Schema describes each tool's inputs).
TOOL_SPECS = [
    {
        "name": "get_patient_context",
        "description": "Get the patient's first name, discharge date, medications (name and instructions) and upcoming appointments. Call this first.",
        "input_schema": {"type": "object", "properties": {"patient_id": {"type": "string"}}, "required": ["patient_id"]},
    },
    {
        "name": "book_followup",
        "description": "Book a 30-minute post-discharge follow-up appointment 1 to 14 days from today. Fails if the patient already has an upcoming appointment.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "date": {"type": "string", "description": "ISO date, YYYY-MM-DD"},
                "time_of_day": {"type": "string", "enum": ["morning", "afternoon"]},
            },
            "required": ["patient_id", "date", "time_of_day"],
        },
    },
    {
        "name": "escalate_to_nurse",
        "description": "Create a task for a nurse to follow up. Use for any symptom, side effect, medical question, emergency, confusion, or uncertainty.",
        "input_schema": {
            "type": "object",
            "properties": {
                "patient_id": {"type": "string"},
                "reason": {"type": "string", "description": "Short factual reason, max 300 characters"},
                "urgency": {"type": "string", "enum": ["routine", "urgent"]},
            },
            "required": ["patient_id", "reason", "urgency"],
        },
    },
]
_FUNCS = {"get_patient_context": get_patient_context, "book_followup": book_followup, "escalate_to_nurse": escalate_to_nurse}


def run_tool(name: str, tool_input: dict, expected_patient_id: str) -> tuple[dict, dict]:
    """Run one tool call. Returns (result, record). Never raises.

    The model may only act on the patient this conversation is about: a different
    patient_id is rejected, so a confused or manipulated model can't touch other records."""
    start = time.perf_counter()
    ok, error, result = True, None, {}
    try:
        if name not in _FUNCS:
            raise ToolError(f"Unknown tool {name!r}.")
        if not isinstance(tool_input, dict) or tool_input.get("patient_id") != expected_patient_id:
            raise ToolError("patient_id does not match this conversation's patient.")
        result = _FUNCS[name](**tool_input)
    except ToolError as e:
        ok, error, result = False, str(e), {"error": str(e)}
    except TypeError as e:  # missing/extra arguments
        ok, error, result = False, "Invalid tool arguments.", {"error": "Invalid tool arguments."}
    except fhir.FhirError as e:
        ok, error, result = False, "FHIR request failed.", {"error": "FHIR request failed."}
    except Exception as e:
        ok, error, result = False, f"Internal error ({type(e).__name__}).", {"error": "Internal error."}
    record = {"tool": name, "input": tool_input, "ok": ok, "error": error, "ms": round((time.perf_counter() - start) * 1000)}
    return result, record
