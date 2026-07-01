# DepGuard for Slack — Setup Guide

Deploy and use the Slack bot.

Overview: [README.md](README.md)

---

## Step 1: clone and install

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

---

## Step 2: create `.env`

```bash
cp .env.example .env
```

Fill in:

```env
SLACK_BOT_TOKEN=xoxb-...
SLACK_SIGNING_SECRET=...
# SLACK_APP_TOKEN=xapp-...   # only for Socket Mode local testing
```

---

## Step 3: create the Slack app

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

---

## Step 4: configure request URLs

Required paths:

- Events URL: `https://YOUR-APP.up.railway.app/slack/events`
- Slash command URL: `https://YOUR-APP.up.railway.app/slack/commands`
- Health URL: `https://YOUR-APP.up.railway.app/health`

Use the full path — not the root domain alone.

---

## Step 5: run locally

```bash
python slack_bot.py
```

Default local server: `http://localhost:3000`

To reach localhost from Slack, tunnel with ngrok:

```bash
ngrok http 3000
```

Paste the ngrok HTTPS URL plus `/slack/events` and `/slack/commands` into Slack app settings.

---

## Step 6: deploy on Railway

1. Connect the GitHub repo in Railway.
2. Let Railway build from the `Dockerfile`.
3. Add environment variables: `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`
4. Deploy and copy the public Railway domain into Slack app settings.

---

## Step 7: use the bot

```text
/depguard https://github.com/ernestkibz/DepGuard
/depguard https://github.com/vercel/next.js
/depguard ernestkibz/DepGuard
```

The bot acknowledges quickly, scans in the background, then posts the final report.

---

## Explaining warnings to your team

| Status | How to describe it |
|--------|-------------------|
| **FAIL** | Confirmed setup issue or unmet requirement |
| **WARN** | Signal-based finding — needs human review |
| **Suggestion** | Safest next diagnostic or recovery step |

Examples:

- Oracle-related markers do not automatically prove active Oracle production usage
- Missing framework markers can be normal in monorepos
- Dependency alignment warnings can come from tests, examples, or partial migrations

---

## Links

- Slack repo: https://github.com/ernestkibz/depguard-slack
- Core engine: https://github.com/ernestkibz/DepGuard
