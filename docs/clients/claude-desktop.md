# Claude Desktop

Claude Desktop launches MCP servers from a JSON file named `claude_desktop_config.json`. The usual locations, from community and tutorial writeups rather than a page re-read from Anthropic during this build, are:

- macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`
- Windows: `%APPDATA%\Claude\claude_desktop_config.json`
- Linux: `~/.config/Claude/claude_desktop_config.json`

If the file is not there, create it from the app's developer or MCP settings. Treat the paths above as unverified against Anthropic's own current page.

```json
{
  "mcpServers": {
    "glovebox": {
      "command": "uv",
      "args": ["run", "glovebox-nhtsa"],
      "cwd": "/absolute/path/to/this/checkout"
    }
  }
}
```

Quit Claude Desktop fully and reopen it. A new chat should be able to call `vehicle_profile`.

`uv` must be on the PATH that Desktop sees. On macOS that is often a different PATH than your terminal. If the server fails to start, use the absolute path to the `uv` binary as `command`.

This server speaks the legacy initialize handshake (verified here with the official Python client in legacy mode) and the current SDK transports. If a future Desktop build speaks only the 2026-07-28 stateless mode, the same official SDK server is what we run. We did not click through the Desktop app in this environment.
