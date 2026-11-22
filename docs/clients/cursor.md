# Cursor

Cursor starts a local stdio server from `mcp.json`. Project config is `.cursor/mcp.json`. User config is `~/.cursor/mcp.json`. The fields are documented at [Cursor MCP](https://cursor.com/docs/mcp).

From a checkout of Glovebox:

```json
{
  "mcpServers": {
    "glovebox": {
      "type": "stdio",
      "command": "uv",
      "args": ["run", "glovebox-mcp"],
      "cwd": "${workspaceFolder}"
    }
  }
}
```

`${workspaceFolder}` is Cursor's own substitution, from their docs. Use it when `.cursor/mcp.json` lives in this repo. If the file is in your home directory, put the absolute path of the checkout in `cwd` instead.

Reload MCP servers from the Cursor MCP settings after saving the file. Then ask: "Use Glovebox to profile VIN 5UXWX7C5*BA, model year 2011." The tool trace should include `vehicle_profile` or `decode_vin`, and the answer should mention error code 6 because that sample VIN is incomplete.

Do not put an API key in this file. Glovebox does not use one. A future model eval key belongs in `.env`, which is gitignored.

Streamable HTTP is off unless you start `glovebox-mcp --transport http`. That binds `127.0.0.1:8741` by default. Leave it off for normal use.
