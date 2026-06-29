"""DepGuard for Slack — Slack Bolt app entry point."""

from __future__ import annotations

import os
import re

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from agent import format_plain_text, format_slack_blocks, scan_repo

GITHUB_URL_RE = re.compile(r"^https?://github\.com/", re.IGNORECASE)

app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)


def _usage_message() -> str:
    return (
        "Usage: `/depguard https://github.com/owner/repo`\n"
        "Example: `/depguard https://github.com/ernestkibz/chaosapp-demo`"
    )


@app.command("/depguard")
def handle_depguard(ack, command, client, respond):
    """Handle /depguard slash command — scan a GitHub repo via MCP + DepGuard."""
    ack()

    repo_url = (command.get("text") or "").strip()
    channel_id = command["channel_id"]
    user_id = command["user_id"]

    if not repo_url:
        respond(text=_usage_message(), response_type="ephemeral")
        return

    if not GITHUB_URL_RE.match(repo_url):
        respond(
            text=(
                "❌ Invalid URL. Provide a public GitHub repository URL.\n"
                f"{_usage_message()}"
            ),
            response_type="ephemeral",
        )
        return

    client.chat_postMessage(
        channel=channel_id,
        text=f"🔍 DepGuard is scanning {repo_url}…",
    )

    try:
        report = scan_repo(repo_url)
        blocks = format_slack_blocks(report)
        fallback = format_plain_text(report)
        client.chat_postMessage(
            channel=channel_id,
            blocks=blocks,
            text=fallback,
        )
    except Exception as exc:  # noqa: BLE001 — surface errors to Slack
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=f"❌ DepGuard scan failed: {exc}",
        )


@app.event("app_mention")
def handle_mention(event, say):
    """Respond to @DepGuard mentions with usage instructions."""
    say(
        text=(
            "Scan any public GitHub repo with:\n"
            "`/depguard https://github.com/owner/repo`\n\n"
            "Powered by DepGuard — github.com/ernestkibz/DepGuard"
        )
    )


def main() -> None:
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise SystemExit(
            "SLACK_APP_TOKEN is required for Socket Mode. "
            "See README.md for setup instructions."
        )

    handler = SocketModeHandler(app, app_token)
    handler.start()


if __name__ == "__main__":
    main()
