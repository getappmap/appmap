# Distribution Strategy: AppMap LLM Navigation Tools

## The Goal

The navigation tools (`appmap_tool`, `appmap_collection`) need to be available to:
- LLMs (Claude Code, Cursor Agent, agentic pipelines, CI) as callable shell commands
- Developers on any OS: Linux, macOS, Windows
- CI environments without Python or Node pre-installed
- Possibly: self-hosted / air-gapped environments

The Python prototype works but is not a distribution strategy. Python may be absent
on Windows, versions conflict, and pip dependencies add friction. We need binaries.

---

## Primary Interface: CLI + Skill

**For agents that can use the command line — which is the common case — a CLI tool
is the right interface.** This covers Claude Code, Cursor Agent, most agentic
pipelines, and any CI environment.

Compared to an MCP server, a CLI tool is:
- **Simpler**: no JSON-RPC handshake, no stdio lifecycle, no connection management
- **Transparent**: a human can run the exact same commands the agent runs, in the
  same terminal, and see the same output — invaluable for debugging
- **Universal**: works in any bash-capable environment with no client-side setup
- **Already readable**: the output format is designed for LLM consumption as plain text

A **skill** (a small prompt or `CLAUDE.md` section) is the documentation layer that
teaches the agent the navigation workflow:
> "Start with `appmap nav list` to orient. Narrow with `find` or `route`. Inspect a
> file with `tree`. Drill into specific events with `show N`."

This is the primary delivery target: **a CLI binary + a companion skill**.

### Note on MCP

MCP (Model Context Protocol) is worth adding later as a secondary interface for GUI
LLM clients that don't expose shell access (Claude Desktop, some IDE integrations).
It's a thin adapter over the same logic — the same binary, a `--mcp` flag, a
different I/O transport. But it provides no benefit over CLI for agents with shell
access, so it is not a priority.

---

## Index Format: JSON vs SQLite

**JSON is the right format for the index.** The arguments for SQLite don't hold at
realistic scale:

| Suite size  | JSON index | Parse time |
|-------------|------------|------------|
| 100 files   | ~130 KB    | <5ms       |
| 500 files   | ~650 KB    | ~20ms      |
| 2,000 files | ~2.6 MB    | ~80ms      |

Real test suites have 50–500 tests. You'd need >5,000 files before JSON parse time
matters — far beyond any single project's test suite.

The pre-built inverted indexes (`by_class`, `by_table`, `by_http_entry`) in the JSON
already give O(1) lookup for all common queries — the same benefit SQLite indexes
would provide, with no extra dependency.

`better-sqlite3` and `node-sqlite3` are native Node.js addons (compiled `.node`
files) that esbuild cannot bundle. This breaks the existing build pipeline and
complicates cross-platform distribution. The distribution cost is real; the
performance benefit at this scale is not.

JSON has genuine interoperability advantages: readable with `jq`, committable to git,
diffable between CI runs, consumable from any language or tool.

**When to revisit:** Only if the use case expands to accumulating historical runs
across many CI builds for trend analysis. That's a different product (analytics, not
navigation), and at that point a proper database — not SQLite — would be warranted.

---

## Distribution Options

### Option A: Add as subcommands to the existing `appmap` CLI ✓ Recommended

The existing `appmap` TypeScript CLI in `getappmap/appmap-js` already:
- Distributes as prebuilt platform binaries (Linux x64/arm64, macOS x64/arm64, Windows x64)
- Uses esbuild for bundling
- Has `@appland/appmap` for AppMap JSON parsing

**Concrete plan:** Add `appmap nav tree <file>`, `appmap nav list <dir>`,
`appmap nav stats <dir>`, etc. as a new command group in `packages/cli`.

**Pros:**
- Zero new distribution infrastructure — existing binary already reaches all users,
  including Windows without Python/Node, and air-gapped installs
- Reuses `@appland/appmap` parser (correct, tested, handles edge cases)
- Single install for all AppMap tooling

**Cons:**
- The existing CLI is "old and quite crufty" — but navigation commands are purely
  additive. New subcommands in a new directory don't touch existing code paths.

**Verdict:** The right first step. The distribution wins far outweigh the code-quality
friction of the existing codebase.

---

### Option B: New standalone package in the appmap-js monorepo

Create `packages/appmap-nav` as a clean new package within the existing monorepo:

```
packages/appmap-nav/
  src/
    tree.ts        — Compact tree renderer
    index.ts       — Collection indexer
    collection.ts  — Collection commands
    cli.ts         — CLI entry point
  package.json
  esbuild.ts       — Bundle config
```

Built with the same esbuild pipeline. The existing CLI's `appmap nav` subcommands
delegate to this package, which can also be published to npm or built as a standalone
binary independently.

**Pros:**
- Clean greenfield design, no crufty code inherited
- Independent release cadence
- Importable as a library by IDE extensions or other consumers

**Cons:**
- Requires setting up release infrastructure for a new package (some work, but the
  monorepo has templates)

**Verdict:** The right long-term architecture. Start with Option A (subcommands
delegating to a new internal module), extract to Option B once the module has
stabilised.

---

### Option C: Bun or Deno single-binary (greenfield)

Both [Bun](https://bun.sh) (`bun build --compile`) and Deno (`deno compile`) produce
self-contained cross-platform executables without a runtime dependency.

**Pros:** Clean slate, modern tooling, fast startup, true single-file binaries.

**Cons:** Requires building release infrastructure from scratch (GitHub Actions matrix,
binary hosting, install instructions). Only worthwhile if the existing distribution
channel genuinely can't be used — which it can.

**Verdict:** Good technology, wrong starting point. Revisit if the tool ever needs to
be distributed completely independently of the AppMap ecosystem.

---

## Recommendation

**Immediate:** Port the Python prototype to TypeScript, add as `appmap nav`
subcommands in `packages/cli`. Write a companion skill (prompt template) documenting
the navigation workflow for agents.

Implementation sketch (~600–800 lines of TypeScript, no new dependencies beyond
`@appland/appmap`):

```
packages/cli/src/cmds/nav/
  tree.ts        — Compact tree renderer
  collection.ts  — Index builder + collection commands
  diff.ts        — Appmap diff
nav.ts           — Command router (appmap nav <subcommand>)
```

**Medium-term:** Extract to `packages/appmap-nav` as the logic stabilises.

**Later, if needed:** Add `--mcp` flag as a thin adapter for GUI LLM clients without
shell access. This is a few dozen lines wrapping the existing CLI handlers.

---

## Implementation Notes for TypeScript Port

`@appland/appmap` already handles AppMap JSON loading including `eventUpdates`.
The key new logic to implement:

```typescript
import AppMap from '@appland/appmap';

// Build call tree: pairs call+return events, tracks depth
function buildCallTree(events: Event[]): Array<[Event, number]> { ... }

// Compact one-liner per call event
function formatTreeLine(call: Event, depth: number, ret?: Event): string { ... }

// Extract lightweight index entry — no appmap loading for collection queries
function extractIndexEntry(filePath: string): IndexEntry { ... }

// Collection-level queries use only the index
function searchIndex(index: CollectionIndex, pattern: RegExp): IndexEntry[] { ... }
```

The `.appmap-index.json` format can match the Python prototype's format exactly —
JSON-serialisable, human-readable, consumable from any language.
