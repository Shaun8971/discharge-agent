"""Thin wrapper over the FHIR REST API.

FHIR (Fast Healthcare Interoperability Resources) is a standard JSON-over-HTTP
format for health data. Each kind of record (Patient, Encounter, ...) is a
"resource" with its own endpoint, e.g. GET {base}/Patient/123.
"""
import requests

from config import FHIR_BASE_URL, FHIR_HEADERS

TIMEOUT = 15


class FhirError(Exception):
    """Raised when the FHIR server answers with an error status (anything other than 2xx).
    The message holds the HTTP method, URL, status code and the first 300 characters of the reply.
    """
    pass


def _check(resp: requests.Response) -> dict:
    """Return the JSON body of a FHIR response, or raise FhirError if the status is not 2xx.

    Args:
        resp (requests.Response): the response to check.

    Returns:
        dict: the parsed JSON body, or {} if the body is empty.

    Raises:
        FhirError: for any non-2xx status. The reply text is cut at 300 characters because
            error bodies can echo parts of a resource.
    """
    if not resp.ok:
        # Truncate: error bodies can echo resource content
        raise FhirError(f"{resp.request.method} {resp.url} -> {resp.status_code}: {resp.text[:300]}")
    return resp.json() if resp.content else {}


def get(resource_type: str, resource_id: str) -> dict:
    """Read one resource by its server-assigned ID (GET /Type/id).

    Args:
        resource_type (str): FHIR resource type, e.g. "Patient".
        resource_id (str): the ID the server gave the resource, e.g. "1000".

    Returns:
        dict: the full resource.

    Raises:
        FhirError: if the resource does not exist (404) or the server rejects the request.

    Example:
        >>> get("Patient", "1000")["name"][0]["family"]
        'Morgan'
    """
    return _check(requests.get(f"{FHIR_BASE_URL}/{resource_type}/{resource_id}", headers=FHIR_HEADERS, timeout=TIMEOUT))


def search(resource_type: str, params: dict) -> list[dict]:
    """Search one resource type and return the matching resources as a plain list.

    FHIR answers a search with a "Bundle" (a wrapper holding a list of entries); this unwraps it.
    Sends Cache-Control: no-cache because HAPI caches identical searches for about a minute.
    Only the first page of results is returned (HAPI's default page size).

    Args:
        resource_type (str): FHIR resource type, e.g. "Encounter".
        params (dict): search parameters, e.g. {"subject": "Patient/1000", "status": "finished"}.

    Returns:
        list[dict]: matching resources (empty list if none).

    Raises:
        FhirError: if the server rejects the search.

    Example:
        >>> [p["id"] for p in search("Patient", {"identifier": "urn:demo:mrn|MRN1001"})]
        ['1000']
    """
    # HAPI caches identical searches for ~1 minute; no-cache avoids stale "not found" answers
    headers = {**FHIR_HEADERS, "Cache-Control": "no-cache"}
    bundle = _check(requests.get(f"{FHIR_BASE_URL}/{resource_type}", params=params, headers=headers, timeout=TIMEOUT))
    return [e["resource"] for e in bundle.get("entry", [])]


def create(resource: dict) -> dict:
    """Create a new resource (POST /Type). The server assigns the ID.

    Args:
        resource (dict): the resource to create; must contain "resourceType".

    Returns:
        dict: the stored resource, including its new "id".

    Raises:
        FhirError: if the server rejects the resource.

    Example:
        >>> create({"resourceType": "Patient", "name": [{"family": "Created"}]})["id"]
        '1045'
    """
    rt = resource["resourceType"]
    return _check(requests.post(f"{FHIR_BASE_URL}/{rt}", json=resource, headers=FHIR_HEADERS, timeout=TIMEOUT))


def conditional_update(resource: dict, params: dict) -> dict:
    """PUT /Type?search-params. A "conditional update": if exactly one resource matches the search
    it is replaced, and if none match the resource is created. This makes seeding idempotent.

    Args:
        resource (dict): the resource to store; must contain "resourceType".
        params (dict): search parameters that identify the existing resource,
            e.g. {"identifier": "urn:demo:mrn|MRN1001"}.

    Returns:
        dict: the stored resource.

    Raises:
        FhirError: if the server rejects the request (for example if several resources match).

    Example:
        >>> a = conditional_update(tmp, {"identifier": "urn:demo:doc-example|X1"})
        >>> b = conditional_update(tmp, {"identifier": "urn:demo:doc-example|X1"})
        >>> a["id"] == b["id"]
        True
    """
    rt = resource["resourceType"]
    return _check(requests.put(f"{FHIR_BASE_URL}/{rt}", params=params, json=resource, headers=FHIR_HEADERS, timeout=TIMEOUT))


def update(resource: dict) -> dict:
    """Replace an existing resource whose ID you already know (PUT /Type/id).

    Args:
        resource (dict): the full new version; must contain "resourceType" and "id".

    Returns:
        dict: the stored resource.

    Raises:
        FhirError: if the server rejects the update.

    Example:
        >>> update({**patient, "name": [{"family": "Changed"}]})["name"][0]["family"]
        'Changed'
    """
    rt = resource["resourceType"]
    return _check(requests.put(f"{FHIR_BASE_URL}/{rt}/{resource['id']}", json=resource, headers=FHIR_HEADERS, timeout=TIMEOUT))


def count(resource_type: str, params: dict) -> int:
    """Count the resources that match a search without downloading them (_summary=count).
    Sends Cache-Control: no-cache so the number is current.

    Args:
        resource_type (str): FHIR resource type, e.g. "Appointment".
        params (dict): search parameters, e.g. {"_tag": "urn:demo:source|discharge-agent"}.

    Returns:
        int: the number of matches.

    Raises:
        FhirError: if the server rejects the search.

    Example:
        >>> count("Appointment", {})
        2
    """
    headers = {**FHIR_HEADERS, "Cache-Control": "no-cache"}
    bundle = _check(requests.get(f"{FHIR_BASE_URL}/{resource_type}", params={**params, "_summary": "count"}, headers=headers, timeout=TIMEOUT))
    return bundle.get("total", 0)
