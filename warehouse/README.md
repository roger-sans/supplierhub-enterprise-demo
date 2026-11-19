# Supplier analytics warehouse

The operational app owns qualification. The analytics boundary consumes a **snapshot of eligible suppliers** and **monthly synthetic observations**. The warehouse view filters its scorecard population by the eligible snapshot. The operational scorecard can report performance even for suppliers currently held.

| Relation | Grain | Purpose |
| --- | --- | --- |
| `DIM_QUALIFIED_SUPPLIER` | Snapshot date and stable supplier ID | Governed dimensional projection of current eligibility |
| `FACT_SUPPLIER_MONTH` | Supplier ID and month | Additive numerator and denominator facts |
| `QUALIFIED_SUPPLIER_SCORECARD` | Snapshot date and eligible supplier ID | Explainable rolling performance and sample sizes |

## Execute with local data

From the root, after starting the app once and installing the development requirements:

```bash
python -m scripts.export_warehouse --out out/warehouse
python -m scripts.check_warehouse out/warehouse
```

The export reads one SQLite transaction. It writes the qualified JSON plus two CSVs with fixed column order and monthly raw counts. The checker compiles the Snowflake SELECT/view statements into DuckDB SQL, loads the export, executes the model and runs quality checks. The test suite compares composite results against the live FastAPI service. The app's API uses the same business-month window and minimum denominators.

## Snowflake execution plan

The setup and scripted load require an external, disposable Snowflake database, a scoped role and a warehouse. Use SnowSQL or a compatible client that supports uploading local files. Select the authorized database and run `01_setup.sql`. Then, from the project root in that client session, upload the files to the demo stage:

```sql
USE SCHEMA SUPPLIERHUB_DEMO;
PUT file://out/warehouse/qualified_suppliers.csv @SUPPLIERHUB_STAGE OVERWRITE=TRUE AUTO_COMPRESS=TRUE;
PUT file://out/warehouse/supplier_monthly_observations.csv @SUPPLIERHUB_STAGE OVERWRITE=TRUE AUTO_COMPRESS=TRUE;
```

Run `02_load.sql` in the same client, then `03_scorecards.sql` and `04_quality.sql`. The load expects one non-empty qualified snapshot for the demo. If it contains zero eligible suppliers, retain the last warehouse load and resolve eligibility or define an explicit empty-snapshot policy before refreshing. The loader validates landing-table counts and grains before replacing serving rows in a transaction. The view uses `DATEADD` and `DATE_TRUNC` for completed reporting months. Inspect the query IDs and compare the results against the local checker before admitting consumers.

**Verification boundary.** The view and DQ query ran locally through DuckDB after SQL dialect translation. Snowflake DDL, stage commands, Snowflake Scripting transaction behavior, roles, billing and a live warehouse connection require external validation. The [backlog](../docs/backlog.json) contains the warehouse validation spike. [Snowflake date and time functions](https://docs.snowflake.com/en/sql-reference/functions-date-time)
