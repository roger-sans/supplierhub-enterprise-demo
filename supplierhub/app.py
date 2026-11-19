"""SupplierHub executable HTTP service."""
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Annotated
from uuid import uuid4

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import governance as flow
from . import identity, reporting, types
from .fixtures import seed
from .store import ROOT, Store, encode, events, many, one

LOG = logging.getLogger("uvicorn.error")


def simulated_actor(x_demo_actor: Annotated[str | None, Header()] = None):
    """Select a workflow perspective for the isolated synthetic workspace."""
    if x_demo_actor not in flow.ACTORS:
        raise HTTPException(403, "Select a simulated workspace role (X-Demo-Actor).")
    return x_demo_actor


Actor = Annotated[str, Depends(simulated_actor)]


def create_app(db_path: Path | None = None):
    store = Store(db_path)

    @asynccontextmanager
    async def lifespan(app):
        store.initialize()
        seed(store)
        yield

    app = FastAPI(
        title="SupplierHub", version="1.0.0", lifespan=lifespan,
        description="Isolated synthetic supplier governance. X-Demo-Actor selects a simulated decision right.",
    )
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["localhost", "127.0.0.1", "testserver", "[::1]"])
    app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")
    as_of = store.as_of

    @app.middleware("http")
    async def request_trace(request: Request, call_next):
        started = perf_counter()
        request_id = uuid4().hex
        response = await call_next(request)
        response.headers["X-Request-Id"] = request_id
        response.headers["X-Content-Type-Options"] = "nosniff"
        if request.url.path.startswith("/api/"):
            response.headers["Cache-Control"] = "no-store"
            LOG.info(encode({
                "event": "http.request", "request_id": request_id, "method": request.method,
                "route": getattr(request.scope.get("route"), "path", "unmatched"),
                "status": response.status_code, "elapsed_ms": round((perf_counter()-started)*1000, 1),
            }))
        return response

    @app.get("/", include_in_schema=False)
    def shell():
        return FileResponse(ROOT / "web" / "index.html")

    @app.get("/api/health", tags=["Observability"])
    def health():
        """Check database readiness and report the fixture version."""
        with store.connect() as conn:
            record = one(conn, "SELECT value FROM metadata WHERE key='fixture_version'")
        if not record:
            raise HTTPException(503, "Synthetic dataset is unavailable.")
        return {"status": "ready", "data_class": "synthetic", "as_of": as_of, "fixture_version": record["value"]}

    @app.get("/api/dashboard", tags=["Reporting"])
    def dashboard():
        with store.connect() as conn:
            return reporting.dashboard(conn, as_of)

    @app.get("/api/data-health", tags=["Observability"])
    def data_health():
        with store.connect() as conn:
            return reporting.health(conn, as_of)

    @app.get("/api/scorecards", tags=["Reporting"])
    def scorecards():
        with store.connect() as conn:
            return reporting.scorecards(conn, as_of)

    @app.get("/api/audit", tags=["Observability"])
    def audit_feed(limit: int = Query(default=100, ge=1, le=250)):
        with store.connect() as conn:
            return events(conn, limit=limit)

    @app.get("/api/suppliers", tags=["Master"])
    def directory(q: str = Query(default="", max_length=100), state: str = "", category: str = "",
                  risk: str = "", limit: int = Query(default=100, ge=1, le=200), offset: int = Query(default=0, ge=0)):
        sql = " FROM suppliers WHERE 1=1"
        params = []
        if q.strip():
            sql += " AND (instr(lower(name), ?) > 0 OR instr(lower(id), ?) > 0 OR instr(lower(registration), ?) > 0)"
            params.extend([q.strip().lower()] * 3)
        for field, value in (("state", state), ("category", category), ("risk", risk)):
            if value:
                sql += f" AND {field} = ?"
                params.append(value)
        with store.connect() as conn:
            total = one(conn, "SELECT COUNT(*) AS n" + sql, params)["n"]
            rows = many(conn, "SELECT *" + sql + " ORDER BY name, id LIMIT ? OFFSET ?", (*params, limit, offset))
        return {"total": total, "rows": rows}

    @app.post("/api/suppliers", status_code=201, tags=["Master"])
    def create_supplier(data: types.SupplierFields, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.create_supplier(conn, data, actor, as_of)

    @app.get("/api/suppliers/{supplier_id}", tags=["Master"])
    def supplier_detail(supplier_id: str):
        with store.connect() as conn:
            row = flow.supplier(conn, supplier_id)
            score = next(score for score in reporting.scorecards(conn, as_of)["rows"] if score["supplier_id"] == supplier_id)
            return {
                **row, "qualified": flow.is_qualified(conn, row, as_of), "gates": flow.gate_snapshot(conn, row, as_of),
                "evidence": many(conn, "SELECT * FROM evidence WHERE supplier_id=? ORDER BY valid_until DESC", (supplier_id,)),
                "incidents": many(conn, "SELECT * FROM incidents WHERE supplier_id=? ORDER BY state DESC, due_on", (supplier_id,)),
                "agreements": many(conn, "SELECT * FROM agreements WHERE supplier_id=? ORDER BY ends_on", (supplier_id,)),
                "initiatives": many(conn, "SELECT * FROM initiatives WHERE supplier_id=? ORDER BY target_on", (supplier_id,)),
                "source_links": many(conn, "SELECT * FROM source_links WHERE supplier_id=? ORDER BY source", (supplier_id,)),
                "audit": events(conn, supplier_id, limit=100), "scorecard": score,
            }

    @app.patch("/api/suppliers/{supplier_id}", tags=["Master"])
    def edit_supplier(supplier_id: str, data: types.EditSupplier, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.edit_supplier(conn, supplier_id, data, actor)

    @app.post("/api/suppliers/{supplier_id}/submit", tags=["Reviews"])
    def submit(supplier_id: str, data: types.Explanation, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.submit(conn, supplier_id, data, actor, as_of)

    @app.post("/api/suppliers/{supplier_id}/decisions", tags=["Reviews"])
    def decision(supplier_id: str, data: types.Decision, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.decide(conn, supplier_id, data, actor, as_of)

    @app.post("/api/suppliers/{supplier_id}/evidence", status_code=201, tags=["Reviews"])
    def register_evidence(supplier_id: str, data: types.EvidenceInput, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.add_evidence(conn, supplier_id, data, actor, as_of)

    @app.post("/api/suppliers/{supplier_id}/incidents", status_code=201, tags=["Incidents"])
    def open_incident(supplier_id: str, data: types.IncidentInput, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.open_incident(conn, supplier_id, data, actor, as_of)

    @app.post("/api/suppliers/{supplier_id}/incidents/{incident_id}/close", tags=["Incidents"])
    def close_incident(supplier_id: str, incident_id: str, data: types.Explanation, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.close_incident(conn, supplier_id, incident_id, data, actor)

    @app.post("/api/suppliers/{supplier_id}/agreements", status_code=201, tags=["Agreements"])
    def propose_agreement(supplier_id: str, data: types.AgreementInput, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.add_agreement(conn, supplier_id, data, actor)

    @app.post("/api/suppliers/{supplier_id}/agreements/{agreement_id}/decisions", tags=["Agreements"])
    def decide_agreement(supplier_id: str, agreement_id: str, data: types.AgreementDecision, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.decide_agreement(conn, supplier_id, agreement_id, data, actor, as_of)

    @app.get("/api/sourcing", tags=["Sourcing"])
    def sourcing():
        with store.connect() as conn:
            return many(conn, """
                SELECT i.*, s.name AS supplier_name FROM initiatives i JOIN suppliers s ON i.supplier_id=s.id
                ORDER BY i.target_on, i.id
            """)

    @app.post("/api/sourcing", status_code=201, tags=["Sourcing"])
    def create_initiative(data: types.InitiativeInput, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.add_initiative(conn, data, actor)

    @app.post("/api/sourcing/{initiative_id}/move", tags=["Sourcing"])
    def move_initiative(initiative_id: str, data: types.InitiativeMove, actor: Actor):
        with store.connect(write=True) as conn:
            return flow.move_initiative(conn, initiative_id, data, actor, as_of)

    @app.get("/api/identity/batches", tags=["Identity"])
    def batches():
        with store.connect() as conn:
            return many(conn, """
                SELECT b.id, b.source, b.extracted_at, COUNT(r.external_key) AS records,
                       SUM(CASE WHEN r.disposition='pending' THEN 1 ELSE 0 END) AS pending
                FROM import_batches b JOIN import_rows r ON r.batch_id=b.id
                GROUP BY b.id ORDER BY b.received_at DESC, b.id
            """)

    @app.get("/api/identity/batches/{batch_id}", tags=["Identity"])
    def batch(batch_id: str):
        with store.connect() as conn:
            return identity.batch(conn, batch_id)

    @app.post("/api/identity/batches", tags=["Identity"], responses={201: {"description": "New staged batch"}})
    def stage_batch(data: types.SourceEnvelope, actor: Actor, response: Response):
        with store.connect(write=True) as conn:
            result, created = identity.stage(conn, data, actor)
        response.status_code = 201 if created else 200
        return result

    @app.post("/api/identity/batches/{batch_id}/rows/{external_key}/resolve", tags=["Identity"])
    def resolve_identity(batch_id: str, external_key: str, data: types.ResolveIdentity, actor: Actor):
        with store.connect(write=True) as conn:
            return identity.resolve(conn, batch_id, external_key, data, actor, as_of)

    @app.get("/api/v1/products/qualified-suppliers", tags=["Data Products"], response_model=types.ProductEnvelope)
    def qualified_product():
        """Publish the allowlisted supplier dimension eligible for downstream use."""
        with store.connect() as conn:
            return reporting.publication(conn, as_of)

    return app


app = create_app()
