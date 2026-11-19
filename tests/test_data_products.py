import json
from decimal import Decimal
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from sqlglot import parse_one
from sqlglot.expressions import Create

from scripts.check_warehouse import run
from scripts.export_contracts import CONTRACTS, schema
from scripts.export_warehouse import export
from supplierhub.store import Store
from supplierhub.types import SourceEnvelope

ROOT = Path(__file__).resolve().parents[1]
HEADERS = {"X-Demo-Actor": "steward"}
BATCHES = "/api/identity/batches"


def contract_example():
    return json.loads((ROOT / "contracts" / "examples" / "supplier-source.v1.json").read_text())


def resolve(client, batch_id, key, action, supplier=None):
    return client.post(f"{BATCHES}/{batch_id}/rows/{key}/resolve", headers=HEADERS, json={
        "action": action, "reason": "The simulated business registration was reviewed.",
        **({"supplier_id": supplier} if supplier else {}),
    })


def test_inbound_contract_and_digest_replay(client):
    example = contract_example()
    record = {**example["records"][0], "external_key": "DEMO-ERP-505", "registration": "DEMO-R9505"}
    example["records"].append(record)
    first = client.post(BATCHES, headers=HEADERS, json=example)
    assert first.status_code == 201
    assert all(row["disposition"] == "pending" for row in first.json()["rows"])
    example["records"].reverse()
    example["extracted_at"] = "2026-11-01T08:00:00+01:00"
    replay = client.post(BATCHES, headers=HEADERS, json=example)
    assert replay.status_code == 200 and replay.json()["id"] == first.json()["id"]
    assert client.get("/api/suppliers").json()["total"] == 36


def test_identity_candidates_never_auto_merge_and_lineage_is_recorded(client):
    info = client.get(BATCHES).json()[0]
    batch_id = info["id"]
    link, name_only, new = client.get(BATCHES + "/" + batch_id).json()["rows"]
    assert link["candidates"][0]["match"] == "Registration"
    assert link["disposition"] == "pending"
    assert name_only["candidates"][0]["match"] == "Normalised name"
    assert resolve(client, batch_id, name_only["external_key"], "create").status_code == 409
    assert resolve(client, batch_id, name_only["external_key"], "link", "SUP-003").status_code == 409
    assert resolve(client, batch_id, name_only["external_key"], "dismiss").status_code == 200
    assert resolve(client, batch_id, link["external_key"], "link", "SUP-001").status_code == 200
    assert resolve(client, batch_id, link["external_key"], "link", "SUP-001").status_code == 409
    result = resolve(client, batch_id, new["external_key"], "create")
    assert result.status_code == 200
    supplier_id = next(row["supplier_id"] for row in result.json()["rows"] if row["disposition"] == "created")
    assert client.get(f"/api/suppliers/{supplier_id}").json()["state"] == "draft"
    supplier = client.get("/api/suppliers/SUP-001").json()
    assert supplier["name"] == "Aster Vale Components"
    assert supplier["source_links"][0]["external_key"] == "DEMO-CAT-201"


def test_conflicting_data_for_existing_source_key_cannot_remap(client):
    body = contract_example()
    body["records"][0]["external_key"] = "DEMO-ERP-001"
    staged = client.post(BATCHES, headers=HEADERS, json=body).json()
    incoming = staged["rows"][0]
    assert incoming["disposition"] == "pending"
    assert incoming["candidates"][0]["match"] == "Existing source link"
    assert resolve(client, staged["id"], incoming["external_key"], "link", "SUP-001").status_code == 409
    assert resolve(client, staged["id"], incoming["external_key"], "create").status_code == 409


def test_source_rejects_bad_scope_unknown_fields_duplicate_keys_and_naive_time(client):
    canonical = contract_example()
    assert client.post(BATCHES, headers={"X-Demo-Actor": "buyer"}, json=canonical).status_code == 403
    body = contract_example()
    body["records"][0]["bank_account"] = "example"
    assert client.post(BATCHES, headers=HEADERS, json=body).status_code == 422
    body = contract_example()
    body["records"].append(body["records"][0])
    assert client.post(BATCHES, headers=HEADERS, json=body).status_code == 422
    body = contract_example()
    body["extracted_at"] = "2026-11-01T07:00:00"
    assert client.post(BATCHES, headers=HEADERS, json=body).status_code == 422


def test_json_schemas_and_live_output_agree(client):
    for name, model in CONTRACTS.items():
        spec = json.loads((ROOT / "contracts" / f"{name}.v1.schema.json").read_text())
        assert spec == schema(name, model)
        Draft202012Validator.check_schema(spec)
    data = client.get("/api/v1/products/qualified-suppliers").json()
    validator = Draft202012Validator(schema("qualified-suppliers", CONTRACTS["qualified-suppliers"]), format_checker=FormatChecker())
    validator.validate(data)
    assert Draft202012Validator(schema("supplier-source", SourceEnvelope)).is_valid(contract_example())
    assert {key for record in data["records"] for key in record} == {
        "supplier_id", "name", "country", "category", "segment", "risk", "payment_days", "currency",
    }


def test_weighted_metrics_and_missing_evidence(client, db_path):
    with Store(db_path).connect(write=True) as conn:
        conn.execute("DELETE FROM observations WHERE supplier_id='SUP-005'")
        conn.executemany("""
            INSERT INTO observations VALUES ('SUP-005',?,?,?,?,?,?,?,?)
        """, [
            ("2026-09-01", 10, 0, 2, 2, 1, 1, "2026-09-30T00:00:00Z"),
            ("2026-10-01", 90, 90, 6, 6, 1, 1, "2026-10-31T00:00:00Z"),
        ])
    rows = client.get("/api/scorecards").json()["rows"]
    score = next(row for row in rows if row["supplier_id"] == "SUP-005")
    assert (score["delivery_pct"], score["quality_pct"], score["compliance_pct"], score["score"]) == (90, None, None, None)
    assert score["delivery_base"] == 100 and score["quality_base"] == 8


def test_actual_warehouse_sql_matches_live_service(client, db_path, tmp_path):
    dimension, fact = export(Store(db_path), tmp_path)
    quality, scores = run(tmp_path)
    live = {row["supplier_id"]: row["score"] for row in client.get("/api/scorecards").json()["rows"]}
    shipped = {row["supplier_id"] for row in client.get("/api/v1/products/qualified-suppliers").json()["records"]}
    assert dimension == len(shipped) == len(scores) and fact == 142
    assert all(value == 0 for value in quality.values())
    assert {sid: float(value) if isinstance(value, Decimal) else value for sid, value in scores.items()} == {
        sid: live[sid] for sid in shipped
    }
    assert isinstance(parse_one((ROOT / "warehouse/snowflake/03_scorecards.sql").read_text(), read="snowflake"), Create)
