# DepGuard for Slack — Architecture

DepGuard for Slack connects Slack slash commands to the DepGuard setup-check engine through an MCP (Model Context Protocol) server. Developers scan any public GitHub repository without leaving Slack.

## Flow diagram

```
Developer
    │
    │  /depguard https://github.com/owner/repo
    ▼
Slack Workspace
    │
    ▼
Slack Bolt App (slack_bot.py)
    │  • Validates GitHub URL
    │  • Acknowledges slash command
    │  • Posts "scanning…" message
    ▼
Agent Layer (agent.py)
    │  • MCP client (stdio transport)
    │  • Calls scan_github_repo tool
    ▼
MCP Server (mcp_server.py)
    │  • Exposes DepGuard as MCP tool
    │  • Clones repo via GitPython → tempfile.mkdtemp()
    │  • Runs 8 checks programmatically (no subprocess)
    │  • Deletes temp folder after scan
    ▼
DepGuard Engine (depguard package)
    │  • run_checks(project_path)
    │  • Python, Node, pip, node_modules, .env, Docker, Git, venv
    ▼
Results JSON
    │
    ▼
Agent Layer (agent.py)
    │  • format_slack_blocks()
    │  • format_plain_text() fallback
    ▼
Slack Block Kit Message
    │
    ▼
Posted to Slack channel
```

## Components

| File | Role |
|------|------|
| `slack_bot.py` | Slack Bolt app — slash command `/depguard`, Socket Mode for free hosting |
| `agent.py` | Orchestration — MCP client, Slack Block Kit formatting |
| `mcp_server.py` | MCP server — `scan_github_repo` tool for hackathon qualification |
| `depguard` (pip) | Core check engine from [DepGuard](https://github.com/ernestkibz/DepGuard) |

## MCP integration

The MCP server exposes one tool:

- **`scan_github_repo(repo_url)`** — clones a public GitHub repo, runs all DepGuard checks, returns JSON report

The agent connects via stdio:

```
python mcp_server.py  ←→  MCP protocol  ←→  agent.py
```

This satisfies the Slack Agent Builder Challenge requirement for MCP server integration.

## Error handling

| Scenario | Behavior |
|----------|----------|
| Missing URL | Ephemeral usage message |
| Invalid URL | Ephemeral error with example |
| Private / missing repo | Error block in channel |
| Clone timeout (120s) | Error block with timeout message |
| Empty repository | Error block — no files to scan |
| MCP / scan failure | Ephemeral error to user |

## Deployment

- **Socket Mode** — no public HTTP endpoint required (works on Railway/Render free tier)
- **Dockerfile** — installs system `git` and starts `gunicorn slack_bot:flask_app`
- **Env vars** — `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_APP_TOKEN`

## Security

- Only public GitHub repositories (no auth tokens stored)
- Temp clone directories deleted after every scan
- No persistent storage of scanned code

## Links

- DepGuard core: https://github.com/ernestkibz/DepGuard
- DepGuard for Slack: https://github.com/ernestkibz/depguard-slack
