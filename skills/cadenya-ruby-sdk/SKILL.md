---
name: cadenya-ruby-sdk
description: Build Cadenya integrations with the official Ruby SDK, the `cadenya` gem (Ruby 3.1+, Faraday, typed model classes, Enumerable pages). Covers client setup, resource method names, snake_case request hashes, pagination, `Cadenya::APIError` handling, SSE objective event streams, and Standard Webhooks verification. Use when writing or debugging Ruby or Rails code that requires `cadenya`, when a Ruby service needs to create tool sets, agents, or objectives, or when hitting `Cadenya::APIError`, `missing workspaceId`, `ArgumentError … must not be blank`, or `stream already consumed`.
---

# Cadenya Ruby SDK usage

## Overview

The `cadenya` gem is generated from the Cadenya OpenAPI contract, so resources, methods, field names, and enum values match the REST API one-to-one: `client.<resource>.<method>(...)`. Every signature is in the gem's `api.md`; response models live under `Cadenya::Types`. The client is synchronous.

For wire conventions shared by every client (IDs and external IDs, field masks, error codes, pagination, streaming semantics, webhooks) see the `cadenya-api` skill. This skill covers what is specific to Ruby.

## Install and construct

```sh
gem install cadenya          # or: gem "cadenya" in the Gemfile
```

```ruby
require "cadenya"

client = Cadenya::Client.new                                            # reads env
client = Cadenya::Client.new(api_key: key, workspace_id: "development", max_retries: 2)
```

| Argument | Env fallback | Notes |
| --- | --- | --- |
| `api_key:` | `CADENYA_API_KEY` | required; missing everywhere raises `ArgumentError` |
| `workspace_id:` | `CADENYA_WORKSPACE_ID` | `workspace_…` or the external ID; default for every workspace-scoped call |
| `base_url:` | `CADENYA_BASE_URL` | `https://api.cadenya.com` |
| `webhook_secret:` | `CADENYA_WEBHOOK_SECRET` | for `client.unwrap_webhook` |
| `max_retries:` | | 0, clamped to 0 to 10 |
| `connection:` | | your own `Faraday::Connection` (its timeouts win); then `stream_transport:` is required for `stream_events` |

An argument passed explicitly but blank raises `ArgumentError` instead of falling back to env. The SDK-owned connection uses a 60-second timeout; override per call with `request_options: { timeout: 5 }`.

## Account and API key

- A person creates the account at https://app.cadenya.com/signup, and the Free plan needs no card. When there is no key yet, give your user that link.
- The API keys page, https://app.cadenya.com/account/apiKeys, lists the account's keys. Sign-up creates a default key that reaches every workspace. Set the key as `CADENYA_API_KEY`: the SDK reads its options and the environment, never the CLI's stored login.
- `client.profiles.whoami.default_workspace.id` is the default workspace ID, the value for `CADENYA_WORKSPACE_ID`, and `cadenya workspaces list` lists the others.
- From a terminal, `cadenya auth login` signs in through the browser with a one-time code (see `cadenya-cli`).
- Keep tool sets, agents, variations, memory layers and widgets as YAML files in `.cadenya/` next to a `cadenya.yaml`, and apply them with `cadenya config apply` ([format](https://cadenya.com/docs/config-files), [GitHub Action](https://github.com/cadenya/cadenya-config-loader)). That keeps the setup in the repository instead of in a one-off provisioning script.

## Resources and method names

Method = operation verb with the resource words removed, snake_case; `Get` is `retrieve`. The resource's own ID is positional, parent IDs first for nested resources; body and query fields are keyword arguments. Workspace-scoped methods take `workspace_id:`. Every method also accepts `request_options:` (allowed keys `headers`, `timeout`, `max_retries`, `reconnect`; anything else raises), which the gem's `api.md` omits from signatures.

```ruby
client.agents.retrieve(id)
client.agents.variations.retrieve(agent_id, id)
client.objectives.approve_tool_call(objective_id, tool_call_id)
client.objectives.continue(objective_id, message: "…")
```

| Accessor | Notable methods |
| --- | --- |
| `accounts` | `retrieve`, `rotate_challenge_token`, `rotate_webhook_signing_key` |
| `profiles` | `whoami` |
| `workspaces` | `list`, `retrieve_temporary` |
| `trusted_endpoints` | `list`, `create`, `retrieve`, `delete`, `verify` (account level) |
| `workspace_admin` | `list_account`, `create`, `retrieve`, `update`, `archive`, `list_members`, `add_member`, `remove_member`, `list_profiles` |
| `api_keys` | `list`, `create`, `retrieve`, `update`, `delete`, `enable`, `disable`, `rotate`, `reveal`, `add_workspace`, `remove_workspace` (account keys) |
| `ai_provider_keys` | CRUD |
| `models` | `list`, `create`, `retrieve`, `update`, `enable`, `disable`, `swap_on_variations` (no `delete`) |
| `tool_sets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive`, `list_events`, `list_usage`, `retrieve_open_api_spec` |
| `tool_sets.tools` | `list`, `create`, `retrieve`, `update`, `delete`, `omit`, `restore` |
| `tool_sets.secrets`, `workspace_secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `agents` | `list`, `create`, `retrieve`, `update`, `delete`, `publish`, `unpublish`, `archive`, `unarchive`, `list_feedback`, `list_webhook_deliveries` |
| `agents.variations` | `list`, `create`, `retrieve`, `update`, `delete`, `add_assignment`, `remove_assignment`, `add_memory_layer`, `update_memory_layer`, `remove_memory_layer` |
| `agents.schedules` | CRUD, `pause`, `resume`, `archive` |
| `agent_pools` | CRUD, `activate`, `deactivate`, `archive`, `unarchive` |
| `objectives` | `list`, `create`, `create_and_stream`, `retrieve`, `list_events`, `stream_events`, `continue`, `interrupt`, `cancel`, `compact`, `list_queued_actions`, `remove_queued_action`, `list_tool_calls`, `retrieve_tool_call`, `approve_tool_call`, `deny_tool_call`, `set_tool_call_content`, `list_tools`, `list_context_windows`, `retrieve_diagnostics`, `list_feedback`, `create_feedback` |
| `memory_layers`, `memory_layers.entries` | CRUD |
| `tenants` | `list`, `retrieve`, `delete`, `list_subjects` |
| `widgets` | CRUD, `archive`, `unarchive` |
| `widget_sessions` | `list`, `create`, `retrieve`, `delete`, `revoke`, `delete_tenant` |
| `uploads` | `create`, `retrieve` |
| `tool_search` | `search_or_sets` |

## Request bodies

Body fields are keyword arguments (`metadata:`, `spec:`, `default_variation:`, `agent_id:`); nested objects are hashes with symbol or string keys, or `Cadenya::Types::*` objects from a previous response.

- **Write snake_case keys.** The gem translates known keys to wire names (`system_prompt_template` → `systemPromptTemplate`); camelCase keys pass through too, but supplying both spellings of one field raises. Your own data inside free-form fields (`system_prompt_data`, `headers`, `labels`, `parameters`, `output_definition`) is never rewritten.
- Unions carry a `type` tag naming the populated key: `{ type: "mcp", mcp: {...} }`, `{ type: "toolSetId", tool_set_id: "..." }`. Tag values stay camelCase.
- Read-only keys on request types are dropped silently, so a fetched object's `to_h` can be edited and sent back. `nil` keyword arguments are omitted; a `nil` inside a hash is sent as JSON `null`.

```ruby
# Tool set. Secrets interpolate as {{ secrets.NAME }} (workspace or tool set secret).
tool_set = client.tool_sets.create(
  metadata: { name: "Support MCP", external_id: "support-mcp" },
  spec: { adapter: { type: "mcp", mcp: {
    url: "https://mcp.example.com/mcp",
    headers: { "Authorization" => "Bearer {{ secrets.MCP_TOKEN }}" },
    tool_approvals: { type: "always", always: true }   # every synced tool needs approval
  } } }
)

# Agent plus its default variation in one call. variation_selection_mode defaults to VARIATION_SELECTION_MODE_WEIGHTED.
agent = client.agents.create(
  metadata: { name: "Support Triager", external_id: "support-triager" },
  spec: { variation_selection_mode: "VARIATION_SELECTION_MODE_RANDOM" },
  default_variation: {
    metadata: { name: "default", external_id: "support-triager-default" },
    spec: {
      system_prompt_template: "You triage support tickets for {{ system_prompt_data.customer_name }}.",
      model_config: { model_id: "getting-started-key.anthropic-claude-sonnet-latest" }, # "<provider-key-slug>.<model-slug>" or model_…
      constraints: { max_tool_calls: 20, inactivity_timeout: "3600s" } # durations are strings
    }
  }
)

# Assignments: add_assignment and remove_assignment take their union body as body:. Tools attach to variations, not agents.
client.agents.variations.add_assignment(
  agent.metadata.id, variation_id,
  body: { type: "toolSetId", tool_set_id: tool_set.metadata.id }
)

# Objective
objective = client.objectives.create(
  agent_id: "external_id:support-triager",
  system_prompt_data: { customer_name: "Ada" },
  first_user_message: "Summarize the open tickets.",
  metadata: { external_id: "ticket-4821", labels: { source: "api" } }
)
```

Other adapters: `{ type: "openapi", openapi: { type: "url", url: ... } }` (or `{ type: "uploadId", upload_id: ... }`), `{ type: "http", http: { base_url: ... } }`, `{ type: "bare", bare: {} }`. The server rejects `${NAME}` (`legacy dollar references are not supported`), even where API doc comments still show it; write `{{ secrets.NAME }}`. Create the secret before the tool set: the create loads the source live with the resolved headers and fails if it is unreachable or lists no tools, and a header naming a secret that does not exist yet skips that check, so mistakes surface later at sync.

Responses are typed objects with snake_case readers and `to_h`: `agent.metadata.external_id`, `objective.state`, `event.data.type`. Enums are strings (`"STATE_PUBLISHED"`); timestamps are `Time`.

## Reads and pagination

List methods return a `Cadenya::Page` (Enumerable): `items`, `next_cursor`, `next_page?`, `next_page`, and `each`/`map`/`find` walk every page (`auto_paging_each` is an alias).

```ruby
client.agents.list(labels: "env=prod", limit: 50).each { |agent| ... }
page = client.objectives.list_events(objective_id, sort_order: "asc")
```

## Updates

`update` takes `metadata:`, `spec:`, and `update_mask:` (a comma-separated string of camelCase paths). Only masked paths change; maps and lists are replaced whole.

```ruby
client.agents.update(agent_id, metadata: { name: "Support Triager v2" }, update_mask: "metadata.name")
```

## Errors

| Class | When | Readers |
| --- | --- | --- |
| `Cadenya::APIError` | 4xx/5xx after retries | `status_code`, `code` (google.rpc), `message`, `details` |
| `Cadenya::APIConnectionError` | transport failure | |
| `Cadenya::APIResponseError` | 2xx with empty, `null`, or malformed JSON; unfollowed redirect | `status_code`, `body` |

```ruby
begin
  client.agents.retrieve("external_id:missing")
rescue Cadenya::APIError => e
  case e.status_code
  when 404 then ... # wrong workspace, or external ID never set
  when 403 then ... # key lacks scope; e.details&.first&.dig("reason") names it (stream-endpoint errors carry no details)
  when 400 then ... # e.details holds BadRequest fieldViolations with proto paths such as spec.model_config.model_id
  else raise
  end
end
```

## Retries and per-request options

Retries default to 0 and only ever apply to GET/HEAD/PUT/DELETE (408, 409, 429, 5xx, transport errors), honoring `Retry-After`. `max_retries:` on the client enables them; `request_options: { max_retries: n }` on a single call opts a POST or PATCH in. Streams never retry.

## Streaming objective events

Semantics you must code around:

- `stream_events` without `last_event_id:` delivers only events created after the connection opens. With it, the server replays everything after that ID, then goes live.
- `stream_events` never ends on its own. Call `stream.close` when you see a terminal event (`finalized`, `error`, `cancelled`, `timedOut`); `each` then returns cleanly.
- An `assistantMessage` with empty `tool_calls` ends the turn; the objective is `OBJECTIVE_STATE_WAITING` until you `continue` it or the inactivity timeout fires.
- A stream is single-use (`stream already consumed`). Mid-stream transport drops reconnect from `stream.last_event_id` (5 attempts per outage); `request_options: { reconnect: false }` surfaces them as `APIConnectionError` so you can resume yourself.
- A replayed `toolApprovalRequested` for a call you already approved makes the approve call fail with 400 (code 9, not waiting for approval); treat that as already handled.
- A clean end of stream (load balancers cut connections after about 10 minutes) returns from `each` with no terminal event and no reconnect. Checkpoint on `stream.last_event_id` and reopen from it in an outer loop until you have seen a terminal event. Not on `event.metadata.id`: `heartbeat` events (`hb_…`) and deltas (`dlt_…`, with `include_deltas: true`) carry IDs the server will not accept as a resume cursor; only durable `objevt_…` IDs advance `stream.last_event_id`.

```ruby
handle = lambda do |event|                         # true when the turn or objective is over
  data = event.data                                # discriminated on data.type; payload sits under the snake_case key
  case data.type
  when "toolApprovalRequested"
    client.objectives.approve_tool_call(objective_id, data.tool_approval_requested.tool_call_id)
    false
  when "assistantMessage"
    puts data.assistant_message.content if data.assistant_message.content
    Array(data.assistant_message.tool_calls).empty?
  when "finalized"
    puts data.finalized.output.inspect
    true
  when "error", "cancelled", "timedOut" then true
  else false                                       # heartbeat, toolCalled, stateChanged, ...
  end
end

last_event_id = nil
client.objectives.list_events(objective_id, sort_order: "asc").each do |event|
  handle.(event); last_event_id = event.metadata.id
end

stream = client.objectives.stream_events(objective_id, last_event_id: last_event_id)
stream.each { |event| stream.close if handle.(event) }
```

To start an objective and watch it in one request, use `create_and_stream` (same arguments as `create`, plus `include_deltas:`; `metadata: { external_id: }` is required and makes retries attach to the same objective). Each item has `type` `"objective"` (first, `item.objective`) or `"event"` (`item.event`, the same event as above), and the server ends this stream itself once the objective is waiting or terminal.

`stream.each_event` yields `Cadenya::ServerSentEvent` envelopes (`event`, `data`, `id`); `stream.last_event_id` is the resume checkpoint. Housekeeping frames (`open`, `ping`) are skipped. `close` is safe from another thread and unblocks a parked read.

## Webhooks

```ruby
# Rails: request.raw_post is the untouched body; a re-serialized body fails verification.
# Pass a plain hash: ActionDispatch's request.headers enumerates CGI keys (HTTP_WEBHOOK_ID) and fails.
headers = %w[webhook-id webhook-timestamp webhook-signature].to_h { |h| [h, request.headers[h]] }
event = client.unwrap_webhook(request.raw_post, headers)   # uses webhook_secret / CADENYA_WEBHOOK_SECRET
# event.type is "objective_event.tool_approval_requested" etc.; event.data.objective.id is the objective,
# event.data.objective_event.data.type the event kind (same union as the stream)
```

Standard Webhooks: headers `webhook-id`, `webhook-timestamp`, `webhook-signature` (`v1,<base64>`), HMAC-SHA256 over `id.timestamp.body`, secret `whsec_…` (the account's `webhookEventsHmacSecret`), 5-minute tolerance. `Cadenya::Webhooks.verify(secret, payload, headers, tolerance_seconds: 300)` checks without decoding; failures raise `Cadenya::WebhookVerificationError`. Rack-style array header values are accepted.

## Logging

No built-in logger. Pass `connection:` with Faraday's logger middleware (and a `stream_transport:`), or wrap calls yourself.

## End to end

```ruby
client = Cadenya::Client.new(workspace_id: "development")

client.workspace_secrets.create(metadata: { name: "MCP_TOKEN" }, spec: { value: ENV.fetch("MCP_TOKEN") })
model = client.models.list(prefix: "claude", state: "STATE_ENABLED", limit: 1).items.first or raise "no enabled model matches"
# … tool_set and agent as in "Request bodies", with model_config: { model_id: model.metadata.id } …

variation = client.agents.variations.list(agent.metadata.id, limit: 1).items.first   # create returns the agent only
client.agents.variations.add_assignment(agent.metadata.id, variation.metadata.id,
                                        body: { type: "toolSetId", tool_set_id: tool_set.metadata.id })
client.agents.publish(agent.metadata.id)   # objectives on a STATE_DRAFT agent are rejected

objective = client.objectives.create(agent_id: agent.metadata.id,
                                     system_prompt_data: { customer_name: "Ada" },
                                     first_user_message: "Summarize the open tickets.")
# … stream as above …
client.objectives.create_feedback(objective.metadata.id, metadata: {}, data: { score: 1.0, comment: "Accurate summary" })
client.objectives.continue(objective.metadata.id, message: "Which one is most urgent?")
```

## Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| `missing workspaceId` | no client default and no `workspace_id:` | `CADENYA_WORKSPACE_ID`, `workspace_id:` on the client, or per call |
| 400 `agent must be published to create an objective` | agent is `STATE_DRAFT` | `client.agents.publish(id)` |
| 400 on `spec.model_config.model_id` | wrong `model_id` form | `model_…` from `models.list`, or `<provider-key-slug>.<model-slug>` |
| 429 creating a variation | the plan caps non-archived variations across the whole account, every workspace included | archive unused variations, or update the existing one |
| stream yields nothing for a finished objective | no `last_event_id:` | replay with `list_events(sort_order: "asc")`, then stream from the last ID |
| `stream already consumed` | iterated a stream twice | open a new one with `last_event_id: stream.last_event_id` |
| `each` never returns | the server keeps the stream open | `stream.close` on terminal events |
| `ArgumentError: streaming with a caller-supplied connection: requires an explicit stream_transport:` | custom `connection:` without a stream transport | pass `stream_transport:` or drop `connection:` |
| `ArgumentError: unknown request_options key` | typo in `request_options:` | only `headers`, `timeout`, `max_retries`, `reconnect` |
| POST silently not retried | retries apply to idempotent methods only | `request_options: { max_retries: n }` |
| header secret not resolved | `${NAME}` syntax | use `{{ secrets.NAME }}` |
| `agents.create` result has no variation ID | `Agent#info` has `variation_count`, not IDs | `agents.variations.list(agent_id)` |

## Related skills

- `cadenya-api`: wire conventions and per-resource request shapes.
- `cadenya-cli`: the same operations from a terminal; `cadenya … --dry-run` prints the exact JSON body the SDK sends.
