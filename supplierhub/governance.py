"""Supplier lifecycle, cross-functional decision rights, evidence and sourcing."""
import re
import unicodedata

from fastapi import HTTPException

from .store import audit, insert, many, new_id, one, utcnow

ACTORS = {
    "buyer": {"label": "Sourcing buyer", "role": "Buyer"},
    "procurement": {"label": "Procurement lead", "role": "Procurement"},
    "finance": {"label": "Finance controller", "role": "Finance"},
    "operations": {"label": "Operations planner", "role": "Operations"},
    "quality": {"label": "Quality engineer", "role": "Quality"},
    "legal": {"label": "Legal reviewer", "role": "Legal"},
    "steward": {"label": "Data steward", "role": "Data Governance"},
}
GATES = {
    "procurement": "supplier_profile", "finance": "financial_review",
    "operations": "capacity_check", "quality": "quality_certificate", "legal": "legal_clearance",
}
INCIDENT_OWNER = {"delivery": "operations", "quality": "quality", "financial": "finance", "compliance": "legal"}
REGIONS = {
    "BE": "Western Europe", "DE": "Central Europe", "ES": "Southern Europe",
    "FI": "Northern Europe", "FR": "Western Europe", "GB": "Northern Europe",
    "IE": "Northern Europe", "NL": "Western Europe", "PL": "Central Europe",
    "PT": "Southern Europe", "SE": "Northern Europe",
}
NEXT_STAGE = {
    "discovery": {"qualification", "closed"}, "qualification": {"commercial", "closed"},
    "commercial": {"awarded", "closed"}, "awarded": {"closed"}, "closed": set(),
}


def require(actor, *allowed):
    if actor not in allowed:
        raise HTTPException(403, "This simulated role cannot perform that action.")


def conflict(message):
    raise HTTPException(409, message)


def supplier(conn, supplier_id, revision=None):
    row = one(conn, "SELECT * FROM suppliers WHERE id = ?", (supplier_id,))
    if row is None:
        raise HTTPException(404, "Supplier was not found.")
    if revision is not None and row["revision"] != revision:
        conflict("The supplier changed. Reload the record before resubmitting.")
    return row


def name_key(name):
    plain = unicodedata.normalize("NFKD", name.casefold())
    letters = "".join(char for char in plain if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", "", letters)


def gate_roles(risk):
    return tuple(GATES) if risk == "high" else tuple(role for role in GATES if role != "legal")


def master_values(fields):
    data = fields.model_dump(include={
        "name", "country", "registration", "category", "segment", "risk", "payment_days", "currency",
    })
    data["name_key"] = name_key(data["name"])
    data["region"] = REGIONS[data["country"]]
    if not data["name_key"]:
        raise HTTPException(422, "Supplier names require at least one Latin letter or digit.")
    return data


def has_registration(conn, country, registration, ignore_id=""):
    return one(conn, "SELECT id FROM suppliers WHERE country=? AND registration=? AND id<>?",
               (country, registration, ignore_id))


def create_supplier(conn, fields, actor, as_of):
    require(actor, "buyer", "steward")
    values = master_values(fields)
    if has_registration(conn, fields.country, fields.registration):
        conflict("A supplier with this country and registration already exists. Reconcile the identity.")
    row = {
        "id": new_id("SUP"), **values, "owner": "buyer", "state": "draft",
        "revision": 1, "cycle": 0, "opened_on": as_of.isoformat(),
    }
    insert(conn, "suppliers", **row)
    audit(conn, row["id"], actor, "supplier.created", row["id"], after=row)
    return row


def touch(conn, row, **changes):
    changes["revision"] = row["revision"] + 1
    columns = ", ".join(f"{key} = ?" for key in changes)
    conn.execute(f"UPDATE suppliers SET {columns} WHERE id = ?", (*changes.values(), row["id"]))
    return {**row, **changes}


def edit_supplier(conn, supplier_id, data, actor):
    require(actor, "buyer", "steward")
    row = supplier(conn, supplier_id, data.revision)
    if row["state"] == "in_review":
        conflict("Return the open review before editing master data.")
    if has_registration(conn, data.country, data.registration, supplier_id):
        conflict("A supplier with this country and registration already exists.")
    values = master_values(data)
    changes = {key: value for key, value in values.items() if value != row[key]}
    if not changes:
        conflict("There are no master data changes to save.")
    if {"country", "registration"} & changes.keys():
        if one(conn, "SELECT source FROM source_links WHERE supplier_id=?", (supplier_id,)):
            conflict("Linked legal identity is immutable in this demo. Escalate to the data steward.")
    if row["state"] == "approved":
        changes["state"] = "draft"
    updated = touch(conn, row, **changes)
    audit(conn, supplier_id, actor, "supplier.edited", supplier_id, row, {**updated, "reason": data.reason})
    return updated


def gate_snapshot(conn, row, as_of):
    evidence = many(conn, "SELECT * FROM evidence WHERE supplier_id=? ORDER BY valid_until DESC, id", (row["id"],))
    reviews = many(conn, "SELECT * FROM reviews WHERE supplier_id=? AND cycle=?", (row["id"], row["cycle"]))
    assigned = {review["role"]: review for review in reviews}
    available = {}
    for item in evidence:
        if item["valid_until"] >= as_of.isoformat():
            available.setdefault(item["kind"], item)
    return [{
        "role": role, "kind": GATES[role], "evidence": available.get(GATES[role]),
        "status": "pending" if role in assigned else "not_started", **assigned.get(role, {}),
    } for role in gate_roles(row["risk"])]


def has_blocker(conn, supplier_id):
    return one(conn, "SELECT id FROM incidents WHERE supplier_id=? AND state='open' AND severity='critical'",
               (supplier_id,)) is not None


def submit(conn, supplier_id, data, actor, as_of):
    require(actor, "buyer")
    row = supplier(conn, supplier_id, data.revision)
    if row["state"] not in {"draft", "changes_requested", "suspended"}:
        conflict("Only draft, returned or suspended suppliers can enter review.")
    if has_blocker(conn, supplier_id):
        conflict("Close critical incidents before starting a review.")
    if not any(gate["evidence"] for gate in gate_snapshot(conn, row, as_of) if gate["role"] == "procurement"):
        conflict("A current supplier profile is required before submitting.")
    cycle = row["cycle"] + 1
    for role in gate_roles(row["risk"]):
        insert(conn, "reviews", supplier_id=supplier_id, cycle=cycle, role=role, status="pending")
    updated = touch(conn, row, state="in_review", cycle=cycle)
    audit(conn, supplier_id, actor, "review.submitted", supplier_id, row, {**updated, "reason": data.reason})
    return updated


def decide(conn, supplier_id, data, actor, as_of):
    require(actor, *GATES)
    row = supplier(conn, supplier_id, data.revision)
    if row["state"] != "in_review":
        conflict("This review is closed.")
    gates = gate_snapshot(conn, row, as_of)
    gate = next((item for item in gates if item["role"] == actor), None)
    if not gate or gate["status"] != "pending":
        conflict("This role has no pending gate for the current cycle.")
    if data.decision == "approve":
        if not gate["evidence"]:
            conflict("Add current evidence for this gate before approving.")
        if has_blocker(conn, supplier_id):
            conflict("Close the critical incident before approving.")
        now_approved = [item for item in gates if item["role"] == actor or item["status"] == "approved"]
        if len(now_approved) == len(gates) and any(not item["evidence"] for item in now_approved):
            conflict("At least one approval has expired evidence. Replace the evidence before activation.")
        result = "approved"
        new_state = "approved" if len(now_approved) == len(gates) else "in_review"
    else:
        result = "returned"
        new_state = "changes_requested"
    timestamp = utcnow()
    conn.execute("""
        UPDATE reviews SET status=?, decided_by=?, reason=?, decided_at=?
        WHERE supplier_id=? AND cycle=? AND role=?
    """, (result, actor, data.reason, timestamp, supplier_id, row["cycle"], actor))
    updated = touch(conn, row, state=new_state)
    audit(conn, supplier_id, actor, f"review.{result}", f"{supplier_id}/{row['cycle']}/{actor}",
          {"state": row["state"], "gate": "pending"},
          {"state": new_state, "reason": data.reason, "gate": result,
           "evidence_id": gate["evidence"]["id"] if gate["evidence"] else None}, time=timestamp)
    return updated


def add_evidence(conn, supplier_id, data, actor, as_of):
    gate_role = next(role for role, kind in GATES.items() if kind == data.kind)
    require(actor, gate_role, *("buyer",) if gate_role == "procurement" else ())
    row = supplier(conn, supplier_id, data.revision)
    if data.valid_until < as_of:
        conflict("New evidence must be current on the workspace business date.")
    if one(conn, "SELECT id FROM evidence WHERE supplier_id=? AND kind=? AND ref=?",
           (supplier_id, data.kind, data.ref)):
        conflict("This evidence reference is already registered.")
    item = {
        "id": new_id("DOC"), "supplier_id": supplier_id, **data.model_dump(mode="json", exclude={"revision"}),
        "created_by": actor, "created_at": utcnow(),
    }
    insert(conn, "evidence", **item)
    touch(conn, row)
    audit(conn, supplier_id, actor, "evidence.registered", item["id"], after=item)
    return item


def open_incident(conn, supplier_id, data, actor, as_of):
    require(actor, "buyer", "procurement", INCIDENT_OWNER[data.kind])
    row = supplier(conn, supplier_id, data.revision)
    if data.due_on < as_of:
        conflict("The remediation due date is earlier than the workspace business date.")
    item = {
        "id": new_id("INC"), "supplier_id": supplier_id, **data.model_dump(mode="json", exclude={"revision"}),
        "owner": INCIDENT_OWNER[data.kind], "state": "open", "opened_at": utcnow(),
    }
    insert(conn, "incidents", **item)
    new_state = "suspended" if data.severity == "critical" and row["state"] in {"approved", "in_review"} else row["state"]
    touch(conn, row, state=new_state)
    audit(conn, supplier_id, actor, "incident.opened", item["id"], {"state": row["state"]},
          {**item, "supplier_state": new_state})
    return item


def close_incident(conn, supplier_id, incident_id, data, actor):
    row = supplier(conn, supplier_id, data.revision)
    item = one(conn, "SELECT * FROM incidents WHERE id=? AND supplier_id=?", (incident_id, supplier_id))
    if not item:
        raise HTTPException(404, "Incident was not found.")
    require(actor, item["owner"])
    if item["state"] != "open":
        conflict("This incident is already closed.")
    conn.execute("UPDATE incidents SET state='closed', resolution=? WHERE id=?", (data.reason, incident_id))
    updated = {**item, "state": "closed", "resolution": data.reason}
    touch(conn, row)
    audit(conn, supplier_id, actor, "incident.closed", incident_id, item, updated)
    return updated


def add_agreement(conn, supplier_id, data, actor):
    require(actor, "buyer", "procurement")
    row = supplier(conn, supplier_id, data.revision)
    if one(conn, "SELECT id FROM agreements WHERE ref=?", (data.ref,)):
        conflict("That agreement reference is already in use.")
    item = {
        "id": new_id("AGR"), "supplier_id": supplier_id, **data.model_dump(mode="json", exclude={"revision"}),
        "state": "proposed",
    }
    insert(conn, "agreements", **item)
    touch(conn, row)
    audit(conn, supplier_id, actor, "agreement.proposed", item["id"], after=item)
    return item


def decide_agreement(conn, supplier_id, agreement_id, data, actor, as_of):
    require(actor, "legal")
    row = supplier(conn, supplier_id, data.revision)
    item = one(conn, "SELECT * FROM agreements WHERE id=? AND supplier_id=?", (agreement_id, supplier_id))
    if not item:
        raise HTTPException(404, "Agreement was not found.")
    if (item["state"], data.state) not in {("proposed", "effective"), ("proposed", "retired"), ("effective", "retired")}:
        conflict("This agreement transition is unavailable.")
    if data.state == "effective" and item["ends_on"] < as_of.isoformat():
        conflict("An expired agreement cannot be activated.")
    conn.execute("UPDATE agreements SET state=? WHERE id=?", (data.state, agreement_id))
    updated = {**item, "state": data.state}
    touch(conn, row)
    audit(conn, supplier_id, actor, f"agreement.{data.state}", agreement_id, item, {**updated, "reason": data.reason})
    return updated


def is_qualified(conn, row, as_of):
    return (row["state"] == "approved" and not has_blocker(conn, row["id"])
            and all(gate["status"] == "approved" and gate["evidence"] for gate in gate_snapshot(conn, row, as_of)))


def add_initiative(conn, data, actor):
    require(actor, "buyer", "procurement")
    row = supplier(conn, data.supplier_id)
    item = {
        "id": new_id("SRC"), **data.model_dump(mode="json"), "stage": "discovery",
        "owner": actor, "revision": 1,
    }
    insert(conn, "initiatives", **item)
    audit(conn, row["id"], actor, "sourcing.created", item["id"], after=item)
    return item


def move_initiative(conn, initiative_id, data, actor, as_of):
    require(actor, "buyer", "procurement")
    row = one(conn, "SELECT * FROM initiatives WHERE id=?", (initiative_id,))
    if not row:
        raise HTTPException(404, "Sourcing initiative was not found.")
    if row["revision"] != data.revision:
        conflict("The sourcing initiative changed. Reload it before resubmitting.")
    if data.stage not in NEXT_STAGE[row["stage"]]:
        conflict("Follow the next stage or close the initiative.")
    if data.stage == "awarded":
        require(actor, "procurement")
        if not is_qualified(conn, supplier(conn, row["supplier_id"]), as_of):
            conflict("Award requires a qualified supplier with current evidence and no critical incident.")
        today = as_of.isoformat()
        if not one(conn, """
            SELECT id FROM agreements WHERE supplier_id=? AND state='effective' AND starts_on<=? AND ends_on>=?
        """, (row["supplier_id"], today, today)):
            conflict("Award requires a current effective agreement.")
    updated = {**row, "stage": data.stage, "revision": row["revision"] + 1}
    conn.execute("UPDATE initiatives SET stage=?, revision=? WHERE id=?", (data.stage, updated["revision"], initiative_id))
    audit(conn, row["supplier_id"], actor, "sourcing.moved", initiative_id, row, {**updated, "reason": data.reason})
    return updated
