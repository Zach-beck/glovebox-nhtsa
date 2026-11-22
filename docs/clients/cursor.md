# Cursor

Cursor starts a local stdio server from `mcp.json`. Project config is `.cursor/mcp.json`. User config is `~/.cursor/mcp.json`. The fields are documented at [Cursor MCP](https://cursor.com/docs/mcp).

The checked-in file is [`.cursor/mcp.json`](../../.cursor/mcp.json):

```json
{
  "mcpServers": {
    "glovebox-nhtsa": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "glovebox-nhtsa"]
    }
  }
}
```

Cursor starts that command with the workspace as the working directory when the file lives in the project. If you copy it to `~/.cursor/mcp.json`, `uv run` will not find this checkout unless you `cd` there first or change the command.

Reload MCP servers from the Cursor MCP settings after saving the file. Then ask: "Use Glovebox to profile VIN 5UXWX7C5*BA, model year 2011." The tool trace should include `vehicle_profile` or `decode_vin`, and the answer should mention error code 6 because that sample VIN is incomplete.

Do not put an API key in this file. Glovebox does not use one. A future model eval key belongs in `.env`, which is gitignored.

Streamable HTTP is off unless you start `glovebox-nhtsa --transport http`. That binds `127.0.0.1:8741` by default. Leave it off for normal use.
