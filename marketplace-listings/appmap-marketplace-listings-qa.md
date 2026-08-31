# AppMap marketplace listings — QA'd copy for PR (JetBrains + VS Code)

**For:** Rafal / next coding agent. **Prepared:** 31 August 2026 (original copy) · **QA pass:** 31 August 2026, verified against the shipped code by Claude (session for Elizabeth Lawler).
**Purpose:** hand this page to a coding agent and let it open two pull requests. Every file path, every replacement, and every image is specified below. The three questions that were marked in red are now **answered**, with evidence, in section 1. All copy blocks in this file **already carry the QA corrections**; every change from the original draft is listed in section 1c so nothing is silent.

**Do not open PRs from this QA session.** This file is the handoff; the next agent opens the PRs.

---

## 0. Instruction to the coding agent

Two repositories are affected. Make one pull request per repository. Do not modify any file not listed. Do not reword the supplied copy. All former «guillemet» placeholders are resolved in this version.

| PR | Repository | Files changed |
|---|---|---|
| 1 | getappmap/appmap-intellij-plugin | description.md (full replace), assets/appmap-mcp-flow.png (new), assets/appmap-mcp-flow.svg (new, source only) |
| 2 | getappmap/vscode-appland | README.md (full replace), package.json (two fields), images/appmap-mcp-flow.png (new), images/appmap-mcp-flow.svg (new, source only) |

Publishing note for the human reviewer, not the agent: neither listing is editable on the marketplace website. JetBrains renders description.md into the plugin description at build time (build.gradle.kts, line 341 — **verified**). VS Code packages README.md into the .vsix. Both changes reach users only when a build is published. Do not attach either PR to a release with a committed date.

---

## 1. The three facts — ANSWERED (31 August 2026)

### Fact 1 — Where does the MCP server ship from? ✅ ANSWERED

**The MCP server ships inside the AppMap CLI** (the `appmap` binary, built from `packages/cli` in [getappmap/appmap-js](https://github.com/getappmap/appmap-js)). It is started with `appmap query mcp` and speaks newline-delimited JSON-RPC 2.0 over stdio. Implementation: `packages/cli/src/cmds/query/queries/mcp.ts` (dispatch) and `packages/cli/src/cmds/query/verbs/mcp.ts` (stdio loop). Public reference doc source: `docs/reference/appmap-mcp.md` in the same repo.

The wording of the copy is accurate — and it can honestly be stronger than the draft feared. **Both plugins download and auto-update this CLI as part of normal operation:**

- VS Code: `src/assets/assetService.ts` installs the binary to `~/.appmap/bin/appmap` (`AppMapCliDownloader`).
- JetBrains: `plugin-core/src/main/java/appland/cli/AppLandDownloadService.java` + `DownloadToolsStartupActivity.java` (auto-update controlled by the `appMap.autoUpdateTools` org setting).

Both plugins also run `appmap index --watch`, which maintains the `query.db` the MCP server reads — so a plugin user's index is already built and fresh. Installing the plugin therefore *does* put the MCP server binary on the machine and keeps its data current; the only manual step is pointing the agent at it. The listing does not overclaim.

**MCP_SETUP_URL** = `https://appmap.io/docs/reference/appmap-mcp.html`
(Sourced from `appmap-js/docs/reference/appmap-mcp.md`; "AppMap MCP Server" is listed in the appmap.io reference menu. Caveat: appmap.io is egress-blocked from this QA sandbox, so I verified the page via the docs source and the site's search index, not by loading it. Have a human click it once before merge.)

**MCP_INSTALL_STEP** (one line, used in step 4 of both Get-started sections):

> In Claude Code, run `claude mcp add appmap -- appmap query mcp`; for any other agent, add `"appmap": { "command": "appmap", "args": ["query", "mcp"] }` to its MCP servers configuration.

Note for support/docs: `appmap` must be on the PATH the agent sees; the plugin-managed binary lives at `~/.appmap/bin/appmap`, so an absolute path there always works.

### Fact 2 — Does the plugin still ship Navie? ✅ YES — restore the Navie block

Navie still ships in **both** plugins and is actively maintained as of the latest commits (August 2026):

- VS Code 0.142.2 registers `appmap.explain`, `appmap.navie.history`, `appmap.navie.quickReview` and the full Navie webview stack (`src/webviews/chatSearchWebview.ts`, `src/services/navieConfigurationService.ts`, …).
- JetBrains registers `appmap.openNavie`, the Navie tool window, editor, and OpenAI-key action in `plugin-core/src/main/resources/META-INF/appmap-core.xml`.
- Neither changelog contains a deprecation, sunset, or retirement note.

**Consequence, per the original document's own section 6 instruction:** the four-line Navie block is pasted back into both listings (done in the copy below), and the transition sentence reads "you can also use the chat in your coding agent" instead of "the chat has moved to your coding agent." Two other lines in the original draft asserted the move and are also corrected below: the JetBrains release note and the VS Code commit message.

The Navie `@` commands named in the block (`@explain`, `@diagram`, `@search`, `@plan`, `@generate`, `@test`, `@help`, `@review`) all still exist in the updated docs — but the link `appmap.io/docs/navie` is stale on the new docs site; the block now links to `https://appmap.io/docs/using-navie-ai/navie-commands.html`.

The new VS Code `package.json` description (Change 1 in section 3b) no longer mentions chat. Navie still shipping means nothing *forces* that change — it is now purely a positioning decision. It is left as drafted; flag to marketing that it is a choice, not a factual necessity.

### Fact 3 — Do the four MCP tool names match the shipped server? ✅ Names yes, count no

All four names — `get_call_tree`, `find_calls`, `find_queries`, `find_requests` — match the shipped server **exactly, verbatim**. But the original sentence "exposes four tools" was wrong: the server exposes **13 tools**:

`list_endpoints`, `function_hotspots`, `sql_hotspots`, `list_labels`, `find_recordings`, `find_requests`, `find_queries`, `find_calls`, `find_logs`, `find_exceptions`, `get_call_tree`, `find_related`, `compare_branches`

…plus two MCP resources (`appmap://endpoints`, `appmap://recording/{ref}/logs`). Source: `packages/cli/src/cmds/query/queries/mcp.ts` and `docs/reference/appmap-mcp.md` in appmap-js.

The copy below now reads "exposes 13 read-only query tools to an agent, including …", and the diagram's bottom bar reads "MCP tools available to the agent include get_call_tree, find_calls, find_queries, find_requests (13 tools in total)". Both the SVG source and the PNG export carry the corrected line.

### 1b. Directives from Elizabeth added during this QA pass (31 Aug)

1. **Link to the new/updated appmap.io docs site from both listings.** Done — every docs link below was checked against the updated docs tree (`appmap-js/docs/`): the MCP reference page, `get-started-with-appmap/making-appmap-data.html`, and `appmap-docs.html` are all on the new site. Two stale links from the draft were replaced (see 1c).
2. **Enterprise/organization configuration is not publicly documented — do not link the GitHub admin docs.** Both enterprise sections now end with: *"For enterprise configuration, contact your AppMap administrator or refer to your internal documentation site (for example, Confluence)."*

### 1c. Full changelog of QA corrections applied to the draft copy

1. **Tool count** — "exposes four tools" → "exposes 13 read-only query tools … including" in both listings, the JetBrains release note, and the diagram (copy + SVG + PNG).
2. **Navie restored** — section 6 block inserted into both listings after the MCP section; transition sentence switched to the "you can also use" variant; JetBrains release note line "Chat has moved to your coding agent" → "You can also chat in your coding agent"; VS Code commit message line "Replaces the Navie chat-mode documentation with a transition note" → "Notes that Navie chat is also available through your coding agent".
3. **Navie docs link** — `appmap.io/docs/navie` → `https://appmap.io/docs/using-navie-ai/navie-commands.html` (old path is not on the updated docs site).
4. **Recording links (JetBrains listing)** — `appmap.io/docs/recording-methods.html#recording-test-cases` and `…#remote-recording` do not exist on the updated docs site → replaced with `https://appmap.io/docs/get-started-with-appmap/making-appmap-data.html#with-test-case-recording` and `…#with-remote-application-recording`.
5. **JetBrains IDE requirement** — "2023.1 and newer" is stale: `gradle.properties` pins `sinceBuild=251.0`, i.e. **2025.1**. Corrected.
6. **Hero image must be PNG, not SVG** — the VS Code Marketplace strips SVG images from READMEs unless they come from a trusted-badge allowlist (enforced in vsce, `src/package.ts`, `TrustedSVGSources`); a raw.githubusercontent SVG would be rejected or dropped. Both listings now reference `appmap-mcp-flow.png` (2×, 1840×680, supplied). The SVG is committed alongside as the editable source but is not referenced by either listing. (JetBrains does not document the same restriction, but PNG is used there too for safety and consistency.)
7. **Enterprise config reference** — GitHub links to `ORGANIZATION_CONFIGURATION.md` / `doc/organization-config.md` removed per Elizabeth's directive; replaced with the contact-your-administrator sentence. (For the record, both files exist and the Splunk mandatory-telemetry claim in the JetBrains copy is accurate per `ORGANIZATION_CONFIGURATION.md` — the claim stays.)
8. **Placeholders resolved** — «MCP_SETUP_URL» and «MCP_INSTALL_STEP» filled in everywhere (values in Fact 1).
9. **VS Code keywords caution (no copy change)** — the existing `keywords` array already has 40 entries; VS Code's manifest guidance suggests a 30-keyword cap, though the current vsce passes all keywords through as marketplace tags (verified in vsce source — no hard limit, extension already publishes with 40). Adding the six new entries works mechanically; consider pruning the list toward 30 with the new terms retained.
10. **Verified as accurate, unchanged** — VS Code version 0.142.2 ✓; `build.gradle.kts:341` renders description.md ✓; `develop` branch exists in the IntelliJ repo and is the existing link convention in its description.md ✓; Splunk-mandatory-telemetry claim ✓; shields.io badges are on the trusted-badge allowlist ✓; "works with any MCP-capable coding agent" ✓ (stdio JSON-RPC, client-agnostic).

---

## 2. PR 1 — JetBrains

**Repository:** getappmap/appmap-intellij-plugin. **Branch:** `listing/runtime-evidence-mcp`. **Action:** replace the entire contents of `/description.md` with the text below. Add the PNG from section 5 at `/assets/appmap-mcp-flow.png` and the SVG source at `/assets/appmap-mcp-flow.svg`.

**Commit message:** `docs: rewrite marketplace description around runtime evidence and MCP`

### Final contents of description.md

```markdown
# Runtime evidence for AI-assisted development

### See what your code actually did, in your JetBrains IDE

AppMap records what your application does when it runs. It captures the calls it made, the SQL it ran, the HTTP requests it handled, and the exceptions it raised. That recording is runtime evidence. Your coding agent reads it instead of inferring the execution path from source.

![How AppMap reaches your coding agent](https://raw.githubusercontent.com/getappmap/appmap-intellij-plugin/develop/assets/appmap-mcp-flow.png)

## What AppMap does

-   Records code execution, data flow, and behavior while your tests or your application run. No code changes.
-   Serves that recording to coding agents over MCP.
-   Renders the same recording as diagrams you can read yourself: sequence diagram, dependency map, flame graph, and trace view.

Recording and the MCP server both run in your development environment. Traces are files in your project.

## Works with your coding agent over MCP

The AppMap MCP server exposes 13 read-only query tools to an agent, including `get_call_tree`, `find_calls`, `find_queries`, and `find_requests`. An agent uses them to answer questions it cannot answer from source alone. Which functions ran. Which queries a request issued. Where an exception came from.

It works with Claude Code, Cursor, GitHub Copilot, Windsurf, and any MCP-capable coding agent.

For setup, see the [AppMap MCP server reference](https://appmap.io/docs/reference/appmap-mcp.html).

If you have used Navie, you can also use the chat in your coding agent. AppMap supplies the runtime context through MCP.

## Navie chat

Navie is still available in the IDE. It answers questions using the same runtime evidence, without leaving your editor. The `@explain`, `@plan`, `@generate`, `@test`, `@diagram`, `@search`, `@review`, and `@help` commands work as before, and are documented in the [Navie command reference](https://appmap.io/docs/using-navie-ai/navie-commands.html).

## Recording AppMap data

You record AppMap data by running your app, either by [running test cases](https://appmap.io/docs/get-started-with-appmap/making-appmap-data.html#with-test-case-recording) or by [recording a short interaction with your app](https://appmap.io/docs/get-started-with-appmap/making-appmap-data.html#with-remote-application-recording).

In IntelliJ, use the "Start with AppMap" menu item. [Visit the documentation](https://appmap.io/docs/get-started-with-appmap/making-appmap-data.html) for other languages or more detail.

![Start with AppMap](https://appmap.io/assets/img/product/start-with-appmap.png)

## Reading the data yourself

The same recording powers four diagrams:

-   **Sequence diagram** to follow the runtime flow of calls made by your application.
-   **Dependency map** to see which libraries and frameworks were used at runtime.
-   **Flame graph** to spot performance bottlenecks.
-   **Trace view** to follow function calls and data flow in detail.

## Requirements and use

**2025.1** and newer JetBrains IDEs are required to use this plugin.

AppMap works best* with the following:

-   **Languages:** Java, Kotlin, Python, Ruby, and Node.js (TypeScript and JavaScript).
-   **Frameworks:** Spring, Django, Flask, Ruby on Rails, Nest.js, Next.js, and Express.

Refer to [AppMap documentation](https://appmap.io/docs/appmap-docs.html) for the latest information on supported languages, frameworks, and versions.

[*] AppMap trace recording requires a language-specific library.

## If your company runs AppMap centrally

AppMap can be configured at the organization level, and several settings you see locally may already be set for you. An administrator can route telemetry to an internal observability stack, point binary downloads at an internal mirror, control CLI auto-update, and distribute this plugin internally. Deployment can be local, self-hosted, or airgapped.

One case is worth knowing about before you go looking for a setting. When an organization configures a Splunk telemetry backend, telemetry becomes mandatory and the local "disable telemetry" setting is ignored.

If this describes your company, read your internal developer documentation before you change AppMap settings on your own machine, and ask your platform or developer tools team who owns the configuration. For enterprise configuration, contact your AppMap administrator or refer to your internal documentation site (for example, Confluence).

## Get started

1. **Install [the AppMap Plugin](https://plugins.jetbrains.com/plugin/16701-appmap)** from within the code editor or from the marketplace.
2. **Sign in** using an email address to obtain a license key and activate AppMap. Use your work email, so that your license can be associated with your organization subscription.
3. **Record your app** by running your tests or by recording an interaction.
4. **Point your coding agent at the AppMap MCP server.** In Claude Code, run `claude mcp add appmap -- appmap query mcp`; for any other agent, add `"appmap": { "command": "appmap", "args": ["query", "mcp"] }` to its MCP servers configuration. See the [setup reference](https://appmap.io/docs/reference/appmap-mcp.html).

## Licensing and security

[Open source MIT license](https://github.com/getappmap/appmap-intellij-plugin/blob/develop/LICENSE) | [Terms and conditions](https://appmap.io/community/terms-and-conditions.html)

To learn more about the security of AppMap and the handling of your data, see the AppMap [security disclosure](https://appmap.io/security).

There is [no fee](https://appmap.io/pricing) for personal use. Pricing for premium features and integrations is listed on [AppMap's pricing page](https://appmap.io/pricing).
```

### Release note for the JetBrains plugin update

```
AppMap now serves runtime evidence to coding agents over MCP. Any MCP-capable agent, including Claude Code, Cursor, GitHub Copilot, and Windsurf, can query recorded calls, SQL queries, and HTTP requests through 13 MCP tools, including get_call_tree, find_calls, find_queries, and find_requests. Recording and the MCP server run in your development environment.

You can also chat in your coding agent. AppMap provides the runtime context. Navie remains available in the IDE.

If your company runs AppMap centrally, model access, telemetry routing, and plugin distribution can be configured for you. Check your internal developer documentation before changing local settings.
```

---

## 3. PR 2 — VS Code

**Repository:** getappmap/vscode-appland (currently 0.142.2 — verified). **Branch:** `listing/runtime-evidence-mcp`. **Action:** replace the entire contents of `/README.md` with the text below, apply the two package.json changes in section 3b, and add the PNG from section 5 at `/images/appmap-mcp-flow.png` plus the SVG source at `/images/appmap-mcp-flow.svg`.

**Commit message.** This repository runs semantic-release, so CHANGELOG.md is generated from the commit message and must not be hand edited. Use exactly:

```
feat: serve runtime evidence to coding agents over MCP

Rewrites the marketplace listing around runtime evidence and MCP.
Notes that Navie chat is also available through your coding agent.
Adds mcp, model context protocol, claude code, cursor, windsurf and
runtime evidence to marketplace keywords.
```

### 3a. Final contents of README.md

```markdown
[![GitHub Stars](https://img.shields.io/github/stars/getappmap/vscode-appland?style=social)](https://github.com/getappmap/vscode-appland)
[![Slack](https://img.shields.io/badge/Slack-Join%20the%20community-green)](https://appmap.io/slack)

# AppMap for Visual Studio Code

### Runtime evidence for AI-assisted development

#### **See what your code actually did, in Visual Studio Code**

AppMap records what your application does when it runs. It captures the calls it made, the SQL it ran, the HTTP requests it handled, and the exceptions it raised. That recording is runtime evidence. Your coding agent reads it instead of inferring the execution path from source.

![How AppMap reaches your coding agent](https://github.com/getappmap/vscode-appland/blob/master/images/appmap-mcp-flow.png?raw=true)

## What AppMap does

- Records code execution, data flow, and behavior while your tests or your application run. No code changes.
- Serves that recording to coding agents over MCP.
- Renders the same recording as diagrams you can read yourself: sequence diagram, dependency map, flame graph, and trace view.

Recording and the MCP server both run in your development environment. Traces are files in your project.

## Works with your coding agent over MCP

The AppMap MCP server exposes 13 read-only query tools to an agent, including `get_call_tree`, `find_calls`, `find_queries`, and `find_requests`. An agent uses them to answer questions it cannot answer from source alone. Which functions ran. Which queries a request issued. Where an exception came from.

It works with Claude Code, Cursor, GitHub Copilot, Windsurf, and any MCP-capable coding agent.

For setup, see the [AppMap MCP server reference](https://appmap.io/docs/reference/appmap-mcp.html).

If you have used Navie, you can also use the chat and the `@` commands in your coding agent. AppMap supplies the runtime context through MCP.

## Navie chat

Navie is still available in the IDE. It answers questions using the same runtime evidence, without leaving your editor. The `@explain`, `@plan`, `@generate`, `@test`, `@diagram`, `@search`, `@review`, and `@help` commands work as before, and are documented in the [Navie command reference](https://appmap.io/docs/using-navie-ai/navie-commands.html).

## Get started

1. **Install [the AppMap extension](https://marketplace.visualstudio.com/items?itemName=appland.appmap)** from within the code editor or from the marketplace.
2. **Sign in with an email address, or with GitHub or GitLab.**
3. **Record your app** by [making AppMap data for your project](https://appmap.io/docs/get-started-with-appmap/making-appmap-data.html), either by running your test cases or by recording a short interaction with your app.
4. **Point your coding agent at the AppMap MCP server.** In Claude Code, run `claude mcp add appmap -- appmap query mcp`; for any other agent, add `"appmap": { "command": "appmap", "args": ["query", "mcp"] }` to its MCP servers configuration. See the [setup reference](https://appmap.io/docs/reference/appmap-mcp.html).

## Reading the data yourself

The same recording powers four diagrams:

- **Sequence diagram** to follow the runtime flow of calls made by your application.
- **Dependency map** to see which libraries and frameworks were used at runtime.
- **Flame graph** to spot performance bottlenecks.
- **Trace view** to follow function calls and data flow in detail.

## Requirements

AppMap records Node.js, Java and Kotlin, Ruby, and Python. It works particularly well with web application frameworks such as Nest.js, Next.js, Spring, Ruby on Rails, Django, and Flask.

Refer to the [documentation](https://appmap.io/docs/appmap-docs.html) for the latest information on supported languages, frameworks, and versions.

## If your company runs AppMap centrally

AppMap can be configured at the organization level, and several settings you see locally may already be set for you. An administrator can push settings from a configuration URL on startup, route telemetry to an internal observability stack, point binary downloads at an internal mirror, and distribute this extension internally. Deployment can be local, self-hosted, or airgapped.

If this describes your company, read your internal developer documentation before you change AppMap settings on your own machine, and ask your platform or developer tools team who owns the configuration. For enterprise configuration, contact your AppMap administrator or refer to your internal documentation site (for example, Confluence).

## Licensing and security

[Open source MIT license](https://github.com/getappmap/vscode-appland/blob/master/LICENSE) | [Terms and conditions](https://appmap.io/community/terms-and-conditions.html)

To learn more about the security of AppMap and the handling of your data, see the AppMap [security disclosure](https://appmap.io/security).

There is [no fee](https://appmap.io/pricing) for personal use. Pricing for premium features and integrations is listed on [AppMap's pricing page](https://appmap.io/pricing).
```

### 3b. package.json — two changes

These drive marketplace search and the one-line summary under the extension name. Today the summary still describes Navie, and a developer searching the marketplace for "mcp" does not find AppMap.

**Change 1. Replace the value of `description`.**

```
Old: "AI-driven chat with a deep understanding of your code. Build effective solutions using an intuitive chat interface and powerful code visualizations."
New: "Runtime evidence for AI-assisted development. Record what your code does when it runs, and let your coding agent query it over MCP."
```

*QA note: Navie still ships (Fact 2), so dropping "chat" from the summary is a positioning choice, not a factual necessity. Left as drafted; marketing may soften it.*

**Change 2. Add six entries to the existing `keywords` array.** Keep every keyword already there. Add, in this order, after the existing entries:

```
"mcp", "model context protocol", "claude code", "cursor", "windsurf", "runtime evidence"
```

*QA note: the array already holds 40 keywords and VS Code's manifest guidance suggests 30; current vsce imposes no hard limit (verified in vsce source; the extension already publishes with 40), so this works — but consider pruning toward 30 with the new terms retained.*

---

## 4. Images

One new diagram is supplied and ready to commit, as a **PNG (referenced by the listings)** plus its **SVG source (committed, not referenced)**. Six existing images are removed from the listings because they show Navie chat surfaces the new copy no longer sells (the Navie section that remains is text-only). Two are kept.

**Why PNG:** the VS Code Marketplace rejects SVG images in extension READMEs unless they come from a trusted badge allowlist (enforced by vsce; shields.io badges are allowed, raw.githubusercontent SVGs are not). The PNG is a 2× export (1840×680) of the SVG. If the diagram ever changes, edit the SVG and re-export.

| Image | Where it is used now | Action | Why |
|---|---|---|---|
| appmap-mcp-flow.png (new, from section 5) | Top of both listings | **Add** | The listing's one explanatory picture. Not a screenshot, so it cannot go stale with the UI, and it carries the point the old images cannot: recording happens locally and the agent reads it over MCP. |
| appmap-mcp-flow.svg (new, source) | Not referenced | **Add** | Editable source for the PNG. |
| appmap.io/assets/img/product/start-with-appmap.png | JetBrains, recording section | **Keep** | Recording is unchanged. The image is still accurate. |
| images/logo.png, images/logo.svg, icons | Extension icon and chrome | **Keep** | Untouched by this change. |
| images/command-palette-menu.jpg | VS Code, "Chat Modes" | **Remove from README** | Shows the Navie @ command palette. Leave the file in the repository. Deleting it breaks nothing and costs nothing to keep. |
| images/pinned-context.jpg | VS Code, "Pinned Context" | **Remove from README** | Navie chat surface. Same treatment as above. |
| The implement-redis animation (GitHub user-content URL, hotlinked) | VS Code, under "Key Benefits" | **Remove from README** | Shows a Navie chat session generating code. It is also hotlinked from a GitHub attachment URL rather than the repository, which is fragile. |
| tools-appmap-vscode.png, new-navie-chat.png, add-context-from-file.png, pin-from-response.png, add-context-in-context-window.png | JetBrains, Navie activation and pinning sections | **Remove from description** | All five show how to open and feed a Navie chat. Hosted on appmap.io, so nothing is deleted from the repository. |

### Two screenshots worth capturing next, not blocking

Neither can be produced without a running IDE, so both are specified rather than supplied.

- **appmap-agent-answer.png** — a coding agent answering a question using an AppMap MCP tool call. The frame must show the question, the tool call naming get_call_tree, and the answer. Capture at 2x on a light background, crop to the panel, and target roughly 1600 px wide. Use a public sample application, never customer code. Alt text: "A coding agent answering a question by calling the AppMap MCP server."
- **appmap-sequence-diagram.png** — a sequence diagram of one real request, showing an HTTP entry point and at least one SQL query. Same capture settings. This one carries the "you can read it too" half of the listing. Alt text: "A sequence diagram of one recorded HTTP request, including its SQL queries."

Both should be committed into the repository and referenced by relative path, not hotlinked to appmap.io, so the listing does not depend on the website's asset paths staying stable.

---

## 5. The diagram, ready to commit

Files supplied alongside this document (in `marketplace-listings/` on this branch):

- `appmap-mcp-flow.svg` — corrected source (tool line now reads "…include get_call_tree, find_calls, find_queries, find_requests (13 tools in total)"). Plain SVG, 920×340, explicit white background, `role="img"` + `aria-label` on the root, system sans fallback stack, no embedded fonts.
- `appmap-mcp-flow.png` — 2× export, 1840×680, the file both listings reference.
- `appmap-mcp-flow-original.svg` — the uncorrected version exactly as supplied in the source document, kept for provenance only. Do not commit to the plugin repos.

Commit destinations: `assets/appmap-mcp-flow.png` + `.svg` in the JetBrains repository; `images/appmap-mcp-flow.png` + `.svg` in the VS Code repository.

---

## 6. If Navie still ships — RESOLVED: it does

Fact 2 came back "Navie still ships and is supported," so the Navie block is already inserted into both copy blocks above (directly after "Works with your coding agent over MCP") and the transition sentence already uses the "you can also use the chat in your coding agent" variant. Nothing further to do; this section is kept only so the section numbering of the original document survives.

---

## 7. Copy rules applied

- Plain English, short sentences, no semicolons, no em dashes. Matches the house rules used for the blog and the website. (QA additions follow the same rules inside the copy blocks; QA annotations outside the copy blocks are exempt.)
- Navie is named in one section and a transition sentence, and never sold. A developer who searched for Navie lands on the Navie section instead of filing a support ticket.
- "Gold Traces" is not used. It is site and paper vocabulary, and it would need a paragraph of explanation the listing does not have room for.
- No benchmark numbers. The approved wording carries caveats that do not fit a marketplace page, and a trimmed version of that claim gets quoted back without them.
- No customer reference of any kind.
- Every product claim traces to a live appmap.io page, to a file in the plugin repository, or to both — now verified against the shipped code (see section 1).
- The enterprise section states what an administrator controls before it tells the reader to go ask. A reader who stops there still learns something.

---

## 8. Risk analysis

| Risk | Likelihood | Impact | Mitigation |
|---|---|---|---|
| The MCP claim is wrong. | **Resolved.** The MCP server ships in the AppMap CLI, which both plugins install and keep updated. | High if it had been wrong. | Fact 1 verified against appmap-js source; setup URL and install step are now real. No longer blocking. |
| Navie documentation is deleted while Navie still ships. | **Resolved.** Navie ships and is maintained. | Medium. Support load, and a fair complaint. | Section 6 block restored in both listings; transition sentence softened. |
| Marketplace re-review delays the release. Both marketplaces re-review on update, and the listing only ships with a build. | Medium on VS Code, lower on JetBrains. | Medium. Blocks a launch date, not users. | Do not couple either PR to a release with a committed date. |
| Marketplace rejects the hero image. | Was high with SVG (vsce trusted-badge allowlist). | High — broken or stripped hero image. | **Resolved:** listings reference the PNG; SVG kept as source only. |
| Loss of search ranking. The VS Code keyword list is being extended rather than replaced, but the short description changes, and marketplace search weights it. | Low. | Medium. Installs are the top of the funnel, currently about 140,000 across both editors. | Every existing keyword is kept. The new description keeps the words "code" and "runtime" and adds "MCP". Check install rate two weeks after publication and revert the description alone if it drops. |
| Named agents go stale. Claude Code, Cursor, GitHub Copilot, and Windsurf are named in copy that is updated rarely. | Medium over a year. | Low. The general clause carries the claim. | Keep "any MCP-capable coding agent" in every future edit. |
| Tool names drift. Four tool names are printed in the copy and drawn in the diagram. | Low near term. | Medium. Wrong tool names are checkable and embarrassing. | Verified against the shipped server 31 Aug 2026 (names exact; count corrected to 13). If a name changes, update the copy and re-export the diagram — the SVG is text, so the edit is one search and replace, then re-export the PNG. |
| The two listings drift apart again. They are maintained in separate repositories on separate release trains. | High over time. It is what produced today's state. | Low individually, compounding. | The copy is deliberately near-identical, so a future diff between the two files shows drift immediately. |
