import argparse
import json
import logging
from typing import List, Dict

from . import catalog


def get_table_sizes() -> List[Dict]:
    """Get table sizes using IBM i catalog."""
    return catalog.get_table_sizes()


def mock_table_sizes() -> List[Dict]:
    """Return mock table size data matching catalog output format."""
    return catalog.get_table_sizes(mock=True)


def format_table(rows: List[Dict]) -> str:
    if not rows:
        return "(no tables)"
    # Determine column widths
    headers = ["TABSCHEMA", "TABNAME", "ROWCOUNT", "DATA_SIZE"]
    widths = {h: max(len(h), *(len(str(r.get(h, ''))) for r in rows)) for h in headers}
    sep = " ".join(h.ljust(widths[h]) for h in headers)
    lines = [sep]
    for r in rows:
        lines.append(
            " ".join(
                str(r.get(h, "")).ljust(widths[h]) for h in headers
            )
        )
    return "\n".join(lines)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description="List table sizes and approximate row counts")
    parser.add_argument("--mock", action="store_true", help="Use mock data instead of querying the database")
    parser.add_argument(
        "--format",
        choices=["table", "json", "csv"],
        default="table",
        help="Output format (table=plain aligned, json=JSON array, csv=comma separated)",
    )
    parser.add_argument("--schema", help="Filter by schema (case sensitive unless DB collation)")
    args = parser.parse_args()

    rows = mock_table_sizes() if args.mock else get_table_sizes()
    if args.schema:
        rows = [r for r in rows if r.get("TABSCHEMA") == args.schema]

    if args.format == "json":
        print(json.dumps(rows, indent=2))
    elif args.format == "csv":
        headers = ["TABSCHEMA", "TABNAME", "ROWCOUNT", "DATA_SIZE"]
        print(",".join(headers))
        for r in rows:
            print(",".join(str(r.get(h, "")) for h in headers))
    else:
        print(format_table(rows))


if __name__ == "__main__":  # pragma: no cover - manual invocation
    main()
