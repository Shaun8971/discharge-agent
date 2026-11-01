"""Parse HL7 v2 ADT^A03 (discharge) messages and match them to a FHIR patient.

HL7 v2 is the older, pipe-delimited messaging standard hospitals still use to announce
events. A message is a few lines ("segments"); each segment is split into numbered
"fields" by `|`, and fields can be split into "components" by `^`.

Segments and fields used here:
  MSH  Message header: who sent it and what kind of message it is.
    MSH-9   Message type, e.g. ADT^A03. ADT = admit/discharge/transfer; A03 = "patient discharged".
    MSH-10  Message control ID: a unique ID for this one message (lets receivers detect duplicates).
  EVN  Event segment: repeats the event code (A03) and when it happened. Not read by this parser.
  PID  Patient identification.
    PID-3   Patient identifier list: here the MRN (medical record number), e.g. MRN1001.
            Must equal the `urn:demo:mrn` identifier on the FHIR Patient.
    PID-5   Patient name, family^given.
    PID-7   Birth date (YYYYMMDD). Not used by this parser.
  PV1  Patient visit.
    PV1-2   Patient class: I = inpatient.
    PV1-45  Discharge date/time (YYYYMMDDHHMMSS+ZZZZ; the +ZZZZ is the offset from UTC).
  DG1  Diagnosis.
    DG1-3   Diagnosis code^description^coding system; here an ICD-10-CM code, e.g. I50.9.
    DG1-6   Diagnosis type; F = final.

Usage:  python hl7_parser.py hl7_messages/adt_a03_MRN1001.hl7
"""
import re
import sys
from datetime import datetime, timedelta, timezone

import hl7

import fhir_client as fhir
from config import MRN_SYSTEM


class HL7Error(ValueError):
    """The message is malformed, is not an ADT A03, or does not match a FHIR patient.
    Subclass of ValueError, so one except clause catches every parser problem.
    """


def _field(msg, segment: str, index: int, required: bool = True) -> str:
    """Read one field of a parsed HL7 message as stripped text.

    Args:
        msg (hl7.Message): parsed message.
        segment (str): segment name, e.g. "PV1".
        index (int): HL7 field number, e.g. 45 for PV1-45.
        required (bool): if True, an empty value raises HL7Error.

    Returns:
        str: the field text.

    Raises:
        HL7Error: if the segment is missing, or the field is empty and required.

    Example:
        >>> _field(msg, "MSH", 10)
        'CTRL-MRN1001-001'
    """
    try:
        value = str(msg.segment(segment)[index]).strip()
    except KeyError:
        raise HL7Error(f"Missing required segment {segment}.") from None
    except IndexError:
        value = ""
    if required and not value:
        raise HL7Error(f"Missing required field {segment}-{index}.")
    return value


def _to_iso(ts: str) -> str:
    """Convert an HL7 timestamp, YYYYMMDD[HHMM[SS]][+/-ZZZZ], to ISO 8601.
    Without an offset the result has no timezone (naive).

    Args:
        ts (str): HL7 timestamp.

    Returns:
        str: ISO 8601 timestamp.

    Raises:
        HL7Error: if the text is not a valid HL7 timestamp.

    Example:
        >>> _to_iso("20261031232638+0000")
        '2026-10-31T23:26:38+00:00'
    """
    m = re.fullmatch(r"(\d{8}|\d{12}|\d{14})([+-]\d{4})?", ts)
    if not m:
        raise HL7Error(f"Invalid HL7 timestamp: {ts!r}.")
    digits, offset = m.groups()
    fmt = {8: "%Y%m%d", 12: "%Y%m%d%H%M", 14: "%Y%m%d%H%M%S"}[len(digits)]
    try:
        return datetime.strptime(digits + (offset or ""), fmt + ("%z" if offset else "")).isoformat()
    except ValueError:
        raise HL7Error(f"Invalid HL7 timestamp: {ts!r}.") from None


def parse_adt(text: str) -> dict:
    """Parse an ADT^A03 (discharge) message into a dict.

    Steps: normalize line endings to the carriage return the hl7 library needs; require MSH first;
    parse; require MSH-9 = ADT^A03; require PV1-2 = I and a PID-3 MRN; read the fields below.

    Args:
        text (str): the raw HL7 message (any line ending).

    Returns:
        dict: message_control_id, event_type, mrn, patient_name, discharge_time (ISO 8601),
            diagnosis_code (None if there is no DG1 segment).

    Raises:
        HL7Error: for anything that is not a valid inpatient ADT^A03.

    Example:
        >>> parse_adt(open("hl7_messages/adt_a03_MRN1001.hl7", newline="").read())["mrn"]
        'MRN1001'
    """
    # The hl7 library requires segments separated by \r; files usually use \n or \r\n.
    text = text.strip().replace("\r\n", "\r").replace("\n", "\r")
    if not text.startswith("MSH"):
        raise HL7Error("Not an HL7 v2 message: it must start with an MSH segment.")
    try:
        msg = hl7.parse(text)
    except Exception as e:
        raise HL7Error(f"Could not parse HL7 message: {e}") from None

    msh9 = msg.segment("MSH")[9]
    msg_type = str(msh9[0][0]) if len(msh9) else ""
    trigger = str(msh9[0][1]) if len(msh9) and len(msh9[0]) > 1 else ""
    if (msg_type, trigger) != ("ADT", "A03"):
        raise HL7Error(
            f"Unsupported message type {str(msh9)!r}: only ADT^A03 (patient discharge) is accepted."
        )

    if _field(msg, "PV1", 2) != "I":
        raise HL7Error("PV1-2 must be 'I' (inpatient).")
    pid3 = msg.segment("PID")[3]
    pid5 = msg.segment("PID")[5]
    if not str(pid3).strip():
        raise HL7Error("Missing required field PID-3 (MRN).")
    name = " ".join(p for p in (str(pid5[0][1]) if len(pid5[0]) > 1 else "", str(pid5[0][0])) if p)

    dg1_3 = msg.segment("DG1")[3] if msg.segments("DG1") else None
    return {
        "message_control_id": _field(msg, "MSH", 10),
        "event_type": f"{msg_type}^{trigger}",
        "mrn": str(pid3[0][0]).strip(),
        "patient_name": name,
        "discharge_time": _to_iso(_field(msg, "PV1", 45)),
        "diagnosis_code": str(dg1_3[0][0]).strip() if dg1_3 else None,
    }


def find_patient(mrn: str) -> tuple[str, str]:
    """Find the FHIR Patient for an MRN and that patient's most recent finished Encounter.

    Args:
        mrn (str): medical record number, e.g. "MRN1001".

    Returns:
        tuple[str, str]: (patient_id, encounter_id).

    Raises:
        HL7Error: if no Patient, more than one Patient, or no finished Encounter is found.

    Example:
        >>> find_patient("MRN1001")
        ('1000', '1001')
    """
    patients = fhir.search("Patient", {"identifier": f"{MRN_SYSTEM}|{mrn}"})
    if not patients:
        raise HL7Error(f"No FHIR Patient found with MRN {mrn}.")
    if len(patients) > 1:
        raise HL7Error(f"{len(patients)} FHIR Patients share MRN {mrn}; expected exactly one.")
    patient_id = patients[0]["id"]
    encounters = fhir.search("Encounter", {"subject": f"Patient/{patient_id}", "status": "finished"})
    if not encounters:
        raise HL7Error(f"Patient/{patient_id} has no finished Encounter.")
    latest = max(encounters, key=lambda e: e.get("period", {}).get("end", ""))
    return patient_id, latest["id"]


def fhir_diagnosis_code(encounter_id: str) -> str | None:
    """Get the ICD-10-CM code of the Condition attached to an Encounter, for cross-checking DG1-3.

    Args:
        encounter_id (str): FHIR Encounter ID.

    Returns:
        str | None: the code, or None if no ICD-10-CM coded Condition exists.

    Example:
        >>> fhir_diagnosis_code("1001")
        'I50.9'
    """
    for cond in fhir.search("Condition", {"encounter": f"Encounter/{encounter_id}"}):
        for coding in cond.get("code", {}).get("coding", []):
            if coding.get("system") == "http://hl7.org/fhir/sid/icd-10-cm":
                return coding["code"]
    return None


def fhir_discharge_time(encounter_id: str) -> str | None:
    """Get Encounter.period.end: the discharge time FHIR holds for this stay.

    Args:
        encounter_id (str): FHIR Encounter ID.

    Returns:
        str | None: ISO 8601 timestamp, or None if the Encounter has no end time.

    Example:
        >>> fhir_discharge_time("1001")
        '2026-10-31T23:26:38Z'
    """
    return fhir.get("Encounter", encounter_id).get("period", {}).get("end")


def _as_utc(iso: str) -> datetime:
    """Turn an ISO 8601 string into a timezone-aware UTC datetime. A time with no offset is
    assumed to already be UTC.

    Args:
        iso (str): ISO 8601 timestamp, with "Z" or an offset.

    Returns:
        datetime: the same instant in UTC.

    Example:
        >>> _as_utc("2026-10-31T18:26:38-05:00")
        datetime.datetime(2026, 10, 31, 23, 26, 38, tzinfo=datetime.timezone.utc)
    """
    dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    # A time with no offset can't be compared reliably; assume UTC and let the check show it.
    return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def discharge_times_match(hl7_iso: str, fhir_iso: str | None, tolerance_minutes: int = 5) -> bool:
    """Check that the HL7 discharge time and the FHIR Encounter end time are within a tolerance.

    Args:
        hl7_iso (str): discharge time from the message (ISO 8601).
        fhir_iso (str | None): Encounter.period.end; None counts as a mismatch.
        tolerance_minutes (int): allowed difference, default 5.

    Returns:
        bool: True if the two instants are no more than tolerance_minutes apart.

    Example:
        >>> discharge_times_match("2026-10-31T23:46:38+00:00", "2026-10-31T23:26:38Z")
        False
    """
    if not fhir_iso:
        return False
    return abs(_as_utc(hl7_iso) - _as_utc(fhir_iso)) <= timedelta(minutes=tolerance_minutes)


def main(path: str) -> int:
    """Command-line entry point: parse a file, look up the patient, print the fields and run the
    two cross-checks (diagnosis code, discharge time).

    Args:
        path (str): path to an .hl7 file.

    Returns:
        int: 0 if both checks pass; 1 for any error or failed check.

    Example:
        $ python hl7_parser.py hl7_messages/adt_a03_MRN1001.hl7
        ... Diagnosis check: DG1 matches FHIR Condition.
        ... Discharge time check: PV1-45 matches FHIR Encounter end (within 5 minutes).
    """
    try:
        with open(path, newline="") as f:
            parsed = parse_adt(f.read())
        patient_id, encounter_id = find_patient(parsed["mrn"])
        fhir_dx = fhir_diagnosis_code(encounter_id)
        fhir_end = fhir_discharge_time(encounter_id)
    except (HL7Error, OSError) as e:
        print(f"ERROR: {e}")
        return 1
    except fhir.FhirError as e:
        print(f"ERROR: FHIR request failed: {e}")
        return 1
    except Exception as e:  # e.g. FHIR server not reachable
        print(f"ERROR: {type(e).__name__}: is the FHIR server running at the configured URL?")
        return 1
    for k, v in parsed.items():
        print(f"{k:<20}{v}")
    print(f"{'fhir_patient_id':<20}{patient_id}")
    print(f"{'fhir_encounter_id':<20}{encounter_id}")
    print(f"{'fhir_diagnosis':<20}{fhir_dx}")
    print(f"{'fhir_discharge':<20}{fhir_end}")
    dx_ok = fhir_dx == parsed["diagnosis_code"]
    time_ok = discharge_times_match(parsed["discharge_time"], fhir_end)
    print(f"Diagnosis check: DG1 {'matches' if dx_ok else 'DOES NOT MATCH'} FHIR Condition.")
    print(f"Discharge time check: PV1-45 {'matches' if time_ok else 'DOES NOT MATCH'} FHIR Encounter end (within 5 minutes).")
    return 0 if dx_ok and time_ok else 1


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.split("Usage:")[-1].strip())
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
