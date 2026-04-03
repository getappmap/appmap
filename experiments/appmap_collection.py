#!/usr/bin/env python3
"""
appmap_collection.py — Navigate a directory of AppMap files without loading them all.

Architecture: two-tier lazy loading
  1. Index (built once, stored as .appmap-index.json) — very lightweight per-file
     summaries + inverted indexes. All collection-level queries use only the index.
  2. Detail (on demand) — delegates to appmap_tool.py for individual file inspection.

Usage:
  python appmap_collection.py index   <dir>               Build/refresh index
  python appmap_collection.py list    <dir> [--failed]    List all appmaps (1 line each)
  python appmap_collection.py stats   <dir>               Collection-level statistics
  python appmap_collection.py failing <dir>               Show only failed tests
  python appmap_collection.py find    <dir> <pattern>     Full-text search across index
  python appmap_collection.py cls     <dir> <ClassName>   Find appmaps using a class
  python appmap_collection.py table   <dir> <table>       Find appmaps querying a table
  python appmap_collection.py route   <dir> <route>       Find appmaps for an HTTP route
  python appmap_collection.py coverage <dir>              HTTP/class/SQL coverage report
  python appmap_collection.py diff    <file1> <file2>     Compare two appmap call trees
  python appmap_collection.py related <dir> <file>        Find appmaps sharing classes/routes
  python appmap_collection.py open    <file> <cmd> [args] Run appmap_tool command on a file
"""

import json
import os
import re
import sys
import glob
import hashlib
import argparse
from typing import Optional
from pathlib import Path

# ──────────────────────────────────────────────────────────────────────────────
# Index building
# ──────────────────────────────────────────────────────────────────────────────

INDEX_FILE = ".appmap-index.json"
INDEX_VERSION = 2


def extract_entry(path: str) -> dict:
    """Extract a lightweight summary from one appmap file."""
    with open(path) as f:
        data = json.load(f)

    events = data.get("events", [])
    meta = data.get("metadata", {})

    # Apply eventUpdates
    if "eventUpdates" in data:
        by_id = {e["id"]: e for e in events}
        for eid_str, upd in data["eventUpdates"].items():
            eid = int(eid_str)
            if eid in by_id:
                by_id[eid].update(upd)
        events = list(by_id.values())

    calls = [e for e in events if e.get("event") == "call"]
    returns = [e for e in events if e.get("event") == "return"]

    # HTTP entry/exit
    http_server_calls = [e for e in calls if "http_server_request" in e]
    http_server_returns = [e for e in returns if "http_server_response" in e]
    http_client_calls = [e for e in calls if "http_client_request" in e]
    http_entry = None
    http_status = None
    http_elapsed = None
    if http_server_calls:
        r = http_server_calls[0]["http_server_request"]
        http_entry = f"{r['request_method']} {r.get('normalized_path_info') or r['path_info']}"
    if http_server_returns:
        resp = http_server_returns[-1]
        http_status = resp["http_server_response"]["status_code"]
        http_elapsed = resp.get("elapsed")

    # Classes called
    classes = sorted(set(
        e["defined_class"] for e in calls if "defined_class" in e
    ))

    # SQL: tables and operations
    sql_calls = [e for e in calls if "sql_query" in e]
    sql_tables = set()
    sql_ops = set()
    for e in sql_calls:
        sql = e["sql_query"]["sql"]
        verb = sql.strip().split()[0].upper()
        sql_ops.add(verb)
        # Extract table name
        m = re.search(r'(?:FROM|INTO|UPDATE|TABLE)\s+"?(\w+)"?', sql, re.I)
        if m:
            sql_tables.add(m.group(1))

    # Outbound HTTP
    http_out = [
        f"{e['http_client_request']['request_method']} {e['http_client_request']['url']}"
        for e in http_client_calls
    ]

    # Exceptions raised
    exceptions = []
    for e in returns:
        for exc in e.get("exceptions", []):
            exceptions.append(exc["class"])

    # Total elapsed (from top-level return)
    total_elapsed = None
    if http_server_returns:
        total_elapsed = http_server_returns[-1].get("elapsed")
    elif returns:
        # Try to find the outermost return
        all_parent_ids = {e.get("parent_id") for e in returns}
        all_call_ids = {e["id"] for e in calls}
        for r in returns:
            pid = r.get("parent_id")
            if pid not in all_call_ids or pid not in {e["id"] for e in calls if e.get("event") == "call"}:
                continue
            if r.get("elapsed"):
                total_elapsed = max(total_elapsed or 0, r["elapsed"])

    # File stat
    stat = os.stat(path)

    return {
        "file": path,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
        "name": meta.get("name", os.path.basename(path)),
        "test_status": meta.get("test_status", "unknown"),
        "test_failure": meta.get("test_failure"),
        "source_location": meta.get("source_location"),
        "event_count": len(events),
        "sql_count": len(sql_calls),
        "http_entry": http_entry,
        "http_status": http_status,
        "http_elapsed": http_elapsed,
        "total_elapsed": total_elapsed,
        "classes": classes,
        "sql_tables": sorted(sql_tables),
        "sql_ops": sorted(sql_ops),
        "http_out": http_out,
        "exceptions": sorted(set(exceptions)),
    }


def build_index(directory: str, force: bool = False) -> dict:
    """Build or refresh the index for a directory of appmap files."""
    index_path = os.path.join(directory, INDEX_FILE)

    # Load existing index if present
    existing = {}
    if os.path.exists(index_path) and not force:
        try:
            with open(index_path) as f:
                idx = json.load(f)
            if idx.get("version") == INDEX_VERSION:
                existing = {e["file"]: e for e in idx.get("appmaps", [])}
        except Exception:
            pass

    # Find all appmap files (recursive)
    pattern = os.path.join(directory, "**", "*.appmap.json")
    files = glob.glob(pattern, recursive=True)
    files = [f for f in files if not f.endswith(INDEX_FILE)]

    appmaps = []
    added = updated = unchanged = 0
    for fpath in sorted(files):
        stat = os.stat(fpath)
        cached = existing.get(fpath)
        if cached and abs(cached.get("mtime", 0) - stat.st_mtime) < 0.01:
            appmaps.append(cached)
            unchanged += 1
        else:
            try:
                entry = extract_entry(fpath)
                appmaps.append(entry)
                if cached:
                    updated += 1
                else:
                    added += 1
            except Exception as ex:
                print(f"Warning: could not parse {fpath}: {ex}", file=sys.stderr)

    # Build inverted indexes
    by_class = {}
    by_table = {}
    by_http_entry = {}
    by_status = {}
    by_exception = {}

    for e in appmaps:
        f = e["file"]
        for cls in e.get("classes", []):
            by_class.setdefault(cls, []).append(f)
        for tbl in e.get("sql_tables", []):
            by_table.setdefault(tbl, []).append(f)
        entry = e.get("http_entry")
        if entry:
            by_http_entry.setdefault(entry, []).append(f)
        status = e.get("test_status", "unknown")
        by_status.setdefault(status, []).append(f)
        for exc in e.get("exceptions", []):
            by_exception.setdefault(exc, []).append(f)

    index = {
        "version": INDEX_VERSION,
        "root": directory,
        "file_count": len(appmaps),
        "appmaps": appmaps,
        "by_class": by_class,
        "by_table": by_table,
        "by_http_entry": by_http_entry,
        "by_status": by_status,
        "by_exception": by_exception,
    }

    with open(index_path, "w") as f:
        json.dump(index, f, indent=2)

    return index, added, updated, unchanged


def load_index(directory: str) -> dict:
    """Load existing index, or build it if absent."""
    index_path = os.path.join(directory, INDEX_FILE)
    if not os.path.exists(index_path):
        print(f"No index found in {directory}, building...", file=sys.stderr)
        index, _, _, _ = build_index(directory)
        return index
    with open(index_path) as f:
        return json.load(f)


# ──────────────────────────────────────────────────────────────────────────────
# Formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def elapsed_str(seconds) -> str:
    if seconds is None:
        return ""
    if seconds < 1:
        return f"{seconds*1000:.0f}ms"
    return f"{seconds:.2f}s"


def status_icon(test_status: str) -> str:
    return {"succeeded": "✓", "failed": "✗", "unknown": "?"}.get(test_status, "?")


def short_name(entry: dict, max_len: int = 55) -> str:
    name = entry.get("name", os.path.basename(entry["file"]))
    if len(name) > max_len:
        name = name[:max_len - 3] + "..."
    return name


def one_liner(entry: dict) -> str:
    icon = status_icon(entry["test_status"])
    name = short_name(entry)
    parts = []
    if entry.get("http_entry"):
        parts.append(entry["http_entry"])
        if entry.get("http_status"):
            parts.append(f"→{entry['http_status']}")
    if entry.get("sql_count", 0) > 0:
        parts.append(f"{entry['sql_count']}sql")
    if entry.get("http_out"):
        parts.append(f"{len(entry['http_out'])}out")
    if entry.get("exceptions"):
        parts.append(f"!{entry['exceptions'][0].split('::')[-1]}")
    elapsed = elapsed_str(entry.get("http_elapsed") or entry.get("total_elapsed"))
    meta = "[" + " ".join(parts) + "]" if parts else ""
    return f"{icon} {name:<56} {meta} {elapsed}"


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────

def cmd_index(args):
    idx, added, updated, unchanged = build_index(args.dir, force=getattr(args, 'force', False))
    n = idx["file_count"]
    index_path = os.path.join(args.dir, INDEX_FILE)
    index_kb = os.path.getsize(index_path) / 1024
    total_kb = sum(e["size"] for e in idx["appmaps"]) / 1024
    print(f"Indexed {n} appmap files in {args.dir}/")
    print(f"  Added: {added}  Updated: {updated}  Unchanged: {unchanged}")
    print(f"  Index size: {index_kb:.0f} KB  (vs {total_kb:.0f} KB raw — "
          f"{index_kb/total_kb*100:.1f}% overhead)")
    print(f"  Saved to: {index_path}")
    print(f"\nClasses indexed: {len(idx['by_class'])}")
    print(f"SQL tables indexed: {len(idx['by_table'])}")
    print(f"HTTP routes indexed: {len(idx['by_http_entry'])}")


def cmd_list(args):
    idx = load_index(args.dir)
    appmaps = idx["appmaps"]

    # Optional filters
    if getattr(args, 'failed', False):
        appmaps = [e for e in appmaps if e["test_status"] == "failed"]
    if getattr(args, 'route', None):
        pat = re.compile(args.route, re.I)
        appmaps = [e for e in appmaps if e.get("http_entry") and pat.search(e["http_entry"])]

    if not appmaps:
        print("No appmaps match.")
        return

    print(f"{'S'} {'Test name':<56} {'[http sql out !exc]':<30} {'elapsed'}")
    print("─" * 100)
    for entry in appmaps:
        print(one_liner(entry))
    print(f"\n{len(appmaps)} appmap(s)")

    if getattr(args, 'count_tokens', False):
        text = "\n".join(one_liner(e) for e in appmaps)
        print(f"\n── ~{len(text)//4} tokens for this listing ──")


def cmd_stats(args):
    idx = load_index(args.dir)
    appmaps = idx["appmaps"]

    total_events = sum(e["event_count"] for e in appmaps)
    total_sql = sum(e["sql_count"] for e in appmaps)
    statuses = {}
    for e in appmaps:
        s = e.get("test_status", "unknown")
        statuses[s] = statuses.get(s, 0) + 1

    total_size_kb = sum(e["size"] for e in appmaps) / 1024
    index_path = os.path.join(args.dir, INDEX_FILE)
    index_size_kb = os.path.getsize(index_path) / 1024 if os.path.exists(index_path) else 0

    # Slowest appmaps
    by_elapsed = sorted(
        [e for e in appmaps if e.get("http_elapsed") or e.get("total_elapsed")],
        key=lambda e: e.get("http_elapsed") or e.get("total_elapsed") or 0,
        reverse=True
    )

    # Most SQL
    by_sql = sorted(appmaps, key=lambda e: e["sql_count"], reverse=True)

    print("═" * 70)
    print(f"Collection: {args.dir}")
    print("═" * 70)
    print(f"Files     : {len(appmaps)}")
    print(f"Events    : {total_events} total, avg {total_events//max(len(appmaps),1)} per file")
    print(f"SQL       : {total_sql} queries total")
    print(f"Test status: {', '.join(f'{v} {k}' for k, v in sorted(statuses.items()))}")
    print(f"Raw size  : {total_size_kb:.0f} KB  Index: {index_size_kb:.0f} KB  "
          f"({index_size_kb/total_size_kb*100:.1f}% of raw)")
    print(f"~Token cost (raw JSON): ~{int(total_size_kb*1024)//4:,} to load everything")
    print(f"~Token cost (index listing): ~{len(chr(10).join(one_liner(e) for e in appmaps))//4:,} tokens")
    print()

    print("HTTP routes covered:")
    for route, files in sorted(idx.get("by_http_entry", {}).items()):
        print(f"  {route:<40} ({len(files)} test(s))")
    print()

    print("SQL tables touched:")
    for tbl, files in sorted(idx.get("by_table", {}).items()):
        ops = set()
        for e in appmaps:
            if tbl in e.get("sql_tables", []):
                ops.update(e.get("sql_ops", []))
        print(f"  {tbl:<20} {sorted(ops)}  ({len(files)} test(s))")
    print()

    if by_elapsed[:5]:
        print("Slowest tests:")
        for e in by_elapsed[:5]:
            el = e.get("http_elapsed") or e.get("total_elapsed", 0)
            print(f"  {elapsed_str(el):>8}  {short_name(e)}")
    print()

    print("Most SQL queries:")
    for e in by_sql[:5]:
        if e["sql_count"] > 0:
            print(f"  {e['sql_count']:>3} queries  {short_name(e)}")

    failed = idx.get("by_status", {}).get("failed", [])
    if failed:
        print()
        print(f"FAILED tests ({len(failed)}):")
        for fpath in failed:
            entry = next((e for e in appmaps if e["file"] == fpath), None)
            if entry:
                failure = entry.get("test_failure", {})
                print(f"  ✗ {short_name(entry)}")
                if failure:
                    print(f"      {failure.get('message','')[:80]}")


def cmd_failing(args):
    idx = load_index(args.dir)
    failed = idx.get("by_status", {}).get("failed", [])
    if not failed:
        print("No failing tests.")
        return

    appmaps_by_file = {e["file"]: e for e in idx["appmaps"]}
    print(f"Failed tests: {len(failed)}\n")
    for fpath in failed:
        entry = appmaps_by_file.get(fpath, {})
        print(f"✗ {entry.get('name', fpath)}")
        if entry.get("source_location"):
            print(f"  Source: {entry['source_location']}")
        failure = entry.get("test_failure", {})
        if failure:
            print(f"  Failure: {failure.get('message', '')}")
            if failure.get("location"):
                print(f"  At: {failure['location']}")
        if entry.get("exceptions"):
            print(f"  Exception: {', '.join(entry['exceptions'])}")
        if entry.get("http_entry"):
            print(f"  HTTP: {entry['http_entry']} → {entry.get('http_status')}")
        print(f"  File: {fpath}")
        print()


def cmd_find(args):
    """Search across the index for pattern. No file loading needed."""
    idx = load_index(args.dir)
    pat = re.compile(args.pattern, re.I)

    def entry_text(e: dict) -> str:
        parts = [
            e.get("name") or "",
            e.get("http_entry") or "",
            e.get("source_location") or "",
            e.get("test_status") or "",
            " ".join(e.get("classes") or []),
            " ".join(e.get("sql_tables") or []),
            " ".join(e.get("http_out") or []),
            " ".join(e.get("exceptions") or []),
            str((e.get("test_failure") or {}).get("message", "")),
        ]
        return " ".join(parts)

    matches = [e for e in idx["appmaps"] if pat.search(entry_text(e))]

    if not matches:
        print(f"No appmaps match: {args.pattern!r}")
        return

    print(f"Found {len(matches)} appmap(s) matching {args.pattern!r}:\n")
    for entry in matches:
        print(one_liner(entry))
        if entry.get("classes"):
            relevant = [c for c in entry["classes"] if pat.search(c)]
            if relevant:
                print(f"  classes: {', '.join(relevant)}")
        if entry.get("sql_tables"):
            relevant = [t for t in entry["sql_tables"] if pat.search(t)]
            if relevant:
                print(f"  tables: {', '.join(relevant)}")
        if entry.get("exceptions"):
            relevant = [ex for ex in entry["exceptions"] if pat.search(ex)]
            if relevant:
                print(f"  exceptions: {', '.join(relevant)}")
        print()


def cmd_cls(args):
    """Find appmaps that call a given class."""
    idx = load_index(args.dir)
    # Fuzzy: match class name as substring
    pat = re.compile(args.classname, re.I)
    matches = {
        cls: files for cls, files in idx.get("by_class", {}).items()
        if pat.search(cls)
    }
    if not matches:
        print(f"No class matching {args.classname!r} found.")
        return

    appmaps_by_file = {e["file"]: e for e in idx["appmaps"]}
    all_files = set()
    for cls, files in matches.items():
        all_files.update(files)

    print(f"Class pattern {args.classname!r} → {len(matches)} class(es), "
          f"{len(all_files)} appmap(s):\n")
    for cls in sorted(matches):
        files = matches[cls]
        print(f"  {cls}  ({len(files)} test(s))")
        for fpath in files:
            entry = appmaps_by_file.get(fpath, {})
            print(f"    {one_liner(entry)}")
        print()


def cmd_table(args):
    """Find appmaps that query a given SQL table."""
    idx = load_index(args.dir)
    pat = re.compile(args.table, re.I)
    matches = {
        tbl: files for tbl, files in idx.get("by_table", {}).items()
        if pat.search(tbl)
    }
    if not matches:
        print(f"No SQL table matching {args.table!r} found.")
        return

    appmaps_by_file = {e["file"]: e for e in idx["appmaps"]}
    print(f"SQL table pattern {args.table!r}:\n")
    for tbl in sorted(matches):
        files = matches[tbl]
        print(f"  Table: {tbl}  ({len(files)} test(s))")
        for fpath in files:
            entry = appmaps_by_file.get(fpath, {})
            ops = entry.get("sql_ops", [])
            print(f"    {one_liner(entry)}  ops:{ops}")
        print()


def cmd_route(args):
    """Find appmaps for a given HTTP route."""
    idx = load_index(args.dir)
    pat = re.compile(args.route, re.I)
    matches = {
        route: files for route, files in idx.get("by_http_entry", {}).items()
        if pat.search(route)
    }
    if not matches:
        print(f"No HTTP route matching {args.route!r} found.")
        return

    appmaps_by_file = {e["file"]: e for e in idx["appmaps"]}
    print(f"HTTP route pattern {args.route!r}:\n")
    for route in sorted(matches):
        files = matches[route]
        print(f"  Route: {route}  ({len(files)} test(s))")
        for fpath in files:
            entry = appmaps_by_file.get(fpath, {})
            print(f"    {one_liner(entry)}")
        print()


def cmd_coverage(args):
    """Show coverage of HTTP routes, SQL tables, and classes across the collection."""
    idx = load_index(args.dir)
    appmaps = idx["appmaps"]
    total = len(appmaps)
    succeeded = len(idx.get("by_status", {}).get("succeeded", []))
    failed = len(idx.get("by_status", {}).get("failed", []))

    print("═" * 70)
    print("Coverage Report")
    print("═" * 70)
    print(f"Total: {total} tests  ({succeeded} pass, {failed} fail)\n")

    print("HTTP Routes:")
    print(f"  {'Route':<45} {'Tests':>5}  {'Status codes'}")
    print("  " + "─" * 70)
    appmaps_by_file = {e["file"]: e for e in appmaps}
    for route in sorted(idx.get("by_http_entry", {})):
        files = idx["by_http_entry"][route]
        statuses = [
            str(appmaps_by_file[f].get("http_status", "?"))
            for f in files if f in appmaps_by_file
        ]
        print(f"  {route:<45} {len(files):>5}  [{', '.join(sorted(set(statuses)))}]")

    print()
    print("SQL Tables:")
    print(f"  {'Table':<25} {'Tests':>5}  {'Operations'}")
    print("  " + "─" * 50)
    for tbl in sorted(idx.get("by_table", {})):
        files = idx["by_table"][tbl]
        ops = set()
        for f in files:
            e = appmaps_by_file.get(f, {})
            ops.update(e.get("sql_ops", []))
        print(f"  {tbl:<25} {len(files):>5}  {sorted(ops)}")

    print()
    print("Classes (appearing in ≥2 tests):")
    for cls in sorted(idx.get("by_class", {})):
        files = idx["by_class"][cls]
        if len(files) >= 2:
            print(f"  {cls:<50} {len(files):>3} tests")

    print()
    exceptions_seen = idx.get("by_exception", {})
    if exceptions_seen:
        print("Exception types raised:")
        for exc in sorted(exceptions_seen):
            files = exceptions_seen[exc]
            print(f"  {exc:<55} {len(files):>2} test(s)")


def cmd_diff(args):
    """Compare two appmap files' call trees."""
    import importlib.util
    tool_path = os.path.join(os.path.dirname(__file__), "appmap_tool.py")
    spec = importlib.util.spec_from_file_location("appmap_tool", tool_path)
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)

    def load_tree(path):
        data = tool.load_appmap(path)
        events = data.get("events", [])
        call_to_return = {
            e["parent_id"]: e for e in events
            if e["event"] == "return" and "parent_id" in e
        }
        tree = tool.build_call_tree(events)
        return [
            (tool.event_kind(e), depth, call_to_return.get(e["id"]))
            for e, depth in tree
        ]

    tree_a = load_tree(args.file1)
    tree_b = load_tree(args.file2)

    # Build signature lists for comparison
    def sig(kind, depth, ret):
        rv = tool.format_return_value(ret) if ret else ""
        return f"{'  '*depth}{kind} {rv}"

    sigs_a = {sig(k, d, r) for k, d, r in tree_a}
    sigs_b = {sig(k, d, r) for k, d, r in tree_b}

    only_in_a = sigs_a - sigs_b
    only_in_b = sigs_b - sigs_a
    common = len(sigs_a & sigs_b)

    name_a = os.path.basename(args.file1)
    name_b = os.path.basename(args.file2)

    print(f"Diff: {name_a}  vs  {name_b}")
    print(f"Common events: {common}  |  Only in A: {len(only_in_a)}  |  Only in B: {len(only_in_b)}")
    print()

    if not only_in_a and not only_in_b:
        print("Call trees are identical.")
        return

    print(f"Only in A ({name_a}):")
    if only_in_a:
        for s in sorted(only_in_a):
            print(f"  - {s.strip()}")
    else:
        print("  (none)")

    print()
    print(f"Only in B ({name_b}):")
    if only_in_b:
        for s in sorted(only_in_b):
            print(f"  + {s.strip()}")
    else:
        print("  (none)")

    print()
    print("Full tree A:")
    for kind, depth, ret in tree_a:
        indent = "  " * depth
        rv = f" {tool.format_return_value(ret)}" if ret else ""
        s = f"{indent}{kind}{rv}"
        marker = " ←" if sig(kind, depth, ret) in only_in_a else ""
        print(f"  {s}{marker}")

    print()
    print("Full tree B:")
    for kind, depth, ret in tree_b:
        indent = "  " * depth
        rv = f" {tool.format_return_value(ret)}" if ret else ""
        s = f"{indent}{kind}{rv}"
        marker = " ←" if sig(kind, depth, ret) in only_in_b else ""
        print(f"  {s}{marker}")


def cmd_related(args):
    """Find appmaps that share classes or HTTP routes with a given file."""
    idx = load_index(args.dir)
    appmaps_by_file = {e["file"]: e for e in idx["appmaps"]}

    # Resolve the target file
    target_path = args.file
    if not os.path.isabs(target_path):
        target_path = os.path.join(args.dir, target_path)
    # Try to find by basename if not exact
    if target_path not in appmaps_by_file:
        base = os.path.basename(args.file)
        for fpath in appmaps_by_file:
            if os.path.basename(fpath) == base:
                target_path = fpath
                break

    target = appmaps_by_file.get(target_path)
    if not target:
        print(f"File not found in index: {args.file}")
        print(f"Available files: {list(appmaps_by_file.keys())[:5]}...")
        return

    target_classes = set(target.get("classes", []))
    target_tables = set(target.get("sql_tables", []))
    target_route = target.get("http_entry")

    scores = {}
    for fpath, entry in appmaps_by_file.items():
        if fpath == target_path:
            continue
        score = 0
        shared_classes = target_classes & set(entry.get("classes", []))
        shared_tables = target_tables & set(entry.get("sql_tables", []))
        same_route = entry.get("http_entry") == target_route and target_route

        score += len(shared_classes) * 2
        score += len(shared_tables) * 3
        score += 5 if same_route else 0

        if score > 0:
            scores[fpath] = (score, shared_classes, shared_tables, same_route)

    if not scores:
        print(f"No related appmaps found for {os.path.basename(target_path)}")
        return

    print(f"Related to: {target.get('name', target_path)}\n")
    print(f"  HTTP entry: {target_route}")
    print(f"  Classes: {', '.join(sorted(target_classes))}")
    print(f"  Tables: {', '.join(sorted(target_tables))}")
    print()

    ranked = sorted(scores.items(), key=lambda x: x[1][0], reverse=True)
    print(f"{'Score':<6} {'Test':<58} {'Shared'}")
    print("─" * 90)
    for fpath, (score, classes, tables, same_route) in ranked[:15]:
        entry = appmaps_by_file[fpath]
        shared_parts = []
        if same_route:
            shared_parts.append(f"route:{target_route}")
        if classes:
            shared_parts.append(f"classes:{','.join(sorted(classes))}")
        if tables:
            shared_parts.append(f"tables:{','.join(sorted(tables))}")
        icon = status_icon(entry["test_status"])
        print(f"  {score:<4} {icon} {short_name(entry):<56} {' | '.join(shared_parts)}")


def cmd_open(args):
    """Delegate to appmap_tool.py for a single file."""
    import subprocess
    tool = os.path.join(os.path.dirname(__file__), "appmap_tool.py")
    cmd = [sys.executable, tool] + list(args.cmd_args)
    subprocess.run(cmd)


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Navigate a collection of AppMap files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    sub = parser.add_subparsers(dest="command")

    p_idx = sub.add_parser("index", help="Build/refresh index")
    p_idx.add_argument("dir")
    p_idx.add_argument("--force", action="store_true", help="Force full rebuild")

    p_list = sub.add_parser("list", help="List all appmaps")
    p_list.add_argument("dir")
    p_list.add_argument("--failed", action="store_true")
    p_list.add_argument("--route", help="Filter by HTTP route pattern")
    p_list.add_argument("--count-tokens", action="store_true")

    p_stats = sub.add_parser("stats", help="Collection statistics")
    p_stats.add_argument("dir")

    p_fail = sub.add_parser("failing", help="Show failed tests")
    p_fail.add_argument("dir")

    p_find = sub.add_parser("find", help="Full-text search across index")
    p_find.add_argument("dir")
    p_find.add_argument("pattern")

    p_cls = sub.add_parser("cls", help="Find appmaps using a class")
    p_cls.add_argument("dir")
    p_cls.add_argument("classname")

    p_tbl = sub.add_parser("table", help="Find appmaps querying a SQL table")
    p_tbl.add_argument("dir")
    p_tbl.add_argument("table")

    p_route = sub.add_parser("route", help="Find appmaps for an HTTP route")
    p_route.add_argument("dir")
    p_route.add_argument("route")

    p_cov = sub.add_parser("coverage", help="HTTP/SQL/class coverage report")
    p_cov.add_argument("dir")

    p_diff = sub.add_parser("diff", help="Compare two appmaps")
    p_diff.add_argument("file1")
    p_diff.add_argument("file2")

    p_rel = sub.add_parser("related", help="Find related appmaps")
    p_rel.add_argument("dir")
    p_rel.add_argument("file")

    p_open = sub.add_parser("open", help="Run appmap_tool command on a file")
    p_open.add_argument("cmd_args", nargs=argparse.REMAINDER)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(1)

    dispatch = {
        "index": cmd_index,
        "list": cmd_list,
        "stats": cmd_stats,
        "failing": cmd_failing,
        "find": cmd_find,
        "cls": cmd_cls,
        "table": cmd_table,
        "route": cmd_route,
        "coverage": cmd_coverage,
        "diff": cmd_diff,
        "related": cmd_related,
        "open": cmd_open,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
