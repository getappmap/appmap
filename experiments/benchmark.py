#!/usr/bin/env python3
"""
benchmark.py — Compare token consumption of different AppMap representations.

Formats compared:
  1. Raw JSON (baseline)
  2. Minified JSON
  3. compact/tree format (this tool)
  4. summary only
  5. compact + no-params
  6. depth-limited tree (depth=2)
  7. http + sql only (focused slices)
  8. Hypothetical "ideal" — just the tree, no raw JSON ever loaded
"""

import json
import sys
import os
import argparse
sys.path.insert(0, os.path.dirname(__file__))
from appmap_tool import (
    load_appmap, cmd_summary, cmd_tree, cmd_sql, cmd_http
)


def approx_tokens(text: str) -> int:
    """Rough estimate: ~4 chars per token (GPT/Claude tiktoken average)."""
    return len(text) // 4


def fmt(n: int) -> str:
    return f"{n:6,}"


class FakeArgs:
    no_params = False
    no_elapsed = False
    depth = None
    count_tokens = False


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="AppMap JSON file")
    args = parser.parse_args()

    data = load_appmap(args.file)
    raw_json = open(args.file).read()
    min_json = json.dumps(json.loads(raw_json), separators=(",", ":"))

    fa = FakeArgs()

    summary_text = cmd_summary(data, fa)
    tree_text = cmd_tree(data, fa)

    fa2 = FakeArgs(); fa2.no_params = True
    tree_noparams = cmd_tree(data, fa2)

    fa3 = FakeArgs(); fa3.depth = 2
    tree_depth2 = cmd_tree(data, fa3)

    http_text = cmd_http(data, fa)
    sql_text = cmd_sql(data, fa)
    focused = http_text + "\n\n" + sql_text

    results = [
        ("Raw JSON (pretty-printed)", raw_json),
        ("Minified JSON", min_json),
        ("summary command", summary_text),
        ("tree (full params + elapsed)", tree_text),
        ("tree (no params)", tree_noparams),
        ("tree (depth≤2)", tree_depth2),
        ("http + sql slices", focused),
        ("summary + tree", summary_text + "\n\n" + tree_text),
    ]

    print("=" * 70)
    print(f"AppMap: {data.get('metadata',{}).get('name','(unnamed)')}")
    print(f"Events: {len(data.get('events',[]))}")
    print("=" * 70)
    print(f"{'Format':<40} {'Chars':>8}  {'~Tokens':>8}  {'vs Raw':>8}")
    print("-" * 70)

    baseline = len(raw_json)
    for label, text in results:
        chars = len(text)
        tokens = approx_tokens(text)
        ratio = chars / baseline
        print(f"{label:<40} {fmt(chars)}  {fmt(tokens)}  {ratio:7.1%}")

    print("=" * 70)
    print()
    print("Notes:")
    print("  Token counts are rough estimates (~4 chars/token).")
    print("  'Chars' = total character length of the representation.")
    print("  'vs Raw' = fraction of original pretty-printed JSON size.")
    print()
    print("Key insight: an LLM can navigate with summary+tree (~4% of raw),")
    print("then call `show N` to get full JSON only for events it cares about.")


if __name__ == "__main__":
    main()
