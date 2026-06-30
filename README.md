# DepGuard for Slack

Scan any public GitHub repository with **DepGuard** directly inside Slack. Built for the [Slack Agent Builder Challenge](https://slack.com/) with **MCP server integration**.

Type a slash command, get color-coded setup diagnostics with exact fix commands — no terminal required.

**Powered by [DepGuard](https://github.com/ernestkibz/DepGuard)** — separate core CLI repo.

> **Full setup + handoff:** [setup.md](setup.md) — Slack app, Railway, URLs, fixes applied, notes for the next AI.

> **DepGuard core (separate repo):** [github.com/ernestkibz/DepGuard](https://github.com/ernestkibz/DepGuard) — do not commit CLI code here.

---

## Repositories (important)

| Repo | GitHub | What it is |
|------|--------|------------|
| **DepGuard for Slack** | [ernestkibz/depguard-slack](https://github.com/ernestkibz/depguard-slack) | **This repo** — Slack bot + MCP |
| **DepGuard** | [ernestkibz/DepGuard](https://github.com/ernestkibz/DepGuard) | Core check engine (pip dependency) |

Commit and push **only** in this repo for Slack work. The parent folder may contain both projects locally; each has its own `.git`.

---

## What it does

1. Developer runs `/depguard https://github.com/owner/repo` in Slack
2. Bot clones the repo into a temp folder (GitPython)
3. DepGuard detects the repository stack and runs the relevant checks via **MCP tool call** (no subprocess)
4. Results posted as a **Slack Block Kit** message
5. Temp folder deleted after every scan

### Example Slack output

```
🔍 DepGuard Report — chaosapp-demo

❌ Python Version — 3.10 does not satisfy 3.11
   Fix: pyenv install 3.11.4

❌ Node Modules — package.json exists but node_modules is missing
   Fix: npm install

⚠️ Environment File — .env is missing but .env.example exists
   Fix: cp .env.example .env

✅ Git Initialized — Git repository is initialized
✅ Node Version — no constraint found

Final score: 3/6 relevant checks passed
Powered by DepGuard — github.com/ernestkibz/DepGuard
```

---

## Architecture

See [architecture.md](architecture.md) for the full diagram and component breakdown.

```
Developer → Slack /depguard → Slack Bolt → MCP Client → MCP Server → DepGuard → Slack blocks
```

---

## Prerequisites

- Python 3.10+
- A Slack workspace (free tier works)
- Git installed on the host machine (for cloning repos)

---

## Step 1 — Create a Slack app

1. Go to [api.slack.com/apps](https://api.slack.com/apps) and click **Create New App**
2. Choose **From scratch**
3. Name it **DepGuard** and pick your workspace

### Enable Socket Mode (optional — local dev only)

HTTP mode (below) is required for Event Subscriptions Request URL. Socket Mode is optional for local testing without a public URL:

1. In the left sidebar: **Socket Mode** → toggle **Enable Socket Mode** ON
2. Create an **App-Level Token** with scope `connections:write`
3. Copy the token — this is your `SLACK_APP_TOKEN` (starts with `xapp-`)
4. Run with `SLACK_MODE=socket python slack_bot.py`

### Bot token scopes

1. Go to **OAuth & Permissions**
2. Under **Bot Token Scopes**, add:
   - `chat:write` — post scan results
   - `chat:write.public` — post to public channels without `/invite` (recommended)
   - `channels:join` — join public channels when needed (fallback)
   - `commands` — slash commands
   - `app_mentions:read` — respond to @mentions

### Signing secret

1. Go to **Basic Information**
2. Under **App Credentials**, copy **Signing Secret** → `SLACK_SIGNING_SECRET`

### Install app to workspace

1. Go to **OAuth & Permissions**
2. Click **Install to Workspace**
3. Copy **Bot User OAuth Token** → `SLACK_BOT_TOKEN` (starts with `xoxb-`)

### DepGuard API URLs (use after backend is deployed)

Slack sends HTTP POST requests to these endpoints. Your backend **must be running** before Slack can verify the URL.

Replace `YOUR-APP` with your Railway/Render domain (e.g. `depguard-slack-production.up.railway.app`):

| Slack setting | Request URL |
|---------------|-------------|
| **Event Subscriptions** | `https://YOUR-APP.up.railway.app/slack/events` |
| **Slash command `/depguard`** | `https://YOUR-APP.up.railway.app/slack/commands` |

Health check: `https://YOUR-APP.up.railway.app/health` → should return `{"status":"ok"}`

When you paste the Event Subscriptions URL, Slack sends a **challenge** request. The `/slack/events` endpoint responds automatically — you should see **Verified ✓**.

> **Not deployed yet?** Deploy to Railway first ([Step 3](#step-3--deploy-free-on-railway)), copy your public URL, then come back and paste it here. `httpbin.org` does **not** work for Event Subscriptions — Slack requires a real endpoint that echoes the challenge.

### Create slash command

1. Go to **Slash Commands** → **Create New Command**
2. Fill in these values:

| Field | Value |
|-------|-------|
| **Command** | `/depguard` |
| **Request URL** | `https://YOUR-APP.up.railway.app/slack/commands` *(after deploy — or `https://httpbin.org/post` temporarily to save the form only)* |
| **Short Description** | `Scan dependencies for vulnerabilities` |
| **Usage Hint** | `scan` |

3. Save

### Event subscriptions (@DepGuard mentions)

1. In the left sidebar, go to **Features → Event Subscriptions**
2. Turn **Enable Events** → **ON**
3. **Request URL** — paste:

```text
https://YOUR-APP.up.railway.app/slack/events
```

Wait for Slack to show **Verified ✓** (your backend must be running).

4. Scroll down to **Subscribe to Bot Events** → **Add Bot User Event**
5. Add:

```text
app_mention
```

This lets Slack notify DepGuard when someone writes:

```text
@DepGuard scan
```

6. **Save Changes**
7. Reinstall the app to your workspace if Slack prompts you.

---

### Next step — deploy the DepGuard backend

Deploy first so you have a real URL for Slack to verify:

```bash
pip install -r requirements.txt
cp .env.example .env   # add SLACK_BOT_TOKEN and SLACK_SIGNING_SECRET
python slack_bot.py    # local test on http://localhost:3000
```

Then deploy on [Railway](#step-3--deploy-free-on-railway) and paste your public URL into Slack.

---

## Step 2 — Run locally

```bash
git clone https://github.com/ernestkibz/depguard-slack.git
cd depguard-slack
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

Copy environment variables:

```bash
cp .env.example .env
```

Edit `.env` with your tokens:

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
# SLACK_APP_TOKEN=xapp-...   # only needed for SLACK_MODE=socket
```

Start the HTTP API (default — required for Slack Event Subscriptions URL):

```bash
python slack_bot.py
# listens on http://localhost:3000
# Event URL: http://localhost:3000/slack/events  (use ngrok for Slack verification)
```

In Slack, run:

```
/depguard https://github.com/ernestkibz/chaosapp-demo
```

---

## Step 3 — Deploy free on Railway

[Railway](https://railway.app) free tier runs the DepGuard HTTP API 24/7 and gives you the public URL Slack needs.

1. Fork or push this repo to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Select `depguard-slack`
4. Railway detects the `Procfile` (`gunicorn slack_bot:flask_app`)
5. Add environment variables in **Variables**:

| Variable | Value |
|----------|-------|
| `SLACK_BOT_TOKEN` | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | your signing secret |

6. Deploy — Railway assigns a public URL like `https://depguard-slack-production.up.railway.app`
7. Paste into Slack:

| Slack setting | URL |
|---------------|-----|
| **Event Subscriptions → Request URL** | `https://YOUR-APP.up.railway.app/slack/events` |
| **Slash command → Request URL** | `https://YOUR-APP.up.railway.app/slack/commands` |

### Railway troubleshooting

If logs show `ImportError: Bad git executable`, the container is missing the `git` CLI. This repo includes `nixpacks.toml` with `aptPkgs = ["git"]` — **trigger a redeploy** after pulling the latest code.

Save Railway log exports under `logs/` (gitignored) for local debugging.

### Render (alternative)

1. [render.com](https://render.com) → **New Background Worker**
2. Connect GitHub repo
3. Build command: `pip install -r requirements.txt`
4. Start command: `python slack_bot.py`
5. Add the same three environment variables

---

## Environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SLACK_BOT_TOKEN` | Yes | Bot OAuth token (`xoxb-`) |
| `SLACK_SIGNING_SECRET` | Yes | App signing secret |
| `SLACK_APP_TOKEN` | Socket Mode only | App-level token (`xapp-`) |

See [setup.md](setup.md) for Railway env vars and Slack app configuration.

---

## MCP server (standalone)

Run the MCP server independently for testing or other MCP clients:

```bash
python mcp_server.py
```

Tool exposed: `scan_github_repo(repo_url)` → JSON report

---

## Project structure

```
depguard-slack/
├── slack_bot.py          # Flask + Bolt — /slack/events, /slack/commands
├── mcp_server.py         # MCP tool scan_github_repo + clone + run_checks
├── agent.py              # MCP client + Slack Block Kit formatting
├── nixpacks.toml         # Railway: installs git CLI
├── requirements.txt      # pins the released DepGuard package
├── setup.md              # Full setup, troubleshooting, AI handoff
├── architecture.md
├── Procfile              # gunicorn slack_bot:flask_app
├── .env.example
├── logs/                 # Railway log exports (gitignored)
└── README.md
```

---

## Handoff for next AI / developer

Read **[setup.md](setup.md)** first. Key facts:

- **Two repos** — this is `depguard-slack` only; core CLI is [DepGuard](https://github.com/ernestkibz/DepGuard)
- **Railway URL paths:** `/slack/events` and `/slack/commands` (not root, not httpbin)
- **Slash command:** users pass a GitHub URL, not the word `scan`
- **Results delivery:** uses slash `response_url` so bot need not be in channel
- **Railway needs `nixpacks.toml`** for system git (GitPython)
- **No `lazy=` on Bolt commands** — use background thread (see setup.md issue table)
- **Released depguard dependency:** `@v1.0.1` in `requirements.txt`
- **Local dev integration:** if a parent folder contains `depguard.py` and `checks/`, `mcp_server.py` prefers that checkout so new core checks work before the next tagged release

---

## Hackathon submission checklist

- [x] Working Slack bot (`/depguard` slash command)
- [x] MCP server integration (`mcp_server.py` + `agent.py` stdio client)
- [x] Architecture diagram ([architecture.md](architecture.md))
- [ ] Demo video (3 minutes) — record a Slack scan and add link here
- [ ] Slack developer sandbox URL — add your workspace invite link here
- [x] GitHub repo public — [github.com/ernestkibz/depguard-slack](https://github.com/ernestkibz/depguard-slack)

---

## Error handling

| Input | Response |
|-------|----------|
| No URL | Ephemeral usage hint |
| Non-GitHub URL | Ephemeral invalid URL message |
| Private / missing repo | Error block in channel |
| Clone timeout (120s) | Error block with timeout message |
| Empty repo | Error block — nothing to scan |
| Scan crash | Ephemeral error to requesting user |

---

## Links

- **Setup & handoff:** [setup.md](setup.md)
- **DepGuard core CLI:** [github.com/ernestkibz/DepGuard](https://github.com/ernestkibz/DepGuard)
- **This repo:** [github.com/ernestkibz/depguard-slack](https://github.com/ernestkibz/depguard-slack)

---

## License

MIT — same as DepGuard core.
