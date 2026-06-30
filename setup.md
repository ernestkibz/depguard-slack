# DepGuard for Slack - Setup & Handoff Guide

This file is split into two tracks:

- `Setup 1` is for deploying and using the Slack bot.
- `Setup 2` is for you as the builder/owner maintaining the Slack wrapper and its relationship to the core `DepGuard` repo.

Important: `depguard-slack` and `DepGuard` are separate git repositories.

---

## Setup 1 - Deploy and Use the Slack Bot

### Step 1: clone and install

```bash
git clone https://github.com/ernestkibz/depguard-slack.git
cd depguard-slack
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

### Step 2: create `.env`

```bash
cp .env.example .env
```

Fill in:

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
# SLACK_APP_TOKEN=xapp-...   # only for Socket Mode local testing
```

### Step 3: create the Slack app

At https://api.slack.com/apps:

1. Create a new app from scratch.
2. Add bot scopes:
   - `chat:write`
   - `chat:write.public`
   - `channels:join`
   - `commands`
   - `app_mentions:read`
3. Install or reinstall the app to the workspace.
4. Copy the bot token and signing secret into `.env`.

### Step 4: configure request URLs

These paths are required:

- Events URL: `https://YOUR-APP.up.railway.app/slack/events`
- Slash command URL: `https://YOUR-APP.up.railway.app/slack/commands`
- Health URL: `https://YOUR-APP.up.railway.app/health`

Do not point Slack at the root domain only. Do not use `httpbin` as the final request URL.

### Step 5: run locally

```bash
python slack_bot.py
```

Default local server:

```text
http://localhost:3000
```

For Slack to reach localhost, tunnel it with ngrok:

```bash
ngrok http 3000
```

Then paste the ngrok HTTPS URL plus `/slack/events` and `/slack/commands` into Slack.

### Step 6: deploy on Railway

1. Connect the GitHub repo in Railway.
2. Let Railway build from the `Dockerfile`.
3. Add environment variables:
   - `SLACK_BOT_TOKEN`
   - `SLACK_SIGNING_SECRET`
4. Deploy.
5. Copy the public Railway domain into Slack app settings.

### Step 7: use the bot

Valid command examples:

```text
/depguard https://github.com/ernestkibz/DepGuard
/depguard https://github.com/ernestkibz/chaosapp-demo
/depguard ernestkibz/DepGuard
```

The bot acknowledges quickly, scans in the background, and then posts the final report.

### How to explain warnings to users

Use this interpretation:

- `FAIL` = confirmed setup issue or unmet requirement
- `WARN` = signal-based finding that still needs human review
- `Suggestion` = safest next diagnostic or recovery step for a human operator

Examples of warning nuance:

- Oracle-related markers do not automatically prove active Oracle production usage.
- Missing framework markers can be normal in monorepos or custom layouts.
- Dependency alignment warnings can come from tests, examples, adapters, or partial migrations.

---

## Setup 2 - Builder/Owner Notes

### Repo relationship

There are two repos:

- `DepGuard` - core engine and CLI
- `depguard-slack` - Slack/MCP wrapper and deployment surface

Keep commits and ownership cleanly separated.

### Current architecture

```text
Slack
  -> /slack/commands or /slack/events
  -> slack_bot.py
  -> background thread
  -> mcp_server.py scan_github_repository()
  -> clone repo with GitPython
  -> import and run DepGuard engine
  -> format output in agent.py
  -> deliver via response_url, chat_postMessage, or ephemeral fallback
```

Important implementation rules:

- use `/slack/events` and `/slack/commands` exactly
- avoid `lazy=` in Slack Bolt command handlers
- prefer `response_url` delivery for slash command results
- use the `Dockerfile` so Railway installs the `git` CLI explicitly
- beware Railway UI start-command overrides if behavior looks stale

### Local development with the core repo

`mcp_server.py` prefers a parent-folder `DepGuard` checkout when both of these exist above this repo:

- `depguard.py`
- `checks/`

That allows Slack-side development against unreleased core changes before the next tag is cut.

### Current dependency pin

```text
depguard @ git+https://github.com/ernestkibz/DepGuard.git@v1.1.0
```

After a new core release:

1. bump this dependency
2. test locally
3. redeploy Railway

### Story and demo context

The system evolved in this order:

1. `DepGuard` was built first as the main reusable scan engine.
2. The engine gained detection-driven checks and source-aware dependency sensing.
3. Communication was improved so ambiguous findings are described as signals rather than hard proof.
4. `depguard-slack` was built as a separate Slack Agent Builder challenge wrapper.
5. Demo scans focused on public GitHub repos such as `DepGuard` itself and `chaosapp-demo` style targets.

### Known production lessons

- Railway is more reliable here with a `Dockerfile` than with Nixpacks because GitPython needs the system `git` CLI.
- If Railway boots but Slack says the app did not respond, verify the public domain and `/health` first.
- If Slack cannot verify the URL, confirm the exact endpoint path and that the backend is reachable.
- If results do not post in channel, inspect `response_url` delivery and the `chat_postMessage` fallback logs.

### End-to-end verification checklist

1. `GET /health` returns `{"status":"ok"}`.
2. Slack Event Subscriptions verifies against `/slack/events`.
3. Slash command points to `/slack/commands`.
4. `/depguard https://github.com/ernestkibz/DepGuard` returns a report.
5. A second demo scan against a known public sample repo also returns a report.

### Troubleshooting shortcuts

- `Bad git executable` on Railway: redeploy from the latest Dockerfile-based build.
- `app did not respond`: confirm fast ack plus background thread behavior and public reachability.
- `not_in_channel`: rely on `response_url` first; otherwise invite the bot or ensure `chat:write.public` exists.
- User typed `scan`: remind them it is only a usage hint and they must pass a repo URL.

---

## Links

- Slack wrapper repo: https://github.com/ernestkibz/depguard-slack
- Core engine repo: https://github.com/ernestkibz/DepGuard
- Overview: [README.md](README.md)
