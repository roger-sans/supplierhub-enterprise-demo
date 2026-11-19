"""Offline, versioned source intake with steward-owned identity decisions."""
import hashlib
import json
from datetime import timezone

from fastapi import HTTPException

from .governance import conflict, create_supplier, name_key, require, supplier, touch
from .store import audit, encode, insert, many, new_id, one, utcnow
from .types import SupplierFields


def stage(conn, envelope, actor, *, batch_id=None, received_at=None):
    require(actor, "steward")
    payload = envelope.model_dump(mode="json")
    payload["extracted_at"] = envelope.extracted_at.astimezone(timezone.utc).isoformat()
    payload["records"].sort(key=lambda row: row["external_key"])
    digest = hashlib.sha256(encode(payload).encode()).hexdigest()
    existing = one(conn, "SELECT id FROM import_batches WHERE digest=?", (digest,))
    if existing:
        return batch(conn, existing["id"]), False
    batch_id = batch_id or new_id("BAT")
    insert(conn, "import_batches", id=batch_id, digest=digest, source=envelope.source,
           extracted_at=payload["extracted_at"], received_at=received_at or utcnow(), actor=actor)
    for row in payload["records"]:
        mapping = one(conn, "SELECT supplier_id FROM source_links WHERE source=? AND external_key=?",
                      (envelope.source, row["external_key"]))
        canonical = supplier(conn, mapping["supplier_id"]) if mapping else None
        unchanged = canonical and all(canonical[key] == row[key] for key in ("name", "country", "registration", "category"))
        insert(conn, "import_rows", batch_id=batch_id, external_key=row["external_key"], payload=encode(row),
               supplier_id=canonical["id"] if unchanged else None,
               disposition="already_linked" if unchanged else "pending")
    audit(conn, None, actor, "identity.batch_staged", batch_id,
          after={"source": envelope.source, "records": len(payload["records"]), "digest": digest}, time=received_at)
    return batch(conn, batch_id), True


def batch(conn, batch_id):
    info = one(conn, "SELECT * FROM import_batches WHERE id=?", (batch_id,))
    if not info:
        raise HTTPException(404, "Import batch was not found.")
    entries = many(conn, "SELECT * FROM import_rows WHERE batch_id=? ORDER BY external_key", (batch_id,))
    for entry in entries:
        record = json.loads(entry.pop("payload"))
        entry["record"] = record
        link = one(conn, "SELECT supplier_id FROM source_links WHERE source=? AND external_key=?",
                   (info["source"], entry["external_key"]))
        candidates = many(conn, """
            SELECT id, name, country, registration, CASE WHEN registration=? THEN 'Registration' ELSE 'Normalised name' END AS match
            FROM suppliers WHERE country=? AND (registration=? OR name_key=?)
            ORDER BY CASE WHEN registration=? THEN 0 ELSE 1 END, name
        """, (record["registration"], record["country"], record["registration"], name_key(record["name"]), record["registration"]))
        if link:
            linked = supplier(conn, link["supplier_id"])
            candidates = [{"id": linked["id"], "name": linked["name"], "country": linked["country"],
                           "registration": linked["registration"], "match": "Existing source link"}] + [
                item for item in candidates if item["id"] != linked["id"]
            ]
        entry["candidates"] = candidates
    return {**info, "rows": entries}


def resolve(conn, batch_id, external_key, data, actor, as_of):
    require(actor, "steward")
    info = batch(conn, batch_id)
    entry = next((row for row in info["rows"] if row["external_key"] == external_key), None)
    if not entry:
        raise HTTPException(404, "Source record was not found.")
    if entry["disposition"] != "pending":
        conflict("This source record has already been resolved.")
    source = info["source"]
    record = entry["record"]
    old_link = one(conn, "SELECT supplier_id FROM source_links WHERE source=? AND external_key=?", (source, external_key))
    supplier_id = None
    if data.action == "dismiss":
        disposition = "dismissed"
    elif data.action == "create":
        if old_link or entry["candidates"]:
            conflict("Resolve candidate matches before creating a new legal entity.")
        fields = SupplierFields(**{key: record[key] for key in ("name", "country", "registration", "category")},
                                segment="standard", risk="medium", payment_days=30, currency="EUR")
        supplier_id = create_supplier(conn, fields, actor, as_of)["id"]
        disposition = "created"
    else:
        canonical = supplier(conn, data.supplier_id)
        supplier_id = canonical["id"]
        if old_link and old_link["supplier_id"] != supplier_id:
            conflict("An existing source identity cannot be remapped.")
        if any(canonical[key] != record[key] for key in ("country", "registration")):
            conflict("Linking requires the same country and registration. Dismiss conflicting source data.")
        disposition = "linked"
    if supplier_id and not old_link:
        insert(conn, "source_links", source=source, external_key=external_key, supplier_id=supplier_id,
               batch_id=batch_id, linked_at=utcnow())
        touch(conn, supplier(conn, supplier_id))
    conn.execute("""
        UPDATE import_rows SET disposition=?, supplier_id=?, resolved_by=?, reason=?
        WHERE batch_id=? AND external_key=?
    """, (disposition, supplier_id, actor, data.reason, batch_id, external_key))
    audit(conn, supplier_id, actor, f"identity.{disposition}", f"{batch_id}/{external_key}",
          {"disposition": "pending"},
          {"source": source, "external_key": external_key, "supplier_id": supplier_id, "reason": data.reason})
    return batch(conn, batch_id)
