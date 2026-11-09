# Cadenya API: minimal request bodies per resource

Placeholders: workspace `development`, AI provider key external ID `getting-started-key`. Every body below is `POST /v1/workspaces/development/<collection>` unless noted.

## Contents

- [Trusted endpoint](#trusted-endpoint)
- [Secrets](#secrets)
- [Tool Set](#tool-set)
- [Tool](#tool)
- [Agent and default variation](#agent-and-default-variation)
- [Assignments](#assignments)
- [Agent pool](#agent-pool)
- [Schedule](#schedule)
- [Objective](#objective)
- [Feedback](#feedback)
- [Memory layers and entries](#memory-layers-and-entries)
- [API key](#api-key)
- [Upload](#upload)
- [Widgets, Widget sessions, tenants](#widgets-widget-sessions-tenants)

## Trusted endpoint

`POST /v1/account/trusted_endpoints`: `{"metadata": {"name": "Support MCP"}, "spec": {"host": "mcp.example.com"}}`.

- `host` is an exact host or a one-label wildcard (`*.acme.com`), with an optional port and no scheme or path.
- Every Tool Set request (validation, sync, tool calls, redirects) goes only to trusted hosts. Add the host **before** creating a Tool Set that points at it; otherwise the create is a 400 with `<host> is not a trusted endpoint: …` on the URL field.
- Check a URL with `POST /v1/account/trusted_endpoints:verify` `{"url": "https://mcp.example.com/mcp"}`. The result is `RESULT_TRUSTED`, `RESULT_UNTRUSTED`, or `RESULT_TEMPLATED` when the host comes from a template.

## Secrets

Workspace secret (`workspace_secrets`; Tool Set secret at `tool_sets/{toolSetId}/secrets`): `{"metadata": {"name": "MCP_TOKEN"}, "spec": {"value": "…"}}`.

- Values are never returned. Updating with a non-empty value rotates it.
- Reference it as `{{ secrets.MCP_TOKEN }}`. A Tool Set can also bring its own secrets in the create body (`spec.secrets`), so a separate secret call first is optional.

## Tool Set

`tool_sets`, with the `spec.adapter` union:

```json
{"metadata": {"name": "Support MCP", "externalId": "support-mcp"},
 "spec": {"adapter": {"type": "mcp", "mcp": {
   "url": "https://mcp.example.com/mcp",
   "headers": {"Authorization": "Bearer {{ secrets.MCP_TOKEN }}"},
   "toolApprovals": {"type": "always", "always": true},
   "includeTools": {"operator": "OPERATOR_OR", "filters": [{"attribute": "ATTRIBUTE_NAME", "matcher": {"type": "startsWith", "startsWith": "ticket_"}}]}}}}}
```

- `spec.secrets` (`[{"name": "…", "value": "…"}]`) creates Tool Set secrets in the same call.
- `openapi`: `{"type": "openapi", "openapi": {"type": "url", "url": "https://api.example.com/openapi.json", "headers": {…}, "baseUrl": "https://…", "serverName": "…"}}`, or `"type": "uploadId", "uploadId": "upload_…"` after an [upload](#upload). It takes the same `includeTools`, `excludeTools`, and `toolApprovals` as MCP.
- `http`: `{"type": "http", "http": {"baseUrl": "https://api.example.com", "headers": {…}}}`, then create each [tool](#tool) yourself.
- `bare`: `{"type": "bare", "bare": {"contentTimeout": "300s"}}`. Calls park until you `:setContent` (default wait 24h).
- MCP and OpenAPI sources are fetched on create, and a source that lists zero tools blocks the write. When a header references a secret that does not exist yet, that check is skipped and the source syncs once the secret exists. Sources re-sync hourly.
- Synced Tool Sets reject manual tool create, update and delete. Curate with `includeTools`/`excludeTools`, `toolApprovals` (`{"type": "always", "always": true}` or `{"type": "only", "only": <filter>}`), and per-tool `:omit`/`:restore`.
- Assigned Tool Sets cannot be deleted; archive them.
- MCP `justInTime.enabled` loads tools at objective start with the objective's secrets instead of background sync.
- Verify: `GET …/tool_sets/support-mcp/tools` lists the synced tools.

## Tool

`tool_sets/{toolSetId}/tools`, HTTP and Bare Tool Sets only:

```json
{"metadata": {"name": "createTicket"},
 "spec": {"description": "Open a ticket", "requiresApproval": true,
   "parameters": {"type": "object", "properties": {"subject": {"type": "string"}}, "required": ["subject"]},
   "config": {"type": "http", "http": {"requestMethod": "POST", "path": "/tickets", "requestBodyContentType": "application/json", "requestBodyTemplate": "{\"subject\": \"{{ subject }}\"}"}}}}
```

Bare tools use `"config": {"type": "bare", "bare": {"alwaysSetResult": "Chart rendered."}}` to return fixed content instead of parking.

## Agent and default variation

`agents`, with its default variation and assignments in one call:

```json
{"metadata": {"name": "Support Triager", "externalId": "support-triager"},
 "spec": {"webhookEventsUrl": "https://app.example.com/cadenya"},
 "defaultVariation": {"metadata": {"name": "default", "externalId": "support-triager-default"},
   "spec": {"modelConfig": {"modelId": "<provider-key-externalId>.<model-externalId>", "temperature": 0.2},
            "systemPromptTemplate": "You triage support tickets for {{ system_prompt_data.customer_name }}.",
            "firstUserMessageTemplate": "{{ first_user_message_data.request }}",
            "constraints": {"maxToolCalls": 20, "inactivityTimeout": "3600s"},
            "compactionConfig": {"triggerThreshold": 0.75},
            "assignments": [{"type": "toolSetId", "toolSetId": "support-mcp"}],
            "memoryLayerAssignments": [{"memoryLayerId": "runbooks", "position": 0}]}}}
```

- `modelId` is `<provider-key-externalId>.<model-externalId>` or a canonical `model_…` ID. Do not guess it: read the provider key's `metadata.externalId` from `GET …/ai_provider_keys` (for example `getting-started-key`), list models with `GET …/models?state=STATE_ENABLED` (filters: `query=` name contains, `prefix=` start of name, external ID or ID, `aiProviderKeyId=`), and use a returned model's `metadata.id`, or join the key's and the model's external IDs with a period. A model's external ID alone is not a valid `modelId`. Omit `modelId` on create to use the workspace default model; with no default the create is a 400 (`model_id is required; no default model is configured for this workspace`).
- Each model has `spec.provider`, `spec.family`, and `spec.capabilities`. Sampling knobs (such as `temperature`) are rejected when the model lacks the capability.
- Templates are Liquid; `{% %}` tags are allowed in prompts (not in headers). `spec.systemPromptDataSchema` (JSON Schema) validates `systemPromptData` and doubles as the tool schema when the Agent is a sub-agent. `spec.outputDefinition` (JSON Schema) makes objectives finalize with structured `output`.
- `spec.variationSelectionMode` is optional; unset means `VARIATION_SELECTION_MODE_WEIGHTED` (Thompson sampling on feedback).
- Agents start `STATE_DRAFT`. `:publish` needs at least one variation, and **objectives require `STATE_PUBLISHED`**. `:unarchive` returns the Agent to draft.
- Variations count toward an account-wide plan cap on non-archived variations, and `defaultVariation` counts too. Over the cap the create is 429 `the account has reached its plan's limit of N for agent_variations` with `ErrorInfo.reason` `ENTITLEMENT_LIMIT_REACHED`.
- Variations live at `agents/{agentId}/variations`. The Agent response does not include the variation; list it to verify.

## Assignments

Assignments live in the variation spec:

- `spec.assignments`: `toolSetId`, `toolId`, `subAgentId` (another Agent as a tool), or `agentPoolId`.
- `spec.memoryLayerAssignments`: `{memoryLayerId, position}`, at most 10; the lower position is consulted first.

Reads always return both, and `info.assignmentMetadata` names the targets. Replace the set with a masked PATCH (`updateMask: "spec.assignments"`), or change one target with `POST …/variations/{id}:addAssignment` / `:removeAssignment` `{"type": "toolSetId", "toolSetId": "support-mcp"}` and `:addMemoryLayer` / `:updateMemoryLayer` `{"memoryLayerId": "…", "position": 0}` (position optional on add, required on update) or `:removeMemoryLayer` `{"memoryLayerId": "…"}`. Each returns the updated variation.

## Agent pool

`agent_pools`:

```json
{"metadata": {"name": "Specialists"},
 "spec": {"description": "Route billing or shipping questions.",
   "assignments": [{"agentId": "agent_…"}, {"agentId": "agent_…"}],
   "instructions": "Pick the agent whose domain matches."}}
```

- Optional `spec.state` is the JSON Schema of the pool tool's input.
- Member `agentId`s and the variation's `agentPoolId` must be canonical IDs; external IDs are rejected there.
- Pools are created `AGENT_POOL_STATE_INACTIVE`; `:activate` needs at least one published member.
- Assign a pool to a variation as `{"type": "agentPoolId", "agentPoolId": "apool_…"}`. It appears as one callable tool that routes to a member.

## Schedule

`agents/{agentId}/schedules` (no cron strings):

```json
{"metadata": {"name": "Daily"},
 "spec": {"schedule": {"timezone": "America/New_York", "calendars": [{"hour": [{"start": 9}], "dayOfWeek": [{"start": 1, "end": 5}]}]},
   "overlapPolicy": "OVERLAP_POLICY_SKIP", "firstUserMessage": "Run the daily report.", "systemPromptData": {}}}
```

Intervals: `"intervals": [{"every": "1800s"}]` (1 minute floor). Each fire creates an objective with `externalId` `schedule:<id>:<unixNano>`; filter objectives by `agentScheduleId`.

## Objective

`objectives` (or `objectives:stream`, which also requires `metadata.externalId`):

```json
{"agentId": "support-triager", "variationId": "support-triager-default",
 "metadata": {"externalId": "ticket-4821", "labels": {"source": "api"}},
 "systemPromptData": {"customer_name": "Ada"},
 "firstUserMessage": "Summarize the open tickets.",
 "secrets": [{"name": "MCP_TOKEN", "value": "<per-user token from your secret store>"}],
 "tenant": {"id": "acme-corp", "name": "Acme"}, "subject": {"id": "user-123"},
 "pinnedParameters": {"orgId": "acme-corp"},
 "episodicMemory": {"key": "customer-42"}}
```

- The response carries the Agent and variation under `configSnapshot` (there is no top-level `agentId`), plus `state`, `stateMessage`, `output`, and `info` counters.
- `agentId` is required. An unpublished Agent is a 400 `validation failed` with the violation `agent must be published to create an objective`.
- `systemPromptData` must satisfy the Agent's `systemPromptDataSchema` when one is set.
- `firstUserMessage`, or a variation `firstUserMessageTemplate` rendered from `firstUserMessageData`, must produce text.
- `variationId` omitted means the Agent's selection mode picks.
- `tenant`/`subject` upsert tenant records (subject needs tenant).
- `episodicMemory.key` is required when the Agent has `enableEpisodicMemory` (unless `alwaysIncludeSubjectMemories` and a subject are set) and rejected otherwise.
- Pinned parameters are removed from tool schemas and forced onto every call.
- `clientTools` defines tools your app executes for this objective only.

## Feedback

`objectives/{id}/feedback`: `{"metadata": {}, "data": {"score": 1.0, "comment": "Accurate"}}`. The score runs from -1.0 to 1.0 and feeds weighted selection.

## Memory layers and entries

- Layer (`memory_layers`): `{"metadata": {"name": "Runbooks", "externalId": "runbooks"}, "spec": {"type": "MEMORY_LAYER_TYPE_SKILLS"}}`.
- Entry (`memory_layers/{id}/entries`): `{"metadata": {"name": "Postmortems"}, "spec": {"type": "content", "key": "skills/postmortem", "description": "Use when drafting a postmortem.", "content": "# …"}}`, or `"type": "uploadId"`.
- Keys are path-like (`^[a-zA-Z0-9!\-_.*'()/]+$`) and must not start with `cadenya/` or `system/`.
- Episodic layers (`MEMORY_LAYER_TYPE_EPISODIC`) are created by the system per episodic key; do not assign them.
- Agents read layers through the built-in `get_memory` and `search_memory` tools; episodic Agents write with `store_memory`.

## API key

`POST /v1/account/api_keys`: `{"metadata": {"name": "CI"}, "spec": {"permissions": ["objectives:manage", "agents:read"], "workspaceAssignments": [{"workspaceId": "workspace_…"}]}}`, or `"allWorkspaces": true` in place of the assignments. Read `spec.token` from the response once and store it in your secret manager.

## Upload

`uploads`: `{"metadata": {"name": "spec.json"}, "spec": {"filename": "spec.json", "contentType": "application/json", "sizeBytes": "20480"}}` (at most 100 MB).

1. The create response has `info.uploadUrl` (presigned PUT, valid 15 minutes, returned only on create).
2. PUT the bytes with exactly that `Content-Type` and length.
3. Poll `GET …/uploads/{id}` until `info.status` is `UPLOAD_STATUS_COMPLETE`.
4. Reference the ID once from an OpenAPI Tool Set or memory entry; it becomes `UPLOAD_STATUS_CONSUMED`.

## Widgets, Widget sessions, tenants

- Widget (`widgets`): `{"metadata": {"name": "Support chat"}, "spec": {"agentId": "support-triager", "originAllowlist": ["https://app.example.com"]}}`. `info.host` is the embed host. Widgets support `:archive`/`:unarchive`.
- Widget session (`widget_sessions`): `{"spec": {"widgetId": "wgt_…", "tenant": {"id": "acme-corp"}, "subject": {"id": "user-123"}, "expiresAt": "<RFC 3339 timestamp>"}, "secrets": [...]}`. Tenant and subject are required. The response returns `credentials` (`sessionId`, `host`, `token`, `tokenExpiresAt` at most 15 minutes out, `sessionExpiresAt`) once, for your backend to hand to the browser. See `cadenya-widgets` for the embed.
- Tenants are created by assertion only (objective or Widget session `tenant`). `DELETE …/tenants/{id}` erases everything they own.
