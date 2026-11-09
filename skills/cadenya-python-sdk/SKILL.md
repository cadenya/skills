---
name: cadenya-python-sdk
description: "Writes and debugs Python code that uses `cadenya`, Cadenya's official Python SDK (PyPI package, Python 3.9+, synchronous httpx client). Covers client setup, resource method names, snake_case request dicts, pagination, `APIError` handling, objective event streams with `create_and_stream`, and webhook verification. Use when Python code imports `cadenya`, when a Python service creates Tool Sets, Agents or objectives, or on `APIError`, `missing workspaceId`, `must not be blank`, or `stream already consumed`. Not for wire-level REST details (use cadenya-api), terminal commands (cadenya-cli), or other languages (their SDK skills)."
---

# Cadenya Python SDK

The `cadenya` package is generated from the Cadenya OpenAPI contract: `client.<resource>.<method>(...)` maps one-to-one onto REST operations, fields and enum values. Full signatures are in the package's `api.md` (inside site-packages); response models are dataclasses in `cadenya.types`. The client is synchronous; there is no async client.

Wire conventions shared by every client (IDs and external IDs, field masks, error codes, streaming semantics) are in the `cadenya-api` skill.

## Install and construct

```sh
pip install cadenya
```

```python
from cadenya import Cadenya, APIError, APIConnectionError, RequestOptions

client = Cadenya()                                    # reads CADENYA_API_KEY, CADENYA_WORKSPACE_ID
client = Cadenya(workspace_id="development", max_retries=2)
with Cadenya() as client:                             # closes the SDK-owned httpx client
    ...
```

| Argument | Env fallback | Notes |
| --- | --- | --- |
| `api_key` | `CADENYA_API_KEY` | required; missing raises `ValueError("missing API key: …")` |
| `workspace_id` | `CADENYA_WORKSPACE_ID` | `workspace_…` ID or external ID; default for every workspace-scoped call |
| `base_url` | `CADENYA_BASE_URL` | `https://api.cadenya.com` |
| `webhook_secret` | `CADENYA_WEBHOOK_SECRET` | for `client.unwrap_webhook` |
| `max_retries` | | default 0, clamped to 0–10 |
| `http_client` | | your own `httpx.Client` (timeouts, proxies); the SDK never closes it |

An argument passed explicitly but blank raises `ValueError("<name> must not be blank")` instead of falling back to env. The SDK-owned client has a 60-second timeout and there is no `timeout` argument: pass `http_client=httpx.Client(timeout=…)` or per-call `RequestOptions(timeout=…)`.

## Account and API key

- A person creates the account at https://app.cadenya.com/signup. When there is no key yet, give your user that link.
- Keys are at https://app.cadenya.com/account/apiKeys; sign-up creates a default key for every workspace. Put the key in `CADENYA_API_KEY` (an env var or secret manager, never source code). The SDK does not read the CLI's stored login.
- `client.profiles.whoami().default_workspace.id` is the default workspace ID for `CADENYA_WORKSPACE_ID`.
- For setup that should live in the repository (Tool Sets, Agents, variations, memory layers, Widgets), prefer YAML in `.cadenya/` applied with `cadenya config apply` ([format](https://cadenya.com/docs/config-files)) over a one-off provisioning script.

## Resources and method names

Method = the operation verb with the resource words removed, snake_case; `Get` is `retrieve`; `continue` is `continue_`. The resource's own ID is positional, parent IDs first; every body or query field is a keyword argument. Workspace-scoped methods also accept `workspace_id=`, and every method accepts `request_options=` (omitted from `api.md` signatures, but present).

```python
client.agents.retrieve(id)
client.agents.variations.retrieve(agent_id, id)
client.objectives.approve_tool_call(objective_id, tool_call_id)
client.objectives.continue_(objective_id, message="…")
```

| Accessor | Notable methods |
| --- | --- |
| `accounts` | `retrieve`, `rotate_challenge_token`, `rotate_webhook_signing_key` |
| `profiles` | `whoami` |
| `workspaces` | `list` |
| `workspace_admin` | `list_account`, `create`, `retrieve`, `update`, `archive`, `list_members`, `add_member`, `remove_member`, `list_profiles` |
| `api_keys` | `list`, `create`, `retrieve`, `update`, `delete`, `enable`, `disable`, `rotate`, `reveal`, `add_workspace`, `remove_workspace` |
| `ai_provider_keys`, `models` | CRUD (`models` has no `delete`); `models.enable`, `models.disable`, `models.swap_on_variations` |
| `tool_sets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive`, `list_events`, `list_usage`, `retrieve_open_api_spec` |
| `tool_sets.tools` | `list`, `create`, `retrieve`, `update`, `delete`, `omit`, `restore` |
| `tool_sets.secrets`, `workspace_secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `agents` | `list`, `create`, `retrieve`, `update`, `delete`, `publish`, `unpublish`, `archive`, `unarchive`, `list_feedback`, `list_webhook_deliveries` |
| `agents.variations` | `list`, `create`, `retrieve`, `update`, `delete`, `add_assignment`, `remove_assignment`, `add_memory_layer`, `update_memory_layer`, `remove_memory_layer` |
| `agents.schedules` | CRUD, `pause`, `resume`, `archive` |
| `agent_pools` | CRUD, `activate`, `deactivate`, `archive`, `unarchive` |
| `objectives` | `create_and_stream`, `create`, `list`, `retrieve`, `list_events`, `stream_events`, `continue_`, `cancel`, `interrupt`, `compact`, `list_tool_calls`, `retrieve_tool_call`, `approve_tool_call`, `deny_tool_call`, `set_tool_call_content`, `list_tools`, `list_context_windows`, `retrieve_diagnostics`, `list_feedback`, `create_feedback`, `list_queued_actions`, `remove_queued_action` |
| `memory_layers`, `memory_layers.entries` | CRUD |
| `tenants` | `list`, `retrieve`, `delete`, `list_subjects` |
| `widgets`, `widget_sessions` | CRUD (`widget_sessions` has no `update`); `widgets.archive`, `widgets.unarchive`, `widget_sessions.revoke`, `widget_sessions.delete_tenant` |
| `trusted_endpoints` | `list`, `create`, `retrieve`, `delete`, `verify` |
| `uploads` | `create`, `retrieve` |
| `tool_search` | `search_or_sets` |

## Request bodies

Body fields are keyword arguments (`metadata=`, `spec=`, `default_variation=`, `agent_id=`); nested objects are plain dicts (typed as `TypedDict`s such as `cadenya.types.AgentSpecParam`).

- **Write snake_case keys.** The SDK translates known keys to wire names (`system_prompt_template` → `systemPromptTemplate`). camelCase keys pass through too, but both spellings of one field raise. Data inside free-form fields (`system_prompt_data`, `headers`, `labels`, `parameters`, `output_definition`) is never rewritten.
- Unions carry a `type` tag naming the populated key, and tag values stay camelCase: `{"type": "mcp", "mcp": {...}}`, `{"type": "toolSetId", "tool_set_id": "..."}`.
- Server-owned keys (`agent_id` inside `default_variation`, an API key spec's `token`) are dropped silently; unknown keys pass through. `None` keyword arguments are omitted; `None` inside a dict is sent as JSON `null`.

```python
# Tool Set. Secrets interpolate as {{ secrets.NAME }} only.
tool_set = client.tool_sets.create(
    metadata={"name": "Support MCP", "external_id": "support-mcp"},
    spec={"adapter": {"type": "mcp", "mcp": {
        "url": "https://mcp.example.com/mcp",
        "headers": {"Authorization": "Bearer {{ secrets.MCP_TOKEN }}"},
        "tool_approvals": {"type": "always", "always": True},   # every synced tool needs approval
    }}},
)

# Model: pick one the workspace has enabled; never hardcode a model slug.
model = client.models.list(state="STATE_ENABLED", limit=1).items[0]   # IndexError: no enabled model

# Agent plus its default variation in one call.
agent = client.agents.create(
    metadata={"name": "Support Triager", "external_id": "support-triager"},
    spec={"description": "Triages support tickets"},   # variation_selection_mode defaults to WEIGHTED
    default_variation={
        "metadata": {"name": "default", "external_id": "support-triager-default"},
        "spec": {
            "system_prompt_template": "You triage support tickets for {{ system_prompt_data.customer_name }}.",
            "model_config": {"model_id": model.metadata.id},   # or "<provider-key-external-id>.<model-external-id>"
            "constraints": {"max_tool_calls": 20, "inactivity_timeout": "3600s"},   # durations are strings
        },
    },
)

# Assignment: tools attach to variations, not Agents. The union body goes in body=.
variation = client.agents.variations.list(agent.metadata.id, limit=1).items[0]   # create returns the Agent only
client.agents.variations.add_assignment(
    agent.metadata.id, variation.metadata.id,
    body={"type": "toolSetId", "tool_set_id": tool_set.metadata.id},
)
client.agents.publish(agent.metadata.id)   # objectives on a STATE_DRAFT Agent are rejected
```

Other adapters: `{"type": "openapi", "openapi": {"type": "url", "url": ...}}` (or `{"type": "uploadId", "upload_id": ...}`), `{"type": "http", "http": {"base_url": ...}}`, `{"type": "bare", "bare": {}}`. `${NAME}` and `$NAME` are rejected with `legacy dollar references are not supported`. The secret can be a workspace secret (`client.workspace_secrets.create(metadata={"name": "MCP_TOKEN"}, spec={"value": os.environ["MCP_TOKEN"]})`) or a Tool Set secret in the same create (`spec={"secrets": [{"name": "MCP_TOKEN", "value": ...}], ...}`). When every referenced secret resolves, the create validates the source live and rejects one that is unreachable or lists no tools; a reference to a secret that does not exist yet skips that check.

Responses are dataclasses with snake_case attributes (`agent.metadata.external_id`, `event.data.type`). Enums are plain strings (`"STATE_PUBLISHED"`); timestamps are `datetime`.

## Reads, pagination, updates

List methods return `SyncPage[T]`: `.items`, `.next_cursor`, `.has_next_page()`, `.get_next_page()`; iterating the page walks every page.

```python
for agent in client.agents.list(labels="env=prod", limit=50): ...
```

`update` takes `metadata=`, `spec=`, and `update_mask=` (comma-separated camelCase paths). Only masked paths change; maps and lists are replaced whole. Retrieve after the write to confirm.

```python
client.agents.update(agent_id, metadata={"name": "Support Triager v2"}, update_mask="metadata.name")
```

## Errors

| Class | When | Attributes |
| --- | --- | --- |
| `APIError` | non-2xx after retries | `status_code`, `code` (google.rpc), `message`, `details` (raw JSON dicts) |
| `APIConnectionError` | transport failure or timeout, or a stream drop with reconnect off or after 5 failed reconnects | |
| `APIResponseError` | 2xx with empty, `null`, or malformed JSON; unfollowed redirect | `status_code`, `body` |

```python
try:
    client.agents.retrieve("external_id:missing")
except APIError as e:
    if e.status_code == 404: ...   # wrong workspace, or external ID never set
    elif e.status_code == 403: ... # key lacks a scope: e.details[0]["reason"] == "SCOPE_MISSING"
    elif e.status_code == 400: ... # e.message == "validation failed"; e.details[0]["fieldViolations"] lists {field, description}
    else: raise
```

Stream-endpoint errors carry only `message` (no `code` or `details`), and a failed precondition there is 409 rather than 400. Timeouts surface as `APIConnectionError`, with the `httpx` exception as `__cause__`.

## Retries and per-request options

`RequestOptions(headers=None, timeout=None, max_retries=None, reconnect=None)`, passed as `request_options=` (a dict raises `TypeError`). The client's `max_retries` applies to GET/HEAD/PUT/DELETE only, on 408, 409, 429, 500, 502, 503, 504 and transport errors, honoring `Retry-After`. `RequestOptions(max_retries=n)` on a single call opts a POST or PATCH in.

## Streaming objective events

Default: start the objective with `create_and_stream`. It creates the objective and streams its events on one connection, and ends on its own once the objective settles (`OBJECTIVE_STATE_WAITING` or terminal). `metadata.external_id` is required: it is the idempotency key, so the SDK's mid-stream reconnect (a re-POST) attaches to the same objective instead of starting another. Any request whose `external_id` already names an objective attaches to it (a re-run of the same script continues the old objective), so use one key per unit of work, such as the ticket ID. The first item has `type == "objective"` (`.objective`); every later item has `type == "event"` (`.event`, an `ObjectiveEvent`).

The end-of-turn signal is a `stateChanged` event whose `to_state` is `OBJECTIVE_STATE_WAITING` (the Agent answered and waits for `continue_`); a terminal `to_state` ends the objective.

```python
SETTLED = {"OBJECTIVE_STATE_WAITING", "OBJECTIVE_STATE_FINALIZED", "OBJECTIVE_STATE_FAILED",
           "OBJECTIVE_STATE_CANCELLED", "OBJECTIVE_STATE_TIMED_OUT"}

def handle(objective_id: str, event) -> bool:
    """Act on one ObjectiveEvent; return True once the objective has settled."""
    data = event.data                                # discriminated on data.type; payload under the snake_case key
    if data.type == "toolApprovalRequested":
        try:
            client.objectives.approve_tool_call(objective_id, data.tool_approval_requested.tool_call_id)
        except APIError as e:
            if e.code != 9: raise                    # 9: already approved or denied (a replayed request)
    elif data.type == "assistantMessage" and data.assistant_message.content:
        print(data.assistant_message.content)
    elif data.type == "finalized":
        print(data.finalized.output)
    elif data.type == "stateChanged":
        return data.state_changed.to_state in SETTLED
    return False

def follow(objective_id: str, last_event_id) -> str:
    """Attach with stream_events until the objective settles; return the resume checkpoint."""
    while True:
        with client.objectives.stream_events(objective_id, last_event_id=last_event_id) as stream:
            for event in stream:
                if handle(objective_id, event):
                    return stream.last_event_id
            last_event_id = stream.last_event_id     # clean end before settling: reopen

settled, objective_id = False, None
with client.objectives.create_and_stream(
    agent_id=agent.metadata.id,
    metadata={"external_id": "ticket-4821", "labels": {"source": "api"}},
    system_prompt_data={"customer_name": "Ada"},
    first_user_message="Summarize the open tickets.",
) as stream:
    for item in stream:
        if item.type == "objective":                 # re-sent first after every reconnect
            objective_id = item.objective.metadata.id
            settled = item.objective.state in SETTLED  # external_id reused from a settled run: no events follow
        elif handle(objective_id, item.event):
            settled = True
    last_event_id = stream.last_event_id
if settled and last_event_id is None:                # attached to a settled run: checkpoint at its newest event
    last_event_id = client.objectives.list_events(objective_id, sort_order="desc", limit=1).items[0].metadata.id
if not settled:                                      # connection cut before the objective settled
    last_event_id = follow(objective_id, last_event_id)

client.objectives.continue_(objective_id, message="Which one is most urgent?")
last_event_id = follow(objective_id, last_event_id)  # next turn, replayed from the checkpoint
```

Rules the code above depends on:

- `stream_events` attaches to an existing objective and **never closes on its own**; stop on the settled `stateChanged`. Without `last_event_id` it delivers only events created after the connection opens; with it, the server replays everything after that ID, then goes live. To attach from scratch, page `list_events(objective_id, sort_order="asc")` and pass the last event's ID.
- Resume only from `stream.last_event_id`, never from `event.metadata.id`. Live-only `heartbeat` events (and deltas, with `include_deltas=True`) carry `hb_`/`dlt_` IDs, and resuming from one fails with 400 `Last-Event-ID must be a persisted objevt_ event ID`. `stream.last_event_id` starts at the ID you passed and advances only on persisted events.
- Mid-stream transport drops reconnect from `stream.last_event_id` (5 attempts per outage). `RequestOptions(reconnect=False)` surfaces them as `APIConnectionError` so you can resume yourself. Connections are cut after about 10 minutes. A cut that reaches the client as a clean end of stream stops the `for` loop with no reconnect, which is why `follow` reopens.
- A stream is single-use (`stream already consumed`); open a new one with `last_event_id=stream.last_event_id`.
- A replayed `toolApprovalRequested` for a call already approved makes `approve_tool_call` fail with 400, code 9 (`… not waiting for approval`); treat it as handled.
- `stream.events()` yields raw `ServerSentEvent(event, data, id)` envelopes; housekeeping frames (`open`, `ping`) are skipped.

Use plain `objectives.create(...)` only when nothing watches the run (webhooks, or polling `retrieve`).

## Webhooks

```python
from cadenya import unwrap_webhook, verify_webhook, WebhookVerificationError

event = client.unwrap_webhook(request.get_data(), request.headers)   # raw body bytes; secret from webhook_secret / CADENYA_WEBHOOK_SECRET
# event.type: "objective_event.tool_approval_requested" etc.; event.data.objective.id is the objective;
# event.data.objective_event.data.type is the event kind (same union as the stream)
```

Standard Webhooks: headers `webhook-id`, `webhook-timestamp`, `webhook-signature` (`v1,<base64>`), HMAC-SHA256 over `id.timestamp.body`, 5-minute tolerance (adjustable only through `verify_webhook(..., tolerance_seconds=)`). The secret starts with `whsec_` and comes from `client.accounts.retrieve().info.webhook_events_hmac_secret`; store it as `CADENYA_WEBHOOK_SECRET`. `verify_webhook(secret, payload, headers)` checks without decoding. Failures raise `WebhookVerificationError`. Pass the raw body, never a re-serialized one.

## Logging

No built-in logger: `logging.getLogger("httpx").setLevel(logging.DEBUG)`, or pass an `http_client` with event hooks. There is no public raw-response accessor.

## Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| `ValueError: missing workspaceId: pass it, set it on the client, or set CADENYA_WORKSPACE_ID` | no workspace anywhere | set one of those three |
| 400 `validation failed`, field `agent_id`: `agent must be published to create an objective` | Agent is `STATE_DRAFT` | `client.agents.publish(id)` |
| 400 `validation failed` on `spec.model_config.model_id` | wrong or disabled model | `metadata.id` from `models.list(state="STATE_ENABLED")` |
| 400 `metadata.externalId is required: …` | `create_and_stream` without `metadata.external_id` | pass `metadata={"external_id": ...}` |
| 409 `resource with the same identifier already exists` | `create` with an external ID already in use | retrieve `external_id:<id>`, or use a new one |
| 429 `the account has reached its plan's limit of N for agent_variations` | account-wide cap on non-archived variations (`ENTITLEMENT_LIMIT_REACHED`; the default variation counts) | delete unused variations, or upgrade the plan (an unclaimed temporary account gets `REQUIRES_CLAIM` instead) |
| `stream_events` loop never ends | that stream stays open | return on the settled `stateChanged` |
| `stream_events` yields nothing for a finished objective | no `last_event_id` | replay with `list_events(sort_order="asc")`, then stream from the last ID |
| `stream already consumed` | iterated a stream twice | new stream with `last_event_id=stream.last_event_id` |
| 400 `Last-Event-ID must be a persisted objevt_ event ID` | resumed from an `hb_`/`dlt_` ID | resume from `stream.last_event_id` |
| POST not retried | client retries cover idempotent methods only | `RequestOptions(max_retries=n)` on that call |
| `TypeError: request_options must be a RequestOptions instance` | passed a dict | `from cadenya import RequestOptions` |
| `legacy dollar references are not supported` | `${NAME}` in a header | `{{ secrets.NAME }}` |
| `agents.create` result has no variation ID | `Agent.info` only has `variation_count` | `agents.variations.list(agent_id)` |

## Related skills

- `cadenya-api`: wire conventions and per-resource request shapes.
- `cadenya-cli`: the same operations from a terminal; `cadenya … --dry-run` prints the JSON body the SDK would send.
