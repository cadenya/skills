---
name: cadenya
description: Starting point for any Cadenya task (Cadenya, the hosted agent runtime) that no more specific Cadenya skill covers. Picks the right Cadenya skill and documentation page for Tool Sets (MCP, OpenAPI, HTTP, or Bare), Agents and variations, objectives and their event streams, tool-call approvals, memory layers, secrets, webhooks, Widgets, the Cadenya MCP server, and `.cadenya/` config files. Use when a request names Cadenya without saying how it will be called. Defers to cadenya-api, cadenya-cli, the SDK skills, cadenya-widgets, and cadenya-start-without-account once the client or situation is known.
---

# Cadenya

Cadenya is a hosted agent runtime. You describe Tool Sets and Agents, and Cadenya runs objectives (agent runs) against them durably and streams their events back.

Your knowledge of Cadenya may be out of date. Prefer retrieval over pre-training: check the installed CLI or SDK version, and verify request shapes, limits, and error messages in the docs before you rely on them.

## Pick the skill

Load the most specific skill that matches, and stop reading this one.

| Skill | Use when |
| --- | --- |
| [cadenya-start-without-account](../cadenya-start-without-account/SKILL.md) | The user has no Cadenya account or credential yet, `cadenya whoami` fails, or a claim link or `REQUIRES_CLAIM` comes up |
| [cadenya-cli](../cadenya-cli/SKILL.md) | The work happens in a shell, a script, CI, or `.cadenya/` config files with `cadenya config plan`/`apply` |
| [cadenya-typescript-sdk](../cadenya-typescript-sdk/SKILL.md) | The code is TypeScript or JavaScript and imports `@cadenya/cadenya` |
| [cadenya-go-sdk](../cadenya-go-sdk/SKILL.md) | The code is Go and imports `go.cadenya.com/cadenya-go` |
| [cadenya-python-sdk](../cadenya-python-sdk/SKILL.md) | The code is Python and imports `cadenya` |
| [cadenya-ruby-sdk](../cadenya-ruby-sdk/SKILL.md) | The code is Ruby or Rails and requires `cadenya` |
| [cadenya-widgets](../cadenya-widgets/SKILL.md) | An Agent is embedded as a chat in a web app for end users, with Widgets and widget sessions |
| [cadenya-api](../cadenya-api/SKILL.md) | The client is curl or a plain HTTP client, or the question is about wire rules every client shares: IDs, field masks, pagination, errors, streams, webhooks |
| cadenya (this skill) | None of the above fits yet: pick a client, then load its skill |

## No client chosen yet

- **Has an account:** follow [Set up Cadenya from a coding agent](https://cadenya.com/docs/setup-from-a-coding-agent.md). A person creates an API key at app.cadenya.com/account/apiKeys; you install the CLI and continue with cadenya-cli.
- **Durable workspace setup:** use [config files](https://cadenya.com/docs/config-files.md) in `.cadenya/` with cadenya-cli.
- **Managing Cadenya from an MCP client:** the [Cadenya MCP server](https://cadenya.com/docs/mcp-server.md) is at `https://mcp.cadenya.com/mcp`.

## Guardrails

- Never put an API key in a committed file, on a command line, or in a plugin manifest. Use `CADENYA_API_KEY` or the client's secret store.
- Reference secrets in Tool Set headers as `{{ secrets.NAME }}`; `${NAME}` is rejected. The value goes in a workspace secret or the Tool Set's `spec.secrets`.
- Objectives need a published Agent. Tools are assigned to variations, not to Agents.
- Don't hardcode a model ID. List models and use one the workspace returns, or leave the model out to use the workspace default.
- Confirm the workspace before you create, update, or delete anything.

## Documentation

- Index of every page, in markdown: [cadenya.com/docs/llms.txt](https://cadenya.com/docs/llms.txt). Append `.md` to any docs URL for markdown.
- Concepts: [Tool Sets](https://cadenya.com/docs/guides/the-basics/tool-sets.md), [Agents](https://cadenya.com/docs/guides/the-basics/agents.md), [Objectives](https://cadenya.com/docs/guides/the-basics/objectives.md), [Memory](https://cadenya.com/docs/guides/the-basics/memory.md), [Widgets](https://cadenya.com/docs/guides/the-basics/widgets.md), [Webhooks](https://cadenya.com/docs/guides/the-basics/webhooks.md)
- [API reference](https://cadenya.com/docs/api-reference.md) and [API keys](https://cadenya.com/docs/api-keys.md)
