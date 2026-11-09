---
name: cadenya-cli
description: Drives Cadenya from a terminal, shell script, or CI with the `cadenya` CLI. Use when a task mentions the Cadenya CLI or `cadenya` commands, shell automation against Cadenya, turning an API call into a command, `.cadenya/` YAML with `cadenya config plan`/`apply`, or a CLI error such as `required flag(s) not set`, `not found (http 404, code 5)`, `AUTH_TOKEN_INVALID`, or `agent must be published to create an objective`. Covers login and workspace selection, request bodies from flags or YAML, creating Tool Sets and Agents, running and streaming objectives, approving tool calls, and paging lists. Not for application code (use the Cadenya SDK skills), and for a user with no account start with `cadenya-start-without-account`.
---

# Cadenya CLI

`cadenya` is a generated, one-to-one command surface over the Cadenya REST API: same resources, same JSON, same IDs. Look up a command's contract instead of guessing it:

```sh
cadenya schema                                    # every command with its one-line purpose
cadenya schema agents variations add-assignment   # one command's full contract
cadenya objectives create --help                  # the same flags, shorter
```

`cadenya schema <group> <command>` prints markdown: the usage line (`[...]...` marks repeatable flags), each positional with the ID forms it accepts, each flag with its wire `Path:`, whether it is required, its enum short forms, and for unions the `Arm:` it belongs to, plus JSON Schema for every document input (`--spec @spec.yml`, `-f body.yml`). Pipe it through `grep 'Path:'` for a flag-to-wire-path map when translating a JSON body from the API docs.

Loop for every create, update, or action command: read `cadenya schema`, build the command, check it with `--dry-run`, run it, then `retrieve` to confirm. The full command list is in [references/commands.md](references/commands.md). Wire conventions shared by every client (IDs, field masks, errors) are in the `cadenya-api` skill.

## Setup

```sh
brew install cadenya/tools/cadenya    # macOS/Linux; Windows: choco install cadenya
cadenya --version                     # binary release plus the API contract it was generated against
```

A person creates the account at https://app.cadenya.com/signup; the Free plan needs no card. With no account yet, give your user that link and then run `cadenya auth login`, or follow `cadenya-start-without-account` (`cadenya workspaces create --temporary`, CLI 1.12.0 or later) to build before they sign up.

**Credentials, first match wins:** `--api-key`, then `CADENYA_API_KEY`, then the stored login, then this directory's `.cadenya/temporary.json` (a temporary workspace).

- Interactive machines: `cadenya auth login` runs a browser device flow (`--no-browser` prints the URL), waits until the code is approved, and stores the credential in `~/.cadenya/credentials` (mode 0600). Show your user the approval link; they pick which workspaces the login may reach.
- CI and scripts: export `CADENYA_API_KEY` (an account API key from https://app.cadenya.com/account/apiKeys, assigned to the workspaces it reaches) and `CADENYA_WORKSPACE_ID`. Never put the key on the command line.
- `cadenya auth status` names the credential source in effect, and exits 0 even when that credential is bad. `cadenya whoami --display json` is the pre-flight check: it exits 1 on a rejected credential.
- `--profile <name>` on any command (including `auth login`) keeps separate logins and stored defaults.

**Workspace, first match wins:** `--workspace-id`, then `CADENYA_WORKSPACE_ID`, then `cadenya config set workspace-id <id>`, then the login's single authorized workspace. Each accepts a workspace ID (`workspace_…`) or its external ID (`development`). `cadenya workspaces list` shows what the credential reaches; `cadenya config list` shows effective values and their sources.

## Workspace configuration files

Keep Tool Sets, Agents, variations, memory layers and Widgets in the repository as YAML, one resource per file, and let the CLI make the workspace match:

```text
cadenya.yaml                    # settings: bundleKey (required here, via --bundle-key, or CADENYA_BUNDLE_KEY), workspaceId
.cadenya/
  toolSets/petstore.yaml
  toolSets/frontend/fetch-form-state.yaml   # a tool in a Bare or HTTP Tool Set
  memoryLayers/playbooks.yaml
  memoryLayers/playbooks/setup.yaml         # an entry in the playbooks memory layer
  agents/support.yaml
  agents/support/default.yaml               # a variation of the support Agent
  widgets/support-chat.yaml
```

- [ ] `cadenya config validate`: local YAML and references, no API calls.
- [ ] `cadenya config plan`: read the create/update/delete/detach operations, and check every delete.
- [ ] `cadenya config apply`: make the workspace match `.cadenya/` (`apply --dry-run` prints the same plan and writes nothing).
- [ ] Run `plan` again to confirm: it ends `Plan: 0 create, N update, 0 delete, 0 detach` (every existing resource is always an update; plan does not diff).

Gotchas:

- Every resource gets the label `bundle_key=<bundleKey>`. Apply deletes every resource with that label whose file is gone, so a missing `agents/` directory deletes every Agent in the bundle. An empty `.cadenya/` needs `--allow-empty`.
- Use one bundle key per repository. Plan fails rather than adopt an existing resource that lacks the label.
- Apply is not transactional: it stops at the first failed request, so fix the cause and run it again.
- Without `state: published` in an Agent file, apply leaves the Agent's state alone, and new Agents start as drafts.
- `-C <dir>` points at another repository root. `--output json` and `--report-file <path>` give machine-readable results.

The format is in the [bundle guide](https://github.com/cadenya/cadenya-cli/blob/main/docs/config-bundles.md), and the [GitHub Action](https://github.com/cadenya/cadenya-config-loader) runs the same commands in CI.

## Positional IDs

Path parameters are positionals in path order, minus the workspace, and they come before flags: `agents variations retrieve <agent-id> <id>`, `objectives approve-tool-call <objective-id> <tool-call-id>`. Every positional and `--workspace-id` accepts the canonical ID (`agent_…`), the bare external ID (`support-triager`), or `external_id:support-triager` (use that form when your external IDs look like Cadenya IDs).

## Building request bodies

Sources layer `-f <path>` (whole body, `-` for stdin), then `--<subtree> <doc>` documents, then individual flags; deeper wins.

- **Scalar flags are named by wire path with the `metadata`/`spec` envelopes dropped:** `metadata.name` is `--name`, `defaultVariation.spec.modelConfig.modelId` is `--default-variation-model-id`.
- **Maps are repeatable `KEY=VALUE`:** `--label team=docs --label env=dev`, `--mcp-header 'Authorization=Bearer {{ secrets.MCP_TOKEN }}'`. Untyped maps take `KEY:=JSON` for non-string values: `--system-prompt-data 'tier:=3'`.
- **Lists repeat the flag:** `--permission objectives:manage --permission agents:read`. Repeatable flags never split on commas.
- **Unions collapse onto their arms.** `--mcp-url` selects the `mcp` adapter; `--adapter` is needed only when no arm flag is set (`--adapter bare`). `--tool-set-id …` on `add-assignment` sets `type: toolSetId`.
- **Documents (`<doc>`)** take a YAML/JSON literal, `@path`, or `-`. A bare `spec.yml` parses as a YAML string, so write `@spec.yml`; only `-f` takes a plain path. Only one input per invocation may read stdin. Plain string flags accept `@path` and `-` too, which keeps secret values out of shell history (`--value @token.txt`). Write `@@` for a literal leading `@`.
- **Body enums accept short forms** (`--variation-selection-mode random`); `list` filters take the full wire value (`agents list --state STATE_PUBLISHED`).
- **Booleans take no separate value:** `--include-info` or `--include-info=false`. `--include-info false` is a usage error (`false` parses as a positional).

`--dry-run` prints the assembled body (YAML, or JSON with `--display json`) and exits without calling the API. Every command that takes a body has it; verb commands such as `publish` or `approve-tool-call` do not. Build once with flags, keep the file, then `-f` it:

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

`-f` drops fields the request does not accept (`id`, timestamps, `state`, `info`) with a warning, so `retrieve --display yaml`, edit, `update -f` round-trips. `--strict` turns that warning into a usage error.

## Updates

`update` derives `updateMask` from the flags and documents you pass, so only those fields change:

```sh
cadenya tool-sets update support-mcp --name "Support MCP (prod)" --label team=docs --dry-run
# metadata: {labels: {team: docs}, name: Support MCP (prod)}
# updateMask: metadata.labels,metadata.name
```

- `--update-mask metadata.name,spec.description` overrides the derived mask (camelCase, dotted).
- Maps and lists are replaced wholesale: to add one label, send every label.
- `-f` with a full document masks the whole `metadata` and `spec` subtrees, which is what a round-trip edit wants.
- A flag inside an object with required fields needs those fields too: `--label` or `--external-id` on `update` needs `--name`, and `--model-temperature` on `agents variations update` needs `--model-id`. Pass the current values.

## Lists and pagination

Every `list` takes `--limit`, `--cursor`, `--sort-order asc|desc` (creation time), and `--labels 'env=prod,team=ai'` (every pair must match), and usually `--prefix`, `--query`, and a state filter. `--include-info` populates the computed `info` block and costs more rate limit.

One page per call. With `--display json` the page is `{"items": [...], "nextCursor": "..."}`, and an empty or missing `nextCursor` means the last page. In `table` mode the cursor goes to stderr as `next cursor: …`.

```sh
cursor=""
while :; do
  page=$(cadenya agents list --limit 50 --display json ${cursor:+--cursor "$cursor"})
  jq -r '.items[].metadata.externalId' <<<"$page"
  cursor=$(jq -r '.nextCursor // ""' <<<"$page")
  [ -z "$cursor" ] && break
done
```

## Output, errors, exit codes

Most commands default to `--display table`, so **scripts pass `--display json`** before piping to `jq`. Delete-style commands with no columns default to JSON. `yaml` and `extended` (vertical records) also exist. Stream commands print NDJSON only and refuse any other mode, including a root `--display table`.

Errors go to stderr as the API's `google.rpc.Status`: `error: cadenya: <message> (http <status>, code <grpc-code>)`, then the `details` list (`ErrorInfo.reason` such as `AUTH_TOKEN_INVALID`, or `BadRequest.fieldViolations[]` whose `field` is the snake_case proto path, for example `spec.model_config.model_id`). Nothing reaches stdout on error. Symptom-by-symptom fixes are in [references/troubleshooting.md](references/troubleshooting.md).

| Exit | Meaning |
| --- | --- |
| `0` | success |
| `1` | API or transport error (also an unknown flag) |
| `2` | usage error caught before any network I/O: missing positional, `required flag(s) not set`, `--strict` violations |
| `3` | the temporary workspace was claimed and its key revoked; the CLI removes `.cadenya/temporary.json` (log in instead) |
| `4` | `workspaces claim-status`: the temporary workspace expired |
| `130` | interrupted (Ctrl-C / SIGTERM) |

`--debug` (or `CADENYA_DEBUG=1`) dumps every HTTP exchange to stderr with the credential header redacted.

## Bootstrap a Tool Set and an Agent

- [ ] Workspace secret, referenced later as `{{ secrets.MCP_TOKEN }}`. Read the value from a file, not the command line. Create it before the Tool Set so the create can check the MCP source; while a referenced secret is missing, that check is skipped.
- [ ] Tool Set, built with `--dry-run` first. Verify: `tool-sets tools list support-mcp --display json` lists the synced tools once the sync has run.
- [ ] Model ID from `models list`. Never hardcode a model slug: which models exist depends on the account's provider keys.
- [ ] Agent with its default variation. Verify: `agents variations list support-triager`.
- [ ] Assign the Tool Set to the variation (tools are assigned to variations, not Agents).
- [ ] Publish. Verify: `agents retrieve support-triager --display json | jq -r .state` prints `STATE_PUBLISHED`.

```sh
export CADENYA_WORKSPACE_ID=development

cadenya workspace-secrets create --name MCP_TOKEN --value @mcp-token.txt

# Every synced tool requires approval; drop --mcp-tool-approvals-always to auto-run them.
cadenya tool-sets create --name "Support MCP" --external-id support-mcp \
  --mcp-url https://mcp.example.com/mcp \
  --mcp-header 'Authorization=Bearer {{ secrets.MCP_TOKEN }}' \
  --mcp-tool-approvals-always
cadenya tool-sets tools list support-mcp --display json | jq -r '.items[].metadata.name'

# Pick an enabled model; add --query <text> to match by name. Use its canonical model_ ID.
cadenya models list --state STATE_ENABLED --display json | jq -r '.items[] | [.metadata.id, .metadata.name] | @tsv'
model=$(cadenya models list --state STATE_ENABLED --limit 1 --display json | jq -r '.items[0].metadata.id // empty')
: "${model:?no enabled model in this workspace}"

# The system prompt is a Liquid template over system_prompt_data.
cadenya agents create --name "Support Triager" --external-id support-triager \
  --default-variation-name default --default-variation-external-id support-triager-default \
  --default-variation-model-id "$model" \
  --default-variation-system-prompt-template 'You triage support tickets for {{ system_prompt_data.customer_name }}.' \
  --default-variation-constraints-inactivity-timeout 3600s
cadenya agents variations list support-triager

cadenya agents variations add-assignment support-triager support-triager-default --tool-set-id support-mcp
cadenya agents publish support-triager   # on a STATE_DRAFT Agent, objectives create fails with "agent must be published to create an objective"; create-and-stream says only "validation failed"
cadenya agents retrieve support-triager --display json | jq -r .state
```

- `agents create` returns the Agent, not the variation. Omitting `--default-variation-model-id` uses the workspace default model, and fails if none is configured.
- To make the bootstrap re-runnable, gate each create on `retrieve <external-id>` (exit 1 on 404). A duplicate external ID fails with `resource with the same identifier already exists (http 409, code 6)`.
- OpenAPI Tool Sets use `--openapi-url` (or `--openapi-upload-id` after `uploads create`). HTTP Tool Sets use `--http-base-url` plus `tool-sets tools create` per tool. Bare Tool Sets (`--adapter bare`) park each call until you `set-tool-call-content`.

## Run an objective

Default to `objectives create-and-stream`. It creates the objective and streams its events on one connection, so no event is missed, and **the stream ends on its own** once the objective reaches `OBJECTIVE_STATE_WAITING` (the turn is over) or a terminal state. `--external-id` is required and is the idempotency key: rerunning with the same external ID attaches to the existing objective instead of creating another, and `--last-event-id` then resumes after that event. An attach without `--last-event-id` sends only new events, so approve anything already pending (`list-tool-calls --status TOOL_CALL_STATUS_WAITING_FOR_APPROVAL`) or the stream waits on it.

- Each stdout line is NDJSON. The first is `{"type":"objective","objective":{…}}`; every later line is `{"type":"event","event":{…}}`.
- The end-of-turn signal is a `stateChanged` event with `toState: OBJECTIVE_STATE_WAITING`. Terminal states are `OBJECTIVE_STATE_FINALIZED`, `OBJECTIVE_STATE_FAILED`, `OBJECTIVE_STATE_CANCELLED`, and `OBJECTIVE_STATE_TIMED_OUT`.
- Only durable `objevt_…` IDs are resume cursors. Heartbeats (`hb_…`) and `--include-deltas` fragments (`dlt_…`) are not; resuming from one fails with `Last-Event-ID must be a persisted objevt_ event ID`.
- Connections are cut after about 10 minutes. The CLI reconnects by itself from the last event ID it saw (up to 5 attempts). If the command still exits before the turn ends, rerun it with `--last-event-id` set to the last `objevt_` ID.
- `continue` needs `OBJECTIVE_STATE_WAITING` unless you pass `--enqueue`. `cancel` and `interrupt` are asynchronous: `interrupt` stops foreground work and leaves the objective WAITING (PENDING when `--enqueue` messages are queued), and `cancel` ends it.

```sh
#!/usr/bin/env bash
set -euo pipefail
export CADENYA_WORKSPACE_ID=development
ext="ticket-4821"   # stable per unit of work: a rerun attaches instead of duplicating
obj="" last="" state="" opened=""

# Stream one turn: create (or rejoin) the objective and read until the stream ends.
turn() {
  state=""
  for _ in 1 2 3 4 5; do
    opened=""
    while IFS= read -r line; do
      if [ "$(jq -r .type <<<"$line")" = objective ]; then   # current state too: an attach to a settled objective sends no events
        opened=1 obj=$(jq -r .objective.metadata.id <<<"$line") state=$(jq -r .objective.state <<<"$line"); continue
      fi
      ev=$(jq -c .event <<<"$line")
      id=$(jq -r .metadata.id <<<"$ev"); [[ $id == objevt_* ]] && last=$id
      case "$(jq -r .data.type <<<"$ev")" in
        toolApprovalRequested)   # or: deny-tool-call "$obj" <tool-call-id> --memo "Use the read-only lookup instead."
          cadenya objectives approve-tool-call "$obj" "$(jq -r .data.toolApprovalRequested.toolCallId <<<"$ev")" </dev/null >/dev/null ;;
        assistantMessage) jq -r '.data.assistantMessage.content // empty' <<<"$ev" ;;
        stateChanged) state=$(jq -r .data.stateChanged.toState <<<"$ev") ;;
      esac
    done < <(cadenya objectives create-and-stream --agent-id support-triager --external-id "$ext" \
      --system-prompt-data customer_name=Ada --first-user-message "Summarize the open tickets." \
      ${last:+--last-event-id "$last"})
    [ -n "$opened" ] || return 1   # rejected before streaming (draft Agent, auth): the error is on stderr
    case "$state" in OBJECTIVE_STATE_PENDING|OBJECTIVE_STATE_RUNNING|OBJECTIVE_STATE_INTERRUPTING) ;; *) return 0 ;; esac
  done
  echo "stream ended before the turn did (last event $last)" >&2; return 1
}

turn
[ "$state" = OBJECTIVE_STATE_WAITING ] || { echo "objective ended: $state" >&2; exit 1; }
cadenya objectives create-feedback "$obj" --data-score 1 --data-comment "Accurate summary"
cadenya objectives continue "$obj" --message "Which one is most urgent?" >/dev/null
turn   # same external ID plus --last-event-id: streams the next turn and ends at the next WAITING
```

To follow an objective created elsewhere, use `objectives stream-events <objective-id> --last-event-id <objevt_…>`. Unlike create-and-stream, **`stream-events` never closes on its own**: stop reading at the end-of-turn signal and kill the process (it exits 130). Without `--last-event-id` it sends only events that arrive after you connect. `objectives create` (no stream) returns at once with `state: OBJECTIVE_STATE_PENDING`.

Related reads: `objectives list-events "$obj" --sort-order asc --display json` (history), `objectives list-tool-calls "$obj" --status TOOL_CALL_STATUS_WAITING_FOR_APPROVAL`, `objectives retrieve "$obj" --display json | jq .output` (structured output after `OBJECTIVE_STATE_FINALIZED`), `objectives retrieve-diagnostics`, `objectives list-context-windows`.

## Related skills

- `cadenya-start-without-account`: a temporary workspace for a user with no account, its claim URL, and the errors around claiming.
- `cadenya-api`: wire-level conventions (IDs, field masks, errors, pagination, streaming, webhooks) and per-resource request shapes.
- `cadenya-typescript-sdk`, `cadenya-go-sdk`, `cadenya-python-sdk`, `cadenya-ruby-sdk`: the same operations from code.
