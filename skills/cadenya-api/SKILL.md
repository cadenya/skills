---
name: cadenya-api
description: Calls the Cadenya REST API directly over HTTPS (`https://api.cadenya.com/v1`) to manage workspaces, tool sets, tools, secrets, trusted endpoints, agents, variations, agent pools, schedules, objectives, tool calls, memory, models, API keys, tenants, widgets, and uploads. Covers bearer auth and scopes, ID and external-ID rules, the metadata/spec envelope, discriminated unions, field-mask updates, cursor pagination and filters, the google.rpc error shape, SSE event streams, Standard Webhooks, and the objective lifecycle. Use when building or debugging an integration with curl or a plain HTTP client, choosing endpoints and scopes, reading the OpenAPI spec, or decoding a 400/403/404/429 from Cadenya. The SDK and CLI skills build on this one; prefer them when the project already uses an SDK or the `cadenya` CLI.
---

# Cadenya API usage

## Overview

- Base URL `https://api.cadenya.com`, every route under `/v1`. OpenAPI 3.1 spec: `https://openapi.cadenya.com/api-spec.yml`. Reference pages: `https://cadenya.com/docs/api-reference`.
- JSON in and out, camelCase field names, gRPC-transcoded: every error is a `google.rpc.Status`, every list is `{ items, pagination }`, enums are `SCREAMING_SNAKE` strings with a type prefix (`STATE_PUBLISHED`, `OBJECTIVE_STATE_WAITING`).
- Almost everything lives under `/v1/workspaces/{workspaceId}/…`. Account-level routes: `GET /v1/whoami`, `GET /v1/workspaces`, `GET /v1/account`, `POST /v1/account:rotateWebhookSigningKey`, `/v1/account/api_keys…`, `/v1/account/trusted_endpoints…`, and `/v1/account/workspaces…` (admin role only; API keys cannot call these).
- The mental model: a **Tool Set** syncs tools from an MCP server, OpenAPI spec, or HTTP API (or is Bare and waits for your app), and may only call hosts on the account's **trusted endpoints**; an **Agent** has **Variations** (model, prompt, assigned tool sets, sub-agents, agent pools, memory layers); an **Objective** runs a variation against a message and emits **events**; you approve **tool calls**, `continue` the conversation, and submit **feedback**.

## Account and API key

- A person creates the account at https://app.cadenya.com/signup, and the Free plan needs no card. When a call fails for lack of a key, give your user that link.
- The API keys page, https://app.cadenya.com/account/apiKeys, lists the account's keys. Sign-up creates a default key with the external ID `default` that reaches every workspace (`GET /v1/account/api_keys/external_id:default` reads it).
- Set the key as `CADENYA_API_KEY`. `GET /v1/whoami` checks it and returns the default workspace as `defaultWorkspace.id`, the value for `CADENYA_WORKSPACE_ID`.
- From a terminal, `cadenya auth login` signs in through the browser with a one-time code (RFC 8628 device flow). See `cadenya-cli`.
- Keep tool sets, agents, variations, memory layers and widgets as YAML files in `.cadenya/` next to a `cadenya.yaml`, and apply them with `cadenya config apply` after `cadenya config plan` ([format](https://cadenya.com/docs/config-files), [GitHub Action](https://github.com/cadenya/cadenya-config-loader)). That keeps the setup in the repository instead of in a one-off provisioning script.

## Authentication and scopes

```
Authorization: Bearer <api key>
```

- API keys are JWTs (HS256, no expiry) that belong to the account. Create one with `POST /v1/account/api_keys` ([reference](https://cadenya.com/docs/api-reference/apikeyservice/create-a-new-api-key)), assigned to workspaces with `spec.workspaceAssignments` or to every workspace with `spec.allWorkspaces: true`. The raw token is `spec.token` in the create and rotate responses, and `POST /v1/account/api_keys/{id}:reveal` returns it again. Change the workspaces with `:addWorkspace` and `:removeWorkspace`; revoke with `:disable` or `:rotate`.
- The workspace is not in the token. A key reaches the workspaces assigned to it, or every workspace when `spec.allWorkspaces` is true, as for the default key. Using a key against another workspace is 403 `WORKSPACE_ACCESS_DENIED` with `metadata.workspace_id`, never 404.
- **Credential failures are HTTP 403 with code 7**, not 401: missing header, malformed token, bad signature, disabled key (`ErrorInfo.reason` is `AUTH_TOKEN_INVALID` or `API_KEY_DISABLED`). Two exceptions return 401: the SSE stream endpoints, and the key of a temporary workspace that has been claimed (`TEMPORARY_WORKSPACE_CLAIMED`). For all of them, the fix is a key from https://app.cadenya.com/account/apiKeys.
- Scopes are `resource:read` or `resource:manage` strings on the key (`spec.permissions`, up to 16): `agents`, `agent_pools`, `models`, `objectives`, `tools`, `memory`, `api_keys`, `workspaces`, `widgets`, `widget_sessions`, `tenants`, `endpoints` (trusted endpoints), plus manage-only `secrets` and `account`, or `*`. `manage` implies `read`, and `api_keys:admin` implies `api_keys:manage`: it is needed to create or change a key that reaches every workspace and to manage keys that other members created (`API_KEY_NOT_OWNED`). Models and AI provider keys use `models:*` (swapping a model on variations takes `agents:manage`), uploads use `objectives:*`, and all secret endpoints (even GET) need `secrets:manage`. A missing scope is 403 `SCOPE_MISSING` with `metadata.required_scope`. Keys can only mint or rotate keys with scopes and workspaces they hold (`SCOPE_NOT_HELD`, `WORKSPACE_NOT_HELD`).

## IDs and external IDs

- IDs are `<prefix>_<ULID>`: `workspace_`, `agent_`, `agentvar_`, `apool_` (agent pool), `as_` (schedule), `toolset_`, `tool_`, `toolsecret_`, `wsecret_`, `te_` (trusted endpoint), `memlyr_`, `mementry_`, `obj_`, `objevt_`, `objwin_`, `objqa_` (queued action), `toolcall_`, `objfb_`, `apikey_`, `aipk_`, `model_`, `tenant_`, `subj_`, `wgt_`, `wsess_`, `upload_`, `whkdlv_` (webhook delivery).
- Set `metadata.externalId` (≤64 chars, unique per parent) on create, then use it anywhere the API takes that resource's ID: path segments including `{workspaceId}`, body references such as `agentId`, `toolSetId` and `memoryLayerId`, and list filters (agent pool references are the exception). A bare value that does not start with the resource's own prefix is treated as an external ID; write `external_id:<value>` to force the lookup when your IDs look like Cadenya's.
- Unresolved path segment or objective `agentId`: 404 `not found`. Unresolved assignment target or list filter: 400 with a `fieldViolations` entry.
- Objects carry `metadata` (`id`, `accountId`, `workspaceId`, `name`, `externalId`, `labels`, `profileId`, `createdAt`, `updatedAt`), user-owned `spec`, read-only `info` (populated on lists only with `includeInfo=true`), and often a read-only `state`. Operations (objectives, events, tool calls, feedback, widget sessions) use `OperationMetadata`, which has no `name`.
- Create bodies take only `metadata.name` (required, ≤64), `metadata.externalId`, `metadata.labels` (≤10 pairs, K8s-shaped keys, values ≤63), and `spec`. **Sending a read-only field (`metadata.id`, `createdAt`, `state`, `info`) is a 400 from the transcoder.**

## Request conventions

- Discriminated unions carry `type` naming the populated key: `{"type": "mcp", "mcp": {…}}`, `{"type": "toolSetId", "toolSetId": "…"}`, event `data.type`. Both keys must agree.
- Custom verbs are `POST …/{id}:verb` with a `{}` body unless noted: `agents/{id}:publish|unpublish|archive|unarchive`, `agent_pools/{id}:activate|deactivate|archive|unarchive`, `agents/{agentId}/schedules/{id}:pause|resume|archive`, `agents/{agentId}/variations/{id}:addAssignment|removeAssignment|addMemoryLayer|updateMemoryLayer|removeMemoryLayer`, `api_keys/{id}:rotate|disable|enable`, `models/{id}:enable|disable`, `models:swapModelOnVariations`, `objectives/{id}:continue|interrupt|cancel|compact`, `objectives/{id}/tool_calls/{toolCallId}:approve|deny|setContent`, `objectives/{id}/queued_actions/{id}:remove`, `tool_sets/{id}:archive|unarchive`, `tool_sets/{toolSetId}/tools/{id}:omit|restore`, `widgets/{id}:archive|unarchive`, `widget_sessions/{id}:revoke`, `account/trusted_endpoints:verify`.
- Durations are strings in seconds (`"3600s"`), not integers, even where the spec says `integer`. `int64` fields such as `sizeBytes` are JSON strings.
- Secrets are referenced from tool set headers and base URLs as Liquid output `{{ secrets.NAME }}` (case-insensitive name; `${NAME}` is rejected). Resolution order, later wins: workspace secret, tool set secret, objective secret. An undefined name is a 400 (`references undefined secret`). Pinned parameters interpolate as `{{ pinnedParameters.key }}`. Field descriptions in the OpenAPI spec that mention `${SECRET_NAME}` or `pinned_parameters` are stale; the server enforces the forms given here.
- There is no general idempotency key and no dry-run mode. The one idempotent create is `POST …/objectives:stream`, keyed on `metadata.externalId`.
- Requests are rate limited per account; objective create, continue and compact, create-and-stream, and tool set create and update have a much smaller budget than the rest. A 429 from the limiter carries `RetryInfo` and a `retry-after` header; wait that long and retry.

## Updates (PATCH with a field mask)

```http
PATCH /v1/workspaces/development/agents/support-triager
{"metadata": {"name": "Support Triager v2"}, "updateMask": "metadata.name"}
```

- `updateMask` is a comma-separated string of camelCase dotted paths (`metadata.name,spec.description,metadata.labels`). Only masked paths change.
- Maps and lists (`metadata.labels`, `spec.overlays`, `spec.permissions`, `spec.assignments`, `spec.memoryLayerAssignments`) are replaced whole; a masked empty collection clears it. Map-key paths (`metadata.labels.env`) are invalid.
- Without a mask the server merges: set scalars overwrite, unset scalars are kept, and any collection you include replaces the stored one. You cannot clear a scalar without a mask. Masking `metadata` while omitting `externalId` clears the external ID, so round-trip the whole metadata object.
- An unknown path is 400 `invalid field mask`. When a body carries `metadata`, include `metadata.name`; when it carries a variation's `spec.modelConfig`, include `modelId`.

## Lists, pagination, filters

```http
GET /v1/workspaces/development/agents?limit=50&labels=env%3Dprod%2Cteam%3Dai&state=STATE_PUBLISHED&sortOrder=desc
```

- Response `{"items": [...], "pagination": {"nextCursor": "…"}}`. Fetch the next page with `cursor=<nextCursor>`; a missing or empty cursor means the last page. There is no total count. `GET /v1/workspaces` items carry `status` (`STATUS_ENABLED`) rather than `state`, and list only the workspaces the key reaches.
- `limit` is 1 to 100, default 20.
- `sortOrder` is `asc` or `desc` (by creation time; by sequence for events). Any other value is a 400.
- `labels=k=v,k2=v2` requires every pair to match exactly (AND). `prefix` is a case-insensitive name prefix. `query` is a case-insensitive substring. State filters take the enum string. Agents, agent pools and tool sets hide archived ones by default; pass `state=STATE_ARCHIVED` (pools: `AGENT_POOL_STATE_ARCHIVED`) to see them.

## Errors

Every error body is a `google.rpc.Status`:

```json
{"code": 3, "message": "validation failed", "details": [{
  "@type": "type.googleapis.com/google.rpc.BadRequest",
  "fieldViolations": [{"field": "spec.model_config.model_id", "description": "model_id must be a reference key in the form <provider-key-slug>.<model-slug> or a canonical model_ ID"}]}]}
```

| HTTP | `code` | Meaning | Typical `details` |
| --- | --- | --- | --- |
| 400 | 3 `INVALID_ARGUMENT` | validation, bad mask, unknown JSON field, unresolved filter or assignment target, untrusted tool set host, objective on an unpublished agent, `continue` on a non-waiting objective without `enqueue` | `BadRequest.fieldViolations[].field` (usually the proto snake_case path) |
| 400 | 9 `FAILED_PRECONDITION` | approve or deny a call that is not waiting, `:interrupt` on an objective that is not running, deleting an assigned agent pool, locked account, plan lacks the feature | message; `ErrorInfo.reason` `ENTITLEMENT_REQUIRED` with `metadata.feature` |
| 403 | 7 `PERMISSION_DENIED` | auth, scope, workspace access, archived workspace, admin role | `ErrorInfo.reason`: `AUTH_TOKEN_INVALID`, `API_KEY_DISABLED`, `SCOPE_MISSING`, `SCOPE_NOT_HELD`, `WORKSPACE_ACCESS_DENIED`, `WORKSPACE_NOT_HELD`, `API_KEY_NOT_OWNED`, `WORKSPACE_ARCHIVED`, `ADMIN_ROLE_REQUIRED` |
| 404 | 5 `NOT_FOUND` | ID or external ID does not resolve in this workspace | none |
| 409 | 6 `ALREADY_EXISTS` | duplicate external ID, assignment, or trusted host | none |
| 429 | 8 `RESOURCE_EXHAUSTED` | rate limit, or a plan limit | rate limit: `RetryInfo` and `retry-after`; plan limit: `ErrorInfo.reason` `ENTITLEMENT_LIMIT_REACHED` with `metadata.feature`, `limit`, `usage` (upgrade, do not retry) |

## Resources: minimal bodies

Placeholders: workspace `development`, provider key slug `getting-started-key`. Every body below is `POST /v1/workspaces/development/<collection>` unless noted.

**Trusted endpoint** (`POST /v1/account/trusted_endpoints`): `{"metadata": {"name": "Support MCP"}, "spec": {"host": "mcp.example.com"}}`. `host` is an exact host or a one-label wildcard (`*.acme.com`), optional port, no scheme or path. Every tool set request (validation, sync, tool calls, redirects) goes only to trusted hosts, so add the host **before** creating a tool set that points at it; otherwise the create is a 400 with `<host> is not a trusted endpoint: …` on the URL field. Check a URL with `POST /v1/account/trusted_endpoints:verify` `{"url": "https://mcp.example.com/mcp"}` (`RESULT_TRUSTED`, `RESULT_UNTRUSTED`, or `RESULT_TEMPLATED` when the host comes from a template).

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

- `spec.secrets` (`[{"name": "…", "value": "…"}]`) creates tool set secrets in the same call.
- `openapi`: `{"type": "openapi", "openapi": {"type": "url", "url": "https://api.example.com/openapi.json", "headers": {…}, "baseUrl": "https://…", "serverName": "…"}}`, or `"type": "uploadId", "uploadId": "upload_…"` after an upload. It takes the same `includeTools`, `excludeTools`, and `toolApprovals` as MCP.
- `http`: `{"type": "http", "http": {"baseUrl": "https://api.example.com", "headers": {…}}}`, then create each tool yourself.
- `bare`: `{"type": "bare", "bare": {"contentTimeout": "300s"}}`; calls park until you `:setContent` (default wait 24h).
- MCP and OpenAPI sources are fetched on create, and a source that lists zero tools blocks the write; they re-sync hourly. Synced sets reject manual tool create/update/delete; curate with `includeTools`/`excludeTools`, `toolApprovals` (`{"type": "always", "always": true}` or `{"type": "only", "only": <filter>}`), and per-tool `:omit`/`:restore`. Assigned tool sets cannot be deleted; archive them. MCP `justInTime.enabled` loads tools at objective start with the objective's secrets instead of background sync.

**Tool** (`tool_sets/{toolSetId}/tools`, HTTP and Bare sets only):

```json
{"metadata": {"name": "createTicket"},
 "spec": {"description": "Open a ticket", "requiresApproval": true,
   "parameters": {"type": "object", "properties": {"subject": {"type": "string"}}, "required": ["subject"]},
   "config": {"type": "http", "http": {"requestMethod": "POST", "path": "/tickets", "requestBodyContentType": "application/json", "requestBodyTemplate": "{\"subject\": \"{{ subject }}\"}"}}}}
```

Bare tools use `"config": {"type": "bare", "bare": {"alwaysSetResult": "Chart rendered."}}` to return fixed content instead of parking.

**Agent** (`agents`) with its default variation and assignments in one call:

```json
{"metadata": {"name": "Support Triager", "externalId": "support-triager"},
 "spec": {"variationSelectionMode": "VARIATION_SELECTION_MODE_RANDOM", "webhookEventsUrl": "https://app.example.com/cadenya"},
 "defaultVariation": {"metadata": {"name": "default", "externalId": "support-triager-default"},
   "spec": {"modelConfig": {"modelId": "getting-started-key.<model externalId>", "temperature": 0.2},
            "systemPromptTemplate": "You triage support tickets for {{ system_prompt_data.customer_name }}.",
            "firstUserMessageTemplate": "{{ first_user_message_data.request }}",
            "constraints": {"maxToolCalls": 20, "inactivityTimeout": "3600s"},
            "compactionConfig": {"triggerThreshold": 0.75},
            "assignments": [{"type": "toolSetId", "toolSetId": "support-mcp"}],
            "memoryLayerAssignments": [{"memoryLayerId": "runbooks", "position": 0}]}}}
```

- `modelId` is `<provider-key-externalId>.<model-externalId>` or a canonical `model_…` ID. Find the slug on `GET …/ai_provider_keys` (`metadata.externalId`, for example `getting-started-key`) and the model on `GET …/models?state=STATE_ENABLED` (or `query=`, `prefix=`, `aiProviderKeyId=`); copy the model's `metadata.externalId` rather than guessing it. Each model has `spec.provider`, `spec.family`, and `spec.capabilities`; sampling knobs are rejected when the model lacks the capability.
- Templates are Liquid; `{% %}` tags are allowed in prompts (not in headers). `spec.systemPromptDataSchema` (JSON Schema) validates `systemPromptData` and doubles as the tool schema when the agent is a sub-agent. `spec.outputDefinition` (JSON Schema) makes objectives finalize with structured `output`.
- Agents start `STATE_DRAFT`; `:publish` needs at least one variation, and **objectives require `STATE_PUBLISHED`**. `:unarchive` returns to draft. `variationSelectionMode` unspecified means weighted (Thompson sampling on feedback).
- Plans cap variations per agent (429 `ENTITLEMENT_LIMIT_REACHED`). Variations live at `agents/{agentId}/variations`; the agent response does not include the variation, list it.

**Assignments** live in the variation spec: `spec.assignments` (`toolSetId`, `toolId`, `subAgentId` for another agent as a tool, or `agentPoolId`) and `spec.memoryLayerAssignments` (`{memoryLayerId, position}`, ≤10, lower position consulted first). Reads always return both, and `info.assignmentMetadata` names the targets. Replace the set with a masked PATCH (`updateMask: "spec.assignments"`), or change one target with `:addAssignment` / `:removeAssignment` `{"type": "toolSetId", "toolSetId": "support-mcp"}` and `:addMemoryLayer` / `:updateMemoryLayer` / `:removeMemoryLayer` `{"memoryLayerId": "…", "position": 0}`. Each returns the updated variation.

**Agent pool** (`agent_pools`): `{"metadata": {"name": "Specialists"}, "spec": {"description": "Route billing or shipping questions.", "assignments": [{"agentId": "agent_…"}, {"agentId": "agent_…"}], "instructions": "Pick the agent whose domain matches."}}`; optional `spec.state` is the JSON Schema of the pool tool's input. Member `agentId`s and the variation's `agentPoolId` must be canonical IDs (external IDs are rejected there). Pools are created `AGENT_POOL_STATE_INACTIVE`; `:activate` needs at least one published member. Assign a pool to a variation as `{"type": "agentPoolId", "agentPoolId": "apool_…"}`; it appears as one callable tool that routes to a member.

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

The response carries the agent and variation under `configSnapshot` (there is no top-level `agentId`), plus `state`, `stateMessage`, `output`, and `info` counters. `agentId` is required; `systemPromptData` must satisfy the agent's `systemPromptDataSchema` when one is set; `firstUserMessage` or a variation `firstUserMessageTemplate` rendered from `firstUserMessageData` must produce text. `variationId` omitted means the agent's selection mode picks. `tenant`/`subject` upsert tenant records (subject needs tenant). `episodicMemory.key` is required when the agent has `enableEpisodicMemory` (unless `alwaysIncludeSubjectMemories` and a subject are set) and rejected otherwise. Pinned parameters are removed from tool schemas and forced onto every call. `clientTools` defines tools your app executes for this objective only.

**Feedback** (`objectives/{id}/feedback`): `{"metadata": {}, "data": {"score": 1.0, "comment": "Accurate"}}`, score from -1.0 to 1.0; feeds weighted selection.

**Memory** (`memory_layers`, `memory_layers/{id}/entries`): layer `{"metadata": {"name": "Runbooks", "externalId": "runbooks"}, "spec": {"type": "MEMORY_LAYER_TYPE_SKILLS"}}`; entry `{"metadata": {"name": "Postmortems"}, "spec": {"type": "content", "key": "skills/postmortem", "description": "Use when drafting a postmortem.", "content": "# …"}}` (or `"type": "uploadId"`). Keys are path-like (`^[a-zA-Z0-9!\-_.*'()/]+$`, no `cadenya/` or `system/` prefix). Episodic layers (`MEMORY_LAYER_TYPE_EPISODIC`) are created by the system per episodic key; do not assign them. Agents read layers through the built-in `get_memory` and `search_memory` tools; episodic agents write with `store_memory`.

**API key** (`POST /v1/account/api_keys`): `{"metadata": {"name": "CI"}, "spec": {"permissions": ["objectives:manage", "agents:read"], "workspaceAssignments": [{"workspaceId": "workspace_…"}]}}`, or `"allWorkspaces": true` in place of the assignments; read `spec.token` from the response.

**Upload** (`uploads`): `{"metadata": {"name": "spec.json"}, "spec": {"filename": "spec.json", "contentType": "application/json", "sizeBytes": "20480"}}` (≤100 MB) returns `info.uploadUrl` (presigned PUT, 15 minutes; only on create). PUT the bytes with exactly that `Content-Type` and length, poll `GET …/uploads/{id}` until `info.status` is `UPLOAD_STATUS_COMPLETE`, then reference the ID once from an OpenAPI tool set or memory entry (it becomes `UPLOAD_STATUS_CONSUMED`).

**Widgets** (`widgets`): `{"metadata": {"name": "Support chat"}, "spec": {"agentId": "support-triager", "originAllowlist": ["https://app.example.com"]}}`; `info.host` is the embed host. **Widget sessions** (`widget_sessions`): `{"spec": {"widgetId": "wgt_…", "tenant": {"id": "acme-corp"}, "subject": {"id": "user-123"}, "expiresAt": "2026-08-28T12:00:00Z"}, "secrets": [...]}` (tenant and subject required) returns `credentials` (`sessionId`, `host`, `token`, `tokenExpiresAt` at most 15 minutes out, `sessionExpiresAt`) once, for your backend to hand to the browser. **Tenants** are created by assertion only; `DELETE …/tenants/{id}` erases everything they own.

## Objective lifecycle and events

States: `OBJECTIVE_STATE_PENDING` → `OBJECTIVE_STATE_RUNNING` → `OBJECTIVE_STATE_WAITING` (turn finished, awaiting `continue`) → back to running; `OBJECTIVE_STATE_INTERRUPTING` while an interrupt settles; terminal `OBJECTIVE_STATE_FINALIZED` (structured output extracted or sub-objective done), `OBJECTIVE_STATE_FAILED`, `OBJECTIVE_STATE_CANCELLED`, `OBJECTIVE_STATE_TIMED_OUT` (inactivity). The objective stays running while a tool call waits for approval or bare content.

- `POST …/objectives/{id}:continue` `{"message": "…"}` from `OBJECTIVE_STATE_WAITING` returns `{"type": "event", "event": <userMessage>}`. With `"enqueue": true` a busy objective queues it instead and returns `{"type": "queuedAction", "queuedAction": {…}}`; list them at `GET …/queued_actions` and drop one with `…/queued_actions/{id}:remove` before the agent picks it up. Sub-objectives and schedule-driven objectives cannot be continued.
- `:interrupt` `{}` stops foreground work (tool calls, approval waits, foreground sub-agents) and returns the `interrupted` event; the objective goes to `OBJECTIVE_STATE_INTERRUPTING`, then `OBJECTIVE_STATE_WAITING`.
- `:compact` `{}` (optional `compactionConfig` override) returns a queued action: a waiting objective compacts now, a busy one before its next assistant turn. Running objectives also compact themselves at `compactionConfig.triggerThreshold`.
- `:cancel` `{"reason": "…"}` cancels a waiting or pending objective at once; a running one is cancelled asynchronously, so poll for `OBJECTIVE_STATE_CANCELLED` or the `cancelled` event.
- Tool approval: a tool with `requiresApproval` emits `toolApprovalRequested{toolCallId}` and waits up to 24h. `GET …/tool_calls?status=TOOL_CALL_STATUS_WAITING_FOR_APPROVAL`, then `:approve` `{}` or `:deny` `{"memo": "Use the read-only lookup instead."}`. Bare calls sit in `executionStatus=TOOL_CALL_EXECUTION_STATUS_WAITING_FOR_CONTENT` until `:setContent` `{"content": [{"type": "text", "text": {"text": "…"}}]}` (also `image`/`audio` blocks with base64 `data` and `mimeType`).
- Structured output lands in the objective's `output` once `OBJECTIVE_STATE_FINALIZED`. Terminal objectives are hard-deleted after the account's retention TTL.

Events (`GET …/objectives/{id}/events?sortOrder=asc`, resumable with `sinceEventId`): `{"metadata": {"id": "objevt_…"}, "contextWindowId": "objwin_…", "data": {"type": "<kind>", "<kind>": {…}}}`. Kinds: `userMessage{content}`, `assistantMessage{content, toolCalls[], completionId}`, `reasoning`, `toolApprovalRequested{toolCallId}`, `toolApproved`, `toolDenied{memo}`, `toolCalled{toolCallId, tool, arguments}`, `toolResult{toolCallId, result}`, `toolError{toolCallId, message}`, `memoryRead`, `contextWindowCompacted`, `subAgentSpawned`, `subAgentUpdated`, `notice`, `stateChanged{fromState, toState, message}`, `interrupted{message}`, `error{type, message}` (objective fails), `cancelled`, `timedOut`, `finalized{output}`. An `assistantMessage` with no `toolCalls` ends the turn.

## Streaming (SSE)

```http
GET /v1/workspaces/development/objectives/ticket-4821/events:stream?includeDeltas=true
Authorization: Bearer …
Last-Event-ID: objevt_01M1338C9KQKAAB646W83TK8SS
```

- Frames: `event: <data.type>`, `id: objevt_…`, `data: <ObjectiveEvent JSON>`. Frames without an `id` are never resume points: `open` (once) and `ping` (every 15s) housekeeping, `heartbeat` events (`hb_…`), and with `includeDeltas=true` the `assistantMessageDelta`/`reasoningDelta` text fragments (`dlt_…`). Concatenate deltas by `completionId`, then replace them with the durable `assistantMessage` or `reasoning` that carries the same `completionId`.
- Without `Last-Event-ID` you receive only events created after connecting. With it, the server replays everything after that ID, then goes live. A non-`objevt_` ID fails with 400 and an ID that is not an event of this objective with 409, both before the stream opens; drop the header and backfill from the events list instead. To see history plus live without a gap: page through the events list, then stream from the newest ID (`GET …/events?sortOrder=desc&limit=1`).
- **`events:stream` never closes** on a terminal state. Stop reading at `finalized`, `error`, `cancelled`, `timedOut`, or at a turn-ending `assistantMessage` if you only want one turn.
- `POST …/objectives:stream` takes the objective create body plus optional `includeDeltas`, with `metadata.externalId` **required**: it creates the objective (or attaches to the existing one with that external ID, resuming from `Last-Event-ID`) and streams it on the same response. The first frame is `event: objective` with `{"type": "objective", "objective": {…}}`; every later frame is `{"type": "event", "event": <ObjectiveEvent>}`. This stream ends by itself once the objective is waiting or terminal.
- Load balancers cut a connection at 10 minutes; reconnect with `Last-Event-ID`. Errors on these endpoints use `{"message": "…"}` bodies and 401 for bad credentials.

## Webhooks

Set `spec.webhookEventsUrl` (HTTPS) on an agent and Cadenya POSTs every durable objective event for that agent:

```json
{"type": "objective_event.tool_approval_requested", "timestamp": "2026-08-28T02:30:00Z",
 "data": {"agent": {…}, "agentVariation": {…}, "objective": {"id": "obj_…", "externalId": "ticket-4821"}, "objectiveEvent": {"metadata": {"id": "objevt_…"}, "data": {"type": "toolApprovalRequested", "toolApprovalRequested": {"toolCallId": "toolcall_…"}}}}}
```

- `type` is `objective_event.` plus the snake_case event kind: `user_message`, `assistant_message`, `reasoning`, `tool_approval_requested`, `tool_approved`, `tool_denied`, `tool_called`, `tool_result`, `tool_error`, `memory_read`, `context_window_compacted`, `sub_agent_spawned`, `sub_agent_updated`, `notice`, `state_changed`, `interrupted`, `error`, `cancelled`, `timed_out`, `finalized`. Heartbeats and deltas are never sent.
- Standard Webhooks headers: `webhook-id` (`wh_…`, idempotency key), `webhook-timestamp` (unix seconds), `webhook-signature` (one or more space-separated `v1,<base64>` entries; one valid entry is enough). The signature is HMAC-SHA256 over the string `<id>.<timestamp>.<raw body>`, keyed with the base64-decoded part after the `whsec_` prefix of the account's `info.webhookEventsHmacSecret` (visible on `GET /v1/account`, rotated by `POST /v1/account:rotateWebhookSigningKey`). Verify against the raw body bytes, compare in constant time, and reject timestamps more than 5 minutes off.
- Delivery: 5 attempts with backoff, any non-2xx retries, a 410 disables that URL. Inspect attempts with `GET …/agents/{agentId}/webhook_deliveries?objectiveId=…`.

## Quick recipe (curl)

```sh
API=https://api.cadenya.com/v1/workspaces/development
H=(-H "Authorization: Bearer $CADENYA_API_KEY" -H "Content-Type: application/json")

curl -s "$API/agents/support-triager:publish" "${H[@]}" -d '{}'
curl -sN "$API/objectives:stream" "${H[@]}" \
  -d '{"agentId":"support-triager","metadata":{"externalId":"ticket-4821"},"systemPromptData":{"customer_name":"Ada"},"firstUserMessage":"Summarize the open tickets."}' \
  | sed -un 's/^data: //p' | jq -c 'select(.type=="event") | {type: .event.data.type, text: .event.data.assistantMessage.content}'
curl -s "$API/objectives/ticket-4821/feedback" "${H[@]}" -d '{"metadata":{},"data":{"score":1}}'
```

Rerunning the stream call with the same `externalId` reattaches to the objective instead of starting another.

## Related skills

- `cadenya-cli`: the same API from a terminal (`cadenya schema <cmd>` prints exact request schemas; `--dry-run` prints bodies).
- `cadenya-typescript-sdk`, `cadenya-go-sdk`, `cadenya-python-sdk`, `cadenya-ruby-sdk`: typed clients with pagination, retries, streaming, and webhook verification built in.
