#!/usr/bin/env python3
"""
appmap_tool.py — LLM-friendly AppMap exploration toolkit.

Transforms verbose AppMap JSON into compact representations and provides
grep/slice/expand capabilities so LLMs can navigate large appmaps without
loading the full JSON into context.

Usage:
  python appmap_tool.py <command> [options] <file.appmap.json>

Commands:
  summary           High-level overview (stats, entry point, key flows)
  tree              Indented call tree (like a stack trace)
  compact           One-line-per-event condensed trace
  show <N> [M]      Full detail for event N (or range N-M)
  grep <pattern>    Filter events matching pattern (regex, searches class/method/sql/value)
  http              Show only HTTP request/response events
  sql               Show only SQL queries
  events <N> [M]    Raw JSON for event N or range N-M

Options:
  --no-params       Hide parameter values in tree/compact output
  --no-elapsed      Hide elapsed time
  --depth <N>       Limit tree depth (default: unlimited)
  --count-tokens    Print approximate token count for output
"""

import json
import sys
import re
import argparse
import textwrap
from typing import Optional


# ──────────────────────────────────────────────────────────────────────────────
# Loading and indexing
# ──────────────────────────────────────────────────────────────────────────────

def load_appmap(path: str) -> dict:
    with open(path) as f:
        data = json.load(f)
    # Apply eventUpdates if present
    if "eventUpdates" in data:
        by_id = {e["id"]: e for e in data.get("events", [])}
        for eid_str, update in data["eventUpdates"].items():
            eid = int(eid_str)
            if eid in by_id:
                by_id[eid].update(update)
        data["events"] = list(by_id.values())
    return data


def index_events(events: list) -> dict:
    """Return {id: event} dict."""
    return {e["id"]: e for e in events}


def build_call_tree(events: list) -> list:
    """
    Build a list of (event, depth) tuples for call events only,
    tracking depth via a stack of open call IDs.
    """
    by_id = index_events(events)
    # Map return event -> its call event
    return_to_call = {}
    for e in events:
        if e["event"] == "return" and "parent_id" in e:
            return_to_call[e["id"]] = e["parent_id"]

    # For each call event find its corresponding return
    call_to_return = {}
    for e in events:
        if e["event"] == "return" and "parent_id" in e:
            call_to_return[e["parent_id"]] = e

    result = []
    depth_stack = []  # stack of call event ids

    for e in events:
        if e["event"] == "call":
            # Pop stack entries whose calls have already returned before this call
            # (they're siblings/cousins, not ancestors)
            while depth_stack:
                top = depth_stack[-1]
                top_ret = call_to_return.get(top)
                if top_ret and top_ret["id"] < e["id"]:
                    depth_stack.pop()
                else:
                    break
            depth = len(depth_stack)
            result.append((e, depth))
            depth_stack.append(e["id"])

    return result


# ──────────────────────────────────────────────────────────────────────────────
# Event formatting helpers
# ──────────────────────────────────────────────────────────────────────────────

def event_kind(e: dict) -> str:
    """Return a short string describing what kind of event this is."""
    if "http_server_request" in e:
        r = e["http_server_request"]
        return f"HTTP→  {r['request_method']} {r.get('normalized_path_info') or r['path_info']}"
    if "http_client_request" in e:
        r = e["http_client_request"]
        return f"HTTP↗  {r['request_method']} {r['url']}"
    if "sql_query" in e:
        sql = e["sql_query"]["sql"]
        verb = sql.strip().split()[0].upper()
        # Extract table name heuristically
        m = re.search(r'(?:FROM|INTO|UPDATE)\s+"?(\w+)"?', sql, re.I)
        table = m.group(1) if m else "?"
        return f"SQL    {verb} {table}"
    if "defined_class" in e:
        cls = e["defined_class"]
        meth = e.get("method_id", "?")
        is_static = e.get("static", False)
        sep = "." if is_static else "#"
        return f"CALL   {cls}{sep}{meth}"
    return "CALL   ?"


def format_params(e: dict, short: bool = True) -> str:
    """Format parameters as a compact string."""
    params = e.get("parameters", [])
    if not params:
        return "()"
    parts = []
    for p in params:
        name = p.get("name", "_")
        val = p.get("value", "")
        cls = p.get("class", "")
        if short:
            # Trim long values
            if len(val) > 40:
                val = val[:37] + "..."
            parts.append(f"{name}={val!r}" if val else f"{name}:{cls}")
        else:
            parts.append(f"{name}:{cls}={val!r}" if val else f"{name}:{cls}")
    return "(" + ", ".join(parts) + ")"


def format_return_value(ret_event: dict) -> str:
    """Format a return event's value as a short string."""
    if "http_server_response" in ret_event:
        return f"→ HTTP {ret_event['http_server_response']['status_code']}"
    if "http_client_response" in ret_event:
        return f"→ HTTP {ret_event['http_client_response']['status_code']}"
    rv = ret_event.get("return_value")
    if rv:
        val = rv.get("value", "")
        cls = rv.get("class", "")
        if len(str(val)) > 40:
            val = str(val)[:37] + "..."
        return f"→ {cls}({val!r})" if val else f"→ {cls}"
    excs = ret_event.get("exceptions", [])
    if excs:
        exc = excs[0]
        return f"→ RAISE {exc['class']}: {exc.get('message','')[:40]}"
    return ""


def elapsed_str(ret_event: dict) -> str:
    elapsed = ret_event.get("elapsed")
    if elapsed is None:
        return ""
    if elapsed < 0.001:
        return f" [{elapsed*1000:.2f}ms]"
    return f" [{elapsed*1000:.0f}ms]"


# ──────────────────────────────────────────────────────────────────────────────
# Commands
# ──────────────────────────────────────────────────────────────────────────────

def cmd_summary(data: dict, args) -> str:
    events = data.get("events", [])
    meta = data.get("metadata", {})
    lines = []

    lines.append("═" * 70)
    lines.append(f"AppMap: {meta.get('name', '(unnamed)')}")
    lines.append("═" * 70)

    # Metadata
    lang = meta.get("language", {})
    if lang:
        lines.append(f"Language : {lang.get('name','')} {lang.get('version','')}")
    fws = meta.get("frameworks", [])
    if fws:
        lines.append(f"Frameworks: {', '.join(f['name']+' '+f['version'] for f in fws)}")
    if meta.get("test_status"):
        lines.append(f"Test status: {meta['test_status'].upper()}")
    if meta.get("source_location"):
        lines.append(f"Source: {meta['source_location']}")
    lines.append("")

    # Event stats
    call_events = [e for e in events if e["event"] == "call"]
    sql_events = [e for e in call_events if "sql_query" in e]
    http_server = [e for e in call_events if "http_server_request" in e]
    http_client = [e for e in call_events if "http_client_request" in e]
    func_calls = [e for e in call_events if "defined_class" in e]

    lines.append(f"Events   : {len(events)} total ({len(call_events)} calls, {len(events)-len(call_events)} returns)")
    lines.append(f"Functions: {len(func_calls)} calls")
    lines.append(f"SQL      : {len(sql_events)} queries")
    if http_server:
        r = http_server[0]["http_server_request"]
        lines.append(f"HTTP In  : {len(http_server)} request(s), entry={r['request_method']} {r['path_info']}")
    if http_client:
        lines.append(f"HTTP Out : {len(http_client)} outbound request(s)")
    lines.append("")

    # Show entry HTTP event if present
    if http_server:
        e = http_server[0]
        r = e["http_server_request"]
        lines.append(f"Entry point: {r['request_method']} {r['path_info']} (event #{e['id']})")
        msg = e.get("message", [])
        if msg:
            lines.append(f"Request params: {', '.join(p['name']+'='+repr(p.get('value','')) for p in msg)}")

    # Show exit HTTP response
    return_events = [e for e in events if e.get("event") == "return"]
    http_responses = [e for e in return_events if "http_server_response" in e]
    if http_responses:
        resp = http_responses[-1]
        lines.append(f"Response: HTTP {resp['http_server_response']['status_code']}{elapsed_str(resp)}")

    lines.append("")
    lines.append("SQL Queries:")
    for e in sql_events:
        sql = e["sql_query"]["sql"]
        lines.append(f"  #{e['id']:3d}  {sql[:80]}")

    if http_client:
        lines.append("")
        lines.append("Outbound HTTP:")
        for e in http_client:
            r = e["http_client_request"]
            lines.append(f"  #{e['id']:3d}  {r['request_method']} {r['url']}")

    lines.append("")
    lines.append(f"Tip: use `tree` for call flow, `compact` for one-line trace,")
    lines.append(f"     `grep <pattern>` to filter, `show <N>` for event details")

    return "\n".join(lines)


def cmd_tree(data: dict, args) -> str:
    events = data.get("events", [])
    by_id = index_events(events)
    call_to_return = {}
    for e in events:
        if e["event"] == "return" and "parent_id" in e:
            call_to_return[e["parent_id"]] = e

    tree = build_call_tree(events)
    max_depth = getattr(args, 'depth', None)
    show_params = not getattr(args, 'no_params', False)
    show_elapsed = not getattr(args, 'no_elapsed', False)

    lines = []
    for e, depth in tree:
        if max_depth is not None and depth > max_depth:
            continue

        indent = "  " * depth
        kind = event_kind(e)
        eid = e["id"]

        # Params
        param_str = ""
        if show_params and "defined_class" in e:
            param_str = format_params(e, short=True)

        # Return value
        ret_str = ""
        elapsed = ""
        ret = call_to_return.get(eid)
        if ret:
            ret_str = format_return_value(ret)
            if show_elapsed:
                elapsed = elapsed_str(ret)

        line = f"{indent}#{eid:3d} {kind}"
        if param_str and param_str != "()":
            line += " " + param_str
        if ret_str:
            line += " " + ret_str
        if elapsed:
            line += elapsed

        lines.append(line)

    return "\n".join(lines)


def cmd_compact(data: dict, args) -> str:
    """One-line-per-event, showing call+return merged on a single line."""
    return cmd_tree(data, args)


def cmd_show(data: dict, args) -> str:
    """Show full JSON detail for one event or a range."""
    events = data.get("events", [])
    by_id = index_events(events)

    n = args.N
    m = getattr(args, 'M', None)

    if m is None:
        # Single event
        e = by_id.get(n)
        if e is None:
            return f"Error: no event with id {n}"
        # Also show its counterpart
        lines = [json.dumps(e, indent=2)]
        if e["event"] == "call":
            for evt in events:
                if evt.get("event") == "return" and evt.get("parent_id") == n:
                    lines.append("")
                    lines.append("Corresponding return:")
                    lines.append(json.dumps(evt, indent=2))
                    break
        elif e["event"] == "return" and "parent_id" in e:
            pid = e["parent_id"]
            call = by_id.get(pid)
            if call:
                lines = ["Corresponding call:"]
                lines.append(json.dumps(call, indent=2))
                lines.append("")
                lines.append("Return:")
                lines.append(json.dumps(e, indent=2))
        return "\n".join(lines)
    else:
        # Range
        range_events = [e for e in events if n <= e["id"] <= m]
        if not range_events:
            return f"Error: no events in range {n}-{m}"
        return json.dumps(range_events, indent=2)


def cmd_grep(data: dict, args) -> str:
    """Filter events matching a pattern and show them in compact form."""
    events = data.get("events", [])
    by_id = index_events(events)
    pattern = re.compile(args.pattern, re.I)

    def event_text(e: dict) -> str:
        """Flatten event to searchable text."""
        parts = []
        parts.append(e.get("defined_class", ""))
        parts.append(e.get("method_id", ""))
        if "sql_query" in e:
            parts.append(e["sql_query"]["sql"])
        if "http_server_request" in e:
            r = e["http_server_request"]
            parts.append(r["request_method"])
            parts.append(r["path_info"])
        if "http_client_request" in e:
            r = e["http_client_request"]
            parts.append(r["request_method"])
            parts.append(r["url"])
        for p in e.get("parameters", []):
            parts.append(p.get("name", ""))
            parts.append(p.get("class", ""))
            parts.append(str(p.get("value", "")))
        if "return_value" in e:
            rv = e["return_value"]
            parts.append(rv.get("class", ""))
            parts.append(str(rv.get("value", "")))
        for exc in e.get("exceptions", []):
            parts.append(exc.get("class", ""))
            parts.append(exc.get("message", ""))
        for msg in e.get("message", []):
            parts.append(msg.get("name", ""))
            parts.append(str(msg.get("value", "")))
        return " ".join(parts)

    matched_ids = set()
    for e in events:
        if pattern.search(event_text(e)):
            matched_ids.add(e["id"])
            # Also add corresponding call/return
            if e["event"] == "return" and "parent_id" in e:
                matched_ids.add(e["parent_id"])
            elif e["event"] == "call":
                for ev2 in events:
                    if ev2.get("event") == "return" and ev2.get("parent_id") == e["id"]:
                        matched_ids.add(ev2["id"])
                        break

    if not matched_ids:
        return f"No events match pattern: {args.pattern!r}"

    # Show matched events in compact tree form
    call_to_return = {}
    for e in events:
        if e["event"] == "return" and "parent_id" in e:
            call_to_return[e["parent_id"]] = e

    tree = build_call_tree(events)
    lines = [f"Grep: {args.pattern!r} — {len(matched_ids)} matching events\n"]
    for e, depth in tree:
        if e["id"] not in matched_ids:
            continue
        indent = "  " * depth
        kind = event_kind(e)
        eid = e["id"]
        param_str = format_params(e, short=True) if "defined_class" in e else ""
        ret_str = ""
        elapsed = ""
        ret = call_to_return.get(eid)
        if ret:
            ret_str = format_return_value(ret)
            elapsed = elapsed_str(ret)
        line = f"{indent}#{eid:3d} {kind}"
        if param_str and param_str != "()":
            line += " " + param_str
        if ret_str:
            line += " " + ret_str
        if elapsed:
            line += elapsed
        lines.append(line)

    return "\n".join(lines)


def cmd_http(data: dict, args) -> str:
    """Show only HTTP events (server and client)."""
    events = data.get("events", [])
    lines = []
    for e in events:
        if e["event"] == "call":
            if "http_server_request" in e:
                r = e["http_server_request"]
                lines.append(f"#{e['id']:3d} → SERVER {r['request_method']} {r['path_info']}")
                msg = e.get("message", [])
                if msg:
                    lines.append(f"     params: {', '.join(p['name']+'='+repr(p.get('value','')) for p in msg)}")
                hdrs = r.get("headers", {})
                interesting = {k: v for k, v in hdrs.items()
                               if k.lower() not in ("host","accept-encoding","accept-language","connection","user-agent")}
                if interesting:
                    lines.append(f"     headers: {interesting}")
            elif "http_client_request" in e:
                r = e["http_client_request"]
                lines.append(f"#{e['id']:3d} ↗ CLIENT {r['request_method']} {r['url']}")
                msg = e.get("message", [])
                if msg:
                    lines.append(f"     params: {', '.join(p['name']+'='+repr(p.get('value','')) for p in msg)}")
        elif e["event"] == "return":
            if "http_server_response" in e:
                resp = e["http_server_response"]
                lines.append(f"#{e['id']:3d} ← SERVER HTTP {resp['status_code']}{elapsed_str(e)}")
            elif "http_client_response" in e:
                resp = e["http_client_response"]
                lines.append(f"#{e['id']:3d} ← CLIENT HTTP {resp['status_code']}{elapsed_str(e)}")
    return "\n".join(lines) if lines else "No HTTP events found."


def cmd_sql(data: dict, args) -> str:
    """Show only SQL query events."""
    events = data.get("events", [])
    by_id = index_events(events)
    call_to_return = {e["parent_id"]: e for e in events
                      if e["event"] == "return" and "parent_id" in e}
    lines = []
    for e in events:
        if e["event"] == "call" and "sql_query" in e:
            q = e["sql_query"]
            ret = call_to_return.get(e["id"])
            el = elapsed_str(ret) if ret else ""
            lines.append(f"#{e['id']:3d} [{q['database_type']}]{el}")
            lines.append(f"     {q['sql']}")
            msg = e.get("message", [])
            for m in msg:
                lines.append(f"     binds: {m.get('value','')}")
            lines.append("")
    return "\n".join(lines) if lines else "No SQL events found."


def cmd_events(data: dict, args) -> str:
    """Raw JSON for event range."""
    return cmd_show(data, args)


# ──────────────────────────────────────────────────────────────────────────────
# Token counting (rough estimate: 1 token ≈ 4 chars)
# ──────────────────────────────────────────────────────────────────────────────

def count_tokens(text: str) -> int:
    return len(text) // 4


# ──────────────────────────────────────────────────────────────────────────────
# CLI
# ──────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="LLM-friendly AppMap exploration tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--count-tokens", action="store_true",
                        help="Append approximate token count to output")
    parser.add_argument("--no-params", action="store_true",
                        help="Hide parameter values")
    parser.add_argument("--no-elapsed", action="store_true",
                        help="Hide elapsed time")
    parser.add_argument("--depth", type=int, default=None,
                        help="Limit call tree depth")

    subparsers = parser.add_subparsers(dest="command")

    for sub in ("summary", "tree", "compact", "http", "sql"):
        sp = subparsers.add_parser(sub)
        sp.add_argument("file")
        sp.add_argument("--count-tokens", action="store_true")
        sp.add_argument("--no-params", action="store_true")
        sp.add_argument("--no-elapsed", action="store_true")
        sp.add_argument("--depth", type=int, default=None)

    show_p = subparsers.add_parser("show")
    show_p.add_argument("N", type=int)
    show_p.add_argument("M", type=int, nargs="?")
    show_p.add_argument("file")
    show_p.add_argument("--count-tokens", action="store_true")

    events_p = subparsers.add_parser("events")
    events_p.add_argument("N", type=int)
    events_p.add_argument("M", type=int, nargs="?")
    events_p.add_argument("file")
    events_p.add_argument("--count-tokens", action="store_true")

    grep_p = subparsers.add_parser("grep")
    grep_p.add_argument("pattern")
    grep_p.add_argument("file")
    grep_p.add_argument("--count-tokens", action="store_true")
    grep_p.add_argument("--no-params", action="store_true")
    grep_p.add_argument("--no-elapsed", action="store_true")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    data = load_appmap(args.file)

    dispatch = {
        "summary": cmd_summary,
        "tree": cmd_tree,
        "compact": cmd_compact,
        "show": cmd_show,
        "events": cmd_events,
        "grep": cmd_grep,
        "http": cmd_http,
        "sql": cmd_sql,
    }

    result = dispatch[args.command](data, args)
    print(result)

    if getattr(args, 'count_tokens', False):
        n = count_tokens(result)
        print(f"\n── ~{n} tokens ──")


if __name__ == "__main__":
    main()
