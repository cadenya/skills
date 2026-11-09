# Cadenya Skills

A collection of [Agent Skills](https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills), plus the hosted Cadenya MCP server, for building, running, and managing AI agents on [Cadenya](https://cadenya.com), the hosted agent runtime.

## Installing

Use the native plugin where supported to install both the Cadenya skills and the Cadenya MCP server. Agents that only support the Agent Skills standard can install the skills separately.

### Codex

Install from the Cadenya plugin marketplace:

```sh
codex plugin marketplace add cadenya/skills
codex plugin add cadenya@cadenya
```

Start a new Codex session after installation.

### Claude Code

Install using the [plugin marketplace](https://code.claude.com/docs/en/plugins/install#add-a-marketplace):

```
/plugin marketplace add cadenya/skills
/plugin install cadenya@cadenya
```

### VS Code / GitHub Copilot

Install directly from this repository:

1. Enable `chat.plugins.enabled` in VS Code settings.
2. Open the Command Palette and run **Chat: Install Plugin From Source**.
3. Enter `https://github.com/cadenya/skills`.

For marketplace installation or troubleshooting, see [VS Code's agent plugin documentation](https://code.visualstudio.com/docs/agent-customization/agent-plugins).

### Cursor

Add manually via **Settings > Rules > Add Rule > Remote Rule (Github)** with `cadenya/skills`.

### npx skills

Install using the [`npx skills`](https://skills.sh) CLI:

```
npx skills add https://github.com/cadenya/skills
```

### Clone / Copy

Clone this repo and copy the skill folders into the appropriate directory for your agent:

| Agent | Skill Directory | Docs |
|-------|-----------------|------|
| Claude Code | `~/.claude/skills/` | [docs](https://code.claude.com/docs/en/skills) |
| Cursor | `~/.cursor/skills/` | [docs](https://cursor.com/docs/context/skills) |
| OpenCode | `~/.config/opencode/skills/` | [docs](https://opencode.ai/docs/skills/) |
| OpenAI Codex | `~/.codex/skills/` | [docs](https://developers.openai.com/codex/skills/) |

## Skills

Agents load a skill when a request matches its description, so you don't need to name it.

| Skill | Useful for |
| --- | --- |
| [cadenya](skills/cadenya/SKILL.md) | Starting point when the client isn't chosen yet. Picks the right skill and documentation page for a Cadenya task. |
| [cadenya-api](skills/cadenya-api/SKILL.md) | curl or a plain HTTP client, and the wire rules every client shares: IDs and external IDs, field masks, pagination, errors, event streams, webhooks, and per-resource request shapes. |
| [cadenya-cli](skills/cadenya-cli/SKILL.md) | The `cadenya` CLI: login and workspaces, request bodies from flags or YAML, Tool Sets and Agents, streaming objectives, approvals, `.cadenya/` config files, and CI scripts. |
| [cadenya-typescript-sdk](skills/cadenya-typescript-sdk/SKILL.md) | The `@cadenya/cadenya` TypeScript SDK: client setup, methods, pagination, errors, objective event streams, and webhook verification. |
| [cadenya-go-sdk](skills/cadenya-go-sdk/SKILL.md) | The `go.cadenya.com/cadenya-go` Go SDK: client options, request structs and unions, pagination, `*APIError` handling, objective event streams, and webhook verification. |
| [cadenya-python-sdk](skills/cadenya-python-sdk/SKILL.md) | The `cadenya` Python SDK: client setup, snake_case request shapes, pagination, `APIError` handling, objective event streams, and webhook verification. |
| [cadenya-ruby-sdk](skills/cadenya-ruby-sdk/SKILL.md) | The `cadenya` Ruby gem: client setup, request hashes, pagination, `Cadenya::APIError` handling, objective event streams, and webhook verification. |
| [cadenya-start-without-account](skills/cadenya-start-without-account/SKILL.md) | Getting a temporary Cadenya workspace with no signup, and claiming it within 24 hours. |
| [cadenya-widgets](skills/cadenya-widgets/SKILL.md) | Embedding an Agent in a web app: creating Widgets, minting tenant-scoped widget sessions on your server, and rendering them with the React UI kit. |

## MCP Servers

| Server | URL | Transport | Authentication |
| --- | --- | --- | --- |
| Cadenya | `https://mcp.cadenya.com/mcp` | Streamable HTTP | OAuth with your Cadenya account, or an API key created in the Cadenya dashboard, sent as `Authorization: Bearer <key>` |

The server supports **MCP protocol revision `2026-07-28` only**. Clients that support only older revisions cannot connect.

It exposes three tools, limited to the credential's workspaces and scopes:

- `cadenya_discover`: Find available operations and their input schemas.
- `cadenya_read`: Run read operations.
- `cadenya_write`: Create, update, or delete resources, continue objectives, and approve or deny tool calls.

The plugin manifests in this repository configure the server without credentials, so clients that support OAuth sign you in on first use. For API-key setup, use your client's secret or environment-variable mechanism. Do not commit API keys. See [MCP server setup](https://cadenya.com/docs/mcp-server).

## Learn more

- [Cadenya website](https://cadenya.com)
- [Documentation](https://cadenya.com/docs)
- [Pricing](https://cadenya.com/pricing)

The live documentation is the source of truth for compatibility and authentication requirements.

## License

[Apache-2.0](LICENSE)
