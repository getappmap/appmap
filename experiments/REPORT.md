# AppMap LLM Navigation: Research Report

**Branch:** `claude/appmap-llm-optimization-Kgbm0`  
**Date:** April 2026  
**Files:** `experiments/appmap_tool.py`, `experiments/appmap_collection.py`, and related

---

## 1. Problem Statement

AppMap JSON files are verbose by design — they capture rich runtime detail including
every function call, parameter value, SQL query, HTTP header, and return value. This
verbosity is essential for static analysis and visualization tools, but it is hostile
to LLM consumption:

- A single HTTP request trace: **19–27 KB** (~4,800–6,800 tokens)
- A 19-test RSpec suite: **84 KB** (~21,400 tokens)
- A 500-test suite: **~2.2 MB** (~550,000 tokens) — far beyond any context window

Even if context windows continue to grow, loading everything is wasteful and causes
**context rot**: the LLM buries the useful signal under mountains of object IDs,
redundant receiver objects, full HTTP headers, and repeated class names.

---

## 2. Sources of Verbosity

### 2.1 Structural redundancy

Every function call is split into two events (`call` + `return`). A 60-event appmap
represents only 30 actual operations. All structural information — hierarchy, duration,
return values — requires correlating pairs by `id`/`parent_id`.

### 2.2 Per-event metadata overhead

Each call event carries:
- `receiver` object (name, class, value, object_id) — the calling object
- `parameters[]` array — each with name, class, value, object_id, optional properties/items
- `path` + `lineno` — source location (already in classMap)
- `thread_id` — nearly constant for single-threaded apps
- `static` — a boolean repeated on every event

### 2.3 HTTP header noise

HTTP server request events include all headers: User-Agent, Accept-Encoding,
Accept-Language, Connection, Content-Length. For LLM navigation, only
Authorization, Content-Type, and custom headers matter.

### 2.4 Object identity tracking

`object_id` appears on every parameter and receiver. These 15-17 digit integers are
essential for tracking object identity across calls but are purely noise for LLMs
trying to understand *what* the code does.

### 2.5 Value strings truncated at 100 chars

Values are already truncated at 100 chars but the truncation boundary is often
mid-value, making them harder to read than a deliberately shortened version.

---

## 3. Single-File Navigation (`appmap_tool.py`)

### 3.1 The compact tree format

The core insight: merge each call+return pair into a single indented line.

```
#  1 HTTP→  POST /orders → HTTP 201 [684ms]
  #  8 CALL   OrdersController#create [682ms]
    # 11 CALL   OrderProcessingService#call (user='#<User id: 42>', ...) → Order('#<Order id: 101...') [680ms]
      # 40 CALL   PaymentService#charge (amount='98.07') → Payment('#<Payment id: 301...') [351ms]
        # 41 HTTP↗  POST https://api.stripe.com/v1/payment_intents → HTTP 200 [343ms]
        # 43 CALL   Payment.create! (order_id='101', amount='98.07') → Payment('#<Payment id: 301...') [7ms]
          # 44 SQL    INSERT payments [6ms]
```

Each line encodes: `#id TYPE Class#method(params) → return_value [elapsed]`

**What's preserved:** event ID (for drill-down), call hierarchy, class + method,
parameter names + truncated values, return type + value, elapsed time, SQL verb +
table, HTTP method + URL/path + status.

**What's dropped by default** (recoverable via `show N`): thread_id, object_id,
path + lineno (in classMap), full HTTP headers, receiver object, size fields.

### 3.2 Token benchmarks (30-event appmap)

| Format | Chars | ~Tokens | vs Raw |
|--------|-------|---------|--------|
| Raw JSON (pretty) | 19,243 | 4,810 | 100% |
| Minified JSON | 12,122 | 3,030 | 63% |
| `summary` | 1,036 | 259 | 5% |
| `tree` (full params + elapsed) | 1,502 | 375 | 8% |
| `tree` (no params) | 1,169 | 292 | 6% |
| `tree` (depth ≤ 2) | 371 | 92 | 2% |
| `http` + `sql` slices | 868 | 217 | 5% |
| `summary` + `tree` | 2,540 | 635 | 13% |

### 3.3 Commands

| Command | Purpose |
|---------|---------|
| `summary <file>` | High-level orientation: stats, HTTP entry/exit, SQL list, outbound calls |
| `tree <file>` | Full indented call tree with params and return values |
| `tree --depth N` | Depth-limited tree (2 levels = ~92 tokens for 30-event map) |
| `tree --no-params` | Tree without parameter values |
| `show N [M]` | Full JSON for event N (or range N–M), with call+return paired |
| `grep <pattern>` | Filter events matching regex, show in tree context |
| `http <file>` | Only HTTP request/response events with relevant headers |
| `sql <file>` | Only SQL queries with bind values |

### 3.4 Recommended LLM workflow for a single file

1. `summary` — orient (259–420 tokens, tells you entry point, SQL count, HTTP calls)
2. `tree` — understand execution flow (375–716 tokens)
3. `grep <pattern>` — focus on a specific concern (e.g., `grep payment`)
4. `show N` — drill into a specific event for full parameter detail

Total for a complex trace: **under 2,000 tokens**, vs 5,000–7,000 for raw JSON.

---

## 4. Collection Navigation (`appmap_collection.py`)

### 4.1 The scale problem

Real test suites generate one `.appmap.json` per test case in
`tmp/appmap/{framework}/`. Loading all files naively:

| Suite size | Raw JSON | ~Tokens |
|------------|----------|---------|
| 19 files (benchmark suite) | 84 KB | ~21,400 |
| 100 files (small app) | ~450 KB | ~112,500 |
| 500 files (medium app) | ~2.2 MB | ~562,500 |

Even loading all compact trees is expensive at scale: ~1,500 tokens for 19 files
scales to ~8,000 for 100 files — still non-trivial.

### 4.2 Two-tier lazy loading architecture

```
┌─────────────────────────────────────┐
│  .appmap-index.json (built once)    │
│                                     │
│  Per file (lightweight entry):      │
│    name, test_status, http_entry,   │
│    http_status, elapsed, classes[], │
│    sql_tables[], sql_ops[],         │
│    http_out[], exceptions[]         │
│                                     │
│  Inverted indexes:                  │
│    by_class, by_table,              │
│    by_http_entry, by_status,        │
│    by_exception                     │
└──────────────┬──────────────────────┘
               │  All collection queries
               ▼
┌──────────────────────────────────┐
│  Individual .appmap.json files   │
│  (loaded only on demand, via     │
│   appmap_tool tree/show/grep)    │
└──────────────────────────────────┘
```

Index size for 19 files: 25 KB vs 84 KB raw (30% overhead).
The ratio improves for larger suites since the per-file index entry is constant
(~1.3 KB) while raw files grow with trace depth.

### 4.3 Token benchmarks (19-file suite)

| Scenario | ~Tokens | Files loaded |
|----------|---------|-------------|
| Naive: all 19 raw files | 21,400 | 19 |
| All 19 compact trees | 1,518 | 19 |
| **Collection listing** | **447** | **0 — index only** |
| Stats report | ~650 | 0 — index only |
| Failing tests detail | ~180 | 0 — index only |
| Route filter (POST /orders) | ~78 | 0 — index only |
| Class search (AuthenticationConcern) | ~120 | 0 — index only |
| **Full debug workflow** | **808** | **2 of 19** |

**96% token reduction** for a realistic debugging workflow.

### 4.4 Commands

| Command | Purpose |
|---------|---------|
| `index <dir>` | Build `.appmap-index.json`, incrementally updates on mtime |
| `list <dir>` | One-line-per-appmap listing with HTTP, SQL, exception summary |
| `stats <dir>` | Collection-wide: routes, tables, slowest tests, failure summary |
| `failing <dir>` | Only failed tests with failure message and location |
| `find <dir> <pat>` | Cross-field regex search over index (no file loading) |
| `cls <dir> <class>` | Find all appmaps calling a class (fuzzy match) |
| `table <dir> <table>` | Find all appmaps querying a SQL table |
| `route <dir> <route>` | Find appmaps for an HTTP route pattern |
| `coverage <dir>` | HTTP routes × status codes, SQL tables × operations, class frequency |
| `diff <file1> <file2>` | Compare two call trees, highlight divergences |
| `related <dir> <file>` | Rank appmaps by similarity score (shared tables, routes, classes) |

### 4.5 The debug workflow in practice

**Scenario:** A test is failing with `expected HTTP status 422 but got 500` on
`POST /orders`. Here's the complete LLM debug session:

**Step 1 — Orient** (~447 tokens, 0 files loaded):
```
appmap_collection list tmp/appmap/rspec
```
```
✓ OrdersController create places an order...   [POST /orders →201 8sql 2out] 504ms
✗ OrdersController create rolls back when...   [POST /orders →500 5sql 1out !CardError] 292ms
✓ OrdersController create returns 422...       [POST /orders →422 3sql !InsufficientStockError] 9ms
```
The `✗` and `!CardError` immediately surface the problem.

**Step 2 — Filter to route** (~78 tokens, 0 files loaded):
```
appmap_collection route tmp/appmap/rspec "POST /orders"
```
Narrows to 3 tests for the same endpoint.

**Step 3 — Diff failing vs passing** (~282 tokens, 2 files loaded):
```
appmap_collection diff <failing>.appmap.json <passing>.appmap.json
```
Output:
```
Only in failing:
  - HTTP↗  POST https://api.stripe.com/v1/payment_intents → HTTP 402
  - CALL   OrdersController#create → RAISE Stripe::CardError
  - HTTP→  POST /orders → HTTP 500

Only in passing:
  + HTTP↗  POST https://api.stripe.com/v1/payment_intents → HTTP 200
  + SQL    UPDATE products
  + SQL    INSERT payments
  + SQL    UPDATE orders
  + HTTP↗  POST https://api.sendgrid.com/v3/mail/send → HTTP 202
  + HTTP→  POST /orders → HTTP 201
```

Root cause immediately visible: Stripe returns 402 (card declined), the controller
raises `Stripe::CardError` unhandled and returns 500. The missing SQL updates confirm
the transaction isn't rolling back properly — the response code should be 422.

**Total: ~808 tokens, 2 of 19 files loaded** (vs 21,400 tokens naive).

### 4.6 The `related` command

Ranks appmaps by weighted similarity to a target file:
- Shared SQL table: +3 per table
- Same HTTP route: +5
- Shared class: +2 per class

This surfaces the best comparison baselines for debugging. In the example above,
`related` ranked the passing order test at score=21 (same route + all classes + all
tables) — exactly the right comparison target.

---

## 5. What Information to Show vs. Hide

### Show by default

- Event ID (enables `show N` drill-down)
- Call hierarchy via indentation (depth)
- `defined_class` + `method_id` with static/instance separator (`.` vs `#`)
- Parameter names + values (truncated to ~40 chars)
- Return value class + value (truncated)
- Elapsed time (ms)
- SQL verb + table name
- HTTP method + URL/path + status code
- Exception class + message (truncated)

### Hide by default (recoverable via `show N`)

| Field | Reason to hide |
|-------|---------------|
| `thread_id` | Constant for single-threaded apps; noise |
| `object_id` | Identity tracking, not behavior understanding |
| `path` + `lineno` | Redundant with classMap; in `show` output |
| `receiver` object | Class already in `defined_class` |
| Full HTTP headers | Mostly noise (User-Agent, encodings, etc.) |
| `size` on params | Rarely useful in navigation context |
| `static` flag | Encoded in `.` vs `#` separator |
| classMap section | Not needed when events are properly attributed |

### Index stores vs. does not store

**In index** (for collection queries without file loading):
- Test name, status, failure message, source location
- HTTP entry (method + path) and response status + elapsed
- All `defined_class` names
- SQL table names and verb types
- Outbound HTTP (method + URL)
- Exception class names

**Not in index** (require loading the file):
- Parameter values and schemas
- Full SQL with bind values
- Full HTTP headers and bodies
- Return values
- Event IDs and depth relationships

---

## 6. Ideas for Further Development

### 6.1 Semantic event grouping
Collapse consecutive related events into logical "operations":
```
[AUTH]    User#42 authenticated via JWT              0.3ms
[READ]    Product#7 fetched, stock=150               2.1ms
[WRITE]   Order#101 created, LineItem#201 created    8.4ms
[EXT]     Stripe charged $59.98 → pi_abc123        312ms
[WRITE]   Payment#301 recorded, Order confirmed      5.2ms
[EXT]     SendGrid email sent → 202                 143ms
```
~6 lines vs 28 tree lines for the same trace.

### 6.2 Diff-based CI regression detection
Compare index from current test run against previous run's index.
Any test where `http_status`, `sql_count`, `exceptions`, or `classes` changed is
flagged as a potential regression — without loading any appmap file.
Useful as a CI step that runs in under a second even for 500-test suites.

### 6.3 Cross-appmap call graph (inverted index on method level)
Extend the per-file index to store method-level calls (not just classes):
`by_method: {"UserRegistrationService#create_user": [file1, file2, ...]}`.
Enables "which tests exercise this specific method?" — the key question for
impact analysis during code review.

### 6.4 Natural language query over the index
The full index for 19 files (~25 KB, ~6,250 tokens) fits in a context window.
An LLM could be given the entire index and asked natural-language questions:
*"Find tests that call Stripe but don't record a payment"* without any CLI syntax.
For larger suites, use semantic search (embeddings on test names + class lists).

### 6.5 MCP server exposure
Expose the index and navigation as Model Context Protocol tools. Any MCP-compatible
client (Claude Desktop, Cursor, Windsurf, VS Code Copilot) would get these
capabilities automatically. See Section 7 for distribution details.

### 6.6 Sequence diagram format as intermediate representation
The `.sequence.json` format defined in this repo (`sequence.json.md`) is already a
compact tree with typed action nodes (Type 4=HTTP, Type 5=external, Type 6=SQL,
Type 3=function). It could serve as an LLM-ready intermediate representation,
eliminating the need for the custom compact format. The `loop` (Type 1) node type
that collapses repeated iterations is especially valuable.

### 6.7 Timeline view for interactive request traces
For web app testing sessions (one appmap per HTTP request, ordered by arrival time),
a timeline showing which endpoints were hit in sequence, with latencies and response
codes, would be more useful than alphabetical listing. Requires the `event.timestamp`
field added in v1.13.0.

---

## 7. Distribution Recommendation

See `DISTRIBUTION.md` for full analysis.

---

## Appendix: Benchmark Data

### Single-file benchmarks

**Sample appmap (30 events, user registration flow):**

| Format | Chars | ~Tokens | % of raw |
|--------|-------|---------|----------|
| Raw JSON | 19,243 | 4,810 | 100% |
| Minified JSON | 12,122 | 3,030 | 63% |
| `summary` | 1,036 | 259 | 5.4% |
| `tree` (full) | 1,502 | 375 | 7.8% |
| `tree` (no-params) | 1,169 | 292 | 6.1% |
| `tree` (depth ≤ 2) | 371 | 92 | 1.9% |
| `http` + `sql` | 868 | 217 | 4.5% |
| `summary` + `tree` | 2,540 | 635 | 13.2% |

**Large appmap (62 events, order processing with payment):**

| Format | Chars | ~Tokens | % of raw |
|--------|-------|---------|----------|
| Raw JSON | 27,384 | 6,846 | 100% |
| `summary` | 1,679 | 419 | 6.1% |
| `tree` (full) | 2,864 | 716 | 10.5% |
| `tree` (depth ≤ 2) | 612 | 153 | 2.2% |
| `summary` + `tree` | 4,545 | 1,136 | 16.6% |

### Collection benchmarks (19-file RSpec suite, 84 KB raw)

| Scenario | ~Tokens | Files loaded | % of naive |
|----------|---------|-------------|------------|
| All 19 raw files | 21,400 | 19 | 100% |
| All 19 summaries | 4,211 | 19 | 19.7% |
| All 19 trees | 1,518 | 19 | 7.1% |
| Collection listing | 447 | 0 | 2.1% |
| Failing tests trees | 238 | 2 | 1.1% |
| Full debug workflow | 808 | 2 | 3.8% |

Token count methodology: `len(text) // 4` (rough GPT/Claude average of ~4 chars/token).
