"""DepGuard for Slack — Slack Bolt app entry point."""

from __future__ import annotations

import os
import re

from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

from agent import format_plain_text, format_slack_blocks, scan_repo

GITHUB_URL_RE = re.compile(r"^https?://github\.com/", re.IGNORECASE)

bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


def _usage_message() -> str:
    return (
        "Usage: `/depguard https://github.com/owner/repo`\n"
        "Example: `/depguard https://github.com/ernestkibz/chaosapp-demo`"
    )


@bolt_app.command("/depguard")
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


@bolt_app.event("app_mention")
def handle_mention(event, say):
    """Respond to @DepGuard mentions with usage instructions."""
    say(
        text=(
            "Scan any public GitHub repo with:\n"
            "`/depguard https://github.com/owner/repo`\n\n"
            "Powered by DepGuard — github.com/ernestkibz/DepGuard"
        )
    )


@flask_app.route("/health", methods=["GET"])
def health() -> tuple[dict, int]:
    return {"status": "ok", "service": "depguard-slack"}, 200


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Slack Event Subscriptions — handles url_verification challenge + events."""
    return handler.handle(request)


@flask_app.route("/slack/commands", methods=["POST"])
def slack_commands():
    """Slash command Request URL — handles /depguard."""
    return handler.handle(request)


def run_http() -> None:
    port = int(os.environ.get("PORT", 3000))
    flask_app.run(host="0.0.0.0", port=port)


def run_socket_mode() -> None:
    app_token = os.environ.get("SLACK_APP_TOKEN")
    if not app_token:
        raise SystemExit(
            "SLACK_APP_TOKEN is required for Socket Mode. "
            "Use HTTP mode instead (unset SLACK_MODE=socket) — see README.md."
        )
    SocketModeHandler(bolt_app, app_token).start()


def main() -> None:
    mode = os.environ.get("SLACK_MODE", "http").lower()
    if mode == "socket":
        run_socket_mode()
    else:
        run_http()


if __name__ == "__main__":
    main()
