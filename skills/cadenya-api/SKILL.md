---
name: cadenya-api
description: Call the Cadenya REST API directly over HTTPS (`https://api.cadenya.com/v1`) to manage workspaces, tool sets, tools, secrets, agents, variations, schedules, objectives, tool calls, memory, models, API keys, tenants, widgets, and uploads. Covers bearer auth and scopes, ID and external-ID rules, the metadata/spec envelope, discriminated unions, field-mask updates, cursor pagination and filters, the google.rpc error shape, SSE event streams, Standard Webhooks, and the objective lifecycle. Use when building or debugging an integration with curl or a plain HTTP client, choosing endpoints and scopes, reading the OpenAPI spec, or decoding a 400/403/404 from Cadenya. The SDK and CLI skills build on this one.
---

# Cadenya API usage

## Overview

- Base URL `https://api.cadenya.com`, every route under `/v1`. OpenAPI 3.1 spec: `https://openapi.cadenya.com/api-spec.yml`. Reference pages: `https://cadenya.com/docs/api-reference`.
- JSON in and out, camelCase field names, gRPC-transcoded: every error is a `google.rpc.Status`, every list is `{ items, pagination }`, enums are `SCREAMING_SNAKE` strings with a type prefix (`STATE_PUBLISHED`, `VARIATION_SELECTION_MODE_RANDOM`).
- Almost everything lives under `/v1/workspaces/{workspaceId}/…`. Account-level routes: `GET /v1/whoami`, `GET /v1/workspaces`, `GET /v1/account`, `POST /v1/account:rotateWebhookSigningKey`, `/v1/account/api_keys…` (the account's API keys), and `/v1/account/workspaces…` (admin role only; API keys cannot call these).
- The mental model: a **Tool Set** syncs tools from an MCP server, OpenAPI spec, or HTTP API (or is Bare and waits for your app); an **Agent** has **Variations** (model, prompt, assigned tool sets); an **Objective** runs a variation against a message and emits **events**; you approve **tool calls**, `continue` the conversation, and submit **feedback**.

## Account and API key

- A person creates the account at https://app.cadenya.com/signup, and the Free plan needs no card. When a call fails for lack of a key, give your user that link.
- The API keys page, https://app.cadenya.com/account/apiKeys, lists the account's keys. Sign-up creates a default key with the external ID `default` that reaches every workspace (`GET /v1/account/api_keys/external_id:default` reads it).
- Set the key as `CADENYA_API_KEY`. `GET /v1/whoami` checks it and returns the default workspace as `defaultWorkspace.id`, the value for `CADENYA_WORKSPACE_ID`.
- From a terminal, `cadenya auth login` signs in through the browser with a one-time code (RFC 8628 device flow). See `cadenya-cli`.
- Keep tool sets, agents, variations, memory layers and widgets as YAML files in `.cadenya/` next to a `cadenya.yaml`, and apply them with `cadenya config apply` ([format](https://cadenya.com/docs/config-files), [GitHub Action](https://github.com/cadenya/cadenya-config-loader)). That keeps the setup in the repository instead of in a one-off provisioning script.

## Authentication and scopes

```
Authorization: Bearer <api key>
```

- API keys are JWTs (HS256, no expiry) that belong to the account. Create one with `POST /v1/account/api_keys` ([reference](https://cadenya.com/docs/api-reference/apikeyservice/create-a-new-api-key)), assigned to workspaces with `spec.workspaceAssignments` or to every workspace with `spec.allWorkspaces: true`. The raw token is `spec.token` in the create and rotate responses, and `POST /v1/account/api_keys/{id}:reveal` returns it again. Change the workspaces with `:addWorkspace` and `:removeWorkspace`; revoke with `:disable` or `:rotate`.
- The workspace is not in the token. A key reaches the workspaces assigned to it, or every workspace when `spec.allWorkspaces` is true, as for the default key. Using a key against another workspace is 403 `WORKSPACE_ACCESS_DENIED` with `metadata.workspace_id`, never 404.
- **Every credential failure is HTTP 403 with code 7**, not 401: missing header, malformed token, bad signature, disabled key (`ErrorInfo.reason` is `AUTH_TOKEN_INVALID` or `API_KEY_DISABLED`). The SSE stream endpoint is the one place that returns 401. For all of them, the fix is a key from https://app.cadenya.com/account/apiKeys.
- Scopes are `resource:read` or `resource:manage` strings on the key (`spec.permissions`, up to 16): `agents`, `agent_pools`, `models`, `objectives`, `tools`, `memory`, `api_keys`, `workspaces`, `widgets`, `widget_sessions`, `tenants`, `endpoints` (trusted endpoints), plus manage-only `secrets` and `account`, or `*`. `manage` implies `read`, and `api_keys:admin` implies `api_keys:manage`: it is needed to create or change a key that reaches every workspace and to manage keys that other members created. Models and AI provider keys use `models:*` (swapping a model on variations takes `agents:manage`), uploads use `objectives:*`, and all secret endpoints (even GET) need `secrets:manage`. A missing scope is 403 `SCOPE_MISSING` with `metadata.required_scope`. Keys can only mint or rotate keys with scopes they hold.

## IDs and external IDs

- IDs are `<prefix>_<ULID>`: `workspace_`, `agent_`, `agentvar_`, `as_` (schedule), `toolset_`, `tool_`, `toolsecret_`, `wsecret_`, `memlyr_`, `mementry_`, `obj_`, `objevt_`, `objwin_`, `toolcall_`, `objfb_`, `apikey_`, `aipk_`, `model_`, `tenant_`, `subj_`, `wgt_`, `wsess_`, `upload_`, `avt_` and `avml_` (variation assignments), `whkdlv_` (webhook delivery).
- Set `metadata.externalId` (≤64 chars, unique per parent) on create, then use it anywhere the API takes that resource's ID: path segments including `{workspaceId}`, body references such as `agentId` and `toolSetId`, and list filters. A bare value that does not start with the resource's own prefix is treated as an external ID; write `external_id:<value>` to force the lookup when your IDs look like Cadenya's.
- Unresolved path or body reference: 404 `not found`. Unresolved list filter: 400 with a `fieldViolations` entry.
- Objects carry `metadata` (`id`, `accountId`, `workspaceId`, `name`, `externalId`, `labels`, `profileId`, `createdAt`, `updatedAt`), user-owned `spec`, read-only `info` (populated on lists only with `includeInfo=true`), and often a read-only `state`. Operations (objectives, events, tool calls, feedback, deliveries) use `OperationMetadata`, which has no `name`.
- Create bodies take only `metadata.name` (required, ≤64), `metadata.externalId`, `metadata.labels` (≤10 pairs, K8s-shaped keys, values ≤63), and `spec`. **Sending a read-only field (`metadata.id`, `createdAt`, `state`, `info`) is a 400 from the transcoder.**

## Request conventions

- Discriminated unions carry `type` naming the populated key: `{"type": "mcp", "mcp": {…}}`, `{"type": "toolSetId", "toolSetId": "…"}`, event `data.type`. Both keys must agree.
- Custom verbs are `POST …/{id}:verb` with a `{}` body unless noted: `agents/{id}:publish|unpublish|archive|unarchive`, `agents/{agentId}/schedules/{id}:pause|resume|archive`, `api_keys/{id}:rotate|disable|enable`, `models/{id}:enable|disable`, `models:swapModelOnVariations`, `objectives/{id}:continue|cancel|compact`, `objectives/{id}/tool_calls/{toolCallId}:approve|deny|setContent`, `tool_sets/{id}:archive|unarchive`, `tool_sets/{toolSetId}/tools/{id}:omit|restore`, `widgets/{id}:archive|unarchive`, `widget_sessions/{id}:revoke`.
- Durations are strings in seconds (`"3600s"`), not integers, even where the spec says `integer`. `int64` fields such as `sizeBytes` are JSON strings.
- Secrets are referenced from tool set headers and base URLs as Liquid output `{{ secrets.NAME }}` (case-insensitive name; `${NAME}` is rejected). Resolution order, later wins: workspace secret, tool set secret, objective secret. Pinned parameters interpolate as `{{ pinnedParameters.key }}`. Field descriptions in the OpenAPI spec that mention `${SECRET_NAME}` or `pinned_parameters` are stale; the server enforces the forms given here.
- There is no idempotency key, no dry-run mode, and no request rate limiting on the API; `includeInfo` only adds server work.

## Updates (PATCH with a field mask)

```http
PATCH /v1/workspaces/development/agents/support-triager
{"metadata": {"name": "Support Triager v2"}, "updateMask": "metadata.name"}
```

- `updateMask` is a comma-separated string of camelCase dotted paths (`metadata.name,spec.description,metadata.labels`). Only masked paths change.
- Maps and lists (`metadata.labels`, `spec.overlays`, `spec.permissions`) are replaced whole; a masked empty collection clears it. Map-key paths (`metadata.labels.env`) are invalid.
- Without a mask the server merges: set scalars overwrite, unset scalars are kept, and any collection you include replaces the stored one. You cannot clear a scalar without a mask. Masking `metadata` while omitting `externalId` clears the external ID, so round-trip the whole metadata object.
- An unknown path is 400 `invalid field mask`. Schema-required fields (`spec.variationSelectionMode` on agents, `spec.modelConfig.modelId` on variations) must be present in the body even when unmasked.

## Lists, pagination, filters

```http
GET /v1/workspaces/development/agents?limit=50&labels=env%3Dprod%2Cteam%3Dai&state=STATE_PUBLISHED&sortOrder=desc
```

- Response `{"items": [...], "pagination": {"nextCursor": "…"}}`. Fetch the next page with `cursor=<nextCursor>`; a missing or empty cursor means the last page. There is no total count. `GET /v1/workspaces` items carry `status` (`STATUS_ENABLED`) rather than `state`, and a workspace key sees only its own workspace.
- `limit` is 1 to 100, default 20. **`limit=100` never returns `nextCursor`; use 99 or less when paginating.**
- `sortOrder` is by creation time; only the exact string `desc` sorts descending.
- `labels=k=v,k2=v2` requires every pair to match exactly (AND). `prefix` is a case-insensitive name prefix. `query` is a case-insensitive substring. State filters take the enum string. Agents hide `STATE_ARCHIVED` and tool sets hide archived by default; pass `state=` to see them.

## Errors

Every error body is a `google.rpc.Status`:

```json
{"code": 3, "message": "validation failed", "details": [{
  "@type": "type.googleapis.com/google.rpc.BadRequest",
  "fieldViolations": [{"field": "spec.model_config.model_id", "description": "model_id must be a reference key in the form <provider-key-slug>.<model-slug> or a canonical model_ ID"}]}]}
```

| HTTP | `code` | Meaning | Typical `details` |
| --- | --- | --- | --- |
| 400 | 3 `INVALID_ARGUMENT` | validation, bad mask, unknown JSON field, unresolved filter ID | `BadRequest.fieldViolations[].field` (proto snake_case path) |
| 400 | 9 `FAILED_PRECONDITION` | wrong state: `continue` on a non-waiting objective, approve a call that is not waiting, locked account | message only |
| 403 | 7 `PERMISSION_DENIED` | auth, scope, workspace access, archived workspace, admin role | `ErrorInfo.reason`: `AUTH_TOKEN_INVALID`, `API_KEY_DISABLED`, `SCOPE_MISSING`, `WORKSPACE_ACCESS_DENIED`, `WORKSPACE_ARCHIVED`, `ADMIN_ROLE_REQUIRED`, `ENTITLEMENT_MISSING` |
| 404 | 5 `NOT_FOUND` | ID or external ID does not resolve in this workspace | none |
| 409 | 6 `ALREADY_EXISTS` | duplicate external ID or assignment | none |
| 429 | 8 `RESOURCE_EXHAUSTED` | plan limit (default plan: 1 variation per agent), widget message allowance | none; no `Retry-After` |
| 501 | 12 `UNIMPLEMENTED` | route exists in the spec but not on the server (`PATCH /v1/account/workspaces/{id}`, objective tasks) | |

## Resources: minimal bodies

Placeholders: workspace `development`, provider key slug `getting-started-key`. Every body below is `POST /v1/workspaces/development/<collection>` unless noted.

**Workspace secret** (`workspace_secrets`, also `tool_sets/{toolSetId}/secrets`): `{"metadata": {"name": "MCP_TOKEN"}, "spec": {"value": "…"}}`. Values are never returned; updating with a non-empty value rotates it. Reference as `{{ secrets.MCP_TOKEN }}`.

**Tool set** (`tool_sets`), `spec.adapter` union:

```json
{"metadata": {"name": "Support MCP", "externalId": "support-mcp"},
 "spec": {"adapter": {"type": "mcp", "mcp": {
   "url": "https://mcp.example.com/mcp",
   "headers": {"Authorization": "Bearer {{ secrets.MCP_TOKEN }}"},
   "toolApprovals": {"type": "always", "always": true},
   "includeTools": {"operator": "OPERATOR_OR", "filters": [{"attribute": "ATTRIBUTE_NAME", "matcher": {"type": "startsWith", "startsWith": "ticket_"}}]}}}}}
```

- `openapi`: `{"type": "openapi", "openapi": {"type": "url", "url": "https://api.example.com/openapi.json", "headers": {…}, "baseUrl": "https://…", "serverName": "…"}}` or `{"type": "uploadId", "uploadId": "upload_…"}` after an upload. The `url` variant takes the same `includeTools`, `excludeTools`, and `toolApprovals` as MCP. Re-synced hourly; the spec is fetched on create, and zero tools blocks the write.
- `http`: `{"type": "http", "http": {"baseUrl": "https://api.example.com", "headers": {…}}}`, then create each tool yourself.
- `bare`: `{"type": "bare", "bare": {"contentTimeout": "300s"}}`; calls park until you `:setContent` (default wait 24h).
- Synced sets (MCP, OpenAPI URL) reject manual tool create/update/delete; curate with `includeTools`/`excludeTools`, `toolApprovals` (`{"type": "always", "always": true}` or `{"type": "only", "only": <filter>}`), and per-tool `:omit`/`:restore`. Assigned tool sets cannot be deleted; archive them. MCP `justInTime.enabled` loads tools at objective start with the objective's secrets instead of background sync.

**Tool** (`tool_sets/{toolSetId}/tools`, HTTP and Bare sets only):

```json
{"metadata": {"name": "createTicket"},
 "spec": {"description": "Open a ticket", "requiresApproval": true,
   "parameters": {"type": "object", "properties": {"subject": {"type": "string"}}, "required": ["subject"]},
   "config": {"type": "http", "http": {"requestMethod": "POST", "path": "/tickets", "requestBodyContentType": "application/json", "requestBodyTemplate": "{\"subject\": \"{{ subject }}\"}"}}}}
```

Bare tools use `"config": {"type": "bare", "bare": {"alwaysSetResult": "Chart rendered."}}` to return fixed content instead of parking.

**Agent** (`agents`) with its default variation in one call:

```json
{"metadata": {"name": "Support Triager", "externalId": "support-triager"},
 "spec": {"variationSelectionMode": "VARIATION_SELECTION_MODE_RANDOM", "webhookEventsUrl": "https://app.example.com/cadenya"},
 "defaultVariation": {"metadata": {"name": "default", "externalId": "support-triager-default"},
   "spec": {"modelConfig": {"modelId": "getting-started-key.claude-opus-5", "temperature": 0.2},
            "systemPromptTemplate": "You triage support tickets for {{ system_prompt_data.customer_name }}.",
            "firstUserMessageTemplate": "{{ first_user_message_data.request }}",
            "constraints": {"maxToolCalls": 20, "inactivityTimeout": "3600s"},
            "compactionConfig": {"triggerThreshold": 0.75}}}}
```

- `modelId` is `<provider-key-externalId>.<model-externalId>` or a canonical `model_…` ID. Find the slug on `GET …/ai_provider_keys` (`metadata.externalId`, for example `getting-started-key`) and the model on `GET …/models?query=<substring>` (or `prefix=`, `aiProviderKeyId=`, `state=STATE_ENABLED`); each model has `metadata.externalId`, `spec.provider`, `spec.family`, and `spec.capabilities`. Sampling knobs are rejected when the model lacks the capability.
- Templates are Liquid; `{% %}` tags are allowed in prompts (not in headers). `spec.systemPromptDataSchema` (JSON Schema) validates `systemPromptData` and doubles as the tool schema when the agent is a sub-agent. `spec.outputDefinition` (JSON Schema) makes objectives finalize with structured `output`.
- Agents start `STATE_DRAFT`; `:publish` needs at least one variation, and **objectives require `STATE_PUBLISHED`**. `:unarchive` returns to draft. `variationSelectionMode` unspecified means weighted (Thompson sampling on feedback).
- Default plan: one variation per agent (429 beyond it). Variations live at `agents/{agentId}/variations`; the agent response does not include the variation, list it.

**Assignments** (`agents/{agentId}/variations/{variationId}/assignments`): `{"type": "toolSetId", "toolSetId": "support-mcp"}`, or `toolId`, or `subAgentId` (another agent as a tool). Response `id` (`avt_…`) is the DELETE handle; current assignments are in the variation's `info.assignments`. Memory: `…/memory_layer_assignments` with `{"memoryLayerId": "memlyr_…", "position": 0}` (lower position wins).

**Schedule** (`agents/{agentId}/schedules`, no cron strings): `{"metadata": {"name": "Daily"}, "spec": {"schedule": {"timezone": "America/New_York", "calendars": [{"hour": [{"start": 9}], "dayOfWeek": [{"start": 1, "end": 5}]}]}, "overlapPolicy": "OVERLAP_POLICY_SKIP", "firstUserMessage": "Run the daily report.", "systemPromptData": {}}}`. Intervals: `"intervals": [{"every": "1800s"}]` (1 minute floor). Each fire creates an objective with `externalId` `schedule:<id>:<unixNano>`; filter objectives by `agentScheduleId`.

**Objective** (`objectives`):

```json
{"agentId": "support-triager", "variationId": "support-triager-default",
 "metadata": {"externalId": "ticket-4821", "labels": {"source": "api"}},
 "systemPromptData": {"customer_name": "Ada"},
 "firstUserMessage": "Summarize the open tickets.",
 "secrets": [{"name": "MCP_TOKEN", "value": "per-user-token"}],
 "tenant": {"id": "acme-corp", "name": "Acme"}, "subject": {"id": "user-123"},
 "pinnedParameters": {"orgId": "acme-corp"},
 "episodicMemory": {"key": "customer-42"}}
```

The response carries the agent and variation under `configSnapshot` (there is no top-level `agentId`), plus `state`, `stateMessage`, `output`, and `info` counters. `agentId` and `systemPromptData` (`{}` is fine) are required; `firstUserMessage` or a variation `firstUserMessageTemplate` rendered from `firstUserMessageData` must produce text. `variationId` omitted means the agent's selection mode picks. `tenant`/`subject` upsert tenant records (subject needs tenant). `episodicMemory.key` is required when the agent has `enableEpisodicMemory` and rejected otherwise. Pinned parameters are removed from tool schemas and forced onto every call.

**Feedback** (`objectives/{id}/feedback`): `{"metadata": {}, "data": {"score": 1.0, "comment": "Accurate"}}`, score from -1.0 to 1.0; feeds weighted selection.

**Memory** (`memory_layers`, `memory_layers/{id}/entries`): layer `{"metadata": {"name": "Runbooks"}, "spec": {"type": "MEMORY_LAYER_TYPE_SKILLS"}}` (or `MEMORY_LAYER_TYPE_EPISODIC`); entry `{"metadata": {"name": "Postmortems"}, "spec": {"type": "content", "key": "skills/postmortem", "description": "Use when drafting a postmortem.", "content": "# …"}}` (or `"type": "uploadId"`). Keys are path-like (`^[a-zA-Z0-9!\-_.*'()/]+$`, no `cadenya/` or `system/` prefix). Agents read layers through the built-in `get_memory` and `search_memory` tools; episodic agents write with `store_memory`.

**API key** (`POST /v1/account/api_keys`): `{"metadata": {"name": "CI"}, "spec": {"permissions": ["objectives:manage", "agents:read"], "workspaceAssignments": [{"workspaceId": "workspace_…"}]}}`, or `"allWorkspaces": true` in place of the assignments; read `spec.token` from the response.

**Upload** (`uploads`): `{"metadata": {"name": "spec.json"}, "spec": {"filename": "spec.json", "contentType": "application/json", "sizeBytes": "20480"}}` returns `info.uploadUrl` (presigned PUT, 15 minutes; only on create). PUT the bytes with exactly that `Content-Type` and length, poll `GET …/uploads/{id}` until `status` is `UPLOAD_STATUS_COMPLETE`, then reference the ID from an OpenAPI tool set or memory entry.

**Widgets** (`widgets`): `{"metadata": {"name": "Support chat"}, "spec": {"agentId": "support-triager", "originAllowlist": ["https://app.example.com"]}}`; `info.host` is the embed host. **Widget sessions** (`widget_sessions`): `{"spec": {"widgetId": "wgt_…", "tenant": {"id": "acme-corp"}, "subject": {"id": "user-123"}, "expiresAt": "2026-08-28T12:00:00Z"}, "secrets": [...]}` returns `spec.token` once. **Tenants** are created by assertion only; `DELETE …/tenants/{id}` erases everything they own.

## Objective lifecycle and events

States: `STATE_PENDING` → `STATE_RUNNING` → `STATE_WAITING` (turn finished, awaiting `continue`) → back to `STATE_RUNNING`; terminal `STATE_FINALIZED` (structured output extracted or sub-objective done), `STATE_FAILED`, `STATE_CANCELLED`, `STATE_TIMED_OUT` (inactivity). The objective stays `STATE_RUNNING` while a tool call waits for approval or bare content.

- `POST …/objectives/{id}:continue` `{"message": "…"}` only from `STATE_WAITING`; returns the new `userMessage` event. Sub-objectives and schedule-driven objectives cannot be continued.
- `:compact` `{}` only from `STATE_WAITING`; running objectives compact themselves at `compactionConfig.triggerThreshold`.
- `:cancel` `{"reason": "…"}` is asynchronous: the response still shows the old state; poll for `STATE_CANCELLED` or the `cancelled` event.
- Tool approval: a tool with `requiresApproval` emits `toolApprovalRequested{toolCallId}` and waits up to 24h. `GET …/tool_calls?status=TOOL_CALL_STATUS_WAITING_FOR_APPROVAL`, then `:approve` `{}` or `:deny` `{"memo": "Use the read-only lookup instead."}`. Bare calls sit in `executionStatus=TOOL_CALL_EXECUTION_STATUS_WAITING_FOR_CONTENT` until `:setContent` `{"content": [{"type": "text", "text": {"text": "…"}}]}` (also `image`/`audio` blocks with base64 `data` and `mimeType`).
- Structured output lands in the objective's `output` once `STATE_FINALIZED`. Terminal objectives are hard-deleted after the account's retention TTL.

Events (`GET …/objectives/{id}/events?sortOrder=asc`, resumable with `sinceEventId`): `{"metadata": {"id": "objevt_…"}, "contextWindowId": "objwin_…", "data": {"type": "<kind>", "<kind>": {…}}}`. Kinds: `userMessage{content}`, `assistantMessage{content, toolCalls[]}`, `reasoning`, `toolApprovalRequested{toolCallId}`, `toolApproved`, `toolDenied{memo}`, `toolCalled{toolCallId, tool, arguments}`, `toolResult{toolCallId, result}`, `toolError{toolCallId, message}`, `memoryRead`, `contextWindowCompacted`, `subAgentSpawned`, `subAgentUpdated`, `notice`, `error{type, message}` (objective fails), `cancelled`, `timedOut`, `finalized{output}`. An `assistantMessage` with no `toolCalls` ends the turn.

## Streaming (SSE)

```http
GET /v1/workspaces/development/objectives/ticket-4821/events:stream
Authorization: Bearer …
Last-Event-ID: objevt_01M1338C9KQKAAB646W83TK8SS
```

- Frames: `event: <data.type>`, `id: objevt_…`, `data: <ObjectiveEvent JSON>`. Housekeeping frames `open` (once) and `ping` (every 15s) have no `id`.
- Without `Last-Event-ID` you receive only events created after connecting. With it, the server replays everything after that ID, then goes live; an unknown ID fails with 400 before the stream opens, so drop the header and backfill from the events list instead. To see history plus live without a gap: page through the events list, then stream from the newest ID (`GET …/events?sortOrder=desc&limit=1`).
- **The server never closes the stream** on a terminal state. Stop reading at `finalized`, `error`, `cancelled`, `timedOut`, or at a turn-ending `assistantMessage` if you only want one turn.
- Stream frames are trimmed: `toolResult` and `toolError` carry only `toolCallId`, and long `reasoning` content is dropped. Fetch bodies from `GET …/tool_calls/{toolCallId}` or the events list.
- Load balancers cut a connection at 10 minutes; reconnect with `Last-Event-ID`. Errors on this endpoint use `{"message": "…"}` bodies and 401 for bad credentials.

## Webhooks

Set `spec.webhookEventsUrl` (HTTPS) on an agent and Cadenya POSTs every objective event for that agent:

```json
{"type": "objective_event.tool_approval_requested", "timestamp": "2026-08-28T02:30:00Z",
 "data": {"agent": {…}, "agentVariation": {…}, "objective": {"id": "obj_…", "externalId": "ticket-4821"}, "objectiveEvent": {"metadata": {"id": "objevt_…"}, "data": {"type": "toolApprovalRequested", "toolApprovalRequested": {"toolCallId": "toolcall_…"}}}}}
```

- `type` is `objective_event.` plus the snake_case event kind: `user_message`, `assistant_message`, `reasoning`, `tool_approval_requested`, `tool_approved`, `tool_denied`, `tool_called`, `tool_result`, `tool_error`, `memory_read`, `context_window_compacted`, `sub_agent_spawned`, `sub_agent_updated`, `notice`, `error`, `cancelled`, `timed_out`, `finalized`.
- Standard Webhooks headers: `webhook-id` (`wh_…`, idempotency key), `webhook-timestamp` (unix seconds), `webhook-signature` (one or more space-separated `v1,<base64>` entries; one valid entry is enough). The signature is HMAC-SHA256 over the string `<id>.<timestamp>.<raw body>`, keyed with the base64-decoded part after the `whsec_` prefix of the account's `info.webhookEventsHmacSecret` (visible on `GET /v1/account`, rotated by `POST /v1/account:rotateWebhookSigningKey`). Verify against the raw body bytes, compare in constant time, and reject timestamps more than 5 minutes off.
- Delivery: 5 attempts with backoff, any non-2xx retries, a 410 disables that URL. Inspect attempts with `GET …/agents/{agentId}/webhook_deliveries?objectiveId=…`.

## Quick recipe (curl)

```sh
API=https://api.cadenya.com/v1/workspaces/development
H=(-H "Authorization: Bearer $CADENYA_API_KEY" -H "Content-Type: application/json")

curl -s "$API/agents/support-triager:publish" "${H[@]}" -d '{}'
obj=$(curl -s "$API/objectives" "${H[@]}" -d '{"agentId":"support-triager","systemPromptData":{"customer_name":"Ada"},"firstUserMessage":"Summarize the open tickets."}' | jq -r .metadata.id)
last=$(curl -s "$API/objectives/$obj/events?sortOrder=desc&limit=1" "${H[@]}" | jq -r '.items[0].metadata.id')
curl -sN "$API/objectives/$obj/events:stream" "${H[@]}" -H "Last-Event-ID: $last" | sed -un 's/^data: //p' | jq -c '{type: .data.type, text: .data.assistantMessage.content}'
curl -s "$API/objectives/$obj/feedback" "${H[@]}" -d '{"metadata":{},"data":{"score":1}}'
```

## Related skills

- `cadenya-cli`: the same API from a terminal (`cadenya schema <cmd>` prints exact request schemas; `--dry-run` prints bodies).
- `cadenya-typescript-sdk`, `cadenya-go-sdk`, `cadenya-python-sdk`, `cadenya-ruby-sdk`: typed clients with pagination, retries, streaming, and webhook verification built in.
