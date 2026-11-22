# OpenCode

OpenCode's current docs are [MCP servers](https://opencode.ai/docs/mcp-servers/). Local servers use `type: "local"` and a command array. The default protocol mode is still the legacy initialize handshake. Glovebox's stdio test uses that legacy mode with the official Python client, so the default should connect. If a build only answers the 2026-07-28 revision, set `protocol` to `"auto"`.

`opencode.json` in the checkout:

```json
{
  "$schema": "https://opencode.ai/config.json",
  "mcp": {
    "servers": {
      "glovebox": {
        "type": "local",
        "command": ["uv", "run", "glovebox-mcp"],
        "cwd": "."
      }
    }
  }
}
```

OpenCode names tools as `server_tool`. Glovebox's `vehicle_profile` becomes `glovebox_vehicle_profile` after their normalization. Prompts become commands such as `/glovebox:buyer_brief`.

Code Mode is on by default in OpenCode, which hides tools behind a code wrapper. Set `"codemode": false` on this server if you want the tools on the model's native tool list. Either way, the server itself is unchanged.

Remote URLs are Streamable HTTP. Glovebox's HTTP transport is for localhost debugging:

```bash
uv run glovebox-mcp --transport http
```

It listens on `127.0.0.1:8741` at `/mcp`. Do not expose that port. If `GLOVEBOX_HTTP_TOKEN` is set, send `Authorization: Bearer <token>`.
