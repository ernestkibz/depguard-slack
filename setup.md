# DepGuard for Slack — Setup & Handoff Guide

Complete setup for the Slack bot that scans public GitHub repos using the [DepGuard](https://github.com/ernestkibz/DepGuard) check engine.

---

## Two separate Git repositories

| Project | GitHub | Purpose |
|---------|--------|---------|
| **DepGuard** (core CLI) | [github.com/ernestkibz/DepGuard](https://github.com/ernestkibz/DepGuard) | Local folder scanner — `depguard` command |
| **DepGuard for Slack** (this repo) | [github.com/ernestkibz/depguard-slack](https://github.com/ernestkibz/depguard-slack) | Slack bot + MCP server |

- **Commit Slack changes here only** — never into the DepGuard repo.
- This repo installs DepGuard as a pip dependency: `depguard @ git+https://github.com/ernestkibz/DepGuard.git@v1.0.1`
- You may clone this repo inside a parent folder next to DepGuard for local dev. Each folder has its own `.git`.

---

## Architecture (current)

```
Slack /depguard https://github.com/owner/repo
    → POST /slack/commands (slack_bot.py, Flask + Gunicorn on Railway)
        → ack within 3s (ephemeral "Scanning…")
        → background thread runs scan_github_repository() (mcp_server.py)
            → git clone (GitPython) → tempfile
            → depguard.run_checks() programmatically
            → temp dir deleted
        → results posted via response_url (works without bot in channel)
            → fallback: chat.postMessage → conversations.join → ephemeral
```

MCP server (`mcp_server.py`) exposes `scan_github_repo` tool for hackathon qualification. Slash commands call the scan function directly (faster than MCP stdio subprocess).

See [architecture.md](architecture.md) for the full diagram.

---

## Production URLs (Railway)

Replace with your actual Railway domain:

| Slack setting | Request URL |
|---------------|-------------|
| **Event Subscriptions** | `https://depguard-slack-production.up.railway.app/slack/events` |
| **Slash command `/depguard`** | `https://depguard-slack-production.up.railway.app/slack/commands` |
| **Health check** | `https://depguard-slack-production.up.railway.app/health` |

**Do not use:**

- Root URL only (`https://….railway.app`) — must include `/slack/events` or `/slack/commands`
- `https://httpbin.org/post` — only echoes JSON back; not a real bot

---

## Step 1 — Create Slack app

1. [api.slack.com/apps](https://api.slack.com/apps) → **Create New App** → **From scratch**
2. Name: **DepGuard**, pick workspace

### Bot token scopes (OAuth & Permissions)

| Scope | Why |
|-------|-----|
| `chat:write` | Post scan results |
| `chat:write.public` | Post to public channels without `/invite` |
| `channels:join` | Join channel if needed (fallback) |
| `commands` | Slash command `/depguard` |
| `app_mentions:read` | Respond to `@DepGuard` |

After adding scopes → **Reinstall to Workspace**.

### Environment variables (Railway + local `.env`)

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
# SLACK_APP_TOKEN=xapp-...   # only if SLACK_MODE=socket
```

### Slash command

| Field | Value |
|-------|-------|
| Command | `/depguard` |
| Request URL | `https://YOUR-APP.up.railway.app/slack/commands` |
| Short Description | `Scan dependencies for vulnerabilities` |
| Usage Hint | `scan` |

**Important:** `scan` is the usage hint shown in Slack UI — **not** what users type. Users must pass a GitHub URL:

```text
/depguard https://github.com/ernestkibz/chaosapp-demo
```

Also accepted: `github.com/owner/repo`, `owner/repo`

### Event Subscriptions

1. **Features → Event Subscriptions** → Enable Events **ON**
2. Request URL: `https://YOUR-APP.up.railway.app/slack/events`
3. Wait for **Verified ✓** (backend must be running; endpoint returns `{"challenge": "..."}`)
4. Subscribe to bot event: `app_mention`
5. Save + reinstall app if prompted

---

## Step 2 — Run locally

```bash
git clone https://github.com/ernestkibz/depguard-slack.git
cd depguard-slack
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env               # fill in tokens
python slack_bot.py                # http://localhost:3000
```

For Slack to reach localhost, use [ngrok](https://ngrok.com): `ngrok http 3000` → paste ngrok URL + `/slack/events` and `/slack/commands`.

---

## Step 3 — Deploy on Railway

1. Connect GitHub repo `ernestkibz/depguard-slack`
2. `Procfile`: `gunicorn slack_bot:flask_app --bind 0.0.0.0:$PORT --timeout 180 --workers 1`
3. `nixpacks.toml` installs `git` CLI (required for GitPython clone)
4. Set `SLACK_BOT_TOKEN` and `SLACK_SIGNING_SECRET`
5. Deploy → copy public URL → paste into Slack app settings

---

## Files in this repo

| File | Role |
|------|------|
| `slack_bot.py` | Flask app, `/slack/events`, `/slack/commands`, slash command handler |
| `mcp_server.py` | MCP tool `scan_github_repo`, clone + run_checks + JSON report |
| `agent.py` | MCP stdio client + Slack Block Kit formatting (used by MCP path) |
| `nixpacks.toml` | Railway: `aptPkgs = ["git"]` |
| `Procfile` | Gunicorn start command |
| `requirements.txt` | slack-bolt, flask, gunicorn, gitpython, mcp, depguard@v1.0.1 |
| `architecture.md` | ASCII architecture diagram |
| `logs/` | Local Railway log exports (gitignored) |

---

## Issues fixed during development (for context)

| Symptom | Cause | Fix (commit area) |
|---------|-------|-------------------|
| Slack URL verify failed | Used root URL not `/slack/events` | Docs + explicit challenge handler in `slack_bot.py` |
| `Worker failed to boot` | `ImportError: Bad git executable` on Railway | `nixpacks.toml` installs git |
| `Worker failed to boot` | `lazy=` not supported on slack-bolt | Background `threading.Thread` instead |
| `/depguard` app did not respond | Scan blocked HTTP >3s | Immediate ack + background thread |
| Invalid URL for `scan` | User typed usage hint not URL | `parse_github_repo_url()` + clearer errors |
| Scan done but no results | `not_in_channel` | Deliver via slash command `response_url` |
| httpbin JSON in channel | Slash URL still `httpbin.org/post` | Point to `/slack/commands` on Railway |

---

## Handoff notes for the next developer / AI

### Current state (working)

- Railway deploys from `main` on [github.com/ernestkibz/depguard-slack](https://github.com/ernestkibz/depguard-slack)
- Latest fixes include: git on Railway, background scan thread, response_url delivery, flexible URL parsing
- Slack workspace used in testing: `depguardworkspace`

### To verify end-to-end

1. `GET /health` → `{"status":"ok"}`
2. Event Subscriptions → Verified ✓ on `/slack/events`
3. In Slack: `/depguard https://github.com/ernestkibz/DepGuard`
4. Expect ephemeral "Scanning…" then in-channel Block Kit report

### Still TODO (hackathon)

- [ ] Demo video (3 min)
- [ ] Slack developer sandbox URL in README
- [ ] Confirm `chaosapp-demo` repo exists if used in demos

### Do not

- Commit this repo's code into [DepGuard](https://github.com/ernestkibz/DepGuard) — separate git remotes
- Use `lazy=` on `@bolt_app.command` — crashes on Railway's slack-bolt version
- Remove `nixpacks.toml` — Railway needs system `git` for clones
- Point slash command at httpbin — it is not DepGuard

### Changing DepGuard checks

Edit the **DepGuard repo**, tag a new release, then update `requirements.txt` in this repo:

```text
depguard @ git+https://github.com/ernestkibz/DepGuard.git@v1.0.2
```

Redeploy Railway after bumping the dependency.

---

## Troubleshooting

| Log / symptom | Fix |
|---------------|-----|
| `Bad git executable` | Redeploy with `nixpacks.toml` on `main` |
| `unexpected keyword argument 'lazy'` | Pull latest `slack_bot.py` (uses threading) |
| `not_in_channel` | Pull latest (response_url) or `/invite @DepGuard` or add `chat:write.public` |
| httpbin JSON in Slack | Change slash Request URL to `…/slack/commands` |
| Invalid URL | Pass full GitHub URL, not `scan` |
| Event URL verify fails | Must be `…/slack/events`, backend running |

Save Railway logs to `logs/` locally for debugging (gitignored).

---

## Links

- **This repo:** [github.com/ernestkibz/depguard-slack](https://github.com/ernestkibz/depguard-slack)
- **DepGuard core:** [github.com/ernestkibz/DepGuard](https://github.com/ernestkibz/DepGuard)
- **Overview:** [README.md](README.md)
