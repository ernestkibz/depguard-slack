"""MCP server exposing DepGuard repository scanning as a tool."""

from __future__ import annotations

import json
import re
import shutil
import tempfile
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from pathlib import Path
from typing import Any

from git import Repo
from git.exc import GitCommandError, InvalidGitRepositoryError

from mcp.server.fastmcp import FastMCP

from depguard import run_checks, score_results

CLONE_TIMEOUT_SECONDS = 120
GITHUB_URL_RE = re.compile(
    r"^https?://github\.com/([\w.-]+)/([\w.-]+?)(?:\.git)?/?$",
    re.IGNORECASE,
)

mcp = FastMCP("DepGuard MCP Server")


def _parse_github_url(repo_url: str) -> tuple[str, str]:
    match = GITHUB_URL_RE.match(repo_url.strip())
    if not match:
        raise ValueError(
            "Invalid GitHub URL. Use: https://github.com/owner/repo"
        )
    owner, repo = match.group(1), match.group(2)
    if repo.endswith(".git"):
        repo = repo[:-4]
    return owner, repo


def _clone_repo(repo_url: str, target: str) -> None:
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(
            Repo.clone_from,
            repo_url.strip(),
            target,
            depth=1,
        )
        try:
            future.result(timeout=CLONE_TIMEOUT_SECONDS)
        except FuturesTimeout:
            raise TimeoutError(
                f"Clone timed out after {CLONE_TIMEOUT_SECONDS} seconds. "
                "The repository may be too large or the network is slow."
            )


def _serialize_results(results: list, passed: int, repo_name: str) -> dict[str, Any]:
    checks = []
    for result in results:
        checks.append(
            {
                "name": result.name,
                "status": result.status.value,
                "message": result.message,
                "fix_command": result.fix_command,
            }
        )
    return {
        "repo_name": repo_name,
        "passed": passed,
        "total": len(results),
        "checks": checks,
    }


def scan_github_repository(repo_url: str) -> dict[str, Any]:
    """Clone a public GitHub repo and run all DepGuard checks."""
    owner, repo = _parse_github_url(repo_url)
    repo_name = repo
    tmpdir = tempfile.mkdtemp(prefix="depguard_")

    try:
        _clone_repo(repo_url, tmpdir)
        project = Path(tmpdir)

        entries = list(project.iterdir())
        if not entries:
            return {
                "error": "empty_repo",
                "message": "Repository is empty — no files to scan.",
                "repo_name": repo_name,
            }

        results = run_checks(project)
        passed = score_results(results)
        return _serialize_results(results, passed, repo_name)

    except ValueError as exc:
        return {"error": "invalid_url", "message": str(exc), "repo_name": repo_name}
    except TimeoutError as exc:
        return {"error": "timeout", "message": str(exc), "repo_name": repo_name}
    except GitCommandError as exc:
        stderr = (exc.stderr or str(exc)).lower()
        if "authentication" in stderr or "403" in stderr or "not found" in stderr:
            return {
                "error": "private_or_missing",
                "message": (
                    "Cannot access repository. It may be private, missing, "
                    "or require authentication. Only public repos are supported."
                ),
                "repo_name": repo_name,
            }
        return {
            "error": "clone_failed",
            "message": f"Git clone failed: {exc.stderr or exc}",
            "repo_name": repo_name,
        }
    except InvalidGitRepositoryError as exc:
        return {
            "error": "clone_failed",
            "message": f"Invalid repository: {exc}",
            "repo_name": repo_name,
        }
    except OSError as exc:
        return {
            "error": "scan_failed",
            "message": f"Scan failed: {exc}",
            "repo_name": repo_name,
        }
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


@mcp.tool()
def scan_github_repo(repo_url: str) -> str:
    """
    Clone a public GitHub repository and run DepGuard setup checks.

    Args:
        repo_url: Full GitHub URL (e.g. https://github.com/owner/repo)

    Returns:
        JSON report with check results, pass count, and fix commands.
    """
    report = scan_github_repository(repo_url)
    return json.dumps(report, indent=2)


if __name__ == "__main__":
    mcp.run()
