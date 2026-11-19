"""Governed reporting over the current master and denominator-based observations."""
from datetime import date, timedelta

from .governance import ACTORS, gate_snapshot, is_qualified
from .store import ROOT, many, one
from .types import ProductEnvelope

SCORE_SQL = (ROOT / "performance.sql").read_text()
WEIGHTS = {"delivery_pct": 0.5, "quality_pct": 0.3, "compliance_pct": 0.2}

# Consumers receive these explicit projections, never review notes or registrations.
PRODUCT_FIELDS = ("name", "country", "category", "segment", "risk", "payment_days", "currency")


def months_before(as_of, months):
    index = as_of.year * 12 + as_of.month - 1 - months
    return date(index // 12, index % 12 + 1, 1).isoformat()


def scorecards(conn, as_of):
    start, end = months_before(as_of, 3), months_before(as_of, 0)
    observations = {row["supplier_id"]: row for row in many(conn, SCORE_SQL, (start, end))}
    rows = []
    for master in many(conn, "SELECT id, name, category, segment FROM suppliers ORDER BY name"):
        score = observations.get(master["id"], {})
        if score and all(score[key] is not None for key in WEIGHTS):
            score["score"] = round(sum(score[key] * weight for key, weight in WEIGHTS.items()), 1)
        else:
            score["score"] = None
        for key in WEIGHTS:
            value = score.get(key)
            score[key] = round(value, 1) if value is not None else None
        rows.append({"supplier_id": master["id"], **master, **score})
    rows.sort(key=lambda row: (row["score"] is None, -(row["score"] or 0), row["name"]))
    return {"as_of": as_of.isoformat(), "start": start, "end_exclusive": end, "weights": WEIGHTS, "rows": rows}


def dashboard(conn, as_of):
    today = as_of.isoformat()
    horizon = (as_of + timedelta(days=45)).isoformat()
    suppliers = many(conn, "SELECT * FROM suppliers ORDER BY opened_on DESC, name")
    active_reviews = [row for row in suppliers if row["state"] == "in_review"]
    qualified = [row for row in suppliers if is_qualified(conn, row, as_of)]
    renewals = many(conn, """
        SELECT a.*, s.name AS supplier_name FROM agreements a JOIN suppliers s ON a.supplier_id=s.id
        WHERE a.state='effective' AND a.ends_on BETWEEN ? AND ? ORDER BY a.ends_on, a.id
    """, (today, horizon))
    blockers = many(conn, """
        SELECT i.*, s.name AS supplier_name FROM incidents i JOIN suppliers s ON i.supplier_id=s.id
        WHERE i.state='open' AND i.severity='critical' ORDER BY i.due_on, i.id
    """)
    status_counts = {key: sum(row["state"] == key for row in suppliers)
                     for key in ("approved", "in_review", "changes_requested", "draft", "suspended")}
    queue = [{**row, "gates": gate_snapshot(conn, row, as_of)} for row in active_reviews]
    recent = sorted(queue, key=lambda row: (row["risk"] != "high", row["name"]))
    start, end = months_before(as_of, 6), months_before(as_of, 0)
    trend = many(conn, """
        SELECT period, SUM(deliveries) AS deliveries, SUM(on_time) AS on_time,
               ROUND(100.0 * SUM(on_time) / NULLIF(SUM(deliveries), 0), 1) AS pct
        FROM observations WHERE period>=? AND period<? GROUP BY period ORDER BY period
    """, (start, end))
    return {
        "as_of": today, "supplier_count": len(suppliers), "qualified_count": len(qualified),
        "review_count": len(active_reviews), "renewals": renewals, "blockers": blockers, "statuses": status_counts,
        "reviews": recent, "trend": trend,
    }


def health(conn, as_of):
    all_rows = many(conn, "SELECT * FROM suppliers")
    held = [row["id"] for row in all_rows if row["state"] == "approved" and not is_qualified(conn, row, as_of)]
    latest = one(conn, "SELECT MAX(observed_at) AS value FROM observations WHERE period<?", (months_before(as_of, 0),))["value"]
    pending = one(conn, "SELECT COUNT(*) AS n FROM import_rows WHERE disposition='pending'")["n"]
    counts = scorecards(conn, as_of)["rows"]
    coverage = sum(row["score"] is not None for row in counts)
    age_days = (as_of - date.fromisoformat(latest[:10])).days if latest else None
    return {
        "as_of": as_of.isoformat(), "latest_observed_at": latest, "observation_age_days": age_days,
        "observation_freshness_target_days": 35,
        "observations_current": age_days is not None and 0 <= age_days <= 35,
        "approved_held": held, "pending_source_rows": pending, "scored_suppliers": coverage,
        "total_suppliers": len(all_rows), "actors": ACTORS,
    }


def publication(conn, as_of):
    data = [
        {"supplier_id": row["id"], **{field: row[field] for field in PRODUCT_FIELDS}}
        for row in many(conn, "SELECT * FROM suppliers WHERE state='approved' ORDER BY id")
        if is_qualified(conn, row, as_of)
    ]
    return ProductEnvelope(version="1.0", product="qualified-suppliers", data_class="synthetic", as_of=as_of, records=data)
