import argparse
import json
import logging
from typing import Dict

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

ORPHAN_SQL_TEMPLATE = (
    "SELECT COUNT(*) AS ORPHANS FROM {child_schema}.{child_table} c "
    "LEFT JOIN {parent_schema}.{parent_table} p ON c.{child_col} = p.{parent_col} "
    "WHERE c.{child_col} IS NOT NULL AND p.{parent_col} IS NULL"
)


def build_orphan_sql(rel: Dict) -> str:
    return ORPHAN_SQL_TEMPLATE.format(
        child_schema=rel["TABSCHEMA"],
        child_table=rel["TABNAME"],
        child_col=rel["COLNAME"],
        parent_schema=rel["REFTABSCHEMA"],
        parent_table=rel["REFTABNAME"],
        parent_col=rel["REFCOLNAME"],
    )


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    parser = argparse.ArgumentParser(description="Generate orphan detection SQL for inferred relationships")
    parser.add_argument("--mock", action="store_true", help="Use mock catalog data")
    parser.add_argument("--json", action="store_true", help="Emit JSON instead of table output")
    parser.add_argument("--min-score", type=float, default=0.0, help="Minimum score threshold")
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

    output_rows = []
    for r in scored:
        sql = build_orphan_sql(r)
        output_rows.append(
            {
                "child_table": f"{r['TABSCHEMA']}.{r['TABNAME']}",
                "child_column": r["COLNAME"],
                "parent_table": f"{r['REFTABSCHEMA']}.{r['REFTABNAME']}",
                "parent_column": r["REFCOLNAME"],
                "score": r["score"],
                "sql": sql,
            }
        )

    if args.json:
        print(json.dumps(output_rows, indent=2))
        return

    if not output_rows:
        print("(no relationships)")
        return

    headers = ["CHILD_TABLE", "CHILD_COLUMN", "PARENT_TABLE", "PARENT_COLUMN", "SCORE"]
    widths = {h: len(h) for h in headers}
    for o in output_rows:
        widths["CHILD_TABLE"] = max(widths["CHILD_TABLE"], len(o["child_table"]))
        widths["CHILD_COLUMN"] = max(widths["CHILD_COLUMN"], len(o["child_column"]))
        widths["PARENT_TABLE"] = max(widths["PARENT_TABLE"], len(o["parent_table"]))
        widths["PARENT_COLUMN"] = max(widths["PARENT_COLUMN"], len(o["parent_column"]))
        widths["SCORE"] = max(widths["SCORE"], len(str(o["score"])))

    print(" ".join(h.ljust(widths[h]) for h in headers))
    for o in output_rows:
        print(
            " ".join(
                [
                    o["child_table"].ljust(widths["CHILD_TABLE"]),
                    o["child_column"].ljust(widths["CHILD_COLUMN"]),
                    o["parent_table"].ljust(widths["PARENT_TABLE"]),
                    o["parent_column"].ljust(widths["PARENT_COLUMN"]),
                    str(o["score"]).ljust(widths["SCORE"]),
                ]
            )
        )
    print("\n-- Example orphan detection SQL for first relationship --")
    print(output_rows[0]["sql"])


if __name__ == "__main__":  # pragma: no cover
    main()
