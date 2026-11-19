CREATE TABLE IF NOT EXISTS suppliers (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    name_key TEXT NOT NULL,
    country TEXT NOT NULL,
    registration TEXT NOT NULL,
    category TEXT NOT NULL,
    segment TEXT NOT NULL CHECK (segment IN ('strategic','preferred','standard')),
    risk TEXT NOT NULL CHECK (risk IN ('low','medium','high')),
    region TEXT NOT NULL,
    payment_days INTEGER NOT NULL CHECK (payment_days BETWEEN 0 AND 180),
    currency TEXT NOT NULL,
    owner TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('draft','in_review','approved','changes_requested','suspended')),
    revision INTEGER NOT NULL CHECK (revision > 0),
    cycle INTEGER NOT NULL CHECK (cycle >= 0),
    opened_on TEXT NOT NULL,
    UNIQUE (country, registration)
);
CREATE INDEX IF NOT EXISTS suppliers_name_key ON suppliers(country, name_key);

CREATE TABLE IF NOT EXISTS evidence (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    kind TEXT NOT NULL,
    title TEXT NOT NULL,
    ref TEXT NOT NULL,
    valid_until TEXT NOT NULL,
    created_by TEXT NOT NULL,
    created_at TEXT NOT NULL,
    UNIQUE (supplier_id, kind, ref)
);
CREATE INDEX IF NOT EXISTS evidence_supplier ON evidence(supplier_id, kind, valid_until);

CREATE TABLE IF NOT EXISTS reviews (
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    cycle INTEGER NOT NULL,
    role TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending','approved','returned')),
    decided_by TEXT,
    reason TEXT,
    decided_at TEXT,
    PRIMARY KEY (supplier_id, cycle, role)
);

CREATE TABLE IF NOT EXISTS incidents (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    title TEXT NOT NULL,
    kind TEXT NOT NULL,
    severity TEXT NOT NULL CHECK (severity IN ('minor','major','critical')),
    owner TEXT NOT NULL,
    due_on TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('open','closed')),
    resolution TEXT,
    opened_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS incidents_supplier ON incidents(supplier_id, state, severity);

CREATE TABLE IF NOT EXISTS agreements (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    ref TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    starts_on TEXT NOT NULL,
    ends_on TEXT NOT NULL CHECK (ends_on >= starts_on),
    currency TEXT NOT NULL,
    annual_value INTEGER NOT NULL CHECK (annual_value > 0),
    state TEXT NOT NULL CHECK (state IN ('proposed','effective','retired'))
);

CREATE TABLE IF NOT EXISTS initiatives (
    id TEXT PRIMARY KEY,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    title TEXT NOT NULL,
    item_family TEXT NOT NULL,
    owner TEXT NOT NULL,
    target_on TEXT NOT NULL,
    stage TEXT NOT NULL CHECK (stage IN ('discovery','qualification','commercial','awarded','closed')),
    revision INTEGER NOT NULL CHECK (revision > 0)
);

CREATE TABLE IF NOT EXISTS observations (
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    period TEXT NOT NULL,
    deliveries INTEGER NOT NULL CHECK (deliveries >= 0),
    on_time INTEGER NOT NULL CHECK (on_time >= 0 AND on_time <= deliveries),
    inspected INTEGER NOT NULL CHECK (inspected >= 0),
    accepted INTEGER NOT NULL CHECK (accepted >= 0 AND accepted <= inspected),
    checks INTEGER NOT NULL CHECK (checks >= 0),
    compliant INTEGER NOT NULL CHECK (compliant >= 0 AND compliant <= checks),
    observed_at TEXT NOT NULL,
    PRIMARY KEY (supplier_id, period)
);

CREATE TABLE IF NOT EXISTS source_links (
    source TEXT NOT NULL,
    external_key TEXT NOT NULL,
    supplier_id TEXT NOT NULL REFERENCES suppliers(id),
    batch_id TEXT NOT NULL,
    linked_at TEXT NOT NULL,
    PRIMARY KEY (source, external_key)
);

CREATE TABLE IF NOT EXISTS import_batches (
    id TEXT PRIMARY KEY,
    digest TEXT NOT NULL UNIQUE,
    source TEXT NOT NULL,
    extracted_at TEXT NOT NULL,
    received_at TEXT NOT NULL,
    actor TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS import_rows (
    batch_id TEXT NOT NULL REFERENCES import_batches(id),
    external_key TEXT NOT NULL,
    payload TEXT NOT NULL,
    supplier_id TEXT REFERENCES suppliers(id),
    disposition TEXT NOT NULL CHECK (disposition IN ('pending','linked','created','already_linked','dismissed')),
    resolved_by TEXT,
    reason TEXT,
    PRIMARY KEY (batch_id, external_key)
);

CREATE TABLE IF NOT EXISTS audit_events (
    seq INTEGER PRIMARY KEY,
    supplier_id TEXT REFERENCES suppliers(id),
    actor TEXT NOT NULL,
    action TEXT NOT NULL,
    entity_id TEXT NOT NULL,
    before_json TEXT NOT NULL,
    after_json TEXT NOT NULL,
    occurred_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS audit_supplier ON audit_events(supplier_id, seq DESC);

CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
