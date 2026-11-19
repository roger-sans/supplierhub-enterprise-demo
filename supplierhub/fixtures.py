"""Original, reproducible fixtures for an imaginary industrial supply network."""
from datetime import date, timedelta
from random import Random

from .governance import GATES, REGIONS, gate_roles, name_key
from .identity import stage as stage_batch
from .store import audit, insert, one
from .types import SourceEnvelope

NAMES = (
    "Aster Vale Components", "Kestrel Arc Materials", "Nordlume Precision", "Morrow Bend Packaging",
    "Rillcrest Motion", "Fable Quay Freight", "Meridian Grove Services", "Cinderwold Alloys",
    "Lintel Beacon Systems", "Alba Tessera Materials", "Fjordmoss Components", "Harrowspan Freight",
    "Vellum Birch Packaging", "Quillstone Services", "Iverfen Castings", "Orchard Spur Components",
    "Lattice Maren Materials", "Solmere Freight", "Bramble Weir Packaging", "Tarnfield Engineering",
    "Rowan Switch Components", "Ridge Fern Metals", "Keel Rowan Packaging", "Lumen Knap Freight",
    "Granite Dusk Services", "Raven Tess Materials", "Sable Kiln Components", "Oriel Shale Packaging",
    "Cobalt Fen Freight", "Hearth Penn Services", "Cairn Weft Materials", "Saffron Point Components",
    "Silver Bracken Freight", "Cormorant Loom Packaging", "Rivermere Services", "Flint Tern Materials",
)
CATEGORIES = ("Components", "Materials", "Components", "Packaging", "Components", "Freight", "Industrial services", "Materials")
COUNTRIES = ("DE", "NL", "SE", "ES", "PL", "GB", "FR", "FI", "PT", "BE", "IE")
EVIDENCE_NAMES = {
    "supplier_profile": "Supplier onboarding profile", "financial_review": "Trade and credit assessment",
    "capacity_check": "Capacity and continuity review", "quality_certificate": "Process quality declaration",
    "legal_clearance": "Enhanced legal clearance",
}
SEED_TIME = "2026-10-27T09:00:00+00:00"


def seed(store):
    rng = Random(284)
    with store.connect(write=True) as conn:
        if one(conn, "SELECT value FROM metadata WHERE key='fixture_version'"):
            return
        for index, name in enumerate(NAMES, start=1):
            sid = f"SUP-{index:03}"
            state = ("in_review" if index in {1, 2, 3, 8, 14, 21, 27, 33} else
                     "changes_requested" if index in {4, 18, 36} else "suspended" if index in {7, 22} else
                     "draft" if index in {16, 24, 31} else "approved")
            cycle = 0 if state == "draft" else 1
            country = COUNTRIES[(index - 1) % len(COUNTRIES)]
            risk = "high" if index in {2, 7, 12, 17, 22, 27, 32} else ("medium" if index % 3 else "low")
            currency = {"GB": "GBP", "SE": "SEK"}.get(country, "EUR")
            row = dict(
                id=sid, name=name, name_key=name_key(name), country=country, region=REGIONS[country],
                registration=f"DEMO-R{index:04}", category=CATEGORIES[(index-1) % len(CATEGORIES)],
                segment=("strategic", "preferred", "standard")[(index - 1) % 3], risk=risk,
                payment_days=(30, 45, 60)[index % 3], currency=currency, owner="buyer",
                state=state, revision=1, cycle=cycle, opened_on=(date(2026, 8, 15) + timedelta(days=index * 2)).isoformat(),
            )
            insert(conn, "suppliers", **row)
            audit(conn, sid, "buyer", "supplier.created", sid, after={"state": "draft"}, time="2026-10-12T10:00:00+00:00")
            if index <= 30:
                insert(conn, "source_links", source="DEMO-ERP", external_key=f"DEMO-ERP-{index:03}",
                       supplier_id=sid, batch_id="baseline-2026-10", linked_at="2026-10-12T11:00:00+00:00")
            for position, role in enumerate(gate_roles(risk)):
                missing = (cycle == 0 and position > 0) or (state == "in_review" and index != 1 and position >= 2 and (index + position) % 3 == 0)
                if not missing:
                    due = date(2026, 11, 2) + timedelta(days=index * 4 + position * 8)
                    if state == "approved" and index in {10, 26} and role == "quality":
                        due = date(2026, 10, 26)
                    if index == 1 and role == "quality":
                        due = date(2026, 10, 26)
                    insert(
                        conn, "evidence", id=f"DOC-{index:03}-{position+1}", supplier_id=sid, kind=GATES[role],
                        title=EVIDENCE_NAMES[GATES[role]], ref=f"DEMO-EV-{index:03}-{position+1}",
                        valid_until=due.isoformat(), created_by=role, created_at="2026-10-18T10:00:00+00:00",
                    )
                if cycle:
                    status = "pending"
                    if state in {"approved", "suspended"} or (state == "in_review" and position < index % 3):
                        status = "approved"
                    if state == "changes_requested" and role == "finance":
                        status = "returned"
                    reason = {"approved": "Synthetic evidence meets the agreed acceptance rule.",
                              "returned": "Confirm commercial exposure before a second review."}.get(status)
                    insert(conn, "reviews", supplier_id=sid, cycle=cycle, role=role, status=status,
                           decided_by=role if reason else None, reason=reason, decided_at=SEED_TIME if reason else None)
                    if reason:
                        audit(conn, sid, role, f"review.{status}", f"{sid}/{cycle}/{role}",
                              after={"reason": reason}, time=SEED_TIME)
            if index % 4 != 0 or index == 28:
                state_agr = "proposed" if index in {1, 2, 14, 27, 33} else "effective"
                ends = "2026-10-28" if index in {6, 25} else (date(2026, 11, 7) + timedelta(days=(index * 11) % 156)).isoformat()
                insert(conn, "agreements", id=f"AGR-{index:03}", supplier_id=sid, ref=f"DEMO-FW-{index:03}",
                       title=f"{row['category']} framework", starts_on="2026-07-01", ends_on=ends,
                       currency=currency, annual_value=25_000 + index * 3_750, state=state_agr)
            if index % 3 == 1 or index in {2, 3, 5, 7}:
                labels = {"Components": "Machined mount", "Materials": "Recycled alloy", "Packaging": "Transit case",
                          "Freight": "Regional lane", "Industrial services": "Preventive maintenance"}
                family = labels[row["category"]]
                stages = ("discovery", "qualification", "commercial")
                stage = "awarded" if index in {13, 19, 28} else stages[(index-1) % 3] if index != 7 else "commercial"
                insert(conn, "initiatives", id=f"SRC-{index:03}", supplier_id=sid, title=f"{family} supply review",
                       item_family=family, owner="buyer", stage=stage, revision=1,
                       target_on=(date(2026, 11, 4) + timedelta(days=index)).isoformat())
            if index in {1, 3, 7, 9, 15, 19, 22, 25, 32}:
                critical = index in {7, 22}
                kind = "quality" if index % 2 else "delivery"
                insert(conn, "incidents", id=f"INC-{index:03}", supplier_id=sid,
                       title="Containment plan overdue" if critical else ("Recheck inspection evidence" if kind == "quality" else "Stabilise dispatch lead times"),
                       kind=kind, severity="critical" if critical else "major",
                       owner="quality" if kind == "quality" else "operations", state="open",
                       due_on=(date(2026, 10, 22) + timedelta(days=index % 16)).isoformat(), opened_at=SEED_TIME)
            if index in {1, 2, 4, 8, 14, 16, 18, 24, 27, 31, 33, 36}:
                continue
            for month in range(5, 11):
                if index % 8 == 0 and month >= 9:
                    continue
                deliveries = rng.randint(35, 160)
                inspected = rng.randint(30, 140)
                checks = rng.randint(6, 24)
                insert(conn, "observations", supplier_id=sid, period=f"2026-{month:02}-01",
                       deliveries=deliveries, on_time=deliveries - round(deliveries / rng.randint(11, 30)),
                       inspected=inspected, accepted=inspected - round(inspected/rng.randint(13, 45)),
                       checks=checks, compliant=checks - rng.randint(0, 2),
                       observed_at=f"2026-{month:02}-28T17:00:00+00:00")
        audit(conn, None, "steward", "data.fixture_loaded", "baseline-2026-10",
              after={"suppliers": len(NAMES), "data_class": "synthetic"}, time="2026-10-31T18:00:00+00:00")
        stage_batch(conn, SourceEnvelope.model_validate({
            "version": "1.0", "source": "DEMO-CATALOG", "data_class": "synthetic",
            "extracted_at": "2026-10-30T12:00:00Z",
            "records": [
                {"external_key": "DEMO-CAT-201", "name": "Aster Vale Components Ltd", "country": "DE",
                 "registration": "DEMO-R0001", "category": "Components"},
                {"external_key": "DEMO-CAT-202", "name": "Nordlume-Precision", "country": "SE",
                 "registration": "DEMO-R9100", "category": "Components"},
                {"external_key": "DEMO-CAT-203", "name": "West Ember Textiles", "country": "PT",
                 "registration": "DEMO-R9101", "category": "Materials"},
            ],
        }), "steward", batch_id="BAT-DEMO-CATALOG", received_at="2026-10-30T12:01:00+00:00")
        insert(conn, "metadata", key="fixture_version", value="1.0")
