# SupplierHub 1.0.0

The first local release delivers a complete synthetic qualification loop, sourcing and agreement decisions, a steward-owned source crosswalk, and a versioned supplier data product.

| Increment | Review evidence |
| --- | --- |
| Cross-functional qualification and quality holds | Aster Vale evidence repair, three independent gate decisions, publication, suspension and fresh-review path |
| Commercial coordination | Legal activation followed by a Procurement-controlled award |
| Domain data product | Source replay, steward resolution, downstream field allowlist, score parity and quality checks |
| Operational workspace | Desktop qualification, desktop identity review and mobile directory captured from the running app |

Acceptance is documented through automated tests and the demonstration scenarios in the [walkthrough](walkthrough.md). It represents release evidence for the synthetic scope. Identity, source admission, multi-user service capacity and Snowflake execution remain tracked in the [ranked backlog](backlog.json).

The seed is generated on first start and recorded in database metadata, keeping subsequent edits through restart. For a fresh demonstration, set `SUPPLIERHUB_DB` to a new SQLite path. Containerized data persists in the Compose volume. Record fixture and contract versions when reviewing behavior across releases.

Local verification passed 22 automated tests in a fresh Python environment, including four Chromium workflows. Warehouse parity and quality checks ran in DuckDB against the synthetic export. GitHub Actions and the Docker image can be validated after the repository is created.
