# DepGuard for Slack

DepGuard for Slack lets people run the DepGuard engine from Slack against public GitHub repositories.

Core engine repo: https://github.com/ernestkibz/DepGuard

Important: `depguard-slack` and `DepGuard` are separate git repositories. Keep commits, releases, and ownership boundaries separate even if both folders exist in one local workspace.

---

## README 1 - For Users

### What this repo does

This repo adds the Slack and MCP delivery layer on top of DepGuard.

A typical flow is:

1. A user runs `/depguard https://github.com/owner/repo` in Slack.
2. The bot clones the public repo into a temporary folder.
3. The core DepGuard engine detects the stack and runs relevant checks.
4. Results are posted back into Slack as Block Kit plus plain-text fallback, including both practical suggestions and exact fix commands where possible.

### What users can type

Accepted inputs include:

- `/depguard https://github.com/owner/repo`
- `/depguard github.com/owner/repo`
- `/depguard owner/repo`

The word `scan` is only a usage hint in Slack. It is not the actual argument.

### How to read the report

- `PASS` means the engine found enough evidence that the setup looks correct.
- `FAIL` means the engine found a concrete problem or unmet requirement.
- `WARN` means the engine found something worth review, but not always a confirmed production issue.

Examples of grey-area warnings:

- a dependency may appear to be used from source imports, but might belong to tests, examples, adapters, or code paths that are not deployed
- database signals may suggest Oracle-related usage, but that does not automatically prove the repo actively uses Oracle Database in production
- framework markers may be incomplete because the repo uses a monorepo layout or custom structure

### Example Slack output

```text
[REPORT] DepGuard Report - chaosapp-demo

[WARN] Database Configuration - DepGuard found database-related dependencies or code signals, but could not confirm common connection markers for: Oracle Database. This may be expected if configuration lives in deployment variables, a secrets manager, optional adapters, or non-standard config files.
       Suggestion: Verify the real runtime database from environment variables, secrets management, deployment config, or connection factory code before treating this as a confirmed production dependency.

[FAIL] Node Modules - package.json exists but node_modules is missing.
       Suggestion: Run the repository's package manager from the project root, let it restore dependencies from the lockfile, and then rerun the app build or tests.
       Fix: npm install

Final score: 0/2 checks passed
Note: Some warnings are signal-based and may reflect optional adapters, examples/tests, custom layouts, or environment-managed config.
```

### Screenshot

DepGuard report posted in Slack after scanning a public GitHub repository:

![DepGuard Slack report for next.js](docs/screenshots/depguard-slack-report.png)

### What users need

- a Slack workspace with the app installed
- a running backend for this repo
- a public GitHub repository URL to scan

For detailed setup, see [setup.md](setup.md).

---

## README 2 - For Builder/Owner

### What this repo is

This is the Slack wrapper repo, not the core engine repo.

Main files:

- `slack_bot.py` - Flask + Slack Bolt HTTP app
- `mcp_server.py` - clone public repo and run the DepGuard engine
- `agent.py` - MCP client and Slack formatting helpers
- `Dockerfile` - Railway/container deploy path with system `git`
- `requirements.txt` - pins the released DepGuard version

### Project story

The sequence was:

1. Build `DepGuard` first as the core local scanner.
2. Grow the engine into a reusable detection-driven check system.
3. Create `depguard-slack` as a separate wrapper repo for the Slack Agent Builder challenge and Slack-based demos.
4. Use public demo targets such as `DepGuard` itself and `chaosapp-demo` style repos to show the end-to-end flow.

### Architecture overview

```text
Slack slash command or mention
  -> slack_bot.py
  -> background scan thread
  -> mcp_server.py clone + run_checks()
  -> agent.py formats blocks/text
  -> post results via response_url or Slack API fallback
```

Important behavior:

- exact HTTP paths are `/slack/events` and `/slack/commands`
- slash commands ack quickly, then scan in a background thread
- `response_url` is preferred for delivery because it works even when the bot is not in the channel
- the repo can prefer a parent-folder `DepGuard` checkout during local development so unreleased core changes can be exercised

### Repo boundary

Keep the roles separated:

- core scan logic in `DepGuard`
- Slack presentation, Slack delivery, and deployment logic in `depguard-slack`
- separate git repos for both

### Current dependency relationship

This repo installs:

```text
depguard @ git+https://github.com/ernestkibz/DepGuard.git@v1.1.0
```

That pin should be bumped when the core engine gets a new release.

### Handoff notes

- Do not move Slack logic into the core repo.
- Do not use `lazy=` in Bolt handlers.
- Do not rely on Railway start-command overrides; keep the Dockerfile path authoritative.
- Keep warning language careful in Slack because Slack audiences may over-interpret ambiguous signals.

For Slack app creation, Railway deployment, troubleshooting, and internal history, see [setup.md](setup.md).

---

## License

MIT.
