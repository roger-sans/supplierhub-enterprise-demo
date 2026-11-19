"""Transactional storage shared by the local service and its synthetic fixtures."""
import json
import os
import sqlite3
from contextlib import closing, contextmanager
from datetime import date, datetime, timezone
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parent
DEMO_DATE = "2026-11-01"


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


def new_id(prefix):
    return f"{prefix}-{uuid4().hex[:12].upper()}"


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


class Store:
    def __init__(self, path=None):
        self.path = Path(path or os.environ.get("SUPPLIERHUB_DB", "data/supplierhub.sqlite"))
        self.as_of = date.fromisoformat(os.environ.get("SUPPLIERHUB_AS_OF", DEMO_DATE))

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(sqlite3.connect(self.path, timeout=10, isolation_level=None)) as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.executescript("BEGIN IMMEDIATE;\n" + (ROOT / "schema.sql").read_text() + "\nCOMMIT;")

    @contextmanager
    def connect(self, *, write=False):
        conn = sqlite3.connect(self.path, timeout=10, isolation_level=None)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise
        finally:
            conn.close()


def one(conn, sql, params=()):
    row = conn.execute(sql, params).fetchone()
    return dict(row) if row is not None else None


def many(conn, sql, params=()):
    return [dict(row) for row in conn.execute(sql, params)]


def insert(conn, table, **values):
    fields = ", ".join(values)
    placeholders = ", ".join("?" for _ in values)
    conn.execute(f"INSERT INTO {table} ({fields}) VALUES ({placeholders})", tuple(values.values()))


def audit(conn, supplier_id, actor, action, entity_id, before=None, after=None, *, time=None):
    insert(
        conn, "audit_events", supplier_id=supplier_id, actor=actor, action=action,
        entity_id=entity_id, before_json=encode(before), after_json=encode(after),
        occurred_at=time or utcnow(),
    )


def events(conn, supplier_id=None, limit=100):
    query = "SELECT * FROM audit_events"
    params = []
    if supplier_id:
        query += " WHERE supplier_id = ?"
        params.append(supplier_id)
    rows = many(conn, query + " ORDER BY seq DESC LIMIT ?", (*params, limit))
    for row in rows:
        row["before"] = json.loads(row.pop("before_json"))
        row["after"] = json.loads(row.pop("after_json"))
    return rows
