# VS Code

VS Code with Copilot reads MCP servers from workspace `.vscode/mcp.json`, or from a user configuration opened with "MCP: Open User Configuration". The current docs are [Add and use MCP servers in VS Code](https://code.visualstudio.com/docs/copilot/customization/mcp-servers).

Workspace file:

```json
{
  "servers": {
    "glovebox": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "glovebox-mcp"]
    }
  }
}
```

The working directory is the workspace folder, so this file belongs in the Glovebox checkout. If you keep the config in user settings instead, set the command to an absolute `uv` and pass `--directory` with the checkout path, as in the Claude Code page.

Enable Copilot for the chat, then ask it to use Glovebox and expand the tool call. A profile that never calls a tool is not a successful setup.

VS Code can also add a server by command from the palette ("MCP: Add Server", then Command). Paste `uv run glovebox-mcp` only when the workspace is this repo.
