import argparse
import json
import logging
from typing import Dict, List

from . import catalog


def get_indexes() -> List[Dict]:
    """Get indexes using IBM i catalog."""
    return catalog.get_indexes()


def mock_indexes() -> List[Dict]:
    """Return mock index data matching catalog output format."""
    return catalog.get_indexes(mock=True)


def format_table(rows: List[Dict]) -> str:
    if not rows:
        return "(no indexes)"
    headers = ["INDEX_SCHEMA", "INDEX_NAME", "TABSCHEMA", "TABNAME", "COLUMN_NAME", "IS_UNIQUE", "ORDINAL_POSITION"]
    widths = {h: max(len(h), *(len(str(r.get(h, ""))) for r in rows)) for h in headers}
    sep = " ".join(h.ljust(widths[h]) for h in headers)
    lines = [sep]
    for r in rows:
        lines.append(" ".join(str(r.get(h, "")).ljust(widths[h]) for h in headers))
    return "\n".join(lines)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description="List index metadata")
    parser.add_argument("--mock", action="store_true", help="Use mock data instead of live catalog queries")
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (table=plain aligned, json=JSON array, csv=comma separated)",
    )
    parser.add_argument("--schema", help="Filter by table schema")
    parser.add_argument("--table", help="Filter indexes for a specific table name")
    args = parser.parse_args()

    rows = mock_indexes() if args.mock else get_indexes()
    if args.schema:
        rows = [r for r in rows if r.get("TABSCHEMA") == args.schema]
    if args.table:
        rows = [r for r in rows if r.get("TABNAME") == args.table]

    if args.format == "json":
        print(json.dumps(rows, indent=2))
    elif args.format == "csv":
        headers = ["INDEX_SCHEMA", "INDEX_NAME", "TABSCHEMA", "TABNAME", "COLUMN_NAME", "IS_UNIQUE", "ORDINAL_POSITION"]
        print(",".join(headers))
        for r in rows:
            print(",".join(str(r.get(h, "")) for h in headers))
    else:
        print(format_table(rows))


if __name__ == "__main__":  # pragma: no cover
    main()
