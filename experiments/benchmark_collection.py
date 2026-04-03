#!/usr/bin/env python3
"""
benchmark_collection.py — Token cost comparison for collection-level navigation.

Compares loading the full collection (naive) vs using the index/tool system.
"""
import json
import os
import sys
import glob

sys.path.insert(0, os.path.dirname(__file__))
from appmap_collection import load_index, one_liner, cmd_stats
from appmap_tool import load_appmap, cmd_summary, cmd_tree

SUITE_DIR = "tmp/appmap/rspec"


def approx_tokens(text: str) -> int:
    return len(text) // 4


def fmt(n: int) -> str:
    return f"{n:7,}"


class FakeArgs:
    no_params = False
    no_elapsed = False
    depth = None
    count_tokens = False


def main():
    files = sorted(glob.glob(os.path.join(SUITE_DIR, "*.appmap.json")))
    idx = load_index(SUITE_DIR)
    fa = FakeArgs()

    # ── Baseline: load everything ─────────────────────────────────────────────
    all_raw = ""
    all_summaries = ""
    all_trees = ""
    for fpath in files:
        raw = open(fpath).read()
        all_raw += raw
        data = load_appmap(fpath)
        all_summaries += cmd_summary(data, fa) + "\n\n"
        all_trees += cmd_tree(data, fa) + "\n\n"

    # ── Index-based views ─────────────────────────────────────────────────────
    listing = "\n".join(one_liner(e) for e in idx["appmaps"])

    # Focused: just the failing tests' trees
    failing_files = idx.get("by_status", {}).get("failed", [])
    failing_trees = ""
    for fpath in failing_files:
        data = load_appmap(fpath)
        failing_trees += f"# {os.path.basename(fpath)}\n"
        failing_trees += cmd_tree(data, fa) + "\n\n"

    # Scenario: debugging the Stripe failure
    # Step 1: listing (identify candidates)
    # Step 2: route search result (~index lookup, no file load)
    route_result = "\n".join(
        one_liner(e) for e in idx["appmaps"]
        if e.get("http_entry") == "POST /orders"
    )
    # Step 3: diff of failing vs passing (load 2 files)
    failing_file = "tmp/appmap/rspec/OrdersController_create_rolls_back_when_stripe_fails.appmap.json"
    passing_file = "tmp/appmap/rspec/OrdersController_create_places_an_order.appmap.json"
    fail_tree = cmd_tree(load_appmap(failing_file), fa)
    pass_tree = cmd_tree(load_appmap(passing_file), fa)
    debug_workflow = listing + "\n\n" + route_result + "\n\n" + fail_tree + "\n\n" + pass_tree

    results = [
        ("── NAIVE APPROACHES ────────────────────────────────────", None),
        ("Load all 19 raw JSON files", all_raw),
        ("Load all 19 summaries", all_summaries),
        ("Load all 19 compact trees", all_trees),
        ("", None),
        ("── INDEX-BASED APPROACHES ──────────────────────────────", None),
        ("Collection listing (1 line/appmap, index only)", listing),
        ("Failing tests' trees only (2 files)", failing_trees),
        ("Route filter: POST /orders (index only)", route_result),
        ("", None),
        ("── REALISTIC DEBUG WORKFLOW ─────────────────────────────", None),
        ("Listing + route filter + 2 file trees (debug workflow)", debug_workflow),
        ("Listing alone (orient)", listing),
        ("2 trees (compare failing vs passing)", fail_tree + "\n\n" + pass_tree),
    ]

    print("=" * 75)
    print(f"Collection: {SUITE_DIR} — {len(files)} appmap files")
    total_raw_kb = sum(os.path.getsize(f) for f in files) / 1024
    index_kb = os.path.getsize(os.path.join(SUITE_DIR, ".appmap-index.json")) / 1024
    print(f"Raw total: {total_raw_kb:.0f} KB   Index: {index_kb:.0f} KB")
    print("=" * 75)
    print(f"{'Scenario':<55} {'~Tokens':>8}  {'vs naive':>9}")
    print("─" * 75)

    baseline_tokens = approx_tokens(all_raw)
    for label, text in results:
        if text is None:
            print(f"\n{label}")
            continue
        tokens = approx_tokens(text)
        ratio = tokens / baseline_tokens if baseline_tokens else 0
        print(f"  {label:<53} {fmt(tokens)}  {ratio:8.1%}")

    print("=" * 75)
    print()
    print("Debug workflow breakdown:")
    print(f"  1. Listing (orient):             ~{approx_tokens(listing):,} tokens  [index only, 0 files loaded]")
    print(f"  2. Route filter (POST /orders):  ~{approx_tokens(route_result):,} tokens  [index only, 0 files loaded]")
    print(f"  3. Failing tree:                 ~{approx_tokens(fail_tree):,} tokens  [1 file loaded]")
    print(f"  4. Passing tree:                 ~{approx_tokens(pass_tree):,} tokens  [1 file loaded]")
    print(f"  TOTAL workflow:                  ~{approx_tokens(debug_workflow):,} tokens  [2 of 19 files loaded]")
    print()
    print(f"  vs naive (all 19 raw files):     ~{baseline_tokens:,} tokens  [{total_raw_kb:.0f} KB]")
    savings = (1 - approx_tokens(debug_workflow) / baseline_tokens) * 100
    print(f"  Savings: {savings:.0f}%")


if __name__ == "__main__":
    main()
