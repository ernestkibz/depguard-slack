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
2. Fill in these values:

| Field | Value |
|-------|-------|
| **Command** | `/depguard` |
| **Request URL** | `https://httpbin.org/post` *(temporary — lets Slack save the command; replace with your real backend URL when deployed)* |
| **Short Description** | `Scan dependencies for vulnerabilities` |
| **Usage Hint** | `scan` |

3. Save

> **Note:** Slack requires a Request URL to save the slash command. Use `https://httpbin.org/post` for now if your DepGuard API is not running yet. This is **not** the final connection — once you deploy `slack_bot.py` on Railway/Render with Socket Mode, the bot receives commands directly. Update the Request URL to your production endpoint when you add HTTP mode later.

### Event subscriptions (@DepGuard mentions)

1. In the left sidebar, go to **Features → Event Subscriptions**
2. Turn **Enable Events** → **ON**

You will see a **Request URL** field — this is where Slack sends events to DepGuard.

| Situation | Request URL |
|-----------|-------------|
| Backend/API **not running yet** | Leave blank for now — we connect this when the DepGuard backend is deployed |
| Backend **already running** | Your real endpoint (e.g. `https://your-app.railway.app/slack/events`) |

3. Scroll down to **Subscribe to Bot Events** → **Add Bot User Event**
4. Add:

```text
app_mention
```

This lets Slack notify DepGuard when someone writes:

```text
@DepGuard scan
```

5. **Save Changes**
6. If Slack prompts you to **reinstall the app to your workspace**, do that so the new event subscription takes effect.

> **Socket Mode note:** When you run `slack_bot.py` with `SLACK_APP_TOKEN`, events are delivered over the WebSocket connection — you do not need a public Request URL for local or Railway deployment. The Request URL field is mainly required for HTTP-mode apps.

---

### Next step — run the DepGuard backend

After Slack is configured, start the backend that receives `/depguard` and replies:

```bash
pip install -r requirements.txt
cp .env.example .env   # add SLACK_BOT_TOKEN, SLACK_SIGNING_SECRET, SLACK_APP_TOKEN
python slack_bot.py
```

Deploy the same command on [Railway](#step-3--deploy-free-on-railway) for 24/7 availability. See **Step 2** below for full local setup.

---

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
