"""Load 5 synthetic patients (Patient, Encounter, Condition, MedicationRequest, Appointment) into FHIR.

Safe to run repeatedly: Patients use conditional update on the MRN identifier; the other
resources carry a seed identifier and are searched for before being created (and
brought up to date if they already exist, e.g. to add codes).
All data is synthetic.

This script is the single source of discharge times: each Encounter's period.end is set
relative to "now" on the first run (and kept on re-runs), and the matching ADT^A03 file in
hl7_messages/ is written from the Encounter's stored end time, with a UTC offset, so the
HL7 message and FHIR agree exactly.
"""
from datetime import datetime, timedelta, timezone
from pathlib import Path

import fhir_client as fhir
from config import MRN_SYSTEM, SEED_ID_SYSTEM, SEED_TAG_CODE, SOURCE_TAG_SYSTEM

RXNORM = "http://www.nlm.nih.gov/research/umls/rxnorm"
ICD10CM = "http://hl7.org/fhir/sid/icd-10-cm"
DIAG_ROLE = "http://terminology.hl7.org/CodeSystem/diagnosis-role"

TAG = {"tag": [{"system": SOURCE_TAG_SYSTEM, "code": SEED_TAG_CODE}]}

# (mrn, first, last, birthDate, phone, street, discharged_hours_ago, has_appt, icd10, icd10_display, meds)
# meds: (text, instruction, rxnorm_code, rxnorm_display)
# RxNorm = US standard drug vocabulary; each code below is a "clinical drug" (SCD): ingredient + strength + form.
# ICD-10-CM = US diagnosis code set. All chosen from CMS readmission-program conditions.
PATIENTS = [
    ("MRN1001", "Alice", "Morgan", "1950-03-14", "555-0101", "12 Elm St", 20, False,
     "I50.9", "Heart failure, unspecified",
     [("Metoprolol 25 mg tablet", "Take 1 tablet by mouth twice daily", "866924", "metoprolol tartrate 25 MG Oral Tablet"),
      ("Furosemide 40 mg tablet", "Take 1 tablet by mouth every morning", "313988", "furosemide 40 MG Oral Tablet"),
      ("Lisinopril 10 mg tablet", "Take 1 tablet by mouth once daily", "314076", "lisinopril 10 MG Oral Tablet")]),
    ("MRN1002", "Ben", "Carter", "1947-11-02", "555-0102", "48 Oak Ave", 30, True,
     "I50.22", "Chronic systolic (congestive) heart failure",
     [("Carvedilol 6.25 mg tablet", "Take 1 tablet by mouth twice daily with food", "200031", "carvedilol 6.25 MG Oral Tablet"),
      ("Spironolactone 25 mg tablet", "Take 1 tablet by mouth once daily", "313096", "spironolactone 25 MG Oral Tablet")]),
    ("MRN1003", "Carla", "Diaz", "1958-07-21", "555-0103", "7 Birch Rd", 12, False,
     "I21.4", "Non-ST elevation (NSTEMI) myocardial infarction",
     [("Atorvastatin 40 mg tablet", "Take 1 tablet by mouth at bedtime", "617311", "atorvastatin 40 MG Oral Tablet"),
      ("Aspirin 81 mg tablet", "Take 1 tablet by mouth once daily", "243670", "aspirin 81 MG Oral Tablet"),
      ("Clopidogrel 75 mg tablet", "Take 1 tablet by mouth once daily", "309362", "clopidogrel 75 MG Oral Tablet")]),
    ("MRN1004", "David", "Evans", "1962-01-30", "555-0104", "93 Cedar Ln", 40, True,
     "J18.9", "Pneumonia, unspecified organism",
     [("Warfarin 5 mg tablet", "Take 1 tablet by mouth every evening", "855332", "warfarin sodium 5 MG Oral Tablet"),
      ("Metformin 500 mg tablet", "Take 1 tablet by mouth twice daily with meals", "861007", "metformin hydrochloride 500 MG Oral Tablet")]),
    ("MRN1005", "Eva", "Fischer", "1955-09-09", "555-0105", "5 Pine Ct", 8, False,
     "J44.1", "Chronic obstructive pulmonary disease with (acute) exacerbation",
     [("Amlodipine 5 mg tablet", "Take 1 tablet by mouth once daily", "197361", "amlodipine 5 MG Oral Tablet"),
      ("Losartan 50 mg tablet", "Take 1 tablet by mouth once daily", "979492", "losartan potassium 50 MG Oral Tablet")]),
]


def iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


HL7_DIR = Path(__file__).parent / "hl7_messages"


def hl7_ts(dt: datetime) -> str:
    """HL7 timestamp with timezone offset: YYYYMMDDHHMMSS+ZZZZ (always UTC here)."""
    return dt.astimezone(timezone.utc).strftime("%Y%m%d%H%M%S+0000")


def write_hl7(mrn, first, last, dob, icd, icd_text, discharge: datetime) -> None:
    """Write the ADT^A03 (discharge) message for this patient. Field meanings: see hl7_parser.py."""
    ts = hl7_ts(discharge)
    pv1 = [""] * 46
    pv1[0], pv1[1], pv1[2], pv1[3], pv1[45] = "PV1", "1", "I", "3WEST^301^A", ts  # PV1-45 = discharge time
    segments = [
        f"MSH|^~\\&|DEMO_EHR|DEMO_GENERAL|DISCHARGE_AGENT|DEMO_GENERAL|{ts}||ADT^A03^ADT_A03|CTRL-{mrn}-001|P|2.5",
        f"EVN|A03|{ts}",
        f"PID|1||{mrn}^^^DEMO^MR||{last}^{first}||{dob.replace('-', '')}",
        "|".join(pv1),
        f"DG1|1|I10|{icd}^{icd_text}^I10||{ts}|F",
    ]
    HL7_DIR.mkdir(exist_ok=True)
    (HL7_DIR / f"adt_a03_{mrn}.hl7").write_text("\r\n".join(segments) + "\r\n", newline="")


def find_or_create(resource: dict, seed_id: str, keep: tuple = ()) -> dict:
    """Search-before-create using our seed identifier, so reruns add nothing.

    If the resource already exists but differs from what we want (e.g. it predates the
    RxNorm codes), update it in place. Fields named in `keep` (times that are relative to
    "now") are left as they were on the first run."""
    resource["identifier"] = [{"system": SEED_ID_SYSTEM, "value": seed_id}]
    found = fhir.search(resource["resourceType"], {"identifier": f"{SEED_ID_SYSTEM}|{seed_id}"})
    if not found:
        return fhir.create(resource)
    existing = found[0]
    wanted = {k: v for k, v in resource.items() if k not in keep}
    if all(existing.get(k) == v for k, v in wanted.items() if k != "meta"):
        return existing
    return fhir.update({**existing, **wanted, "id": existing["id"]})


def seed_patient(mrn, first, last, dob, phone, street, hours_ago, has_appt, icd, icd_text, meds):
    # Patient: the person. identifier = MRN (medical record number), the key HL7 messages use.
    patient = fhir.conditional_update(
        {
            "resourceType": "Patient",
            "meta": TAG,
            "identifier": [{"system": MRN_SYSTEM, "value": mrn}],
            "name": [{"use": "official", "family": last, "given": [first]}],
            "birthDate": dob,
            "telecom": [{"system": "phone", "value": phone, "use": "mobile"}],
            "address": [{"line": [street], "city": "Springfield-on-Demo", "state": "ZZ", "postalCode": "00000"}],
        },
        {"identifier": f"{MRN_SYSTEM}|{mrn}"},
    )
    pid = patient["id"]
    ref = {"reference": f"Patient/{pid}"}
    now = datetime.now(timezone.utc)

    # Encounter: one hospital stay. class IMP = inpatient. period.end = discharge time.
    # On re-runs the stored period is kept, so this "now"-relative time only matters the first time.
    discharge = now - timedelta(hours=hours_ago)
    encounter = {
        "resourceType": "Encounter", "meta": TAG, "status": "finished",
        "class": {"system": "http://terminology.hl7.org/CodeSystem/v3-ActCode", "code": "IMP", "display": "inpatient encounter"},
        "subject": ref,
        "period": {"start": iso(discharge - timedelta(days=4)), "end": iso(discharge)},
    }
    enc = find_or_create(dict(encounter), f"{mrn}-ENC", keep=("period",))

    # Write the HL7 file from the time FHIR actually holds (not the freshly computed one).
    stored_end = datetime.fromisoformat(enc["period"]["end"].replace("Z", "+00:00"))
    write_hl7(mrn, first, last, dob, icd, icd_text, stored_end)

    # Condition: a diagnosis. Coded with ICD-10-CM, linked to the Patient and this Encounter.
    cond = find_or_create(
        {
            "resourceType": "Condition", "meta": TAG,
            "clinicalStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-clinical", "code": "active"}]},
            "verificationStatus": {"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-ver-status", "code": "confirmed"}]},
            "category": [{"coding": [{"system": "http://terminology.hl7.org/CodeSystem/condition-category", "code": "encounter-diagnosis"}]}],
            "code": {"coding": [{"system": ICD10CM, "code": icd, "display": icd_text}], "text": icd_text},
            "subject": ref,
            "encounter": {"reference": f"Encounter/{enc['id']}"},
        },
        f"{mrn}-DX",
    )

    # Encounter.diagnosis: points back at the Condition. role DD = "discharge diagnosis".
    find_or_create(
        {
            **encounter,
            "diagnosis": [{
                "condition": {"reference": f"Condition/{cond['id']}"},
                "use": {"coding": [{"system": DIAG_ROLE, "code": "DD", "display": "Discharge diagnosis"}]},
                "rank": 1,
            }],
        },
        f"{mrn}-ENC", keep=("period",),
    )

    # MedicationRequest: a prescription order. status active + intent order = currently ordered.
    for i, (name, instruction, rx, rx_display) in enumerate(meds, 1):
        find_or_create(
            {
                "resourceType": "MedicationRequest", "meta": TAG, "status": "active", "intent": "order",
                "medicationCodeableConcept": {"coding": [{"system": RXNORM, "code": rx, "display": rx_display}], "text": name},
                "subject": ref,
                "dosageInstruction": [{"text": instruction}],
            },
            f"{mrn}-MED{i}",
        )

    # Appointment: a booked visit; participant.actor points at the Patient.
    if has_appt:
        start = (now + timedelta(days=5)).replace(hour=10, minute=0, second=0, microsecond=0)
        find_or_create(
            {
                "resourceType": "Appointment", "meta": TAG, "status": "booked",
                "description": "Post-discharge follow-up",
                "start": iso(start), "end": iso(start + timedelta(minutes=30)),
                "participant": [{"actor": ref, "status": "accepted"}],
            },
            f"{mrn}-APPT", keep=("start", "end"),
        )
    return pid


def main():
    rows = []
    for p in PATIENTS:
        pid = seed_patient(*p)
        n_meds = len(fhir.search("MedicationRequest", {"subject": f"Patient/{pid}"}))
        n_appt = len(fhir.search("Appointment", {"actor": f"Patient/{pid}"}))
        rows.append((p[0], pid, n_meds, "yes" if n_appt else "no", p[8]))
    print(f"{'MRN':<9}{'Patient ID':<14}{'Meds':<6}{'Has appointment':<17}Discharge dx (ICD-10-CM)")
    for mrn, pid, n, a, dx in rows:
        print(f"{mrn:<9}{pid:<14}{n:<6}{a:<17}{dx}")


if __name__ == "__main__":
    main()
