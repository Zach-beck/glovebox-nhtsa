# Claude Code

Claude Code adds a stdio server with `claude mcp add`. The official instructions are [Connect Claude Code to tools via MCP](https://code.claude.com/docs/en/mcp). The `--` separates Claude's flags from the server command.

From the Glovebox checkout:

```bash
claude mcp add --transport stdio glovebox -- uv run glovebox-nhtsa
```

Run that inside the checkout so `uv run` finds this project. To pin the directory from anywhere:

```bash
claude mcp add --transport stdio glovebox -- uv run --directory /absolute/path/to/this/checkout glovebox-nhtsa
```

`uv run --directory` is uv's flag. If your uv is older and rejects it, `cd` to the checkout and use the first command.

Check with `claude mcp list`. In a session, ask for a recall profile and confirm a tool call, not a guessed answer.

Do not pass `OPENAI_API_KEY` into the server env. Glovebox does not read it. The eval runner does, and only from a local `.env` when you run `python evals/local.py` yourself.
