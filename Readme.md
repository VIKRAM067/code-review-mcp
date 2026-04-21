# code-review-mcp

An MCP (Model Context Protocol) server that turns Claude into an agentic code reviewer. Point Claude at any public GitHub repo and it autonomously fetches the code, runs static analysis, scans for leaked secrets, and returns a structured quality report — all from a single prompt.

---

## What it does

Claude orchestrates four tools in sequence without any manual intervention:

1. **`fetchRepo`** — clones a GitHub repo to a local temp folder
2. **`runLinter`** — runs `ruff` on the codebase and returns lint findings
3. **`detectSecrets`** — scans every file for accidentally committed API keys, tokens, and credentials
4. **`scoreCodeQuality`** — aggregates lint and secret findings into a score out of 100 with a grade breakdown

---

## Example

**Prompt to Claude:**
> "Fetch https://github.com/VIKRAM067/agenticRAG, run the linter, scan for secrets, then score the code quality"

**Output:**
```json
{
  "score": 94,
  "grade": "A",
  "breakdown": {
    "lint_issues": 3,
    "secrets_found": 0,
    "lint_deduction": 6,
    "secret_deduction": 0
  },
  "summary": "Found 3 lint issues and 0 secrets. Grade: A"
}
```

---

## How the scoring works

| Issue | Deduction |
|---|---|
| Each lint issue | -2 points |
| Each secret found | -10 points |

| Score | Grade |
|---|---|
| 90–100 | A |
| 75–89 | B |
| 60–74 | C |
| Below 60 | D |

---

## Tech stack

- **MCP server** — `FastMCP` (Python)
- **Linter** — `ruff`
- **Secret scanner** — `detect-secrets` (Yelp)
- **Git** — `gitpython`
- **Transport** — stdio (local), SSE (remote)

---

## Local setup

**Requirements:**
- Python 3.10+
- Claude Desktop
- WSL2 (if on Windows)
- `git` installed in your environment

**1. Clone the repo**
```bash
git clone https://github.com/VIKRAM067/code-review-mcp.git
cd code-review-mcp
```

**2. Create and activate virtualenv**
```bash
python3 -m venv venv
source venv/bin/activate
```

**3. Install dependencies**
```bash
pip install mcp gitpython ruff detect-secrets
```

**4. Add to Claude Desktop config**

Open `claude_desktop_config.json`:
- **Mac:** `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows (WSL2):** `C:\Users\<you>\AppData\Roaming\Claude\claude_desktop_config.json`

Add:
```json
{
  "mcpServers": {
    "code-review": {
      "command": "wsl.exe",
      "args": [
        "/absolute/path/to/venv/bin/python",
        "/absolute/path/to/server.py"
      ]
    }
  }
}
```

**5. Restart Claude Desktop**

Look for the 🔨 hammer icon in the chat input. That confirms the server loaded.

**6. Test it**
> "Fetch https://github.com/VIKRAM067/agenticRAG, run the linter, scan for secrets, then score the code quality"

---

## Project structure

```
code-review-mcp/
├── server.py        # MCP server — all four tools
├── requirements.txt
└── README.md
```

---

## Why MCP?

MCP is an open protocol — this server works with any MCP-compatible client, not just Claude Desktop. Cursor, Windsurf, Zed, and any client implementing the spec can connect to it.

---

## Author

Vikram — [github.com/VIKRAM067](https://github.com/VIKRAM067) · [vikram067.github.io](https://vikram067.github.io)