# Technical design and consumer contracts

## Boundaries and decisions

- **ADR 001 · Qualification is derived at read time.** A master record retains its lifecycle state and approval history. An eligibility projection checks the current cycle, current evidence, and critical incidents on the workspace business date. This prevents expiring evidence from leaving a stale approved flag in the publication. Runtime evaluation costs a small number of local queries per supplier. A scaled implementation would evaluate the same rules on an indexed projection and reconcile it against the source.
- **ADR 002 · Local transactions for operational authority.** FastAPI and SQLite are a single deployable service so an evaluator can run the entire demo locally. `BEGIN IMMEDIATE` serializes mutations, including source identity resolutions, and optimistic supplier or initiative revisions reject stale forms. Audit and state commit together. WAL permits concurrent reads. PostgreSQL becomes a candidate for a shared multi-writer pilot. Docker uses a named SQLite volume.
- **ADR 003 · Separate operational and analytical authority.** Operational workflow data stays in the app. A versioned eligible dimension and read-only monthly observations support analytics. No downstream model updates local qualifications. Snowflake is the modeled publication target, with local DuckDB checks on the same view SQL and fixtures.
- **ADR 004 · Native modules for a small local UI.** The application uses semantic HTML, CSS and JavaScript with same-origin API calls. It needs no frontend build step or external asset services. Browser flows exercise the same routes an evaluator uses. A component framework becomes relevant if the product develops reusable surfaces across multiple applications.

## Operating model

| Data asset | Authority / grain | Consumers |
| --- | --- | --- |
| Supplier master | Procurement · one row per stable supplier identity | Buying and all review teams |
| Source crosswalk | Data steward · one mapping per source namespace and external key | ERP integration and lineage review |
| Evidence and approvals | Named function · one decision per supplier, cycle, role | Procurement and audit |
| Risk incidents | Function owning the incident type · one event record per case | Buying and relevant reviewers |
| Commercial agreement | Buying proposes, Legal activates or retires · agreement reference | Procurement and Legal |
| Monthly observations | Synthetic Operations, Quality and Compliance dimensions · one supplier-month row | Operational performance and warehouse scorecards |
| Qualified Suppliers v1.0 | Procurement Data · one eligible supplier per snapshot date | Finance, Buying and Analytics |

Each function acts through a simulated role. The header `X-Demo-Actor` represents that selection and is checked against action rules. It is a teaching mechanism with no real authentication, authorization, signature or retention guarantees. Use the service on loopback. Document entries are metadata references for fictional evidence. The demo persists no binaries, supplier contact data or credentials.

Business-date rules use `SUPPLIERHUB_AS_OF` (default `2026-11-01`). New audit entries use actual UTC time. This separation makes expiry examples reproducible and preserves when a demo action took place. The UI's assigned owner and statuses reflect the operational record. A held publication state can differ from historical approval. An evidence owner can restore eligibility for expiry alone by registering current evidence. A master edit or a critical incident requires a new approval cycle.

## Versioned contracts

| Boundary | Contract | Checks |
| --- | --- | --- |
| Source intake | [Supplier source 1.0](../contracts/supplier-source.v1.schema.json) · [example](../contracts/examples/supplier-source.v1.json) | Only synthetic namespaces, 1–50 rows, unique external keys, timezone-aware extraction and explicit fields |
| Serving | [Qualified Suppliers 1.0](../contracts/qualified-suppliers.v1.schema.json) · `GET /api/v1/products/qualified-suppliers` | Stable IDs, one row per eligible supplier, explicit business date, no registration, source keys or review notes |
| Warehouse | [Export and model](../warehouse/README.md) | One eligible supplier per as-of date, one fact per supplier-month, count bounds, completed windows and parity |

Intake sorts by external key and normalizes the harvest timestamp before computing a SHA-256 replay digest. The same payload returns its existing batch. A record can match on country plus registration, normalized name, or an existing source link. Exact legal registration permits a confirmed link. Name similarity triggers triage. A confirmed mapping can be traced from supplier to source key, input batch and decision. The importer stages payloads before steward action and cannot overwrite the accepted master via source data.

For a breaking contract change, register the use case with the Procurement Data owner, publish v2 alongside v1, update consumer tests, accept a migration window with each consumer and agree a retirement date. This demo carries v1.0 only.

## Metrics and observability

- **Delivery** is on-time deliveries divided by total deliveries. **Quality** is accepted inspections divided by inspected units. **Compliance** is passing checks divided by performed checks. Each uses summed counts across the three completed months before the business date.
- The respective minimum bases are **20**, **20** and **3**. The composite uses **50%**, **30%** and **20%** on the unrounded rates. A missing component yields no composite. The dashboard shows the weighted delivery rate over six completed months. A data coverage denominator includes all master records.
- `GET /api/health` checks that the fixture schema is usable. Structured request logs carry a request ID, method, route template, duration and status. Payloads and names are excluded from those logs.
- The audit feed records actor, UTC timestamp, affected record, before/after data and the reason where relevant. The demo truncates interactive audit reads to the newest records. The database retains the transaction history.
- The Data products view shows source freshness against a 35-day target, score coverage, unresolved identities and holds on previously approved suppliers. Monitoring and incident response outside the demo remain pilot work.

## Acceptance and limits

Run the [walkthrough](walkthrough.md) against the shipped seed. Automated checks exercise revision conflicts, role decisions, stage rules, risk remediation, persistence, source replay, JSON contracts and local SQL parity. Server path `/docs` exposes the interactive OpenAPI document.

A future pilot needs central identity, authorized environment isolation, evidence retention controls, source admission and Snowflake execution evidence. The API deliberately operates without live ERP transport. No other data service is required to run the demo.
