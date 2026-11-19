"""Run the core Snowflake scorecard and DQ SQL on exported fixtures in DuckDB."""
import argparse
from pathlib import Path

import duckdb
from sqlglot import transpile

ROOT = Path(__file__).resolve().parents[1] / "warehouse" / "snowflake"


def load(connection, table, path):
    dataset = connection.read_csv(str(path), header=True, sample_size=-1)
    if len(dataset.columns) == 0:
        raise ValueError(f"Missing columns in {path.name}")
    dataset.create(table)


def run(output):
    with duckdb.connect() as connection:
        load(connection, "DIM_QUALIFIED_SUPPLIER", output / "qualified_suppliers.csv")
        load(connection, "FACT_SUPPLIER_MONTH", output / "supplier_monthly_observations.csv")
        for file in ("03_scorecards.sql", "04_quality.sql"):
            for statement in transpile((ROOT / file).read_text(), read="snowflake", write="duckdb"):
                result = connection.execute(statement)
        quality = dict(result.fetchall())
        scores = dict(connection.execute("SELECT supplier_id, composite FROM QUALIFIED_SUPPLIER_SCORECARD").fetchall())
        return quality, scores


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("export_directory", type=Path)
    args = parser.parse_args()
    quality, scores = run(args.export_directory)
    for check, value in quality.items():
        print(f"{check}: {value}")
    print(f"Scorecard rows: {len(scores)}; scored: {sum(score is not None for score in scores.values())}")
    raise SystemExit(int(any(quality.values())))
