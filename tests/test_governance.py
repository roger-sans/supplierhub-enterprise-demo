from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from supplierhub.app import create_app
from supplierhub.store import Store

SUP = "/api/suppliers/"
PRODUCT = "/api/v1/products/qualified-suppliers"
WHY = "Synthetic evidence checked against the acceptance rule."


def request(client, path, actor, payload, method="POST"):
    return client.request(method, path, headers={"X-Demo-Actor": actor}, json=payload)


def detail(client, supplier):
    return client.get(SUP + supplier).json()


def mutate(client, supplier, suffix, actor, **payload):
    data = {"revision": detail(client, supplier)["revision"], **payload}
    return request(client, SUP + supplier + "/" + suffix, actor, data)


def decide(client, supplier, actor, action="approve"):
    return mutate(client, supplier, "decisions", actor, decision=action, reason=WHY)


def add_document(client, supplier, actor, kind, ref):
    return mutate(client, supplier, "evidence", actor, kind=kind, ref=ref, title="Synthetic renewal evidence",
                  valid_until="2027-01-01")


def published(client):
    return {row["supplier_id"] for row in client.get(PRODUCT).json()["records"]}


def test_baseline_publication_and_directory(client):
    health = client.get("/api/health")
    assert health.json() == {"status": "ready", "data_class": "synthetic", "as_of": "2026-11-01", "fixture_version": "1.0"}
    assert health.headers["x-request-id"]
    assert client.get(SUP).status_code == 200
    listing = client.get(SUP, params={"q": "aster", "state": "in_review"}).json()
    assert listing["total"] == 1 and listing["rows"][0]["id"] == "SUP-001"
    assert len(published(client)) == 18
    assert "SUP-010" not in published(client)
    assert set(client.get("/api/data-health").json()["approved_held"]) == {"SUP-010", "SUP-026"}


def test_current_evidence_or_approval_is_blocked(client):
    assert decide(client, "SUP-001", "buyer").status_code == 403
    blocked = decide(client, "SUP-001", "quality")
    assert blocked.status_code == 409 and "current evidence" in blocked.json()["detail"].lower()
    assert add_document(client, "SUP-001", "buyer", "quality_certificate", "DEMO-NQ-001").status_code == 403
    response = add_document(client, "SUP-001", "quality", "quality_certificate", "DEMO-NQ-001")
    assert response.status_code == 201
    assert decide(client, "SUP-001", "quality").status_code == 200
    assert decide(client, "SUP-001", "operations").status_code == 200
    response = decide(client, "SUP-001", "finance")
    assert response.status_code == 200 and response.json()["state"] == "approved"
    assert "SUP-001" in published(client)
    assert any(event["after"].get("evidence_id") for event in detail(client, "SUP-001")["audit"]
               if event["action"] == "review.approved")


def test_high_risk_requires_legal_and_uses_independent_reviewer(client):
    assert decide(client, "SUP-002", "buyer").status_code == 403
    assert decide(client, "SUP-002", "procurement").status_code == 409  # Existing approval cannot be repeated.
    for actor, kind in (("operations", "capacity_check"), ("quality", "quality_certificate"), ("legal", "legal_clearance")):
        gate = next(item for item in detail(client, "SUP-002")["gates"] if item["role"] == actor)
        if not gate["evidence"]:
            assert add_document(client, "SUP-002", actor, kind, f"DEMO-REF-{actor.upper()}").status_code == 201
        response = decide(client, "SUP-002", actor)
        assert response.status_code == 200
        assert response.json()["state"] == ("approved" if actor == "legal" else "in_review")
    assert "SUP-002" in published(client)


def test_return_starts_clean_cycle(client):
    assert decide(client, "SUP-001", "finance", "return").json()["state"] == "changes_requested"
    assert decide(client, "SUP-001", "operations").status_code == 409
    submitted = mutate(client, "SUP-001", "submit", "buyer", reason=WHY)
    assert submitted.json()["cycle"] == 2
    row = detail(client, "SUP-001")
    assert all(gate["status"] == "pending" for gate in row["gates"])
    assert any(event["action"] == "review.returned" for event in row["audit"])


def test_critical_incident_suspends_and_remediation_requires_new_review(client):
    assert "SUP-005" in published(client)
    response = mutate(client, "SUP-005", "incidents", "quality", title="Synthetic review failure", kind="quality",
                      severity="critical", due_on="2026-11-10")
    assert response.status_code == 201
    incident = response.json()["id"]
    assert detail(client, "SUP-005")["state"] == "suspended"
    assert "SUP-005" not in published(client)
    assert mutate(client, "SUP-005", "submit", "buyer", reason=WHY).status_code == 409
    path = f"incidents/{incident}/close"
    assert mutate(client, "SUP-005", path, "buyer", reason=WHY).status_code == 403
    assert mutate(client, "SUP-005", path, "quality", reason=WHY).status_code == 200
    assert "SUP-005" not in published(client)
    assert mutate(client, "SUP-005", "submit", "buyer", reason=WHY).json()["state"] == "in_review"


def test_sourcing_award_requires_procurement_and_agreement(client):
    opened = request(client, "/api/sourcing", "buyer", {
        "supplier_id": "SUP-020", "title": "Sleeve sourcing", "item_family": "Machined sleeves", "target_on": "2026-11-28",
    }).json()
    path = f"/api/sourcing/{opened['id']}/move"
    for revision, stage in enumerate(("qualification", "commercial"), 1):
        assert request(client, path, "buyer", {"revision": revision, "stage": stage, "reason": WHY}).status_code == 200
    payload = {"revision": 3, "stage": "awarded", "reason": WHY}
    assert request(client, path, "buyer", payload).status_code == 403
    assert "agreement" in request(client, path, "procurement", payload).json()["detail"].lower()
    response = mutate(client, "SUP-020", "agreements", "buyer", title="Sleeves agreement", ref="DEMO-AG-9900",
                      starts_on="2026-11-01", ends_on="2027-12-01", annual_value=50000, currency="EUR")
    assert response.status_code == 201
    activate = "agreements/" + response.json()["id"] + "/decisions"
    assert mutate(client, "SUP-020", activate, "procurement", state="effective", reason=WHY).status_code == 403
    assert mutate(client, "SUP-020", activate, "legal", state="effective", reason=WHY).status_code == 200
    assert request(client, path, "procurement", payload).json()["stage"] == "awarded"


def test_concurrent_requests_use_single_revision(client):
    rev = detail(client, "SUP-001")["revision"]
    payload = {"revision": rev, "decision": "approve", "reason": WHY}
    with ThreadPoolExecutor(max_workers=2) as pool:
        states = list(pool.map(lambda actor: request(client, SUP+"SUP-001/decisions", actor, payload).status_code,
                               ["finance", "operations"]))
    assert sorted(states) == [200, 409]
    assert detail(client, "SUP-001")["revision"] == rev + 1


def test_master_edit_invalidates_qualification_and_survives_restart(client, db_path):
    live = detail(client, "SUP-005")
    fields = {field: live[field] for field in ("name", "country", "registration", "category", "segment", "risk", "payment_days", "currency")}
    fields.update(revision=live["revision"], reason=WHY, registration="DEMO-S025")
    assert request(client, SUP+"SUP-005", "steward", fields, "PATCH").status_code == 409
    fields.update(registration=live["registration"], payment_days=90)
    assert request(client, SUP+"SUP-005", "buyer", fields, "PATCH").json()["state"] == "draft"
    with TestClient(create_app(db_path)) as restarted:
        assert detail(restarted, "SUP-005")["payment_days"] == 90
        assert "SUP-005" not in published(restarted)
        assert restarted.get(SUP).json()["total"] == 36


def test_failed_scope_does_not_write_audit(client, db_path):
    with Store(db_path).connect() as connection:
        before = connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0]
    assert decide(client, "SUP-001", "legal").status_code == 409
    with Store(db_path).connect() as connection:
        assert connection.execute("SELECT COUNT(*) FROM audit_events").fetchone()[0] == before


def test_duplicate_supplier_is_rejected_and_draft_requires_profile(client):
    fields = {"name": "Hollow Wren Components", "country": "DE", "registration": "DEMO-R0001",
              "category": "Components", "segment": "standard", "risk": "low", "payment_days": 30, "currency": "EUR"}
    assert request(client, SUP, "buyer", fields).status_code == 409
    fields["registration"] = "DEMO-HW91"
    created = request(client, SUP, "buyer", fields)
    assert created.status_code == 201
    sid = created.json()["id"]
    assert mutate(client, sid, "submit", "buyer", reason=WHY).status_code == 409
    assert add_document(client, sid, "buyer", "supplier_profile", "DEMO-NEW-PROFILE").status_code == 201
    assert mutate(client, sid, "submit", "buyer", reason=WHY).status_code == 200


def test_wrong_sourcing_jump_and_stale_agreement_date_are_rejected(client):
    assert request(client, "/api/sourcing/SRC-001/move", "procurement",
                   {"revision": 1, "stage": "awarded", "reason": WHY}).status_code == 409
    assert mutate(client, "SUP-003", "agreements", "buyer", title="Bad dates agreement", ref="DEMO-BAD-900",
                  starts_on="2027-02-01", ends_on="2027-01-01", currency="EUR", annual_value=36000).status_code == 422
