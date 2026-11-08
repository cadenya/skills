---
name: cadenya-cli
description: Drive Cadenya from a terminal or shell script with the `cadenya` CLI. Log in, pick a workspace, build request bodies from flags or YAML, create tool sets and agents, run and stream objectives, approve tool calls, page through lists, and script it all for CI. Use when a task mentions the CLI or `cadenya` commands, shell automation against Cadenya, turning an API call into a command, or a CLI error such as `required flag(s) not set`, `not found (http 404, code 5)`, `AUTH_TOKEN_INVALID`, or `agent must be published to create an objective`.
---

# Cadenya CLI usage

## Overview

`cadenya` is a generated, one-to-one command surface over the Cadenya REST API: same resources, same JSON, same IDs. Every command's exact contract is one call away, so look it up instead of guessing:

```sh
cadenya schema objectives create      # positionals, every flag with its wire path, JSON Schema for document inputs
cadenya objectives create --help      # the same flags, shorter
cadenya schema                        # every command in one list
```

For wire conventions shared by every client (IDs, external IDs, field masks, pagination, error shape) see the `cadenya-api` skill.

## Read the schema before you build a command

`cadenya schema <group> <command>` is the CLI's self-description, written for coding assistants. Run it before composing any create, update, or action command; it removes the guesswork that `--help` leaves:

```sh
cadenya schema                                    # every command with its one-line purpose
cadenya schema agents variations add-assignment   # one command's full contract
```

The output is markdown with four parts:

- **Usage line** showing positionals and every flag, with `[...]...` for repeatable flags.
- **Arguments**: each positional with the ID forms it accepts (`Accepts the canonical agent_… form or the external_id:<value> form`).
- **Flags**: each flag's wire `Path:` (`defaultVariation.spec.modelConfig.modelId`), whether it is required, its enum short forms (`One of: random, weighted`), and for unions which `Arm:` it belongs to and which flag selects that arm.
- **Types**: JSON Schema (with `$defs`) for every document input, so you can write `--spec @spec.yml` or `-f body.yml` without inventing keys. Discriminated unions appear as `oneOf` with `"type": {"const": "toolSetId"}`.

```
- `--type <tool-id|tool-set-id|sub-agent-id>` (required) Arms: `tool-id` (…_ToolId), `tool-set-id` (…_ToolSetId), `sub-agent-id` (…_SubAgentId).
- `[--tool-set-id <value>]` (required in its arm) Path: `toolSetId`. Arm: `type = tool-set-id`.
```

Workflow: `cadenya schema …` to learn the shape, build the command and confirm it with `--dry-run`, then run it. `cadenya schema <group> <command> | grep 'Path:'` is a quick flag-to-wire-path map when translating a JSON body from the API docs into flags.

## Setup

```sh
brew install cadenya/tools/cadenya    # macOS/Linux; Windows: choco install cadenya
cadenya --version                     # binary release plus the API contract it was generated against
```

**Credential resolution, first match wins:** `--api-key` flag, then `CADENYA_API_KEY`, then the stored login.

- Interactive machines: `cadenya auth login` runs a browser device flow (`--no-browser` prints the URL) and stores the credential in `~/.cadenya/credentials` (mode 0600). You pick which workspaces the login may reach on the approval page.
- CI and scripts: export `CADENYA_API_KEY` (an account API key assigned to the workspace) and `CADENYA_WORKSPACE_ID`. Never put the key on the command line.
- `cadenya auth status` names the credential source in effect and lists the workspaces the login can reach; it exits 0 even when that credential is bad. `cadenya whoami` is the pre-flight check that exits 1 on a rejected credential.
- `--profile <name>` on any command (including `auth login`) keeps separate logins and stored defaults.

**Workspace resolution, first match wins:** `--workspace-id`, then `CADENYA_WORKSPACE_ID`, then `cadenya config set workspace-id <id>`, then the login's single authorized workspace. Both accept a workspace ID (`workspace_…`) or its external ID (`development`).

```sh
cadenya workspaces list                       # what this credential can reach
cadenya config set workspace-id development   # per-profile default
cadenya config list                           # effective values and their sources
```

## Command map

Groups mirror API resources. Nested resources are subgroups (`agents variations`, `tool-sets tools`).

| Group | Commands |
| --- | --- |
| `auth` | `login`, `logout`, `status` |
| `config` | `set`, `get`, `unset`, `list` |
| `whoami`, `profiles whoami` | the profile behind the credential |
| `workspaces` | `list` |
| `workspace-admin` | `list-account`, `create`, `retrieve`, `update`, `archive`, `list-members`, `add-member`, `remove-member`, `list-profiles` (admin role) |
| `api-keys` | `list`, `create`, `retrieve`, `update`, `delete`, `enable`, `disable`, `rotate`, `reveal`, `add-workspace`, `remove-workspace` (account-level) |
| `ai-provider-keys` | `list`, `create`, `retrieve`, `update`, `delete` |
| `models` | `list`, `retrieve`, `enable`, `disable`, `swap-on-variations` |
| `tool-sets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive`, `list-events`, `list-usage`, `retrieve-open-api-spec` |
| `tool-sets tools` | `list`, `create`, `retrieve`, `update`, `delete`, `omit`, `restore` |
| `tool-sets secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `workspace-secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `agents` | `list`, `create`, `retrieve`, `update`, `delete`, `publish`, `unpublish`, `archive`, `unarchive`, `list-feedback`, `list-webhook-deliveries` |
| `agents variations` | `list`, `create`, `retrieve`, `update`, `delete`, `add-assignment`, `remove-assignment`, `add-memory-layer`, `update-memory-layer`, `remove-memory-layer` |
| `agents schedules` | `list`, `create`, `retrieve`, `update`, `delete`, `pause`, `resume`, `archive` |
| `objectives` | `list`, `create`, `retrieve`, `list-events`, `stream-events`, `continue`, `cancel`, `compact`, `list-tool-calls`, `retrieve-tool-call`, `approve-tool-call`, `deny-tool-call`, `set-tool-call-content`, `list-tools`, `list-tasks`, `retrieve-task`, `list-context-windows`, `retrieve-diagnostics`, `list-feedback`, `create-feedback` |
| `memory-layers` | `list`, `create`, `retrieve`, `update`, `delete` |
| `memory-layers entries` | `list`, `create`, `retrieve`, `update`, `delete` |
| `tenants` | `list`, `retrieve`, `delete`, `list-subjects` |
| `widgets`, `widget-sessions` | CRUD plus `archive`/`unarchive` (widgets) and `revoke`, `delete-tenant` (sessions) |
| `uploads` | `create`, `retrieve` |
| `tool-search` | `search-or-sets --query <text>` |
| `schema` | print any command's contract as markdown |

## Positional IDs

Path parameters are positionals in path order, minus the workspace: `retrieve <id>`, `agents variations retrieve <agent-id> <id>`, `objectives approve-tool-call <objective-id> <tool-call-id>`. Every positional and `--workspace-id` accepts the canonical ID (`agent_…`), the bare external ID (`support-triager`), or the explicit form `external_id:support-triager`.

```sh
cadenya agents retrieve support-triager
cadenya agents retrieve external_id:support-triager   # use this form if your external IDs look like Cadenya IDs
```

## Building request bodies

Rules, in priority order (deeper wins): `-f <file>` whole body, then `--<subtree> <doc>` documents, then individual flags.

- **Scalar fields are flags named by their wire path with the `metadata`/`spec` envelopes dropped.** `metadata.name` is `--name`, `spec.description` is `--description`, `defaultVariation.spec.modelConfig.modelId` is `--default-variation-model-id`. `cadenya schema` prints the `Path:` of every flag.
- **Maps are repeatable `KEY=VALUE`:** `--label team=docs --label env=dev`, `--mcp-header 'Authorization=Bearer {{ secrets.MCP_TOKEN }}'`. Untyped maps take `KEY:=JSON` for non-string values: `--system-prompt-data 'customer_name=Ada' --system-prompt-data 'tier:=3'`.
- **Lists repeat the flag:** `--permission objectives:manage --permission agents:read`.
- **Unions collapse onto their arms.** Setting `--mcp-url` selects the `mcp` adapter; `--adapter mcp` is only needed when no arm flag is set. Same for `--openapi-url` vs `--openapi-upload-id`, `--type tool-set-id --tool-set-id …` on assignments.
- **Documents (`<doc>`)** take a YAML/JSON literal, `@path`, or `-` for stdin. Only one input per invocation may read stdin. Plain string flags accept `@path` and `-` too, which keeps secret values out of shell history (`--value @token.txt`, `--value -`). Write `@@` for a literal leading `@`.
- **Enums accept short forms:** `--variation-selection-mode random` sends `VARIATION_SELECTION_MODE_RANDOM`; `--help` lists them.
- **Booleans take no separate value:** `--include-info` or `--include-info=false`. `--include-info false` is a usage error (`false` parses as a positional).
- **Repeatable flags never split on commas**, so JSON documents with commas are safe.

`--dry-run` prints the assembled body (YAML, or JSON with `--display json`) and exits without calling the API. It exists on every command that takes a body; verb commands such as `publish` or `approve-tool-call` have none. Build once with flags, keep the file, then `-f` it:

```sh
cadenya tool-sets create --name "Support MCP" --external-id support-mcp \
  --mcp-url https://mcp.example.com/mcp \
  --mcp-header 'Authorization=Bearer {{ secrets.MCP_TOKEN }}' \
  --mcp-tool-approvals-always --dry-run > tool-set.yml
```

```yaml
metadata:
  externalId: support-mcp
  name: Support MCP
spec:
  adapter:
    mcp:
      headers:
        Authorization: Bearer {{ secrets.MCP_TOKEN }}
      toolApprovals:
        always: true
        type: always
      url: https://mcp.example.com/mcp
    type: mcp
```

Fields the request does not accept (`id`, timestamps, `state`, `info`) are dropped from `-f` documents with a warning, so `retrieve --display yaml`, edit, `update -f` round-trips. `--strict` turns that warning into a usage error.

## Lists and pagination

Every `list` takes `--limit`, `--cursor`, `--sort-order asc|desc` (creation time), `--labels 'env=prod,team=ai'` (every pair must match), and usually `--prefix`, `--query`, and a state filter (`--state STATE_PUBLISHED`). `--include-info` populates the computed `info` block and counts more against your rate limit.

One page per call. In `--display json` the page is `{"items": [...], "nextCursor": "..."}`; an empty or missing `nextCursor` means the last page. In `table` mode the cursor goes to stderr as `next cursor: …` so stdout stays clean.

```sh
cursor=""
while :; do
  page=$(cadenya agents list --limit 50 --display json ${cursor:+--cursor "$cursor"})
  jq -r '.items[].metadata.externalId' <<<"$page"
  cursor=$(jq -r '.nextCursor // ""' <<<"$page")
  [ -z "$cursor" ] && break
done
```

## Updates

`update` derives `updateMask` from the flags and documents you pass, so only those fields change:

```sh
cadenya tool-sets update support-mcp --name "Support MCP (prod)" --label team=docs --dry-run
# metadata: {labels: {team: docs}, name: Support MCP (prod)}
# updateMask: metadata.labels,metadata.name
```

- Pass `--update-mask metadata.name,spec.description` to override the derived mask (paths are camelCase, dotted).
- Maps and lists are replaced wholesale. To add one label, send every label.
- `-f` with a full document masks the whole `metadata` and `spec` subtrees, which is what a round-trip edit wants.
- Some update commands insist on a schema-required field even when you only want to rename: `agents update` needs `--variation-selection-mode`, `agents variations update` needs `--model-id`. Pass the current value; the derived mask includes it harmlessly.

## Output, errors, exit codes

`--display json|yaml|table|extended` (root or per command). JSON is always the default so scripts stay stable; `table` prints configured columns; `extended` prints psql-style vertical records. Streams are NDJSON only.

Errors go to stderr as the API's `google.rpc.Status`: `error: cadenya: <message> (http <status>, code <grpc-code>)` followed by the `details` list (`ErrorInfo.reason` such as `AUTH_TOKEN_INVALID`, or `BadRequest.fieldViolations[]` with `field` in snake_case proto form, for example `spec.model_config.model_id`). Nothing is written to stdout on error.

| Exit | Meaning |
| --- | --- |
| `0` | success |
| `1` | API or transport error (also an unknown flag) |
| `2` | usage error caught before any network I/O: missing positional, `required flag(s) not set`, `--strict` violations |
| `130` | interrupted (Ctrl-C / SIGTERM), for example while following a stream |

`--debug` (or `CADENYA_DEBUG=1`) dumps every HTTP exchange to stderr with `Authorization: [redacted]`. Response headers include `Grpc-Status`; a `501` on a route means a stale deployment, not a client bug.

## Bootstrap a tool set and an agent

```sh
export CADENYA_WORKSPACE_ID=development

# 1. Secret, referenced later as {{ secrets.MCP_TOKEN }}. Read the value from a file, not the command line.
cadenya workspace-secrets create --name MCP_TOKEN --value @mcp-token.txt

# 2. Tool set. Every synced tool requires approval here; drop --mcp-tool-approvals-always to auto-run.
cadenya tool-sets create --name "Support MCP" --external-id support-mcp \
  --mcp-url https://mcp.example.com/mcp \
  --mcp-header 'Authorization=Bearer {{ secrets.MCP_TOKEN }}' \
  --mcp-tool-approvals-always

# 3. Pick a model. modelId is "<provider-key-slug>.<model-slug>" or the canonical model_ ID.
cadenya ai-provider-keys list                     # EXTERNAL ID column is the provider-key slug
cadenya models list --query claude                # EXTERNAL ID column is the model slug; --query is a substring, --prefix a name/ID prefix

# 4. Agent with its default variation in one call. The variation's system prompt is a Liquid template
#    over system_prompt_data; first_user_message_template renders first_user_message_data.
cadenya agents create --name "Support Triager" --external-id support-triager \
  --variation-selection-mode random \
  --default-variation-name default --default-variation-external-id support-triager-default \
  --default-variation-model-id getting-started-key.claude-opus-5 \
  --default-variation-system-prompt-template 'You triage support tickets for {{ system_prompt_data.customer_name }}.' \
  --default-variation-constraints-inactivity-timeout 3600s

# 5. Assign the tool set to the variation (tools are assigned to variations, not agents).
cadenya agents variations add-assignment support-triager support-triager-default \
  --type tool-set-id --tool-set-id support-mcp

# 6. Publish. Objectives on a STATE_DRAFT agent fail with "agent must be published to create an objective".
cadenya agents publish support-triager
```

`agents create` returns the agent, not the variation; `agents variations list <agent>` shows it. To make the bootstrap re-runnable, gate each create on `retrieve <external-id>` (exit 1 on 404): a create with a duplicate external ID fails with 409 `already exists`. OpenAPI tool sets use `--openapi-url` (or `--openapi-upload-id` after `uploads create`), HTTP tool sets use `--http-base-url` plus `tool-sets tools create` per tool, and Bare tool sets (`--adapter bare`) park each call until you `set-tool-call-content`.

## Run an objective end to end

Facts that shape the loop:

- `objectives create` returns immediately with `state: STATE_PENDING`; the `userMessage` event already exists.
- `stream-events` without `--last-event-id` delivers only events that arrive after you connect. With it, the server replays everything after that ID, then goes live. An invalid ID fails before the stream opens.
- The stream never closes on its own. Stop reading when you see a terminal event: `finalized`, `error`, `cancelled`, `timedOut`. An `assistantMessage` with no `toolCalls` means the turn is over and the objective is `STATE_WAITING` (not terminal): `continue` it or let the inactivity timeout finalize it.
- `cancel` is asynchronous; poll `retrieve` for `STATE_CANCELLED` if you need to wait.

```sh
#!/usr/bin/env bash
set -euo pipefail
export CADENYA_WORKSPACE_ID=development

obj=$(cadenya objectives create --agent-id support-triager --external-id "ticket-$RANDOM" \
  --system-prompt-data customer_name=Ada \
  --first-user-message "Summarize the open tickets." --display json | jq -er '.metadata.id')

# Newest event so far: the stream replays everything after it, then goes live. No gap, no duplicates.
last=$(cadenya objectives list-events "$obj" --sort-order desc --limit 1 --display json | jq -er '.items[0].metadata.id')

# Read in the main shell (a pipe would run the loop in a subshell) and stop the stream yourself:
# the server never closes it, and a killed stream exits 130, which `set -e` in a pipeline would turn into a failure.
exec 3< <(cadenya objectives stream-events "$obj" --last-event-id "$last")
done=""
while [ -z "$done" ] && IFS= read -r -t 600 line <&3; do
  last=$(jq -r '.metadata.id' <<<"$line")
  case "$(jq -r '.data.type' <<<"$line")" in
    toolApprovalRequested)   # or deny-tool-call "$obj" <tool-call-id> --memo "Use the read-only lookup instead."
      cadenya objectives approve-tool-call "$obj" "$(jq -r '.data.toolApprovalRequested.toolCallId' <<<"$line")" >/dev/null ;;
    assistantMessage)
      jq -r '.data.assistantMessage.content // empty' <<<"$line"
      [ "$(jq '.data.assistantMessage.toolCalls // [] | length' <<<"$line")" = 0 ] && done=turn ;;
    finalized|error|cancelled|timedOut)
      done=$(jq -r '.data.type' <<<"$line") ;;
  esac
done
exec 3<&-
pkill -f "stream-events $obj" || true
# An empty $done means the connection ended without a terminal event (load balancers cut streams after
# about 10 minutes): reopen from "$last" and keep going.

cadenya objectives create-feedback "$obj" --data-score 1 --data-comment "Accurate summary"
cadenya objectives continue "$obj" --message "Which one is most urgent?"   # resumes a STATE_WAITING objective
```

Related reads: `objectives list-tool-calls "$obj" --status TOOL_CALL_STATUS_WAITING_FOR_APPROVAL`, `objectives retrieve "$obj" --display json | jq .output` (structured output after `STATE_FINALIZED`), `objectives retrieve-diagnostics`, `objectives list-context-windows`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `invalid authentication token provided (http 403, code 7)`, reason `AUTH_TOKEN_INVALID`, even though `auth login` worked | `CADENYA_API_KEY` (or `--api-key`) is set and overrides the stored login | `cadenya auth status` shows the source; unset the variable or pass the right key |
| `admin role required (http 403, code 7)`, reason `ADMIN_ROLE_REQUIRED` | `workspace-admin` commands need the account admin role | use an admin profile, or the non-admin `workspaces list` |
| `not found (http 404, code 5)` on a resource you can see in the UI | wrong workspace, or an external ID that was never set | check `cadenya config list`; pass `--workspace-id`; use `external_id:` |
| `validation failed (http 400, code 3)` with `fieldViolations` | body rejected server-side; `field` names the proto path | fix that field; `--dry-run` to inspect what was sent |
| `agent must be published to create an objective` | agent is `STATE_DRAFT` | `cadenya agents publish <agent>` |
| `model_id must be a reference key in the form <provider-key-slug>.<model-slug> or a canonical model_ ID` | wrong `modelId` form | `ai-provider-keys list` for the slug, `models list --prefix …` for the model |
| `required flag(s) not set: --variation-selection-mode` on `agents update` | schema-required field enforced on update | pass the current value |
| `expected exactly 1 positional argument(s) (<id>), got 0` | missing positional | positionals come before flags: `retrieve <id> --workspace-id …` |
| `flag provided but not defined` | typo, or a flag that belongs to another arm/command | `cadenya schema <group> <command>` |
| stream prints nothing for a finished objective | no `--last-event-id`, so only new events are sent | `list-events --sort-order asc` for history, or resume from an ID |
| `--file: invalid YAML/JSON` | literal, `@path`, and `-` are the only forms; `-` may be used once per invocation | pass `-f @body.yml` or `-f -` |

## Related skills

- `cadenya-api`: wire-level conventions (IDs, field masks, errors, pagination, streaming, webhooks) and per-resource request shapes.
- `cadenya-typescript-sdk`: the same operations from code; the Go, Python, and Ruby SDKs ([cadenya-go](https://github.com/cadenya/cadenya-go), [cadenya-python](https://github.com/cadenya/cadenya-python), [cadenya-ruby](https://github.com/cadenya/cadenya-ruby)) are generated from the same API contract.
