---
name: cadenya-python-sdk
description: "Build Cadenya integrations with the official Python SDK, the `cadenya` package on PyPI (Python 3.9+, httpx, typed dataclasses and TypedDicts, sync client). Covers client setup, resource method names, snake_case request shapes, pagination, `APIError` handling, SSE objective event streams, and Standard Webhooks verification. Use when writing or debugging Python that imports `cadenya`, when a Python service needs to create tool sets, agents, or objectives, or when hitting `APIError`, `missing workspaceId`, `ValueError: … must not be blank`, or `stream already consumed`."
---

# Cadenya Python SDK usage

## Overview

The `cadenya` package is generated from the Cadenya OpenAPI contract, so resources, methods, field names, and enum values match the REST API one-to-one: `client.<resource>.<method>(...)`. Every signature is in the package's `api.md` (`cadenya/api.md` inside site-packages); response models are dataclasses in `cadenya.types`. The client is synchronous; there is no async client.

For wire conventions shared by every client (IDs and external IDs, field masks, error codes, pagination, streaming semantics, webhooks) see the `cadenya-api` skill. This skill covers what is specific to Python.

## Install and construct

```sh
pip install cadenya
```

```python
from cadenya import Cadenya, APIError, APIConnectionError, RequestOptions

client = Cadenya()                                   # reads env
client = Cadenya(api_key=key, workspace_id="development", max_retries=2)
with Cadenya() as client:                            # closes the SDK-owned httpx client
    ...
```

| Argument | Env fallback | Notes |
| --- | --- | --- |
| `api_key` | `CADENYA_API_KEY` | required; missing everywhere raises `ValueError("missing API key: …")` |
| `workspace_id` | `CADENYA_WORKSPACE_ID` | `workspace_…` or the external ID; default for every workspace-scoped call |
| `base_url` | `CADENYA_BASE_URL` | `https://api.cadenya.com` |
| `webhook_secret` | `CADENYA_WEBHOOK_SECRET` | for `client.unwrap_webhook` |
| `max_retries` | | 0, clamped to 0 to 10 |
| `http_client` | | your own `httpx.Client` (timeouts, proxies); never closed by the SDK |

An argument passed explicitly but blank raises `ValueError` instead of falling back to env. The SDK-owned client uses a 60-second timeout; there is no `timeout` constructor argument, so pass `http_client=httpx.Client(timeout=…)` or per-call `RequestOptions(timeout=…)`.

## Account and API key

- A person creates the account at https://app.cadenya.com/signup, and the Free plan needs no card. When there is no key yet, give your user that link.
- The API keys page, https://app.cadenya.com/account/apiKeys, lists the account's keys. Sign-up creates a default key that reaches every workspace. Set the key as `CADENYA_API_KEY`: the SDK reads its options and the environment, never the CLI's stored login.
- `client.profiles.whoami().default_workspace.id` is the default workspace ID, the value for `CADENYA_WORKSPACE_ID`, and `cadenya workspaces list` lists the others.
- From a terminal, `cadenya auth login` signs in through the browser with a one-time code (see `cadenya-cli`).
- Keep tool sets, agents, variations, memory layers and widgets as YAML files in `.cadenya/` next to a `cadenya.yaml`, and apply them with `cadenya config apply` ([format](https://cadenya.com/docs/config-files), [GitHub Action](https://github.com/cadenya/cadenya-config-loader)). That keeps the setup in the repository instead of in a one-off provisioning script.

## Resources and method names

Method = operation verb with the resource words removed, snake_case; `Get` is `retrieve`; the Python keyword `continue` becomes `continue_`. The resource's own ID is positional, parent IDs first for nested resources, and every body or query field is a keyword argument. Every method also accepts `workspace_id=` and `request_options=` (the package's `api.md` omits `request_options` from signatures; it is there).

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
| `api_keys` | `list`, `create`, `retrieve`, `update`, `delete`, `enable`, `disable`, `rotate`, `reveal`, `add_workspace`, `remove_workspace` (account keys) |
| `ai_provider_keys`, `models` | CRUD; `models.enable`, `models.disable`, `models.swap_on_variations` |
| `tool_sets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive`, `list_events`, `list_usage`, `retrieve_open_api_spec` |
| `tool_sets.tools` | `list`, `create`, `retrieve`, `update`, `delete`, `omit`, `restore` |
| `tool_sets.secrets`, `workspace_secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `agents` | `list`, `create`, `retrieve`, `update`, `delete`, `publish`, `unpublish`, `archive`, `unarchive`, `list_feedback`, `list_webhook_deliveries` |
| `agents.variations` | `list`, `create`, `retrieve`, `update`, `delete`, `add_assignment`, `remove_assignment`, `add_memory_layer`, `update_memory_layer`, `remove_memory_layer` |
| `agents.schedules` | CRUD, `pause`, `resume`, `archive` |
| `objectives` | `list`, `create`, `retrieve`, `list_events`, `stream_events`, `continue_`, `cancel`, `compact`, `list_tool_calls`, `retrieve_tool_call`, `approve_tool_call`, `deny_tool_call`, `set_tool_call_content`, `list_tools`, `list_context_windows`, `retrieve_diagnostics`, `list_feedback`, `create_feedback` |
| `memory_layers`, `memory_layers.entries` | CRUD |
| `tenants` | `list`, `retrieve`, `delete`, `list_subjects` |
| `widgets`, `widget_sessions` | CRUD; `widget_sessions.revoke`, `widget_sessions.delete_tenant` |
| `uploads` | `create`, `retrieve` |
| `tool_search` | `search_or_sets` |

## Request bodies

Body fields are keyword arguments (`metadata=`, `spec=`, `default_variation=`, `agent_id=`); nested objects are plain dicts (typed as `TypedDict`s such as `cadenya.types.AgentSpecParam`).

- **Write snake_case keys.** The SDK translates known keys to wire names (`system_prompt_template` → `systemPromptTemplate`); camelCase keys pass through too, but supplying both spellings of one field raises. Your own data inside free-form fields (`system_prompt_data`, `headers`, `labels`, `parameters`, `output_definition`) is never rewritten.
- Unions carry a `type` tag naming the populated key: `{"type": "mcp", "mcp": {...}}`, `{"type": "toolSetId", "tool_set_id": "..."}`. Tag values stay camelCase.
- Read-only keys on request types are dropped silently, so a fetched object's `to_dict`-style data can be edited and sent back. `None` keyword arguments are omitted; a `None` inside a dict is sent as JSON `null`.

```python
# Tool set. Secrets interpolate as {{ secrets.NAME }} (workspace or tool set secret).
tool_set = client.tool_sets.create(
    metadata={"name": "Support MCP", "external_id": "support-mcp"},
    spec={"adapter": {"type": "mcp", "mcp": {
        "url": "https://mcp.example.com/mcp",
        "headers": {"Authorization": "Bearer {{ secrets.MCP_TOKEN }}"},
        "tool_approvals": {"type": "always", "always": True},   # every synced tool needs approval
    }}},
)

# Agent plus its default variation in one call. variation_selection_mode is required.
agent = client.agents.create(
    metadata={"name": "Support Triager", "external_id": "support-triager"},
    spec={"variation_selection_mode": "VARIATION_SELECTION_MODE_RANDOM"},
    default_variation={
        "metadata": {"name": "default", "external_id": "support-triager-default"},
        "spec": {
            "system_prompt_template": "You triage support tickets for {{ system_prompt_data.customer_name }}.",
            "model_config": {"model_id": "getting-started-key.claude-opus-5"},  # "<provider-key-slug>.<model-slug>" or model_…
            "constraints": {"max_tool_calls": 20, "inactivity_timeout": "3600s"},  # durations are strings
        },
    },
)

# Assignment: the one union-typed body, passed as body=. Tools attach to variations, not agents.
client.agents.variations.add_assignment(
    agent.metadata.id, variation_id,
    body={"type": "toolSetId", "tool_set_id": tool_set.metadata.id},
)

# Objective
objective = client.objectives.create(
    agent_id="external_id:support-triager",
    system_prompt_data={"customer_name": "Ada"},
    first_user_message="Summarize the open tickets.",
    metadata={"external_id": "ticket-4821", "labels": {"source": "api"}},
)
```

Other adapters: `{"type": "openapi", "openapi": {"type": "url", "url": ...}}` (or `{"type": "uploadId", "upload_id": ...}`), `{"type": "http", "http": {"base_url": ...}}`, `{"type": "bare", "bare": {}}`. Doc comments inside the package that mention `${SECRET_NAME}` are stale; the server accepts only `{{ secrets.NAME }}`. Create a secret before the tool set that references it: the create performs a live sync with those headers.

Responses are dataclasses with snake_case attributes: `agent.metadata.external_id`, `objective.state`, `event.data.type`. Enums are plain strings (`"STATE_PUBLISHED"`); timestamps are `datetime`.

## Reads and pagination

List methods return `SyncPage[T]`: `.items`, `.next_cursor`, `.has_next_page()`, `.get_next_page()`, and iteration walks every page.

```python
for agent in client.agents.list(labels="env=prod", limit=50): ...
page = client.objectives.list_events(objective_id, sort_order="asc")
```

## Updates

`update` takes `metadata=`, `spec=`, and `update_mask=` (a comma-separated string of camelCase paths). Only masked paths change; maps and lists are replaced whole.

```python
client.agents.update(agent_id, metadata={"name": "Support Triager v2"}, update_mask="metadata.name")
```

## Errors

| Class | When | Attributes |
| --- | --- | --- |
| `APIError` | any non-2xx after retries | `status_code`, `code` (google.rpc), `message`, `details` |
| `APIConnectionError` | transport failure | |
| `APIResponseError` | 2xx with empty, `null`, or malformed JSON; unfollowed redirect | `status_code`, `body` |

```python
try:
    client.agents.retrieve("external_id:missing")
except APIError as e:
    if e.status_code == 404: ...        # wrong workspace, or external ID never set
    elif e.status_code == 403: ...      # key lacks scope; (e.details or [{}])[0].get("reason") names it (stream-endpoint errors carry no details)
    elif e.status_code == 400: ...      # e.details holds BadRequest field_violations with proto paths such as spec.model_config.model_id
    else: raise
```

Timeouts surface as `httpx` exceptions from the underlying client.

## Retries and per-request options

`RequestOptions(headers=None, timeout=None, max_retries=None, reconnect=None)`, passed as `request_options=`. Retries default to 0 and only ever apply to GET/HEAD/PUT/DELETE (408, 409, 429, 5xx, transport errors), honoring `Retry-After`. `max_retries` on the client enables them; `RequestOptions(max_retries=n)` on a single call opts a POST or PATCH in.

## Streaming objective events

Semantics you must code around:

- `stream_events` without `last_event_id` delivers only events created after the connection opens. With it, the server replays everything after that ID, then goes live.
- The server never closes the stream. Break on a terminal event (`finalized`, `error`, `cancelled`, `timedOut`); leaving the `with` block closes it.
- An `assistantMessage` with empty `tool_calls` ends the turn; the objective is `STATE_WAITING` until you `continue_` it or the inactivity timeout fires.
- A stream is single-use (`stream already consumed`). Mid-stream transport drops reconnect from `stream.last_event_id` (5 attempts per outage); `RequestOptions(reconnect=False)` surfaces them as `APIConnectionError` so you can resume yourself.
- A replayed `toolApprovalRequested` for a call you already approved makes the approve call fail with 400 (code 9, not waiting for approval); treat that as already handled.
- A clean end of stream (load balancers cut connections after about 10 minutes) ends the `for` loop with no terminal event and no reconnect. Track `event.metadata.id` as your checkpoint (`stream.last_event_id` stays `None` until an event with an ID arrives) and reopen from it in an outer loop until you have seen a terminal event.

```python
last_event_id = None
for event in client.objectives.list_events(objective_id, sort_order="asc"):
    handle(event); last_event_id = event.metadata.id

with client.objectives.stream_events(objective_id, last_event_id=last_event_id) as stream:
    for event in stream:
        if handle(event):
            break

def handle(event) -> bool:
    data = event.data                           # discriminated on data.type; payload sits under the snake_case key
    if data.type == "toolApprovalRequested":
        client.objectives.approve_tool_call(objective_id, data.tool_approval_requested.tool_call_id)
    elif data.type == "assistantMessage":
        if data.assistant_message.content:
            print(data.assistant_message.content)
        return not data.assistant_message.tool_calls
    elif data.type == "finalized":
        print(data.finalized.output); return True
    elif data.type in ("error", "cancelled", "timedOut"):
        return True
    return False
```

`stream.events()` yields `ServerSentEvent(event, data, id)` envelopes; `stream.last_event_id` is the resume checkpoint. Housekeeping frames (`open`, `ping`) are skipped.

## Webhooks

```python
from cadenya import unwrap_webhook, verify_webhook

event = client.unwrap_webhook(request.get_data(), request.headers)   # raw bytes; uses webhook_secret / CADENYA_WEBHOOK_SECRET
# event.type is "objective_event.tool_approval_requested" etc.; event.data.objective.id is the objective,
# event.data.objective_event.data.type the event kind (same union as the stream)
```

Standard Webhooks: headers `webhook-id`, `webhook-timestamp`, `webhook-signature` (`v1,<base64>`), HMAC-SHA256 over `id.timestamp.body`, secret `whsec_…` (the account's `webhookEventsHmacSecret`), 5-minute tolerance (`tolerance_seconds=`). `verify_webhook(secret, payload, headers)` checks without decoding; failures raise `WebhookVerificationError`. Pass the raw body, not a re-serialized one.

## Logging and raw responses

No built-in logger. Enable httpx's: `logging.getLogger("httpx").setLevel(logging.DEBUG)`, or pass an `http_client` with event hooks. There is no public raw-response accessor.

## End to end

```python
import os
from cadenya import Cadenya

with Cadenya(workspace_id="development") as client:
    client.workspace_secrets.create(metadata={"name": "MCP_TOKEN"}, spec={"value": os.environ["MCP_TOKEN"]})
    # … tool_set and agent as in "Request bodies" …

    model = next(iter(client.models.list(prefix="claude", state="STATE_ENABLED", limit=1)))   # StopIteration when nothing matches
    variation = client.agents.variations.list(agent.metadata.id, limit=1).items[0]   # create returns the agent only
    client.agents.variations.add_assignment(agent.metadata.id, variation.metadata.id,
                                            body={"type": "toolSetId", "tool_set_id": tool_set.metadata.id})
    client.agents.publish(agent.metadata.id)          # objectives on a STATE_DRAFT agent are rejected

    objective = client.objectives.create(agent_id=agent.metadata.id,
                                         system_prompt_data={"customer_name": "Ada"},
                                         first_user_message="Summarize the open tickets.")
    # … stream as above …
    client.objectives.create_feedback(objective.metadata.id, metadata={}, data={"score": 1.0, "comment": "Accurate summary"})
    client.objectives.continue_(objective.metadata.id, message="Which one is most urgent?")
```

## Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| `missing workspaceId` | no client default and no `workspace_id=` | `CADENYA_WORKSPACE_ID`, `workspace_id` on the client, or per call |
| 400 `agent must be published to create an objective` | agent is `STATE_DRAFT` | `client.agents.publish(id)` |
| 400 on `spec.model_config.model_id` | wrong `model_id` form | `model_…` from `models.list`, or `<provider-key-slug>.<model-slug>` |
| 429 creating a second variation | default plan allows 1 variation per agent | use `default_variation`; update it |
| stream yields nothing for a finished objective | no `last_event_id` | replay with `list_events(sort_order="asc")`, then stream from the last ID |
| `stream already consumed` | iterated a stream twice | open a new one with `last_event_id=stream.last_event_id` |
| stream loop never ends | the server keeps it open | `break` on terminal events |
| POST silently not retried | retries apply to idempotent methods only | `RequestOptions(max_retries=n)` on that call |
| `TypeError: request_options must be a RequestOptions instance` | passed a dict | `from cadenya import RequestOptions` |
| header secret not resolved | `${NAME}` syntax | use `{{ secrets.NAME }}` |
| `agents.create` result has no variation ID | `Agent.info` only has `variation_count` | `agents.variations.list(agent_id)` |
| `continue` is a syntax error | Python keyword | `client.objectives.continue_(...)` |

## Related skills

- `cadenya-api`: wire conventions and per-resource request shapes.
- `cadenya-cli`: the same operations from a terminal; `cadenya … --dry-run` prints the exact JSON body the SDK sends.
