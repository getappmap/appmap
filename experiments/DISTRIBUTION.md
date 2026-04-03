# Distribution Strategy: AppMap LLM Navigation Tools

## The Goal

The navigation tools (`appmap_tool`, `appmap_collection`) need to be available to:
- LLMs (Claude, Cursor, Windsurf, VS Code Copilot, etc.) as callable tools
- Developers on any OS: Linux, macOS, Windows
- CI environments without Python or Node pre-installed
- Possibly: self-hosted / air-gapped environments

The Python prototype works but is not a distribution strategy. Python may be absent
on Windows, versions conflict, and pip dependencies add friction. We need binaries.

---

## Interface: CLI + Skill vs MCP Server

**For agents with shell access, CLI is the right primary interface.** This covers
Claude Code, Cursor Agent, most agentic pipelines, and any CI environment. A CLI
tool called via bash is strictly simpler than an MCP server: no protocol overhead
(no JSON-RPC handshake, no stdio lifecycle), the output is already LLM-readable
text, and the same commands work identically for humans and agents.

A **skill** (a small prompt or CLAUDE.md section) is the documentation layer that
teaches the agent the navigation workflow:
> "Start with `appmap nav list` to orient, narrow with `find`/`route`, inspect with
> `tree`, drill into specific events with `show N`."

**MCP is the right secondary interface** for GUI LLM clients that don't expose shell
access — Claude Desktop, some IDE integrations. Both can be served by the same
binary: `appmap nav tree file.appmap.json` for CLI, `appmap nav --mcp` for MCP mode.

The implementation is identical; only the I/O transport differs. Build CLI first,
add MCP mode later as a thin adapter.

---

## Index Format: JSON vs SQLite

**JSON is correct for the index.** The arguments for SQLite do not hold at realistic
scale:

| Suite size | JSON index | Parse time |
|------------|------------|------------|
| 100 files  | ~130 KB    | <5ms       |
| 500 files  | ~650 KB    | ~20ms      |
| 2,000 files| ~2.6 MB    | ~80ms      |

Real test suites have 50–500 tests. You'd need >5,000 files before JSON parse time
matters — far beyond any single project's current test suite.

The pre-built inverted indexes (`by_class`, `by_table`, `by_http_entry`) in the JSON
already provide O(1) lookup for all common queries, which is what SQLite indexes
would give you anyway.

More importantly, `better-sqlite3` and `node-sqlite3` are **native Node.js addons**
(compiled `.node` files) that esbuild cannot bundle. This breaks the existing build
pipeline and complicates cross-platform distribution significantly. Bun has built-in
SQLite but that ties the tool to Bun. The distribution cost is real and the
performance benefit is not.

JSON also has genuine interoperability advantages: readable with jq, committable to
git, diffable between CI runs, consumable from any language.

**When to revisit:** If the use case expands to accumulating *historical* runs across
many CI builds for trend analysis. That's a different product (analytics, not
navigation) and would warrant a proper database rather than SQLite anyway.

---

---

## Option A: Add as subcommands to the existing `appmap` CLI

The existing `appmap` TypeScript CLI in `getappmap/appmap-js` already:
- Distributes as prebuilt platform binaries (Linux x64/arm64, macOS x64/arm64, Windows x64)
- Uses esbuild for bundling
- Has `@appland/appmap` for AppMap JSON parsing

**Concrete plan:** Add `appmap nav summary <file>`, `appmap nav tree <file>`,
`appmap nav collection stats <dir>`, etc. as a new command group in `packages/cli`.

**Pros:**
- Zero new distribution infrastructure — existing binary already reaches all users
- Reuses `@appland/appmap` parser (correct, tested, handles edge cases)
- Windows users already have it; air-gapped installs already documented
- Single install for all AppMap tooling

**Cons:**
- The existing CLI is described as "old and quite crufty" — risk of inheriting debt
- Slower iteration: must navigate existing PR/review process for a new domain
- The CLI may have architectural constraints (e.g., command routing, output format)

**Verdict:** The right first step. Navigation commands are purely additive and don't
touch any existing code paths. Even a crufty codebase can cleanly host new subcommands.
The distribution wins far outweigh the code-quality friction.

---

## Option B: New standalone package in the appmap-js monorepo

Create `packages/appmap-nav` (or `packages/navie-index`) as a new package:

```
packages/appmap-nav/
  src/
    index.ts       — Collection indexer
    tree.ts        — Compact tree renderer
    diff.ts        — Appmap diff
    cli.ts         — CLI entry point
    mcp.ts         — MCP server entry point (see Option C)
  package.json
  esbuild.ts       — Bundle to single JS file
  Makefile         — Cross-compile to platform binaries
```

Built with the same esbuild pipeline, released alongside the existing CLI,
optionally imported by `packages/cli` so the `appmap nav` subcommands delegate here.

**Pros:**
- Clean greenfield design, no crufty code inherited
- Can be iterated independently (separate release cadence)
- Can be imported as a library by the existing CLI *and* by IDE extensions
- Can also be compiled to a standalone binary for users who don't want the full CLI

**Cons:**
- Requires setting up release infrastructure (GitHub Actions, binary distribution)
  for the new package — some work but the monorepo already has templates
- Two binaries for users until the existing CLI delegates here

**Verdict:** The best long-term architecture. Start with Option A (subcommands in
existing CLI delegating to a new shared module), extract to Option B when the module
has stabilised. This gives immediate distribution with a clean internal design.

---

## Option C: MCP Server (Model Context Protocol)

Rather than building a CLI that LLMs invoke via shell, expose the navigation as an
[MCP server](https://spec.modelcontextprotocol.io/). An MCP server is a process that
speaks a JSON-RPC protocol over stdio (or HTTP+SSE). Every MCP-compatible LLM client
— Claude Desktop, Cursor, Windsurf, VS Code Copilot, Zed — can call its tools natively.

**This is the highest-leverage distribution target for LLM use cases.**

### What the MCP tools would look like

```typescript
// tools exposed by the MCP server
{
  name: "appmap_collection_index",
  description: "Build or refresh the AppMap index for a directory",
  inputSchema: { type: "object", properties: { dir: { type: "string" } } }
},
{
  name: "appmap_collection_list",
  description: "List all appmaps (1 line each). Call this first to orient.",
  inputSchema: { type: "object", properties: { dir: { type: "string" },
    failed_only: { type: "boolean" }, route: { type: "string" } } }
},
{
  name: "appmap_collection_find",
  description: "Search across all appmaps by pattern (regex, searches class names, SQL tables, HTTP routes, exceptions, test names). Returns matching appmaps without loading files.",
  inputSchema: { type: "object", properties: { dir: { type: "string" },
    pattern: { type: "string" } } }
},
{
  name: "appmap_tree",
  description: "Show the compact call tree for one appmap file. Use after list/find to inspect a specific file.",
  inputSchema: { type: "object", properties: { file: { type: "string" },
    depth: { type: "integer" }, no_params: { type: "boolean" } } }
},
{
  name: "appmap_show_event",
  description: "Get full JSON detail for one or more events by ID. Use after tree to drill into specific events.",
  inputSchema: { type: "object", properties: { file: { type: "string" },
    event_id: { type: "integer" }, end_id: { type: "integer" } } }
},
{
  name: "appmap_diff",
  description: "Compare two appmap files and show what differs in their call trees.",
  inputSchema: { type: "object", properties: {
    file_a: { type: "string" }, file_b: { type: "string" } } }
},
{
  name: "appmap_grep",
  description: "Filter events in one appmap matching a pattern.",
  inputSchema: { type: "object", properties: { file: { type: "string" },
    pattern: { type: "string" } } }
},
{
  name: "appmap_sql",
  description: "Show only SQL queries from one appmap with bind values.",
  inputSchema: { type: "object", properties: { file: { type: "string" } } }
},
{
  name: "appmap_http",
  description: "Show only HTTP events from one appmap.",
  inputSchema: { type: "object", properties: { file: { type: "string" } } }
}
```

### Why MCP is the right long-term target

1. **The LLM calls the tools directly** — no need to teach the LLM to invoke a CLI
   via bash. The tool schema is self-documenting. The LLM knows exactly what
   `appmap_tree(file, depth=2)` returns.

2. **Structured outputs** — MCP tools return typed results. The LLM gets a clean
   data structure, not shell text to parse.

3. **Progressive disclosure is natural** — the LLM naturally chains:
   `list` → `find` → `tree` → `show_event`, loading only what it needs.

4. **Works in every MCP-compatible client** — Claude Desktop, Cursor, Windsurf,
   Zed, VS Code (via extensions), etc. One implementation reaches all.

5. **Same binary, two modes** — the binary can run as a CLI (`appmap nav tree file`)
   *and* as an MCP server (`appmap nav --mcp`). The logic is identical; only the
   I/O differs.

### Distribution of the MCP server

An MCP server is just an executable. Users configure their LLM client to launch it:

```json
// Claude Desktop: ~/.config/claude/claude_desktop_config.json
{
  "mcpServers": {
    "appmap": {
      "command": "/usr/local/bin/appmap",
      "args": ["nav", "--mcp"]
    }
  }
}
```

The binary is the same `appmap` binary already distributed today. No new install.

---

## Option D: Bun single-binary (greenfield)

[Bun](https://bun.sh) compiles TypeScript to a self-contained executable with
`bun build --compile --target=bun-linux-x64 src/cli.ts -o appmap-nav`.

Supported targets: `bun-linux-x64`, `bun-linux-arm64`, `bun-darwin-x64`,
`bun-darwin-arm64`, `bun-windows-x64`. Binary size: ~50–80 MB (Bun runtime + code).

**Pros:**
- Modern, clean, fast startup (~10ms vs ~300ms for Node)
- Full Node.js compatibility — can use any npm package
- Single-file executables with no runtime dependency
- Good cross-compilation story

**Cons:**
- Requires setting up a new release pipeline (GitHub Actions matrix build)
- Separate binary from the existing `appmap` — more for users to install
- No existing install surface: users have to know about a new tool

**Verdict:** Excellent technology choice for a future standalone tool or MCP server,
but the distribution bootstrapping cost makes it secondary to piggybacking on the
existing CLI first.

---

## Option E: Deno

Similar to Bun: `deno compile --allow-read --allow-write --target x86_64-unknown-linux-gnu src/cli.ts`.

Generates self-contained binaries. Deno's permission model (`--allow-read`,
`--allow-write`, `--allow-net`) maps well to an AppMap navigation tool that only
needs filesystem access.

**Pros:**
- Excellent cross-compilation: all platforms in one `deno compile` command
- TypeScript native, no `tsconfig.json` needed
- Smaller binaries than Bun (~50 MB)
- Permission model is a good fit (filesystem-only for nav tools)

**Cons:**
- npm compatibility is good but imperfect; `@appland/appmap` may need verification
- Less mainstream than Node/Bun in the TypeScript ecosystem
- Same bootstrapping cost as Bun

---

## Recommendation

### Immediate (now)

**Port the prototype to TypeScript and add as `appmap nav` subcommands** in
`packages/cli` of the existing `appmap-js` monorepo, plus a companion skill
(prompt template) that teaches agents the navigation workflow.

Implementation sketch:
- `packages/cli/src/cmds/nav/` — new command directory
  - `tree.ts` — compact tree renderer (uses `@appland/appmap` AppMap loader)
  - `index.ts` — collection indexer (pure JSON, no extra dependencies)
  - `collection.ts` — collection commands (list, stats, find, diff, related)
  - `mcp.ts` — MCP server mode (`appmap nav --mcp`)
- `packages/cli/src/cmds/nav.ts` — command router
- ~600–800 lines of TypeScript, no new dependencies beyond `@appland/appmap`

The Python prototype is a working spec — port it directly. The logic is
straightforward and the AppMap parsing is simpler in TypeScript because
`@appland/appmap` already handles it.

### Short-term (1–2 months)

**Expose as MCP server** (`appmap nav --mcp`) as a secondary interface for GUI LLM
clients (Claude Desktop, Cursor) that don't expose shell access. The implementation
is the same CLI logic wrapped in a stdio JSON-RPC adapter. For agents with shell
access, the CLI + skill is already sufficient and simpler.

### Medium-term

**Extract to `packages/appmap-nav`** as a standalone library package that:
- Is imported by `packages/cli` for the `appmap nav` subcommands
- Can be built as a standalone binary (using Bun or Node SEA) for users who want
  a lighter install
- Can be published to npm separately for IDE extension authors

---

## Implementation Notes for TypeScript Port

The `@appland/appmap` package already provides AppMap loading. The key things
to implement from scratch:

```typescript
import AppMap from '@appland/appmap';

// Load an appmap (handles eventUpdates, etc.)
const appmap = await AppMap.load(filePath);

// Build call tree: pairs call+return events, tracks depth
function buildCallTree(events: AppMap.Event[]): [AppMap.Event, number][] { ... }

// Compact one-liner per call event
function formatTreeLine(callEvent: AppMap.Event, depth: number,
                        returnEvent?: AppMap.Event): string { ... }

// Extract lightweight index entry from one appmap
function extractIndexEntry(filePath: string, appmap: AppMap): IndexEntry { ... }

// Collection-level queries use only the index (no AppMap loading)
function searchIndex(index: CollectionIndex, pattern: RegExp): IndexEntry[] { ... }
```

The index file format (`.appmap-index.json`) can be identical to the Python
prototype's format — keeping it JSON-serialisable makes it easy to cache, diff,
and consume from any language or tool.

### MCP server skeleton

```typescript
import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';

const server = new Server({ name: 'appmap-nav', version: '1.0.0' }, {
  capabilities: { tools: {} }
});

server.setRequestHandler(ListToolsRequestSchema, async () => ({
  tools: [
    { name: 'appmap_collection_list', description: '...', inputSchema: { ... } },
    { name: 'appmap_tree', description: '...', inputSchema: { ... } },
    // ... etc
  ]
}));

server.setRequestHandler(CallToolRequestSchema, async (request) => {
  switch (request.params.name) {
    case 'appmap_collection_list': return handleList(request.params.arguments);
    case 'appmap_tree': return handleTree(request.params.arguments);
    // ...
  }
});

const transport = new StdioServerTransport();
await server.connect(transport);
```

The `@modelcontextprotocol/sdk` npm package is ~15 KB and has no heavy dependencies.
It can be bundled with esbuild just like the rest of the CLI.
