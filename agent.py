"""Slack agent orchestration — calls DepGuard via MCP and formats Slack blocks."""

from __future__ import annotations

import asyncio
import json
import sys
from pathlib import Path
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

MCP_SERVER_PATH = Path(__file__).resolve().parent / "mcp_server.py"

STATUS_ICONS = {
    "pass": "✅",
    "fail": "❌",
    "warn": "⚠️",
}


async def _call_mcp_scan(repo_url: str) -> dict[str, Any]:
    """Invoke the DepGuard MCP tool via stdio transport."""
    server_params = StdioServerParameters(
        command=sys.executable,
        args=[str(MCP_SERVER_PATH)],
        env=None,
    )

    async with stdio_client(server_params) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(
                "scan_github_repo",
                arguments={"repo_url": repo_url},
            )

            if result.isError:
                text = result.content[0].text if result.content else "MCP tool error"
                return {"error": "mcp_error", "message": text, "repo_name": "unknown"}

            if not result.content:
                return {
                    "error": "mcp_error",
                    "message": "MCP tool returned no content.",
                    "repo_name": "unknown",
                }

            return json.loads(result.content[0].text)


def scan_repo(repo_url: str) -> dict[str, Any]:
    """Synchronous wrapper for Slack Bolt handlers."""
    return asyncio.run(_call_mcp_scan(repo_url))


def _short_check_line(check: dict[str, Any]) -> str:
    icon = STATUS_ICONS.get(check["status"], "•")
    name = check["name"]
    message = check["message"]
    line = f"{icon} {name} — {message}"
    if check.get("fix_command") and check["status"] != "pass":
        line += f"\n   Fix: {check['fix_command']}"
    return line


def format_plain_text(report: dict[str, Any]) -> str:
    """Plain-text fallback for Slack notifications."""
    if report.get("error"):
        return f"❌ DepGuard error: {report.get('message', 'Unknown error')}"

    repo_name = report.get("repo_name", "project")
    lines = [f"🔍 DepGuard Report — {repo_name}", ""]

    for check in report.get("checks", []):
        lines.append(_short_check_line(check))
        lines.append("")

    passed = report.get("passed", 0)
    total = report.get("total", 8)
    lines.append(f"Final score: {passed}/{total} checks passed")
    lines.append("Powered by DepGuard — github.com/ernestkibz/DepGuard")
    return "\n".join(lines)


def format_slack_blocks(report: dict[str, Any]) -> list[dict[str, Any]]:
    """Build Slack Block Kit payload from a DepGuard report."""
    if report.get("error"):
        return [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"❌ *DepGuard could not scan this repository*\n"
                        f"{report.get('message', 'Unknown error')}"
                    ),
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Powered by DepGuard — github.com/ernestkibz/DepGuard",
                    }
                ],
            },
        ]

    repo_name = report.get("repo_name", "project")
    blocks: list[dict[str, Any]] = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"🔍 DepGuard Report — {repo_name}",
                "emoji": True,
            },
        },
        {"type": "divider"},
    ]

    for check in report.get("checks", []):
        icon = STATUS_ICONS.get(check["status"], "•")
        blocks.append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{icon} *{check['name']}* — {check['message']}",
                },
            }
        )
        if check.get("fix_command") and check["status"] != "pass":
            blocks.append(
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Fix: `{check['fix_command']}`",
                        }
                    ],
                }
            )

    passed = report.get("passed", 0)
    total = report.get("total", 8)
    blocks.extend(
        [
            {"type": "divider"},
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Final score: {passed}/{total} checks passed*",
                },
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "Powered by DepGuard — github.com/ernestkibz/DepGuard",
                    }
                ],
            },
        ]
    )
    return blocks
