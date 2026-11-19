"""Export a read-only, allowlisted warehouse snapshot from a SupplierHub database."""
import argparse
import csv
from pathlib import Path

from supplierhub.reporting import PRODUCT_FIELDS, publication
from supplierhub.store import Store, many

DIM_COLUMNS = ("as_of", "supplier_id", *PRODUCT_FIELDS)
FACT_COLUMNS = ("supplier_id", "period", "deliveries", "on_time", "inspected", "accepted", "checks", "compliant", "observed_at")


def write_csv(path, columns, rows):
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, columns)
        writer.writeheader()
        writer.writerows(rows)


def export(store, output):
    if not store.path.is_file():
        raise FileNotFoundError(f"Start SupplierHub to initialize the database at {store.path}.")
    with store.connect() as conn:
        product = publication(conn, store.as_of)
        facts = many(conn, "SELECT " + ", ".join(FACT_COLUMNS) + " FROM observations ORDER BY supplier_id, period")
    output.mkdir(parents=True, exist_ok=True)
    (output / "qualified_suppliers.json").write_text(product.model_dump_json(indent=2) + "\n", encoding="utf-8")
    dimension = [{"as_of": product.as_of.isoformat(), **row.model_dump()} for row in product.records]
    write_csv(output / "qualified_suppliers.csv", DIM_COLUMNS, dimension)
    write_csv(output / "supplier_monthly_observations.csv", FACT_COLUMNS, facts)
    return len(dimension), len(facts)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, help="Operational SQLite database")
    parser.add_argument("--out", required=True, type=Path, help="Export directory")
    args = parser.parse_args()
    members, observations = export(Store(args.db), args.out)
    print(f"Exported {members} eligible suppliers and {observations} monthly observations.")
