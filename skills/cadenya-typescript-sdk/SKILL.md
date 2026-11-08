---
name: cadenya-typescript-sdk
description: Build Cadenya integrations with the official TypeScript SDK, `@cadenya/cadenya` (ESM, zero dependencies, Node 18+, Bun, Deno, browsers). Covers client setup, resource method names, request body shapes, pagination, errors, SSE objective event streams, and Standard Webhooks verification. Use when writing or debugging TypeScript or JavaScript that imports `@cadenya/cadenya`, when a Node project needs to create tool sets, agents, or objectives, or when hitting `APIError`, `Missing 'workspaceId'`, `must not be blank when provided explicitly`, or `stream already consumed`.
---

# Cadenya TypeScript SDK usage

## Overview

`@cadenya/cadenya` is generated from the Cadenya OpenAPI contract, so method names, field names, and enum values match the REST API one-to-one: `client.<resource>.<method>(...)`. Every method signature is in the package's `api.md` (`node_modules/@cadenya/cadenya/api.md`); every type is exported from the package root.

For wire conventions shared by every client (IDs and external IDs, field masks, error codes, pagination, streaming semantics, webhooks) see the `cadenya-api` skill. This skill covers what is specific to TypeScript.

## Install and import

```sh
npm install @cadenya/cadenya
```

ESM only (`"type": "module"`, no `require`). Default and named exports both work; everything, including types, comes from the package root:

```ts
import Cadenya, { APIError, APIConnectionError, Webhooks } from '@cadenya/cadenya';
import type { Agent, ObjectiveEvent, ToolSetCreateParams } from '@cadenya/cadenya';
```

## Account and API key

- A person creates the account at https://app.cadenya.com/signup, and the Free plan needs no card. When there is no key yet, give your user that link.
- The API keys page, https://app.cadenya.com/account/apiKeys, lists the account's keys. Sign-up creates a default key that reaches every workspace. Set the key as `CADENYA_API_KEY`: the SDK reads its options and the environment, never the CLI's stored login.
- `(await client.profiles.whoami()).defaultWorkspace?.id` is the default workspace ID, the value for `CADENYA_WORKSPACE_ID`, and `cadenya workspaces list` lists the others.
- From a terminal, `cadenya auth login` signs in through the browser with a one-time code (see `cadenya-cli`).
- Keep tool sets, agents, variations, memory layers and widgets as YAML files in `.cadenya/` next to a `cadenya.yaml`, and apply them with `cadenya config apply` ([format](https://cadenya.com/docs/config-files), [GitHub Action](https://github.com/cadenya/cadenya-config-loader)). That keeps the setup in the repository instead of in a one-off provisioning script.

## Client

```ts
const client = new Cadenya();                       // reads env
const client = new Cadenya({ apiKey, workspaceId, maxRetries: 2, logLevel: 'debug' });
```

| Option | Env fallback | Default |
| --- | --- | --- |
| `apiKey` | `CADENYA_API_KEY` | required; missing everywhere throws at construction |
| `workspaceId` | `CADENYA_WORKSPACE_ID` | none; needed by every workspace-scoped call |
| `baseURL` | `CADENYA_BASE_URL` | `https://api.cadenya.com` |
| `webhookSecret` | `CADENYA_WEBHOOK_SECRET` | used by `client.webhooks.unwrap` |
| `timeout` | | 60 000 ms, covers the request through body decode |
| `maxRetries` | | 0 |
| `logLevel`, `logger` | | `'warn'`, `console` |
| `fetch`, `defaultHeaders` | | global `fetch`, none |

Rules:

- An option you pass explicitly but blank throws `"<name> must not be blank when provided explicitly; omit it to use the environment instead."` Omit it to fall back to env.
- `workspaceId` accepts `workspace_…` or the workspace's external ID (`development`). Every `*Params` object also takes `workspaceId` to override per call. With neither, the promise rejects with `Missing 'workspaceId': pass it in params, set it on the client, or set the CADENYA_WORKSPACE_ID environment variable.`

## Resources and method names

Method = operation verb with the resource words removed; `Get` is `retrieve`. The resource's own ID is the first positional argument; parent IDs come first for nested resources; the body or query is a single params object; `RequestOptions` is last.

```ts
client.agents.retrieve(id, params?, options?)
client.agents.variations.retrieve(agentId, id, params?, options?)
client.objectives.approveToolCall(objectiveId, toolCallId, params?, options?)
```

| Accessor | Notable methods |
| --- | --- |
| `accounts` | `retrieve`, `rotateChallengeToken`, `rotateWebhookSigningKey` |
| `profiles` | `whoami` |
| `workspaces` | `list` |
| `workspaceAdmin` | `listAccount`, `create`, `retrieve`, `update`, `archive`, `listMembers`, `addMember`, `removeMember`, `listProfiles` |
| `apiKeys` | `list`, `create`, `retrieve`, `update`, `delete`, `enable`, `disable`, `rotate`, `reveal`, `addWorkspace`, `removeWorkspace` (account keys) |
| `aiProviderKeys` | CRUD |
| `models` | `list`, `create`, `retrieve`, `update`, `enable`, `disable`, `swapOnVariations` (no `delete`) |
| `toolSets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive`, `listEvents`, `listUsage`, `retrieveOpenApiSpec` |
| `toolSets.tools` | `list`, `create`, `retrieve`, `update`, `delete`, `omit`, `restore` |
| `toolSets.secrets`, `workspaceSecrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `agents` | `list`, `create`, `retrieve`, `update`, `delete`, `publish`, `unpublish`, `archive`, `unarchive`, `listFeedback`, `listWebhookDeliveries` |
| `agents.variations` | `list`, `create`, `retrieve`, `update`, `delete`, `addAssignment`, `removeAssignment`, `addMemoryLayer`, `updateMemoryLayer`, `removeMemoryLayer` |
| `agents.schedules` | CRUD, `pause`, `resume`, `archive` |
| `objectives` | `list`, `create`, `createAndStream`, `retrieve`, `listEvents`, `streamEvents`, `continue`, `interrupt`, `cancel`, `compact`, `listQueuedActions`, `removeQueuedAction`, `listToolCalls`, `retrieveToolCall`, `approveToolCall`, `denyToolCall`, `setToolCallContent`, `listTools`, `listContextWindows`, `retrieveDiagnostics`, `listFeedback`, `createFeedback` |
| `memoryLayers`, `memoryLayers.entries` | CRUD |
| `tenants` | `list`, `retrieve`, `delete`, `listSubjects` |
| `widgets` | CRUD, `archive`, `unarchive` |
| `widgetSessions` | `list`, `create`, `retrieve`, `delete`, `revoke`, `deleteTenant` |
| `agentPools` | CRUD, `activate`, `deactivate`, `archive`, `unarchive` |
| `trustedEndpoints` | `list`, `create`, `retrieve`, `delete`, `verify` |
| `uploads` | `create`, `retrieve` |
| `toolSearch` | `searchOrSets` |
| `webhooks` | `unwrap` (pre-wired with `webhookSecret`) |

Params types are `<Singular><Op>Params` (`AgentCreateParams`, `ObjectiveStreamEventsParams`); model types keep their wire names (`Agent`, `AgentVariationSpec_ModelConfig`); enums are string literal unions (`'STATE_PUBLISHED'`). Types whose request shape differs from the response get a `Param` suffix (`CreateAgentVariationRequestParam`).

## Request bodies

Keys are camelCase exactly as on the wire. Resources take `{ metadata, spec }`; objectives are flat. Unions carry a `type` tag naming the populated key:

```ts
// Tool set: adapter union. Secrets interpolate as {{ secrets.NAME }} (workspace or tool set secret).
const toolSet = await client.toolSets.create({
  metadata: { name: 'Support MCP', externalId: 'support-mcp' },
  spec: {
    adapter: {
      type: 'mcp',
      mcp: {
        url: 'https://mcp.example.com/mcp',
        headers: { Authorization: 'Bearer {{ secrets.MCP_TOKEN }}' },
        toolApprovals: { type: 'always', always: true },   // every synced tool needs approval
      },
    },
  },
});

// Agent plus its default variation in one call. variationSelectionMode defaults to WEIGHTED.
const agent = await client.agents.create({
  metadata: { name: 'Support Triager', externalId: 'support-triager' },
  spec: { variationSelectionMode: 'VARIATION_SELECTION_MODE_RANDOM' },
  defaultVariation: {
    metadata: { name: 'default', externalId: 'support-triager-default' },
    spec: {
      systemPromptTemplate: 'You triage support tickets for {{ system_prompt_data.customer_name }}.',
      modelConfig: { modelId: 'getting-started-key.anthropic-claude-haiku-latest' }, // "<provider-key-external-id>.<model-external-id>" or model_…
      constraints: { maxToolCalls: 20, inactivityTimeout: '3600s' },  // durations are strings
    },
  },
});

// Assignment: the params object is the union itself. Tools attach to variations, not agents.
await client.agents.variations.addAssignment(agent.metadata.id, variationId, {
  type: 'toolSetId', toolSetId: toolSet.metadata.id,
});

// Objective
const objective = await client.objectives.create({
  agentId: 'external_id:support-triager',
  systemPromptData: { customer_name: 'Ada' },
  firstUserMessage: 'Summarize the open tickets.',
  metadata: { externalId: 'ticket-4821', labels: { source: 'api' } },
});
```

Other adapters: `{ type: 'openapi', openapi: { type: 'url', url } }` (or `{ type: 'uploadId', uploadId }`), `{ type: 'http', http: { baseUrl } }`, `{ type: 'bare', bare: {} }`. Doc comments inside the package that mention `${SECRET_NAME}` are stale; the server rejects `$` references and accepts only `{{ secrets.NAME }}`. The MCP and OpenAPI create checks the source live with resolved headers (it must list at least one tool), but skips that check when a header names a secret that does not exist yet. Create the secret first, or pass it in `spec.secrets: [{ name, value }]`, so a bad URL or token fails at create time.

`undefined` fields are dropped from the wire; read-only fields on `Param` types are stripped, so a fetched resource can be edited and sent back.

## Reads and pagination

List methods return `Promise<Page<T>>`: `items`, `nextCursor`, `hasNextPage()`, `getNextPage()`, and an async iterator that walks every page.

```ts
for await (const agent of await client.agents.list({ labels: 'env=prod', limit: 50 })) { … }
const page = await client.objectives.listEvents(objectiveId, { sortOrder: 'asc' });
```

List filters mirror the API query params (`limit`, `cursor`, `prefix`, `query`, `labels`, `state`, `sortOrder`, `includeInfo`).

## Updates

`update` sends `metadata`, `spec`, and `updateMask` (comma-separated camelCase paths). Only masked paths change; maps and lists are replaced whole.

```ts
await client.agents.update(agentId, {
  metadata: { name: 'Support Triager v2' },
  updateMask: 'metadata.name',
});
```

## Errors

Every class extends `Error` directly; check with `instanceof` (or `err.name`).

| Class | When | Fields |
| --- | --- | --- |
| `APIError` | non-2xx after retries | `status` (HTTP), `code` (google.rpc), `message`, `details` |
| `APIConnectionError` | fetch threw | `cause` |
| `APITimeoutError` | `timeout` elapsed | |
| `APIUserAbortError` | your `signal` aborted | |
| `APIRequestError` | body not serializable; no request sent | |
| `APIResponseError` | 2xx with empty, `null`, or malformed JSON | `status` |

```ts
try {
  await client.agents.retrieve('external_id:missing');
} catch (err) {
  if (err instanceof APIError && err.status === 404) { /* wrong workspace or external ID never set */ }
  else if (err instanceof APIError && err.status === 403) { /* key lacks scope; see err.details?.[0]?.reason (stream-endpoint errors carry no details) */ }
  else throw err;
}
```

Validation failures are `status === 400` with `message` `validation failed`; the reason is in `details`, a `google.rpc.BadRequest` with `fieldViolations[]` whose `field` is the proto path (`spec.model_config.model_id`) and `description` says what is wrong.

## Retries, timeouts, per-request options

`RequestOptions` (last argument): `timeout`, `maxRetries`, `signal`, `headers`, `lastEventId`, `reconnect`.

- Retries default to 0 and by default apply only to GET/HEAD/PUT/DELETE (408, 409, 429, 500, 502, 503, 504, connection errors), honoring `Retry-After`. Set `maxRetries` on the client to enable; set it on a single call to opt a POST/PATCH in.
- `timeout` of 0 or less disables the deadline. Streams bound only header acquisition; the body lives under your `signal`.

## Streaming objective events

Default: start and watch a new objective with `createAndStream`. It needs `metadata.externalId`, the idempotency key: a repeat of the request (including the SDK's automatic reconnect, which re-sends the POST) attaches to the objective that already has that external ID instead of starting another. The first frame is `{ type: 'objective', objective }`, every later one `{ type: 'event', event }`. The stream ends by itself once the objective settles (`OBJECTIVE_STATE_WAITING`, `FINALIZED`, `FAILED`, `CANCELLED`, or `TIMED_OUT`).

```ts
const SETTLED = new Set(['OBJECTIVE_STATE_WAITING', 'OBJECTIVE_STATE_FINALIZED', 'OBJECTIVE_STATE_FAILED', 'OBJECTIVE_STATE_CANCELLED', 'OBJECTIVE_STATE_TIMED_OUT']);

const stream = await client.objectives.createAndStream({
  agentId: 'external_id:support-triager',
  metadata: { externalId: 'ticket-4821' },
  systemPromptData: { customer_name: 'Ada' },
  firstUserMessage: 'Summarize the open tickets.',
});
let objectiveId = '';
for await (const frame of stream) {
  if (frame.type === 'objective') objectiveId = frame.objective.metadata.id;
  else handle(objectiveId, frame.event);
}

function handle(objectiveId: string, event: ObjectiveEvent): 'settled' | undefined {
  const data = event.data;                 // discriminated on data.type; payload sits under the same-named key
  switch (data.type) {
    case 'toolApprovalRequested':
      void client.objectives.approveToolCall(objectiveId, data.toolApprovalRequested.toolCallId);
      return;
    case 'assistantMessage':
      if (data.assistantMessage.content) console.log(data.assistantMessage.content);
      return;
    case 'finalized':
      console.log(data.finalized.output);
      return;
    case 'stateChanged':
      return SETTLED.has(data.stateChanged.toState) ? 'settled' : undefined;
  }
}
```

`OBJECTIVE_STATE_WAITING` means the turn ended: the objective waits for `continue` or the inactivity timeout. After `continue`, watch it again with `streamEvents`.

`streamEvents` attaches to an existing objective. Semantics you must code around:

- Without `lastEventId` it delivers only events that arrive after the connection opens. With `lastEventId`, the server replays everything after that event and then goes live.
- The server never closes this stream on its own. Break on a settling `stateChanged` and `close()`.
- Only durable `objevt_` IDs are resume points. The stream also yields heartbeat (`hb_`) and delta (`dlt_`) events; sending one of their IDs as `lastEventId` fails with 400 `Last-Event-ID must be a persisted objevt_ event ID`. `stream.lastEventId` only ever holds a durable ID (or the one you resumed from), so checkpoint with it rather than `event.metadata.id`.
- A stream is consumed once. Mid-stream transport drops reconnect from `stream.lastEventId` (5 attempts per outage); pass `{ reconnect: false }` to handle drops yourself (`APIConnectionError`).
- A clean end of stream (load balancers cut connections after about 10 minutes) ends the loop with no settling event and no reconnect. Reopen from `stream.lastEventId` in an outer loop until you have seen one.
- A replayed `toolApprovalRequested` for a call you already approved makes the approve call fail with 400 (code 9, `not waiting for approval`); treat that as already handled.

```ts
const history = await client.objectives.listEvents(objectiveId, { sortOrder: 'asc' });
let lastEventId: string | undefined;
let settled = false;
for await (const event of history) { if (handle(objectiveId, event)) settled = true; lastEventId = event.metadata.id; }

while (!settled) {
  const stream = await client.objectives.streamEvents(objectiveId, undefined, { lastEventId });
  try {
    for await (const event of stream) {
      if (handle(objectiveId, event) === 'settled') { settled = true; break; }
    }
  } finally {
    lastEventId = stream.lastEventId;
    await stream.close();
  }
}
```

`stream.events()` yields the raw `{ event, data, id }` envelopes instead of decoded payloads. Housekeeping frames (`open`, `ping`) are skipped.

## Webhooks

```ts
import express from 'express';
app.post('/cadenya', express.raw({ type: 'application/json' }), async (req, res) => {
  const event = await client.webhooks.unwrap(req.body.toString('utf8'), req.headers); // or new Webhooks(secret)
  // event.type is 'objective_event.tool_approval_requested' etc.; event.data.objective.id is the objective,
  // event.data.objectiveEvent.data.type the event kind (same union as the stream)
  res.sendStatus(200);
});
```

The `UnwrapWebhookEvent.type` union names only 14 kinds (message, tool, sub-agent, memory, reasoning, error, and `state_changed`), so a comparison against `'objective_event.finalized'` is a type error even though the delivery arrives; switch on `event.data.objectiveEvent.data.type`, which carries every kind.

Verification follows Standard Webhooks: headers `webhook-id`, `webhook-timestamp`, `webhook-signature` (`v1,<base64>`), HMAC-SHA256 over `id.timestamp.body`, secret `whsec_…` from `(await client.accounts.retrieve()).info.webhookEventsHmacSecret`, 5-minute tolerance. Pass the raw body bytes; a re-serialized body fails. Failures throw `WebhookVerificationError`.

## Raw responses and logging

`APIPromise`: `await` for the value, `.withResponse()` for `{ data, response }`, `.asResponse()` (call synchronously, before any `await`) for the unconsumed `Response`. List calls return plain promises.

`logLevel: 'debug'` logs one line per request and response (method, path, status, duration); headers and bodies are never logged.

## End to end

```ts
import Cadenya, { APIError } from '@cadenya/cadenya';

const client = new Cadenya({ workspaceId: 'development' });

const secret = await client.workspaceSecrets.create({ metadata: { name: 'MCP_TOKEN' }, spec: { value: process.env.MCP_TOKEN! } });
const toolSet = await client.toolSets.create({
  metadata: { name: 'Support MCP', externalId: 'support-mcp' },
  spec: { adapter: { type: 'mcp', mcp: { url: 'https://mcp.example.com/mcp', headers: { Authorization: 'Bearer {{ secrets.MCP_TOKEN }}' } } } },
});

const model = (await client.models.list({ prefix: 'anthropic', state: 'STATE_ENABLED', limit: 1 })).items[0];
if (!model) throw new Error('no enabled model matches');
const agent = await client.agents.create({
  metadata: { name: 'Support Triager', externalId: 'support-triager' },
  spec: { variationSelectionMode: 'VARIATION_SELECTION_MODE_RANDOM' },
  defaultVariation: {
    metadata: { name: 'default' },
    spec: { systemPromptTemplate: 'You triage tickets for {{ system_prompt_data.customer_name }}.', modelConfig: { modelId: model.metadata.id } },
  },
});
const variation = (await client.agents.variations.list(agent.metadata.id, { limit: 1 })).items[0]; // create returns the agent only
await client.agents.variations.addAssignment(agent.metadata.id, variation.metadata.id, { type: 'toolSetId', toolSetId: toolSet.metadata.id });
await client.agents.publish(agent.metadata.id);   // objectives on a STATE_DRAFT agent are rejected

const objective = await client.objectives.create({
  agentId: agent.metadata.id,
  systemPromptData: { customer_name: 'Ada' },
  firstUserMessage: 'Summarize the open tickets.',
});
// … watch it with streamEvents as above, or start it with createAndStream instead …
await client.objectives.createFeedback(objective.metadata.id, { metadata: {}, data: { score: 1, comment: 'Accurate summary' } });
await client.objectives.continue(objective.metadata.id, { message: 'Which one is most urgent?' });
```

## Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| `Missing 'workspaceId'` | no client default and none in params | set `CADENYA_WORKSPACE_ID`, `workspaceId` on the client, or `params.workspaceId` |
| 400 `validation failed`, field violation `agent_id`: `agent must be published to create an objective` | agent is `STATE_DRAFT` | `client.agents.publish(id)` |
| 400 on `spec.model_config.model_id` | wrong `modelId` form | `model_…` ID from `models.list`, or `<provider-key-external-id>.<model-external-id>` |
| 429 `the account has reached its plan's limit of N for agent_variations` | the plan caps variations across the whole account, every workspace (Free: 3); an agent's `defaultVariation` counts too | edit an existing variation, or archive agents you no longer use (their variations stop counting) |
| stream yields nothing for a finished objective | no `lastEventId` | replay with `listEvents({ sortOrder: 'asc' })`, then stream from the last ID |
| `stream already consumed` | iterated a `Stream` twice | open a new stream with `{ lastEventId: stream.lastEventId }` |
| `streamEvents` connection stays open after the objective settled | that stream never closes itself | `break` on a settling `stateChanged` and `close()`, or use `createAndStream` |
| 400 `metadata.externalId is required` from `createAndStream` | the idempotency key is missing | set `metadata.externalId` |
| 400 `Last-Event-ID must be a persisted objevt_ event ID` | resumed from a heartbeat or delta ID | resume from `stream.lastEventId` |
| POST silently not retried | retries apply to idempotent methods only | pass `{ maxRetries: n }` on that call |
| `legacy dollar references are not supported` | `${NAME}` or `$NAME` in a header | use `{{ secrets.NAME }}` |
| `agents.create` result has no variation ID | `Agent` carries only `info.variationCount` | `agents.variations.list(agentId)` |

## Related skills

- `cadenya-api`: wire conventions and per-resource request shapes.
- `cadenya-cli`: the same operations from a terminal; `cadenya … --dry-run` prints the exact JSON body the SDK sends.
