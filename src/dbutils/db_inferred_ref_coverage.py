import argparse
import json
import logging

from dbutils.db_relate import (
    get_columns,
    get_primary_keys,
    get_tables,
    infer_relationships,
    mock_get_columns,
    mock_get_primary_keys,
    mock_get_tables,
    score_relationships,
)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(
        description="List inferred relationships with heuristic scores (no data sampling)."
    )
    parser.add_argument("--mock", action="store_true", help="Use mock catalog data")
    parser.add_argument(
        "--format",
        choices=["table", "json"],
        default="table",
        help="Output format (table or json)",
    )
    parser.add_argument("--min-score", type=float, default=0.0, help="Filter relationships by score")
    args = parser.parse_args()

    if args.mock:
        tables = mock_get_tables()
        columns = mock_get_columns()
        pks = mock_get_primary_keys()
    else:
        tables = get_tables()
        columns = get_columns()
        pks = get_primary_keys()

    rels = infer_relationships(tables, columns, pks, use_mock=args.mock)
    scored = score_relationships(rels, columns, pks)
    if args.min_score > 0:
        scored = [r for r in scored if r["score"] >= args.min_score]

    if args.format == "json":
        print(json.dumps(scored, indent=2))
        return

    # Table format
    if not scored:
        print("(no relationships)")
        return
    headers = [
        "TABSCHEMA",
        "TABNAME",
        "COLNAME",
        "REFTABSCHEMA",
        "REFTABNAME",
        "REFCOLNAME",
        "SCORE",
    ]
    widths = {h: len(h) for h in headers}
    for r in scored:
        widths["TABSCHEMA"] = max(widths["TABSCHEMA"], len(str(r.get("TABSCHEMA", ""))))
        widths["TABNAME"] = max(widths["TABNAME"], len(str(r.get("TABNAME", ""))))
        widths["COLNAME"] = max(widths["COLNAME"], len(str(r.get("COLNAME", ""))))
        widths["REFTABSCHEMA"] = max(widths["REFTABSCHEMA"], len(str(r.get("REFTABSCHEMA", ""))))
        widths["REFTABNAME"] = max(widths["REFTABNAME"], len(str(r.get("REFTABNAME", ""))))
        widths["REFCOLNAME"] = max(widths["REFCOLNAME"], len(str(r.get("REFCOLNAME", ""))))
        widths["SCORE"] = max(widths["SCORE"], len(str(r.get("score", ""))))

    line_header = " ".join(h.ljust(widths[h]) for h in headers)
    print(line_header)
    for r in scored:
        print(
            " ".join(
                [
                    str(r.get("TABSCHEMA", "")).ljust(widths["TABSCHEMA"]),
                    str(r.get("TABNAME", "")).ljust(widths["TABNAME"]),
                    str(r.get("COLNAME", "")).ljust(widths["COLNAME"]),
                    str(r.get("REFTABSCHEMA", "")).ljust(widths["REFTABSCHEMA"]),
                    str(r.get("REFTABNAME", "")).ljust(widths["REFTABNAME"]),
                    str(r.get("REFCOLNAME", "")).ljust(widths["REFCOLNAME"]),
                    str(r.get("score", "")).ljust(widths["SCORE"]),
                ]
            )
        )


if __name__ == "__main__":  # pragma: no cover
    main()
