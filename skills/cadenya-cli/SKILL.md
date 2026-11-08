---
name: cadenya-cli
description: Drives Cadenya from a terminal or shell script with the `cadenya` CLI. Covers logging in, picking a workspace, building request bodies from flags or YAML, creating tool sets and agents, running and streaming objectives, approving tool calls, paging through lists, and keeping workspace resources in `.cadenya/` YAML with `cadenya config plan`/`apply` for CI. Use when a task mentions the CLI or `cadenya` commands, shell automation against Cadenya, turning an API call into a command, or a CLI error such as `required flag(s) not set`, `not found (http 404, code 5)`, `AUTH_TOKEN_INVALID`, or `agent must be published to create an objective`. For calls from application code, use the SDK skills instead.
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

A person creates the account at https://app.cadenya.com/signup, and the Free plan needs no card. When there is no account yet, give your user that link, then run `cadenya auth login`. To start building before the user signs up, follow the `cadenya-start-without-account` skill: `cadenya workspaces create --temporary` (CLI 1.12.0 or later) makes a temporary workspace that the user claims later.

**Credential resolution, first match wins:** `--api-key` flag, then `CADENYA_API_KEY`, then the stored login, then this directory's `.cadenya/temporary.json` (a temporary workspace).

- Interactive machines: `cadenya auth login` runs a browser device flow (`--no-browser` prints the URL) and stores the credential in `~/.cadenya/credentials` (mode 0600). You pick which workspaces the login may reach on the approval page. The command waits until the code is approved, so show your user the approval link.
- CI and scripts: export `CADENYA_API_KEY` (an account API key from https://app.cadenya.com/account/apiKeys, assigned to the workspaces it reaches) and `CADENYA_WORKSPACE_ID`. Never put the key on the command line.
- `cadenya auth status` names the credential source in effect and lists the workspaces the login can reach; it exits 0 even when that credential is bad. `cadenya whoami --display json` is the pre-flight check that exits 1 on a rejected credential.
- `--profile <name>` on any command (including `auth login`) keeps separate logins and stored defaults.

**Workspace resolution, first match wins:** `--workspace-id`, then `CADENYA_WORKSPACE_ID`, then `cadenya config set workspace-id <id>`, then the login's single authorized workspace. Both accept a workspace ID (`workspace_…`) or its external ID (`development`).

```sh
cadenya workspaces list                       # what this credential can reach
cadenya config set workspace-id development   # per-profile default
cadenya config list                           # effective values and their sources
```

## Workspace configuration files

Keep tool sets, agents, variations, memory layers and widgets in the repository as YAML, one resource per file, and let the CLI make the workspace match:

```text
cadenya.yaml                    # settings: bundleKey (required here, via --bundle-key, or CADENYA_BUNDLE_KEY), workspaceId
.cadenya/
  toolSets/petstore.yaml
  toolSets/frontend/fetch-form-state.yaml   # a tool in a Bare or HTTP tool set
  memoryLayers/playbooks.yaml
  memoryLayers/playbooks/setup.yaml         # an entry in the playbooks layer
  agents/support.yaml
  agents/support/default.yaml               # a variation of the support agent
  widgets/support-chat.yaml
```

```sh
cadenya config validate          # local YAML and references, no API calls
cadenya config plan              # the create/update/delete/detach operations apply would run
cadenya config apply --dry-run   # same plan, nothing written
cadenya config apply             # make the workspace match .cadenya/
```

- Every resource gets the label `bundle_key=<bundleKey>`. Apply deletes every resource with that label whose file is gone, so a missing `agents/` directory deletes every agent in the bundle. An empty `.cadenya/` needs `--allow-empty`.
- Use one bundle key per repository and do not share it. Plan fails rather than adopt an existing resource that lacks the label.
- `-C <dir>` points at another repository root. `--output json` and `--report-file <path>` give machine-readable results. Apply is not transactional: it stops at the first failed request, so fix the cause and run it again.
- Without `state: published` in an agent file, apply leaves the agent's state alone, and new agents start as drafts.

The format is in the [bundle guide](https://github.com/cadenya/cadenya-cli/blob/main/docs/config-bundles.md), and the [GitHub Action](https://github.com/cadenya/cadenya-config-loader) runs the same commands in CI.

## Command map

Groups mirror API resources. Nested resources are subgroups (`agents variations`, `tool-sets tools`).

| Group | Commands |
| --- | --- |
| `auth` | `login`, `logout`, `status` |
| `config` | `set`, `get`, `unset`, `list`, `validate`, `plan`, `apply` |
| `whoami`, `profiles whoami` | the profile behind the credential |
| `accounts` | `retrieve`, `rotate-challenge-token`, `rotate-webhook-signing-key` |
| `workspaces` | `list`, `create --temporary` (a temporary workspace without an account), `claim-status` (`--wait`); see `cadenya-start-without-account` |
| `workspace-admin` | `list-account`, `create`, `retrieve`, `update`, `archive`, `list-members`, `add-member`, `remove-member`, `list-profiles` (admin role) |
| `api-keys` | `list`, `create`, `retrieve`, `update`, `delete`, `enable`, `disable`, `rotate`, `reveal`, `add-workspace`, `remove-workspace` (account keys) |
| `trusted-endpoints` | `list`, `create`, `retrieve`, `delete`, `verify --url <url>` (account-wide hosts tool sets may call; no workspace) |
| `ai-provider-keys` | `list`, `create`, `retrieve`, `update`, `delete` |
| `models` | `list`, `create`, `retrieve`, `update`, `enable`, `disable`, `swap-on-variations` |
| `tool-sets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive`, `list-events`, `list-usage`, `retrieve-open-api-spec` |
| `tool-sets tools` | `list`, `create`, `retrieve`, `update`, `delete`, `omit`, `restore` |
| `tool-sets secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `workspace-secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `agents` | `list`, `create`, `retrieve`, `update`, `delete`, `publish`, `unpublish`, `archive`, `unarchive`, `list-feedback`, `list-webhook-deliveries` |
| `agent-pools` | `list`, `create`, `retrieve`, `update`, `delete`, `activate`, `deactivate`, `archive`, `unarchive` (a group of agents assigned to a variation as one callable target) |
| `agents variations` | `list`, `create`, `retrieve`, `update`, `delete`, `add-assignment`, `remove-assignment`, `add-memory-layer`, `update-memory-layer`, `remove-memory-layer` |
| `agents schedules` | `list`, `create`, `retrieve`, `update`, `delete`, `pause`, `resume`, `archive` |
| `objectives` | `list`, `create`, `create-and-stream`, `retrieve`, `list-events`, `stream-events`, `continue` (`--enqueue`), `interrupt`, `cancel`, `compact`, `list-queued-actions`, `remove-queued-action`, `list-tool-calls`, `retrieve-tool-call`, `approve-tool-call`, `deny-tool-call`, `set-tool-call-content`, `list-tools`, `list-context-windows`, `retrieve-diagnostics`, `list-feedback`, `create-feedback` |
| `memory-layers` | `list`, `create`, `retrieve`, `update`, `delete` |
| `memory-layers entries` | `list`, `create`, `retrieve`, `update`, `delete` |
| `tenants` | `list`, `retrieve`, `delete`, `list-subjects` |
| `widgets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive` |
| `widget-sessions` | `list`, `create`, `retrieve`, `delete`, `revoke`, `delete-tenant` |
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

Rules, in priority order (deeper wins): `-f <path>` whole body (`-` for stdin), then `--<subtree> <doc>` documents, then individual flags.

- **Scalar fields are flags named by their wire path with the `metadata`/`spec` envelopes dropped.** `metadata.name` is `--name`, `spec.description` is `--description`, `defaultVariation.spec.modelConfig.modelId` is `--default-variation-model-id`. `cadenya schema` prints the `Path:` of every flag.
- **Maps are repeatable `KEY=VALUE`:** `--label team=docs --label env=dev`, `--mcp-header 'Authorization=Bearer {{ secrets.MCP_TOKEN }}'`. Untyped maps take `KEY:=JSON` for non-string values: `--system-prompt-data 'customer_name=Ada' --system-prompt-data 'tier:=3'`.
- **Lists repeat the flag:** `--permission objectives:manage --permission agents:read`.
- **Unions collapse onto their arms.** Setting `--mcp-url` selects the `mcp` adapter; `--adapter mcp` is only needed when no arm flag is set (`--adapter bare` has none). Same for `--openapi-url` vs `--openapi-upload-id`, and `--tool-set-id …` on `add-assignment` sets `type: toolSetId`.
- **Documents (`<doc>`)** take a YAML/JSON literal, `@path`, or `-` for stdin; a bare `spec.yml` is parsed as a YAML string, so write `@spec.yml`. Only `-f` takes a plain path. Only one input per invocation may read stdin. Plain string flags accept `@path` and `-` too, which keeps secret values out of shell history (`--value @token.txt`, `--value -`). Write `@@` for a literal leading `@`.
- **Body enums accept short forms:** `--variation-selection-mode random` sends `VARIATION_SELECTION_MODE_RANDOM`; `--help` lists them. `list` filters take the full wire value: `agents list --state STATE_PUBLISHED`.
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
- A flag inside an object with required fields needs those fields too: `--label` or `--external-id` on `update` needs `--name`, and `--model-temperature` on `agents variations update` needs `--model-id`. Pass the current values; the derived mask includes them harmlessly.

## Output, errors, exit codes

`--display json|yaml|table|extended` (root or per command). Most commands default to `table` (configured columns only), so **scripts pass `--display json`** before piping to `jq`. `delete`-style commands with no columns default to JSON. `extended` prints psql-style vertical records. Streams are NDJSON only and refuse any other mode, including a root `--display table`.

Errors go to stderr as the API's `google.rpc.Status`: `error: cadenya: <message> (http <status>, code <grpc-code>)` followed by the `details` list (`ErrorInfo.reason` such as `AUTH_TOKEN_INVALID`, or `BadRequest.fieldViolations[]` with `field` in snake_case proto form, for example `spec.model_config.model_id`). Nothing is written to stdout on error.

| Exit | Meaning |
| --- | --- |
| `0` | success |
| `1` | API or transport error (also an unknown flag) |
| `2` | usage error caught before any network I/O: missing positional, `required flag(s) not set`, `--strict` violations |
| `3` | the temporary workspace was claimed, so its key is revoked; the CLI removes `.cadenya/temporary.json` (log in instead) |
| `4` | `workspaces claim-status`: the temporary workspace expired |
| `130` | interrupted (Ctrl-C / SIGTERM), for example while following a stream |

`--debug` (or `CADENYA_DEBUG=1`) dumps every HTTP exchange to stderr with the credential header redacted.

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
cadenya ai-provider-keys list                     # EXTERNAL ID column is the provider-key slug (every account has getting-started-key)
cadenya models list --prefix anthropic            # EXTERNAL ID column is the model slug; --prefix matches name, external ID or ID

# 4. Agent with its default variation in one call. The variation's system prompt is a Liquid template
#    over system_prompt_data; first_user_message_template renders first_user_message_data.
cadenya agents create --name "Support Triager" --external-id support-triager \
  --variation-selection-mode random \
  --default-variation-name default --default-variation-external-id support-triager-default \
  --default-variation-model-id getting-started-key.anthropic-claude-sonnet-latest \
  --default-variation-system-prompt-template 'You triage support tickets for {{ system_prompt_data.customer_name }}.' \
  --default-variation-constraints-inactivity-timeout 3600s

# 5. Assign the tool set to the variation (tools are assigned to variations, not agents).
cadenya agents variations add-assignment support-triager support-triager-default --tool-set-id support-mcp

# 6. Publish. Objectives on a STATE_DRAFT agent fail with "agent must be published to create an objective".
cadenya agents publish support-triager
```

`agents create` returns the agent, not the variation; `agents variations list <agent>` shows it. To make the bootstrap re-runnable, gate each create on `retrieve <external-id>` (exit 1 on 404): a create with a duplicate external ID fails with `resource with the same identifier already exists (http 409, code 6)`. OpenAPI tool sets use `--openapi-url` (or `--openapi-upload-id` after `uploads create`), HTTP tool sets use `--http-base-url` plus `tool-sets tools create` per tool, and Bare tool sets (`--adapter bare`) park each call until you `set-tool-call-content`.

## Run an objective end to end

Default to `objectives create-and-stream`: one command creates the objective and streams its events, so no event is missed. `--external-id` is required and is the idempotency key. Rerunning with the same external ID attaches to the existing objective instead of starting another, and `--last-event-id` resumes after that event.

Facts that shape the loop:

- Each stdout line is NDJSON. The first is `{"type":"objective","objective":{…}}`, and every later line is `{"type":"event","event":{…}}` with the same shape as `stream-events` output (which has no envelope).
- Only durable `objevt_…` IDs are resume cursors. Heartbeats (`data.type: heartbeat`, `hb_…` IDs) and `--include-deltas` fragments (`dlt_…`) are not, so never save their IDs.
- The stream never closes on its own. Stop reading on a terminal event (`finalized`, `error`, `cancelled`, `timedOut`), or when a `stateChanged` event has `toState: OBJECTIVE_STATE_WAITING`: the turn is over, so `continue` the objective or let the inactivity timeout end it.
- `cancel` and `interrupt` are asynchronous. `interrupt` stops foreground work and leaves the objective `OBJECTIVE_STATE_WAITING`; `cancel` ends it. Poll `retrieve` for the state if you need to wait.

```sh
#!/usr/bin/env bash
set -euo pipefail
export CADENYA_WORKSPACE_ID=development
ext="ticket-4821"   # stable per unit of work: a rerun attaches instead of duplicating
obj="" last="" done=""

while [ -z "$done" ]; do   # reconnect loop: a dropped connection resumes from $last
  # Read in the main shell (a pipe would run the loop in a subshell) and stop the stream yourself.
  exec 3< <(cadenya objectives create-and-stream --agent-id support-triager --external-id "$ext" \
    --system-prompt-data customer_name=Ada --first-user-message "Summarize the open tickets." \
    ${last:+--last-event-id "$last"})
  while [ -z "$done" ] && IFS= read -r line <&3; do
    if [ "$(jq -r .type <<<"$line")" = objective ]; then obj=$(jq -r .objective.metadata.id <<<"$line"); continue; fi
    ev=$(jq -c .event <<<"$line")
    id=$(jq -r .metadata.id <<<"$ev"); [[ $id == objevt_* ]] && last=$id
    case "$(jq -r .data.type <<<"$ev")" in
      toolApprovalRequested)   # or: deny-tool-call "$obj" <tool-call-id> --memo "Use the read-only lookup instead."
        cadenya objectives approve-tool-call "$obj" "$(jq -r .data.toolApprovalRequested.toolCallId <<<"$ev")" >/dev/null ;;
      assistantMessage) jq -r '.data.assistantMessage.content // empty' <<<"$ev" ;;
      stateChanged) [ "$(jq -r .data.stateChanged.toState <<<"$ev")" = OBJECTIVE_STATE_WAITING ] && done=waiting ;;
      finalized|error|cancelled|timedOut) done=$(jq -r .data.type <<<"$ev") ;;
    esac
  done
  exec 3<&-
  pkill -f -- "--external-id $ext" || true   # the server never closes the stream; a killed stream exits 130
done

cadenya objectives create-feedback "$obj" --data-score 1 --data-comment "Accurate summary"
cadenya objectives continue "$obj" --message "Which one is most urgent?"   # needs OBJECTIVE_STATE_WAITING unless --enqueue
```

To follow an objective created elsewhere, use `objectives stream-events <objective-id> --last-event-id <objevt_…>`. Without `--last-event-id` it sends only events that arrive after you connect, and an invalid ID fails before the stream opens. `objectives create` (no stream) returns at once with `state: OBJECTIVE_STATE_PENDING`.

Related reads: `objectives list-events "$obj" --sort-order asc --display json` (history), `objectives list-tool-calls "$obj" --status TOOL_CALL_STATUS_WAITING_FOR_APPROVAL`, `objectives retrieve "$obj" --display json | jq .output` (structured output after `OBJECTIVE_STATE_FINALIZED`), `objectives retrieve-diagnostics`, `objectives list-context-windows`.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| ``missing credentials: pass --api-key, set CADENYA_API_KEY, or run `cadenya auth login` `` | no `--api-key`, no `CADENYA_API_KEY`, no stored login, no `.cadenya/temporary.json` | `cadenya auth login`, or set `CADENYA_API_KEY` to a key from https://app.cadenya.com/account/apiKeys |
| `invalid authentication token provided (http 403, code 7)`, reason `AUTH_TOKEN_INVALID` (HTTP 401 on stream commands), even though `auth login` worked | `CADENYA_API_KEY` (or `--api-key`) is set and overrides the stored login | `cadenya auth status` shows the source; unset the variable or pass the right key |
| `admin role required (http 403, code 7)`, reason `ADMIN_ROLE_REQUIRED` | `workspace-admin` commands need the account admin role | use an admin profile, or the non-admin `workspaces list` |
| `not found (http 404, code 5)` on a resource you can see in the UI | wrong workspace, or an external ID that was never set | check `cadenya config list`; pass `--workspace-id`; use `external_id:` |
| `validation failed (http 400, code 3)` with `fieldViolations` | body rejected server-side; `field` names the proto path | fix that field; `--dry-run` to inspect what was sent |
| `validation failed` with field `agent_id`: `agent must be published to create an objective` | agent is `STATE_DRAFT` | `cadenya agents publish <agent>` |
| `model_id must be a reference key in the form <provider-key-slug>.<model-slug> or a canonical model_ ID` | wrong `modelId` form | `ai-provider-keys list` for the slug, `models list --prefix …` for the model |
| `required flag(s) not set: --name` on `update --label …` | `metadata.name` is required whenever `metadata` is sent | pass the current name |
| `expected exactly 1 positional argument(s) (<id>), got 0` | missing positional | positionals come before flags: `retrieve <id> --workspace-id …` |
| `flag provided but not defined` | typo, or a flag that belongs to another arm/command | `cadenya schema <group> <command>` |
| stream prints nothing for a finished objective | no `--last-event-id`, so only new events are sent | `list-events --sort-order asc` for history, or resume from an ID |
| `--spec: expected an object (YAML mapping or JSON object)` | a document flag got a bare path, which parses as a string | `--spec @spec.yml`; only `-f` takes a plain path |
| `'-' (stdin) may supply at most one input per command` | two inputs set to `-` | read the others from `@path` |
| `streaming commands support only --display json` | root or command `--display` is not `json` | drop `--display` on stream commands |

## Related skills

- `cadenya-start-without-account`: a temporary workspace for a user with no account, its claim URL, and the errors around claiming.
- `cadenya-api`: wire-level conventions (IDs, field masks, errors, pagination, streaming, webhooks) and per-resource request shapes.
- `cadenya-typescript-sdk`, `cadenya-go-sdk`, `cadenya-python-sdk`, `cadenya-ruby-sdk`: the same operations from code.
