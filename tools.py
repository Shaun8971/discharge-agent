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
    """A problem the model should be told about: bad input or a broken rule (for example
    "already has an appointment"). run_tool() turns it into an error tool_result.
    """


def _patient_ref(patient_id) -> dict:
    """Check that patient_id is well formed and exists in FHIR; return a FHIR reference to it.

    Args:
        patient_id (str): FHIR Patient ID, letters, digits, "-" or "." (1 to 64 characters).

    Returns:
        dict: {"reference": "Patient/<id>"}, ready to put in a resource.

    Raises:
        ToolError: if the ID is malformed or no such patient exists.

    Example:
        >>> _patient_ref("1000")
        {'reference': 'Patient/1000'}
    """
    if not isinstance(patient_id, str) or not re.fullmatch(r"[A-Za-z0-9\-.]{1,64}", patient_id):
        raise ToolError("patient_id must be the patient ID from the discharge event.")
    try:
        fhir.get("Patient", patient_id)  # exists?
    except fhir.FhirError:
        raise ToolError(f"No patient with ID {patient_id}.") from None
    return {"reference": f"Patient/{patient_id}"}


def _upcoming_booked(patient_id: str) -> list[dict]:
    """List the patient's appointments that are booked and start in the future, soonest first.

    Args:
        patient_id (str): FHIR Patient ID.

    Returns:
        list[dict]: Appointment resources (any appointment, not only follow-ups).

    Example:
        >>> [a["start"] for a in _upcoming_booked("1006")]
        ['2026-11-06T15:00:00Z']
    """
    now = datetime.now(timezone.utc)
    appts = fhir.search("Appointment", {"actor": f"Patient/{patient_id}", "status": "booked"})
    return sorted(
        (a for a in appts if a.get("start") and datetime.fromisoformat(a["start"].replace("Z", "+00:00")) > now),
        key=lambda a: a["start"],
    )


def get_patient_context(patient_id: str) -> dict:
    """Tool 1. Return the minimum the model needs to run the check-in (the PHI minimization point).

    Returns ONLY first name, discharge date, medications (name and instruction text) and upcoming
    appointments (date, local time, status). No address, phone, birth date, diagnosis or drug codes,
    and never a full FHIR resource.

    Args:
        patient_id (str): FHIR Patient ID.

    Returns:
        dict: {"first_name", "discharge_date", "medications", "upcoming_appointments"}.

    Raises:
        ToolError: if patient_id is malformed or unknown.

    Example:
        >>> get_patient_context("1006")["upcoming_appointments"]
        [{'date': '2026-11-06', 'time': '10:00', 'status': 'booked'}]
    """
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
    """Tool 2. Book a 30-minute post-discharge follow-up Appointment in FHIR.

    Rules: time_of_day is "morning" (09:00) or "afternoon" (14:00) in the hospital timezone; the
    date is 1 to 14 days from today; the patient must have no other upcoming booked appointment.

    Args:
        patient_id (str): FHIR Patient ID.
        date (str): ISO date, e.g. "2026-11-04".
        time_of_day (str): "morning" or "afternoon".

    Returns:
        dict: {"appointment_id", "date", "time", "status": "booked"}.

    Raises:
        ToolError: for a bad time_of_day or date, a date outside the 1 to 14 day window, or an
            existing upcoming appointment.

    Example:
        >>> book_followup("1024", "2026-11-04", "morning")
        {'appointment_id': '1046', 'date': '2026-11-04', 'time': '09:00', 'status': 'booked'}
    """
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
    """Tool 3. Create a FHIR Task asking a nurse to follow up with the patient.

    Args:
        patient_id (str): FHIR Patient ID.
        reason (str): short factual reason, not empty, at most 300 characters.
        urgency (str): "routine" or "urgent".

    Returns:
        dict: {"task_id", "urgency", "status": "requested"}.

    Raises:
        ToolError: for a bad urgency, an empty reason, or a reason longer than 300 characters.

    Example:
        >>> escalate_to_nurse("1024", "Patient asked about a rash", "routine")
        {'task_id': '1047', 'urgency': 'routine', 'status': 'requested'}
    """
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
    """Store the end-of-conversation summary as a FHIR Communication. Not a model tool: the agent
    code calls it once, when the conversation ends.

    Args:
        patient_id (str): FHIR Patient ID.
        summary (str): the 2 to 3 sentence summary (should contain no patient name).
        encounter_id (str | None): FHIR Encounter ID to link, or None.

    Returns:
        str: the ID of the new Communication.

    Raises:
        fhir_client.FhirError: if FHIR rejects the resource.

    Example:
        >>> write_summary("1024", "Example summary.")
        '1048'
    """
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
    """Run one tool call requested by the model, safely. Never raises.

    Only the patient this conversation is about may be touched: any other patient_id is rejected,
    so a confused or manipulated model cannot reach other records.

    Args:
        name (str): tool name, one of the three in TOOL_SPECS.
        tool_input (dict): the input the model supplied.
        expected_patient_id (str): the patient ID of this conversation.

    Returns:
        tuple[dict, dict]: (result, record). result is the tool output, or {"error": message}.
            record is {"tool", "input", "ok", "error", "ms"} for the audit log.

    Example:
        >>> run_tool("get_patient_context", {"patient_id": "1006"}, "1000")
        ({'error': "patient_id does not match this conversation's patient."}, {... 'ok': False ...})
    """
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
