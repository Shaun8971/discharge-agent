"""Thin wrapper over the FHIR REST API.

FHIR (Fast Healthcare Interoperability Resources) is a standard JSON-over-HTTP
format for health data. Each kind of record (Patient, Encounter, ...) is a
"resource" with its own endpoint, e.g. GET {base}/Patient/123.
"""
import requests

from config import FHIR_BASE_URL, FHIR_HEADERS

TIMEOUT = 15


class FhirError(Exception):
    pass


def _check(resp: requests.Response) -> dict:
    if not resp.ok:
        # Truncate: error bodies can echo resource content
        raise FhirError(f"{resp.request.method} {resp.url} -> {resp.status_code}: {resp.text[:300]}")
    return resp.json() if resp.content else {}


def get(resource_type: str, resource_id: str) -> dict:
    """Read one resource by its server-assigned ID."""
    return _check(requests.get(f"{FHIR_BASE_URL}/{resource_type}/{resource_id}", headers=FHIR_HEADERS, timeout=TIMEOUT))


def search(resource_type: str, params: dict) -> list[dict]:
    """Search a resource type. FHIR returns a 'Bundle'; we unwrap it to a list of resources."""
    # HAPI caches identical searches for ~1 minute; no-cache avoids stale "not found" answers
    headers = {**FHIR_HEADERS, "Cache-Control": "no-cache"}
    bundle = _check(requests.get(f"{FHIR_BASE_URL}/{resource_type}", params=params, headers=headers, timeout=TIMEOUT))
    return [e["resource"] for e in bundle.get("entry", [])]


def create(resource: dict) -> dict:
    """POST a new resource; the server assigns its ID."""
    rt = resource["resourceType"]
    return _check(requests.post(f"{FHIR_BASE_URL}/{rt}", json=resource, headers=FHIR_HEADERS, timeout=TIMEOUT))


def conditional_update(resource: dict, params: dict) -> dict:
    """PUT /Type?search-params. A 'conditional update': if exactly one match exists it is
    replaced; if none, the resource is created. This is what makes seeding idempotent."""
    rt = resource["resourceType"]
    return _check(requests.put(f"{FHIR_BASE_URL}/{rt}", params=params, json=resource, headers=FHIR_HEADERS, timeout=TIMEOUT))


def update(resource: dict) -> dict:
    """PUT /Type/id: replace an existing resource whose ID we already know."""
    rt = resource["resourceType"]
    return _check(requests.put(f"{FHIR_BASE_URL}/{rt}/{resource['id']}", json=resource, headers=FHIR_HEADERS, timeout=TIMEOUT))
