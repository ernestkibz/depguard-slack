# DepGuard for Slack

Scan any public GitHub repository with **DepGuard** directly inside Slack. Built for the [Slack Agent Builder Challenge](https://slack.com/) with **MCP server integration**.

Type a slash command, get color-coded setup diagnostics with exact fix commands — no terminal required.

**Powered by [DepGuard](https://github.com/ernestkibz/DepGuard)** — the open-source project setup doctor.

---

## What it does

1. Developer runs `/depguard https://github.com/owner/repo` in Slack
2. Bot clones the repo into a temp folder (GitPython)
3. DepGuard runs 8 setup checks via **MCP tool call** (no subprocess)
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

Final score: 3/8 checks passed
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

### Enable Socket Mode

1. In the left sidebar: **Socket Mode** → toggle **Enable Socket Mode** ON
2. Create an **App-Level Token** with scope `connections:write`
3. Copy the token — this is your `SLACK_APP_TOKEN` (starts with `xapp-`)

### Bot token scopes

1. Go to **OAuth & Permissions**
2. Under **Bot Token Scopes**, add:
   - `chat:write` — post scan results
   - `commands` — slash commands
   - `app_mentions:read` — respond to @mentions

### Signing secret

1. Go to **Basic Information**
2. Under **App Credentials**, copy **Signing Secret** → `SLACK_SIGNING_SECRET`

### Install app to workspace

1. Go to **OAuth & Permissions**
2. Click **Install to Workspace**
3. Copy **Bot User OAuth Token** → `SLACK_BOT_TOKEN` (starts with `xoxb-`)

### Create slash command

1. Go to **Slash Commands** → **Create New Command**
2. Command: `/depguard`
3. Short description: `Scan a GitHub repo with DepGuard`
4. Usage hint: `https://github.com/owner/repo`
5. Save

### Event subscriptions (optional — for @mentions)

1. Go to **Event Subscriptions** → Enable Events ON
2. Subscribe to bot event: `app_mention`
3. Reinstall app if prompted

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
SLACK_APP_TOKEN=xapp-...
```

Start the bot:

```bash
python slack_bot.py
```

In Slack, run:

```
/depguard https://github.com/ernestkibz/chaosapp-demo
```

---

## Step 3 — Deploy free on Railway

[Railway](https://railway.app) offers a free tier suitable for Socket Mode bots (no public URL needed).

1. Fork or push this repo to GitHub
2. Go to [railway.app](https://railway.app) → **New Project** → **Deploy from GitHub repo**
3. Select `depguard-slack`
4. Railway detects the `Procfile` automatically
5. Add environment variables in **Variables**:

| Variable | Value |
|----------|-------|
| `SLACK_BOT_TOKEN` | `xoxb-...` |
| `SLACK_SIGNING_SECRET` | your signing secret |
| `SLACK_APP_TOKEN` | `xapp-...` |

6. Deploy — Railway runs `python slack_bot.py`

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
| `SLACK_APP_TOKEN` | Yes | App-level token for Socket Mode (`xapp-`) |

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
├── slack_bot.py          # Slack Bolt app entry point
├── mcp_server.py         # MCP server exposing DepGuard as a tool
├── agent.py              # MCP client + Slack Block Kit formatting
├── requirements.txt
├── .env.example
├── architecture.md
├── README.md
└── Procfile              # Railway / Render deployment
```

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

- **DepGuard core CLI:** [github.com/ernestkibz/DepGuard](https://github.com/ernestkibz/DepGuard)
- **DepGuard for Slack:** [github.com/ernestkibz/depguard-slack](https://github.com/ernestkibz/depguard-slack)

---

## License

MIT — same as DepGuard core.
