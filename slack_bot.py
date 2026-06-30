"""DepGuard for Slack — Slack Bolt app entry point."""

from __future__ import annotations

import json
import logging
import os
import re
import threading
import urllib.error
import urllib.request

from flask import Flask, jsonify, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler
from slack_bolt.adapter.socket_mode import SocketModeHandler
from slack_sdk.errors import SlackApiError

from agent import format_plain_text, format_slack_blocks

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/[\w.-]+/[\w.-]+(?:\.git)?/?$",
    re.IGNORECASE,
)


def parse_github_repo_url(raw: str) -> str | None:
    """Accept full URLs, Slack link format, bare github.com paths, or owner/repo."""
    text = (raw or "").strip()
    if not text or text.lower() == "scan":
        return None

    # Slack autolink: <https://github.com/...|label> or <https://github.com/...>
    slack_link = re.search(r"<(https?://[^>|]+)(?:\|[^>]+)?>", text, re.IGNORECASE)
    if slack_link:
        text = slack_link.group(1)

    # Full URL anywhere in the string (e.g. "scan https://github.com/...")
    url_match = re.search(
        r"(https?://github\.com/[\w.-]+/[\w.-]+)",
        text,
        re.IGNORECASE,
    )
    if url_match:
        return url_match.group(1).rstrip("/").removesuffix(".git")

    # github.com/owner/repo without https://
    bare_match = re.search(
        r"github\.com/([\w.-]+/[\w.-]+)",
        text,
        re.IGNORECASE,
    )
    if bare_match:
        return f"https://github.com/{bare_match.group(1).rstrip('/').removesuffix('.git')}"

    # owner/repo shorthand
    if re.fullmatch(r"[\w.-]+/[\w.-]+", text):
        return f"https://github.com/{text}"

    if GITHUB_URL_RE.match(text.rstrip("/").removesuffix(".git")):
        return text.rstrip("/").removesuffix(".git")

    return None

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


def _post_via_response_url(
    response_url: str,
    *,
    blocks: list[dict],
    text: str,
) -> None:
    """Post scan results via slash-command response_url (works without joining channel)."""
    payload = json.dumps(
        {
            "response_type": "in_channel",
            "blocks": blocks,
            "text": text,
        }
    ).encode("utf-8")
    req = urllib.request.Request(
        response_url,
        data=payload,
        headers={"Content-Type": "application/json; charset=utf-8"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        resp.read()


def _deliver_scan_results(
    client,
    *,
    channel_id: str,
    user_id: str,
    response_url: str | None,
    blocks: list[dict],
    text: str,
) -> None:
    """Deliver results — prefer response_url, then join channel + post."""
    if response_url:
        try:
            _post_via_response_url(response_url, blocks=blocks, text=text)
            return
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("response_url delivery failed: %s", exc)

    try:
        client.chat_postMessage(channel=channel_id, blocks=blocks, text=text)
        return
    except SlackApiError as exc:
        if exc.response.get("error") != "not_in_channel":
            raise
        logger.info("Bot not in channel — attempting conversations.join")

    try:
        client.conversations_join(channel=channel_id)
        client.chat_postMessage(channel=channel_id, blocks=blocks, text=text)
    except SlackApiError as exc:
        logger.exception("Could not post scan results to channel")
        client.chat_postEphemeral(
            channel=channel_id,
            user=user_id,
            text=(
                f"{text}\n\n"
                "_Tip: invite DepGuard to this channel with_ `/invite @DepGuard` "
                "_or add the_ `chat:write.public` _bot scope._"
            ),
        )


def _run_depguard_scan_async(
    client,
    channel_id: str,
    user_id: str,
    repo_url: str,
    response_url: str | None,
) -> None:
    """Background scan — Slack gets an immediate ack; results post when ready."""
    logger.info("DepGuard scan started for %s", repo_url)

    try:
        from mcp_server import scan_github_repository

        report = scan_github_repository(repo_url)
        blocks = format_slack_blocks(report)
        fallback = format_plain_text(report)
        _deliver_scan_results(
            client,
            channel_id=channel_id,
            user_id=user_id,
            response_url=response_url,
            blocks=blocks,
            text=fallback,
        )
        logger.info("DepGuard scan completed for %s", repo_url)
    except Exception as exc:  # noqa: BLE001
        logger.exception("DepGuard scan failed for %s", repo_url)
        error_text = f"❌ DepGuard scan failed: {exc}"
        if response_url:
            try:
                _post_via_response_url(
                    response_url,
                    blocks=[{"type": "section", "text": {"type": "mrkdwn", "text": error_text}}],
                    text=error_text,
                )
                return
            except (urllib.error.URLError, TimeoutError, OSError):
                pass
        try:
            client.chat_postEphemeral(channel=channel_id, user=user_id, text=error_text)
        except SlackApiError:
            logger.exception("Could not deliver error message to user")


@bolt_app.command("/depguard")
def handle_depguard(ack, command, client, respond):
    """Ack within 3 seconds; heavy scan runs in a background thread."""
    raw_text = (command.get("text") or "").strip()
    channel_id = command["channel_id"]
    user_id = command["user_id"]

    logger.info("Slash command received: text=%r", raw_text)

    repo_url = parse_github_repo_url(raw_text)

    if not repo_url:
        ack()
        hint = (
            f"You sent: `{raw_text or '(empty)'}`\n\n"
            if raw_text and raw_text.lower() != "scan"
            else "`scan` is the usage hint, not the command argument.\n\n"
        )
        respond(
            text=hint + _usage_message(),
            response_type="ephemeral",
        )
        return

    ack(
        response_type="ephemeral",
        text=f"🔍 DepGuard is scanning `{repo_url}`… results will appear in this channel shortly.",
    )

    threading.Thread(
        target=_run_depguard_scan_async,
        args=(client, channel_id, user_id, repo_url, command.get("response_url")),
        daemon=True,
    ).start()


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
        "note": "Slash command Request URL must end with /slack/commands",
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
    logger.info("Slack slash command POST received")
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
