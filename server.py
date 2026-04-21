import json
import os
import shutil
import git
import subprocess
from detect_secrets import SecretsCollection
from detect_secrets.settings import default_settings
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("code-review")


@mcp.tool()
def fetchRepo(repoUrl: str) -> str:
    """Clone a GitHub repository to a local temp folder and return the folder path."""
    try:
        repo_name = repoUrl.rstrip("/").split("/")[-1]
        clone_path = f"/tmp/{repo_name}"

        if os.path.exists(clone_path):
            shutil.rmtree(clone_path)

        git.Repo.clone_from(repoUrl, clone_path)
        return json.dumps({"status": "success", "path": clone_path})

    except git.exc.GitCommandError as e:
        return json.dumps(
            {
                "error": "Git clone failed. Repo may be private, URL may be wrong, or git is not installed.",
                "detail": str(e),
            }
        )
    except Exception as e:
        return json.dumps({"error": "Unexpected error during clone.", "detail": str(e)})


@mcp.tool()
def runLinter(repoPath: str) -> str:
    """Run ruff linter on a cloned repo and return findings as structured JSON."""
    try:
        if not os.path.exists(repoPath):
            return json.dumps(
                {
                    "error": f"Path does not exist: {repoPath}. Did fetchRepo run successfully?"
                }
            )

        result = subprocess.run(
            [
                "/home/vikram/mcpServer/venv/bin/ruff",
                "check",
                repoPath,
                "--output-format",
                "json",
            ],
            capture_output=True,
            text=True,
        )

        findings = json.loads(result.stdout) if result.stdout.strip() else []

        simplified = [
            {
                "file": f["filename"],
                "line": f["location"]["row"],
                "code": f["code"],
                "message": f["message"],
            }
            for f in findings
        ]

        return json.dumps(simplified, indent=2)

    except FileNotFoundError:
        return json.dumps({"error": "ruff not found. Is it installed in your venv?"})
    except Exception as e:
        return json.dumps(
            {"error": "Unexpected error during linting.", "detail": str(e)}
        )


@mcp.tool()
def detectSecrets(repoPath: str) -> str:
    """Scan a cloned repo for accidentally committed secrets like API keys and tokens."""
    try:
        if not os.path.exists(repoPath):
            return json.dumps(
                {
                    "error": f"Path does not exist: {repoPath}. Did fetchRepo run successfully?"
                }
            )

        secrets = SecretsCollection()
        findings = []

        with default_settings():
            for root, dirs, files in os.walk(repoPath):
                dirs[:] = [d for d in dirs if d != ".git"]

                for filename in files:
                    filepath = os.path.join(root, filename)

                    try:
                        with open(filepath, "r", encoding="utf-8") as f:
                            f.read()
                    except (UnicodeDecodeError, PermissionError):
                        continue

                    secrets.scan_file(filepath)

        # outside all loops — runs after entire repo is scanned
        for filename, secret_list in secrets:
            for secret in secret_list:
                findings.append(
                    {
                        "file": filename,
                        "line": secret.line_number,
                        "type": secret.type,
                    }
                )

        if not findings:
            return json.dumps({"status": "clean", "secrets_found": 0})

        return json.dumps(
            {
                "status": "secrets_found",
                "secrets_found": len(findings),
                "findings": findings,
            },
            indent=2,
        )

    except Exception as e:
        return json.dumps(
            {"error": "Unexpected error during secret scan.", "detail": str(e)}
        )


@mcp.tool()
def scoreCodeQuality(lintResults: str, secretResults: str) -> str:
    """
    Takes results from runLinter and detectSecrets,
    calculates a quality score out of 100 and returns a structured report.
    """
    try:
        lint_findings = json.loads(lintResults)
        secret_findings = json.loads(secretResults)

        # Handle error passthrough from previous tools
        if "error" in lint_findings:
            return json.dumps(
                {"error": f"Lint results invalid: {lint_findings['error']}"}
            )
        if "error" in secret_findings:
            return json.dumps(
                {"error": f"Secret results invalid: {secret_findings['error']}"}
            )

        lint_count = len(lint_findings)
        secret_count = secret_findings.get("secrets_found", 0)

        score = 100
        score -= lint_count * 2
        score -= secret_count * 10
        score = max(0, score)

        if score >= 90:
            grade = "A"
        elif score >= 75:
            grade = "B"
        elif score >= 60:
            grade = "C"
        else:
            grade = "D"

        report = {
            "score": score,
            "grade": grade,
            "breakdown": {
                "lint_issues": lint_count,
                "secrets_found": secret_count,
                "lint_deduction": lint_count * 2,
                "secret_deduction": secret_count * 10,
            },
            "summary": f"Found {lint_count} lint issues and {secret_count} secrets. Grade: {grade}",
        }

        return json.dumps(report, indent=2)

    except json.JSONDecodeError:
        return json.dumps(
            {
                "error": "Invalid JSON passed to scoreCodeQuality. Check previous tool outputs."
            }
        )
    except Exception as e:
        return json.dumps(
            {"error": "Unexpected error during scoring.", "detail": str(e)}
        )


if __name__ == "__main__":
    mcp.run()
