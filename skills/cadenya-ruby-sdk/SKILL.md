---
name: cadenya-ruby-sdk
description: Writes and debugs Ruby or Rails code that uses Cadenya's `cadenya` gem. Covers `Cadenya::Client` setup, resource method names, snake_case request hashes, pagination, `Cadenya::APIError` handling, objective streams (`create_and_stream`, `stream_events`), tool call approvals, and webhook verification with `unwrap_webhook`. Use when Ruby code requires `cadenya`, or on `Cadenya::APIError`, `missing workspaceId`, `… must not be blank`, or `stream already consumed`. Not for raw HTTP (`cadenya-api`), the terminal (`cadenya-cli`), or other languages (`cadenya-typescript-sdk`, `cadenya-python-sdk`, `cadenya-go-sdk`).
---

# Cadenya Ruby SDK

The `cadenya` gem (Ruby >= 3.1) is generated from the Cadenya OpenAPI contract. Resources, methods, fields, and enum values match the REST API one-to-one as `client.<resource>.<method>(...)`. The gem's `api.md` lists every signature, and response models live under `Cadenya::Types`. The client is synchronous. Wire conventions shared by every client (IDs and external IDs, field masks, error codes, webhooks) are in the `cadenya-api` skill.

## Client

```ruby
require "cadenya"   # gem "cadenya"

client = Cadenya::Client.new                                # reads the environment
client = Cadenya::Client.new(workspace_id: "development", max_retries: 2)
```

| Argument | Env fallback | Notes |
| --- | --- | --- |
| `api_key:` | `CADENYA_API_KEY` | required |
| `workspace_id:` | `CADENYA_WORKSPACE_ID` | `workspace_…` or the external ID; default for every workspace-scoped call |
| `base_url:` | `CADENYA_BASE_URL` | `https://api.cadenya.com` |
| `webhook_secret:` | `CADENYA_WEBHOOK_SECRET` | for `client.unwrap_webhook` |
| `max_retries:` | | default 0, clamped to 0..10 |
| `connection:` | | your own `Faraday::Connection` (its timeouts win); streaming then also needs `stream_transport:` |

Keep the API key in `CADENYA_API_KEY`, never in code. A missing key raises `ArgumentError`, and so does an argument passed explicitly as blank (`workspace_id must not be blank`); a blank never falls back to the environment. The SDK's own connection uses a 60-second timeout. Override it per call with `request_options: { timeout: 5 }`.

## Account and API key

- A person creates the account at https://app.cadenya.com/signup; the Free plan needs no card. With no key yet, give your user that link.
- https://app.cadenya.com/account/apiKeys lists the account's keys. Sign-up creates a default key that reaches every workspace. The SDK reads only its arguments and the environment, never the CLI's stored login.
- `client.profiles.whoami.default_workspace.id` is the value for `CADENYA_WORKSPACE_ID`. `cadenya workspaces list` lists the others.
- Keep Tool Sets, Agents, variations, memory layers and Widgets as YAML in `.cadenya/` next to a `cadenya.yaml`, and apply them with `cadenya config apply` ([format](https://cadenya.com/docs/config-files), [GitHub Action](https://github.com/cadenya/cadenya-config-loader)), instead of a one-off provisioning script.

## Resources and method names

A method is the operation verb with the resource words removed, in snake_case; `Get` is `retrieve`. The resource's own ID is positional, after any parent IDs. Body and query fields are keyword arguments, and workspace-scoped methods take `workspace_id:`. Every method also accepts `request_options:` with the keys `headers`, `timeout`, `max_retries`, and `reconnect`; any other key raises `ArgumentError`. `api.md` leaves `request_options:` out of the signatures.

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

Body fields are keyword arguments (`metadata:`, `spec:`, `default_variation:`, `agent_id:`). Nested objects are hashes with symbol or string keys, or `Cadenya::Types::*` objects from an earlier response.

- **Write snake_case keys.** The gem maps known keys to wire names (`system_prompt_template` → `systemPromptTemplate`). camelCase keys pass through too, but giving both spellings of one field raises. Free-form fields (`system_prompt_data`, `headers`, `labels`, `parameters`, `output_definition`) are sent exactly as you wrote them.
- A union carries a `type` tag that names the populated key: `{ type: "mcp", mcp: {...} }`, `{ type: "toolSetId", tool_set_id: "..." }`. Tag values stay camelCase.
- Read-only keys on request types are dropped silently, so you can edit a fetched object's `to_h` and send it back. `nil` keyword arguments are omitted; a `nil` inside a hash is sent as JSON `null`.
- Secrets interpolate only as `{{ secrets.NAME }}`. The server rejects `${NAME}` with `legacy dollar references are not supported`, even though some API doc comments still show it.

```ruby
# Tool Set. MCP_TOKEN can be a workspace secret or come in spec.secrets in this same call.
tool_set = client.tool_sets.create(
  metadata: { name: "Support MCP", external_id: "support-mcp" },
  spec: {
    adapter: { type: "mcp", mcp: {
      url: "https://mcp.example.com/mcp",
      headers: { "Authorization" => "Bearer {{ secrets.MCP_TOKEN }}" },
      tool_approvals: { type: "always", always: true }   # every synced tool needs approval
    } },
    secrets: [{ name: "MCP_TOKEN", value: ENV.fetch("MCP_TOKEN") }]
  }
)

# Agent plus its default variation in one call. variation_selection_mode defaults to WEIGHTED.
agent = client.agents.create(
  metadata: { name: "Support Triager", external_id: "support-triager" },
  spec: { description: "Triages inbound support tickets." },
  default_variation: {
    metadata: { name: "default", external_id: "support-triager-default" },
    spec: {
      system_prompt_template: "You triage support tickets for {{ system_prompt_data.customer_name }}.",
      model_config: { model_id: model.metadata.id },   # from models.list; omit model_config for the workspace default model
      constraints: { max_tool_calls: 20, inactivity_timeout: "3600s" }   # durations are strings
    }
  }
)

# Tools attach to variations, not Agents. add_assignment and remove_assignment take the union as body:.
client.agents.variations.add_assignment(agent.metadata.id, variation_id,
                                        body: { type: "toolSetId", tool_set_id: tool_set.metadata.id })
```

Pick the model with `model = client.models.list(state: "STATE_ENABLED", query: "claude").items.first`; `query:` matches part of the name, while `prefix:` matches only the start of the name, external ID or ID. Never hardcode a model slug. A literal `model_id` takes the form `<provider-key-external-id>.<model-external-id>`.

Other adapters: `{ type: "openapi", openapi: { type: "url", url: ... } }` (or `{ type: "uploadId", upload_id: ... }`), `{ type: "http", http: { base_url: ... } }`, `{ type: "bare", bare: {} }`. The Tool Set create loads an MCP or OpenAPI source live and fails if the source is unreachable or lists no tools. When a header names a secret that does not exist yet, the create skips that check, and the mistake surfaces later at sync.

Responses are typed objects with snake_case readers and `to_h`: `agent.metadata.external_id`, `objective.state`, `event.data.type`. Enums are strings (`"STATE_PUBLISHED"`), and timestamps are `Time`.

## Reads, pagination, updates

List methods return a `Cadenya::Page`, which is Enumerable: `items`, `next_cursor`, `next_page?`, `next_page`, and `each`/`map`/`find` walk every page (`auto_paging_each` is an alias).

```ruby
client.agents.list(labels: "env=prod", limit: 50).each { |agent| ... }
client.agents.update(agent_id, metadata: { name: "Support Triager v2" }, update_mask: "metadata.name")
```

`update` takes `metadata:`, `spec:`, and `update_mask:`, a comma-separated string of camelCase paths. Only masked paths change, and maps and lists are replaced whole. Retrieve the resource after a write when the next step depends on it.

## Errors

| Class | When | Readers |
| --- | --- | --- |
| `Cadenya::APIError` | 4xx/5xx after retries | `status_code`, `code` (google.rpc), `message`, `details` (array of hashes) |
| `Cadenya::APIConnectionError` | transport failure | |
| `Cadenya::APIResponseError` | 2xx with an empty, `null`, or malformed JSON body; an unfollowed redirect | `status_code`, `body` |

```ruby
begin
  client.agents.retrieve("external_id:missing")
rescue Cadenya::APIError => e
  reason = e.details.to_a.find { |d| d["reason"] }&.dig("reason")   # ErrorInfo, e.g. SCOPE_MISSING
  case e.status_code
  when 400 then e.details.to_a.flat_map { |d| d["fieldViolations"].to_a }   # message is "validation failed"
  when 403 then ... # the key lacks the scope named by reason
  when 404 then ... # wrong workspace, or the external ID was never set
  when 409 then ... # "resource with the same identifier already exists": retrieve it by external ID
  when 429 then ... # ENTITLEMENT_LIMIT_REACHED is a plan cap, not a rate limit
  else raise
  end
end
```

Stream-endpoint errors carry only a message, with no details, and report FailedPrecondition as 409 where unary calls return 400.

## Retries

Retries default to 0 and apply only to GET, HEAD, PUT and DELETE, on 408, 409, 429, 500, 502, 503 and 504 and on transport errors, honoring `Retry-After`. `max_retries:` on the client turns them on; `request_options: { max_retries: n }` opts a single POST or PATCH in. Streams never retry; they reconnect (below).

## Streaming objectives

Default to `create_and_stream`: it creates the objective and streams it in one request, and the server ends the stream once the objective is `OBJECTIVE_STATE_WAITING` (the turn is over) or terminal. It takes the same arguments as `create` plus `include_deltas:`, and `metadata: { external_id: }` is required: it is the idempotency key that makes a reconnect attach to the same objective. The first item has `type` `"objective"` (`item.objective`); every later item has `type` `"event"` (`item.event`).

The end-of-turn signal is a `stateChanged` event whose `to_state` is `OBJECTIVE_STATE_WAITING`. `OBJECTIVE_STATE_FINALIZED`, `_FAILED`, `_CANCELLED` and `_TIMED_OUT` are terminal. Tool approvals happen mid-turn, while the objective is still running.

```ruby
SETTLED = %w[OBJECTIVE_STATE_WAITING OBJECTIVE_STATE_FINALIZED OBJECTIVE_STATE_FAILED
             OBJECTIVE_STATE_CANCELLED OBJECTIVE_STATE_TIMED_OUT].freeze
objective_id = nil

handle = lambda do |event|   # true once the objective is waiting or terminal
  data = event.data          # payload sits under the snake_case form of data.type
  case data.type
  when "toolApprovalRequested"
    client.objectives.approve_tool_call(objective_id, data.tool_approval_requested.tool_call_id)
  when "assistantMessage"
    puts data.assistant_message.content if data.assistant_message.content
  when "finalized"
    puts data.finalized.output.inspect
  when "stateChanged"
    return SETTLED.include?(data.state_changed.to_state)
  end
  false
end

# Attach with stream_events until settled; returns the cursor for the next turn.
follow = lambda do |cursor|
  loop do
    stream = client.objectives.stream_events(objective_id, last_event_id: cursor)
    settled = false
    stream.each { |event| stream.close if (settled = handle.(event)) }
    cursor = stream.last_event_id || cursor
    return cursor if settled
  end
end

stream = client.objectives.create_and_stream(
  agent_id: "external_id:support-triager",
  system_prompt_data: { customer_name: "Ada" },
  first_user_message: "Summarize the open tickets.",
  metadata: { external_id: "ticket-4821", labels: { source: "api" } }
)
settled = false
stream.each do |item|
  if item.type == "objective" then objective_id = item.objective.metadata.id
  elsif handle.(item.event) then settled = true
  end
end
cursor = stream.last_event_id
cursor = follow.(cursor) unless settled   # the stream ended early: connection cut

client.objectives.continue(objective_id, message: "Which one is most urgent?")
cursor = follow.(cursor)                  # the next turn
```

Rules for `stream_events`, the attach-only stream:

- It never ends on its own. Call `stream.close` once `handle` returns true; `each` then returns cleanly.
- Without `last_event_id:` it delivers only events created after the connection opens. With it, the server replays everything after that ID, then goes live. To attach to an objective you did not start, replay `list_events(objective_id, sort_order: "asc")` through `handle` and stream from the last item's `metadata.id`.
- Resume only from `stream.last_event_id`, never from `event.metadata.id` of a streamed event. Heartbeats (`hb_…`) and deltas (`dlt_…`, with `include_deltas: true`) carry IDs the server rejects as a cursor (400 `Last-Event-ID must be a persisted objevt_ event ID`); only `objevt_…` IDs advance `stream.last_event_id`.

Both streams:

- Connections are cut after about 10 minutes. That ends `each` cleanly, with no reconnect, so loop until settled as `follow` does.
- Mid-stream transport drops reconnect from `stream.last_event_id`, up to 5 attempts per outage. `request_options: { reconnect: false }` raises `APIConnectionError` instead, so you can resume yourself.
- A stream is single-use: iterating it twice raises `IOError` (`stream already consumed`). Open a new one from `stream.last_event_id`.
- A replayed `toolApprovalRequested` for a call you already approved makes `approve_tool_call` fail with 400 (code 9, not waiting for approval). Treat that as already handled.
- `stream.each_event` yields `Cadenya::ServerSentEvent` envelopes (`event`, `data`, `id`). `open` and `ping` frames are skipped. `close` is safe from another thread and unblocks a parked read.

## Webhooks

```ruby
# Rails: request.raw_post is the untouched body; a re-serialized body fails verification.
# Pass a plain hash: ActionDispatch's request.headers enumerates CGI keys (HTTP_WEBHOOK_ID) and fails.
headers = %w[webhook-id webhook-timestamp webhook-signature].to_h { |h| [h, request.headers[h]] }
event = client.unwrap_webhook(request.raw_post, headers)   # uses webhook_secret / CADENYA_WEBHOOK_SECRET
event.type                                  # "objective_event.tool_approval_requested", ...
event.data.objective.id
event.data.objective_event.data.type        # same union as the stream
```

Signatures follow Standard Webhooks: headers `webhook-id`, `webhook-timestamp` and `webhook-signature` (`v1,<base64>`), HMAC-SHA256 over `id.timestamp.body`, and a 5-minute tolerance. The secret starts with `whsec_` and is `client.accounts.retrieve.info.webhook_events_hmac_secret`; store it as `CADENYA_WEBHOOK_SECRET`. `Cadenya::Webhooks.verify(secret, payload, headers, tolerance_seconds: 300)` checks without decoding. Failures raise `Cadenya::WebhookVerificationError`. Rack-style array header values are accepted.

## Logging

The gem has no logger. Pass `connection:` with Faraday's logger middleware (plus a `stream_transport:`), or wrap calls yourself.

## Build checklist

1. `client.profiles.whoami` succeeds with the key and workspace you expect.
2. Pick a model from `client.models.list(state: "STATE_ENABLED")`, or omit `model_config` to use the workspace default.
3. Create the Tool Set, then check `client.tool_sets.tools.list(tool_set.metadata.id)`. The first sync runs after the create returns, so poll briefly before treating an empty list as a failure.
4. Create the Agent with `default_variation:`. `agents.create` returns no variation ID, so get it from `client.agents.variations.list(agent.metadata.id, limit: 1).items.first`.
5. `add_assignment` the Tool Set to that variation.
6. `client.agents.publish(agent.metadata.id)`. An objective on a `STATE_DRAFT` Agent fails with 400 `validation failed`, field `agent_id`: `agent must be published to create an objective`.
7. Run `create_and_stream` with an `external_id`, handle approvals, and stop on the settled `stateChanged`.
8. Optionally record feedback: `client.objectives.create_feedback(objective_id, metadata: {}, data: { score: 1.0, comment: "Accurate summary" })`.

## Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ArgumentError: missing workspaceId: pass it, set it on the client, or set CADENYA_WORKSPACE_ID` | no client default and no `workspace_id:` | set one of those |
| 400 field `spec.model_config.model_id` | wrong `model_id` form, disabled model, or no workspace default | a `model_…` ID from `models.list` |
| 429 `the account has reached its plan's limit of N for agent_variations` | the plan caps non-archived variations across the whole account; `default_variation` counts | archive unused variations, or update an existing one |
| 400 `metadata.externalId is required …` from `create_and_stream` | no `metadata: { external_id: }` | add a stable external ID |
| `stream_events` yields nothing for a finished objective | no `last_event_id:` | replay `list_events(sort_order: "asc")`, then stream from the last ID |
| `stream_events` `each` never returns | that stream never closes | `stream.close` on the settled `stateChanged` |
| `ArgumentError: streaming with a caller-supplied connection: requires an explicit stream_transport:` | custom `connection:` without a stream transport | pass `stream_transport:`, or drop `connection:` |
| `ArgumentError: unknown request_options key(s): …` | typo in `request_options:` | only `headers`, `timeout`, `max_retries`, `reconnect` |
| a POST is not retried | retries apply to idempotent methods only | `request_options: { max_retries: n }` |
| a header secret is not resolved | `${NAME}` syntax | `{{ secrets.NAME }}` |

## Related skills

- `cadenya-api`: wire conventions and per-resource request shapes.
- `cadenya-cli`: the same operations from a terminal; `cadenya … --dry-run` prints the JSON body a request would send.
