"""
Subprocess data loader for Qt GUI.

Reads a single JSON command on stdin:
  {"cmd":"start", "schema_filter": str|null, "use_mock": bool, "initial_limit": int, "batch_size": int}

Emits newline-delimited JSON messages on stdout:
  {"type":"progress", "message": str, "current": int, "total": int}
  {"type":"chunk", "tables": [...], "columns": [...], "loaded": int, "estimated": int}
  {"type":"schemas", "schemas": ["SCHEMA1", ...]}
  {"type":"done"}
  {"type":"error", "message": str}

Tables use dicts: {"schema","name","remarks"}
Columns use dicts: {"schema","table","name","typename","length","scale","nulls","remarks"}
"""

from __future__ import annotations

import sys
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


def jprint(obj: Dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def get_schema_cache_path() -> Path:
    """Get the path to the schema cache file."""
    cache_dir = Path.home() / ".cache" / "dbutils"
    cache_dir.mkdir(parents=True, exist_ok=True)
    return cache_dir / "schemas.json"


def load_cached_schemas() -> Optional[List[str]]:
    """Load schemas from cache file."""
    try:
        cache_path = get_schema_cache_path()
        if cache_path.exists():
            with open(cache_path, 'r') as f:
                data = json.load(f)
                return data.get('schemas', [])
    except Exception as e:
        sys.stderr.write(f"Failed to load schema cache: {e}\n")
        sys.stderr.flush()
    return None


def save_schemas_to_cache(schemas: List[str]) -> None:
    """Save schemas to cache file."""
    try:
        cache_path = get_schema_cache_path()
        with open(cache_path, 'w') as f:
            json.dump({'schemas': schemas}, f)
        sys.stderr.write(f"Saved {len(schemas)} schemas to cache\n")
        sys.stderr.flush()
    except Exception as e:
        sys.stderr.write(f"Failed to save schema cache: {e}\n")
        sys.stderr.flush()


def to_table_dicts(tables) -> List[Dict[str, Any]]:
    out = []
    for t in tables:
        # Try attribute access first (dataclass), then dict access
        if hasattr(t, "schema"):
            schema = t.schema
            name = t.name
            remarks = t.remarks or ""
        else:
            schema = t.get("schema") or t.get("TABSCHEMA")
            name = t.get("name") or t.get("TABNAME")
            remarks = t.get("remarks") or t.get("TABLE_TEXT") or ""
        out.append({"schema": schema, "name": name, "remarks": remarks})
    return out


def to_column_dicts(cols) -> List[Dict[str, Any]]:
    out = []
    for c in cols:
        # Try attribute access first (dataclass), then dict access
        if hasattr(c, "schema"):
            schema = c.schema
            table = c.table
            name = c.name
            typename = c.typename
            length = c.length
            scale = c.scale
            nulls = c.nulls
            remarks = c.remarks or ""
        else:
            schema = c.get("schema") or c.get("TABSCHEMA")
            table = c.get("table") or c.get("TABNAME")
            name = c.get("name") or c.get("COLUMN_NAME") or c.get("COLNAME")
            typename = c.get("typename") or c.get("DATA_TYPE") or c.get("TYPENAME")
            length = c.get("length") or c.get("LENGTH")
            scale = c.get("scale") or c.get("NUMERIC_SCALE")
            nulls = c.get("nulls") or c.get("IS_NULLABLE")
            remarks = c.get("remarks") or c.get("COLUMN_TEXT") or ""
        
        # Normalize nulls to Y/N
        if nulls in ("Y", "N"):
            pass
        elif nulls is True:
            nulls = "Y"
        elif nulls is False:
            nulls = "N"
        else:
            nulls = "Y" if str(nulls).upper() == "Y" else "N"
        
        out.append(
            {
                "schema": schema,
                "table": table,
                "name": name,
                "typename": typename,
                "length": length,
                "scale": scale,
                "nulls": nulls,
                "remarks": remarks,
            }
        )
    return out


def main():
    try:
        line = sys.stdin.readline()
        if not line:
            return 0
        cmd = json.loads(line)
        if cmd.get("cmd") != "start":
            jprint({"type": "error", "message": "invalid command"})
            return 1

        schema_filter: Optional[str] = cmd.get("schema_filter")
        use_mock: bool = bool(cmd.get("use_mock", False))
        initial_limit: int = int(cmd.get("initial_limit", 200))
        batch_size: int = int(cmd.get("batch_size", 500))

        # Log to stderr for debugging
        sys.stderr.write(f"Starting data loader: schema_filter={schema_filter}, use_mock={use_mock}, initial_limit={initial_limit}, batch_size={batch_size}\n")
        sys.stderr.flush()

        # Import from absolute paths since this runs as __main__
        import dbutils.db_browser as db_browser

        # Track all loaded tables to build schema list
        all_loaded_tables = []
        
        # Initial chunk
        sys.stderr.write("Loading initial chunk...\n")
        sys.stderr.flush()
        jprint({"type": "progress", "message": "Connecting…", "current": 0, "total": 3})

        cached = db_browser.load_from_cache(schema_filter, limit=initial_limit, offset=0)
        sys.stderr.write(f"Cache result: {'hit' if cached else 'miss'}\n")
        sys.stderr.flush()
        if cached:
            tables, columns = cached
        else:
            tables, columns = db_browser.get_all_tables_and_columns(
                schema_filter, use_mock, use_cache=True, limit=initial_limit, offset=0
            )

        all_loaded_tables.extend(tables)
        loaded_total = len(tables)
        # Estimate if we likely have more
        if loaded_total < initial_limit:
            estimated_total = loaded_total
        else:
            estimated_total = loaded_total + batch_size * 4

        sys.stderr.write(f"Sending initial chunk: {loaded_total} tables, {len(columns)} columns\n")
        sys.stderr.flush()
        jprint(
            {
                "type": "chunk",
                "tables": to_table_dicts(tables),
                "columns": to_column_dicts(columns),
                "loaded": loaded_total,
                "estimated": estimated_total,
            }
        )
        sys.stderr.write("Sent chunk\n")
        sys.stderr.flush()
        jprint({"type": "progress", "message": f"Loaded {loaded_total} tables…", "current": 1, "total": 3})

        # Stream remaining pages
        offset = initial_limit
        while True:
            cached = db_browser.load_from_cache(schema_filter, limit=batch_size, offset=offset)
            if cached:
                t_chunk, c_chunk = cached
            else:
                t_chunk, c_chunk = db_browser.get_all_tables_and_columns(
                    schema_filter, use_mock, use_cache=True, limit=batch_size, offset=offset
                )

            if not t_chunk:
                break

            all_loaded_tables.extend(t_chunk)
            loaded_total += len(t_chunk)
            jprint(
                {
                    "type": "chunk",
                    "tables": to_table_dicts(t_chunk),
                    "columns": to_column_dicts(c_chunk),
                    "loaded": loaded_total,
                    "estimated": estimated_total,
                }
            )
            jprint({"type": "progress", "message": f"Loaded {loaded_total} tables…", "current": 2, "total": 3})

            offset += len(t_chunk)
            if len(t_chunk) < batch_size:
                break

        # Try to load schemas from cache first
        schemas_list = load_cached_schemas()
        
        if schemas_list:
            sys.stderr.write(f"Loaded {len(schemas_list)} schemas from cache\n")
            sys.stderr.flush()
        else:
            # Build schema list from loaded tables if cache miss
            sys.stderr.write("Cache miss, building schema list from loaded tables\n")
            sys.stderr.flush()
            schemas = set()
            for t in all_loaded_tables:
                if hasattr(t, "schema"):
                    schemas.add(t.schema)
                else:
                    schemas.add(t.get("schema") or t.get("TABSCHEMA", ""))
            
            schemas_list = sorted(schemas)
            # Save to cache for next time
            save_schemas_to_cache(schemas_list)
        
        sys.stderr.write(f"Sending completion: {len(schemas_list)} schemas\n")
        sys.stderr.flush()
        jprint({"type": "schemas", "schemas": schemas_list})
        jprint({"type": "progress", "message": "Done", "current": 3, "total": 3})
        jprint({"type": "done"})
        sys.stderr.write("All done, exiting normally\n")
        sys.stderr.flush()

        return 0
    except Exception as e:
        import traceback
        error_details = traceback.format_exc()
        sys.stderr.write(f"ERROR in data loader:\n{error_details}\n")
        sys.stderr.flush()
        jprint({"type": "error", "message": f"{type(e).__name__}: {str(e)}"})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
