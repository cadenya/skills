# Cadenya MCP

Connect your MCP client to [Cadenya](https://cadenya.com), the hosted agent runtime.

This repository documents Cadenya's hosted MCP integration. The server runs at **https://mcp.cadenya.com/mcp**; this repository does not contain its implementation.

## Connect

Use Streamable HTTP with the endpoint above. Sign in with your Cadenya account using OAuth, or send your Cadenya API key in an `Authorization: Bearer` header.

The server supports **MCP protocol revision `2026-07-28` only**. Clients that support only older revisions cannot connect.

For clients that support OAuth and client ID metadata documents:

```json
{
  "mcpServers": {
    "cadenya": {
      "url": "https://mcp.cadenya.com/mcp"
    }
  }
}
```

For API-key setup, use your client's secret or environment-variable mechanism. Do not commit API keys. See the [connection and authentication documentation](https://cadenya.com/docs/mcp-server).

## Tools

- `cadenya_discover`: Find available operations and their input schemas.
- `cadenya_read`: Run read operations.
- `cadenya_write`: Create, update, or delete resources, continue objectives, and approve or deny tool calls.

These tools cover Agents, variations, Tool Sets, tools, memory, objectives, Widgets, and workspaces. Access is limited by the credential's workspaces and scopes.

## Learn more

- [Cadenya website](https://cadenya.com)
- [Documentation](https://cadenya.com/docs)
- [MCP server setup](https://cadenya.com/docs/mcp-server)
- [Pricing](https://cadenya.com/pricing)

The live documentation is the source of truth for compatibility and authentication requirements.
