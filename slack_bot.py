"""DepGuard for Slack — Slack Bolt app entry point."""

from __future__ import annotations

import json
import logging
import os
import re

from flask import Flask, jsonify, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler

from agent import format_plain_text, format_slack_blocks, scan_repo

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_URL_RE = re.compile(r"^https?://github\.com/", re.IGNORECASE)

bolt_app = App(
    token=os.environ.get("SLACK_BOT_TOKEN"),
    signing_secret=os.environ.get("SLACK_SIGNING_SECRET"),
)

flask_app = Flask(__name__)
handler = SlackRequestHandler(bolt_app)


def _slack_url_verification_response():
    """
    Slack Event Subscriptions verification handshake.

    Slack POSTs: {"type": "url_verification", "challenge": "abc123"}
    Must reply:  {"challenge": "abc123"}
    """
    payload = request.get_json(silent=True)
    if payload is None and request.data:
        try:
            payload = json.loads(request.data.decode("utf-8"))
        except (json.JSONDecodeError, UnicodeDecodeError):
            payload = None

    if payload and payload.get("type") == "url_verification":
        challenge = payload.get("challenge", "")
        logger.info("Slack url_verification challenge received")
        return jsonify({"challenge": challenge}), 200

    return None


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


@flask_app.route("/", methods=["GET"])
def index() -> tuple[dict, int]:
    return {
        "service": "depguard-slack",
        "health": "/health",
        "slack_events": "/slack/events",
        "slack_commands": "/slack/commands",
        "note": "Use /slack/events as your Slack Event Subscriptions Request URL",
    }, 200


@flask_app.route("/health", methods=["GET"])
def health() -> tuple[dict, int]:
    return {"status": "ok", "service": "depguard-slack"}, 200


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    """Slack Event Subscriptions — url_verification challenge + bot events."""
    challenge_response = _slack_url_verification_response()
    if challenge_response is not None:
        return challenge_response

    logger.info("Slack event POST received")
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
