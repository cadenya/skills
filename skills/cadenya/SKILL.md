---
name: cadenya
description: Build, run, and manage AI agents on Cadenya, the hosted agent runtime. Use when a task mentions Cadenya, or involves creating Tool Sets (MCP, OpenAPI, HTTP, or Bare), Agents and variations, running or streaming objectives, approving tool calls, memory layers, secrets, webhooks, Widgets, or Cadenya config files. Routes to the Cadenya API, CLI, SDK, and start-without-an-account skills and to the live documentation.
---

# Cadenya

Cadenya is a hosted agent runtime. You describe Tool Sets and Agents; Cadenya runs objectives (agent runs) against them, durably, and streams their events back.

Your knowledge of Cadenya's API, CLI, and SDKs may be outdated. **Prefer retrieval over pre-training.** Check the installed CLI or SDK version, and verify request shapes, limits, and error messages against the documentation before relying on them.

## Pick the skill for the task

| Task | Skill |
| --- | --- |
| Wire conventions shared by every client: IDs and external IDs, field masks, pagination, errors, event streams, webhooks, per-resource request shapes | [cadenya-api](../cadenya-api/SKILL.md) |
| Shell commands, scripts, and CI with the `cadenya` CLI | [cadenya-cli](../cadenya-cli/SKILL.md) |
| TypeScript or JavaScript code that imports `@cadenya/cadenya` | [cadenya-typescript-sdk](../cadenya-typescript-sdk/SKILL.md) |
| Go code that uses the Cadenya Go SDK | [cadenya-go-sdk](../cadenya-go-sdk/SKILL.md) |
| Python code that uses the Cadenya Python SDK | [cadenya-python-sdk](../cadenya-python-sdk/SKILL.md) |
| Ruby code that uses the Cadenya Ruby SDK | [cadenya-ruby-sdk](../cadenya-ruby-sdk/SKILL.md) |
| The user has no Cadenya account or credential yet | [cadenya-start-without-account](../cadenya-start-without-account/SKILL.md) |

## Where to start

- **No account yet:** use [cadenya-start-without-account](../cadenya-start-without-account/SKILL.md), or read [Start without an account](https://cadenya.com/docs/start-without-an-account.md). The CLI creates a temporary workspace and an API key, and returns a claim link that the person must open within 24 hours.
- **Has an account:** [Set up Cadenya from a coding agent](https://cadenya.com/docs/setup-from-a-coding-agent.md). A person copies an API key from app.cadenya.com/account/apiKeys; you install the CLI and do the rest.
- **Declarative setup:** [Config files](https://cadenya.com/docs/config-files.md). Describe Tool Sets, Agents, variations, memory layers, and Widgets as YAML in `.cadenya/`, then run `cadenya config plan` and `cadenya config apply`.
- **Managing Cadenya from an MCP client:** [MCP server](https://cadenya.com/docs/mcp-server.md) at `https://mcp.cadenya.com/mcp`.

## Guardrails

- Never write an API key into a file that is committed, a command line, or a plugin manifest. Use `CADENYA_API_KEY` or the client's secret store.
- Reference secrets in Tool Set headers as `{{ secrets.NAME }}`, and create the secret before the Tool Set that uses it.
- Objectives require a published Agent. Tools are assigned to variations, not to Agents.
- Confirm the workspace before you create, update, or delete anything.

## Documentation

- Index of every page, in markdown: [cadenya.com/docs/llms.txt](https://cadenya.com/docs/llms.txt)
- Concepts: [Tool Sets](https://cadenya.com/docs/guides/the-basics/tool-sets.md), [Agents](https://cadenya.com/docs/guides/the-basics/agents.md), [Objectives](https://cadenya.com/docs/guides/the-basics/objectives.md), [Memory](https://cadenya.com/docs/guides/the-basics/memory.md), [Widgets](https://cadenya.com/docs/guides/the-basics/widgets.md), [Webhooks](https://cadenya.com/docs/guides/the-basics/webhooks.md)
- [API reference](https://cadenya.com/docs/api-reference.md) and [API keys](https://cadenya.com/docs/api-keys.md)
