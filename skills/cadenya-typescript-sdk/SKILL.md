---
name: cadenya-typescript-sdk
description: Writes and debugs TypeScript or JavaScript that imports `@cadenya/cadenya`, the official Cadenya SDK (ESM, Node 18+). Covers client setup, method names, request body shapes, creating Tool Sets, Agents and objectives, pagination, errors, retries, objective event streams (`createAndStream`, `streamEvents`), and webhook verification. Use when code imports `@cadenya/cadenya`, when a Node project needs to call Cadenya, or when it hits `APIError`, `Missing 'workspaceId'`, `must not be blank when provided explicitly`, `stream already consumed`, or `Last-Event-ID must be a persisted objevt_ event ID`. Do not use for raw HTTP or other languages (cadenya-api, cadenya-go-sdk, cadenya-python-sdk, cadenya-ruby-sdk), terminal work (cadenya-cli), or embedding a chat in a web app (cadenya-widgets).
---

# Cadenya TypeScript SDK

`@cadenya/cadenya` is generated from the Cadenya API contract, so method names, field names and enum values match the REST API: `client.<resource>.<method>(...)`. Exact signatures are in `node_modules/@cadenya/cadenya/api.md`, and every type is exported from the package root. Wire conventions shared by every client (IDs, external IDs, field masks, error codes) are in the `cadenya-api` skill.

## Install and import

```sh
npm install @cadenya/cadenya
```

ESM only, no `require`. It has no dependencies and uses the global `fetch`.

```ts
import Cadenya, { APIError, APIConnectionError, Webhooks } from '@cadenya/cadenya';
import type { Agent, ObjectiveEvent, ToolSetCreateParams } from '@cadenya/cadenya';
```

## API key and workspace

- No account yet: give your user https://app.cadenya.com/signup (the Free plan needs no card). Keys are at https://app.cadenya.com/account/apiKeys.
- Put the key in `CADENYA_API_KEY`. Never hardcode it, and never ship it to a browser. The SDK reads only its options and the environment, never the CLI's stored login.
- `(await client.profiles.whoami()).defaultWorkspace?.id` is the default workspace, the value for `CADENYA_WORKSPACE_ID`.
- For setup that must be repeatable, keep Tool Sets, Agents, variations, memory layers and Widgets as YAML in `.cadenya/` and apply them with `cadenya config apply` ([format](https://cadenya.com/docs/config-files)). Use the SDK for runtime work.

## Client

```ts
const client = new Cadenya({ workspaceId: 'development', maxRetries: 2 }); // apiKey from CADENYA_API_KEY
```

| Option | Env fallback | Default |
| --- | --- | --- |
| `apiKey` | `CADENYA_API_KEY` | required; missing everywhere throws at construction |
| `workspaceId` | `CADENYA_WORKSPACE_ID` | none; every workspace-scoped call needs one |
| `baseURL` | `CADENYA_BASE_URL` | `https://api.cadenya.com` |
| `webhookSecret` | `CADENYA_WEBHOOK_SECRET` | used by `client.webhooks.unwrap` |
| `timeout` | | 60000 ms; 0 or less disables it |
| `maxRetries` | | 0 |
| `logLevel`, `logger` | | `'warn'`, `console` |
| `fetch`, `defaultHeaders` | | global `fetch`, none |

- An option passed explicitly but blank throws `<name> must not be blank when provided explicitly; omit it to use the environment instead.`
- `workspaceId` takes a `workspace_…` ID or the workspace's external ID. Every params object also takes `workspaceId` for one call. With neither, the call rejects with `Missing 'workspaceId': pass it in params, set it on the client, or set the CADENYA_WORKSPACE_ID environment variable.`

## Method and type names

- The method is the operation verb without the resource words; `Get` is `retrieve`.
- Positional arguments: parent IDs, then the resource's own ID, then one params object (body and query together), then `RequestOptions`.
  `client.agents.variations.retrieve(agentId, id, params?, options?)`
- Params types are `<Singular><Op>Params` (`AgentCreateParams`). Enums are string literal unions (`'STATE_PUBLISHED'`).

The full accessor and method list is in [references/resources.md](references/resources.md).

## Request bodies

- Keys are camelCase, as on the wire. Resources take `{ metadata, spec }`; objective create is flat.
- Unions carry a `type` tag that names the populated key: `{ type: 'mcp', mcp: { … } }`.
- `undefined` fields are dropped. `Param` types strip read-only fields, so a fetched resource can be edited and sent back.
- Durations are strings: `inactivityTimeout: '3600s'`.
- Tool Set adapters: `{ type: 'mcp', mcp: { url } }`, `{ type: 'openapi', openapi: { type: 'url', url } }` (or `{ type: 'uploadId', uploadId }`), `{ type: 'http', http: { baseUrl } }`, `{ type: 'bare', bare: {} }`.
- Secrets interpolate only as `{{ secrets.NAME }}`, from a workspace secret or the Tool Set's own `spec.secrets`. The package's doc comments mention `${SECRET_NAME}`; that form is rejected with `legacy dollar references are not supported`.
- Tools attach to variations, not Agents. `addAssignment` takes the union itself as params: `addAssignment(agentId, variationId, { type: 'toolSetId', toolSetId })`.

## Workflow: provision and run

- [ ] Create the Tool Set, with its secret in `spec.secrets`.
- [ ] Pick an enabled model with `models.list`. Do not hardcode a model ID: the catalog differs per workspace and provider key.
- [ ] Create the Agent and its default variation, with the Tool Set assigned, in one call.
- [ ] Publish the Agent. Objectives on a `STATE_DRAFT` Agent are rejected.
- [ ] Run an objective with `createAndStream`, and handle its events.
- [ ] Verify: the stream ended with a `stateChanged` to `OBJECTIVE_STATE_WAITING` or a terminal state.

```ts
import Cadenya from '@cadenya/cadenya';

const client = new Cadenya({ workspaceId: 'development' });

// MCP and OpenAPI creates check the source live and must find at least one tool.
// Passing the secret here makes a bad URL or token fail now, not at run time.
const toolSet = await client.toolSets.create({
  metadata: { name: 'Support MCP', externalId: 'support-mcp' },
  spec: {
    adapter: {
      type: 'mcp',
      mcp: {
        url: 'https://mcp.example.com/mcp',
        headers: { Authorization: 'Bearer {{ secrets.MCP_TOKEN }}' },
        toolApprovals: { type: 'always', always: true }, // every tool call waits for approval
      },
    },
    secrets: [{ name: 'MCP_TOKEN', value: process.env.MCP_TOKEN! }],
  },
});

// Narrow with { query: 'haiku' } (name contains) or { prefix } (start of name, external ID or ID).
const model = (await client.models.list({ state: 'STATE_ENABLED', limit: 1 })).items[0];
if (!model) throw new Error('no enabled model in this workspace');

const agent = await client.agents.create({
  metadata: { name: 'Support Triager', externalId: 'support-triager' },
  spec: {}, // variationSelectionMode defaults to WEIGHTED
  defaultVariation: {
    metadata: { name: 'default', externalId: 'support-triager-default' },
    spec: {
      systemPromptTemplate: 'You triage support tickets for {{ system_prompt_data.customer_name }}.',
      modelConfig: { modelId: model.metadata.id }, // or '<provider-key-external-id>.<model-external-id>'
      constraints: { maxToolCalls: 20, inactivityTimeout: '3600s' },
      assignments: [{ type: 'toolSetId', toolSetId: toolSet.metadata.id }],
    },
  },
});
await client.agents.publish(agent.metadata.id);
```

`agents.create` returns the Agent only (`info.variationCount`, no variation ID). Get the variation with `agents.variations.list(agentId)`.

Re-running this script fails with 409 `resource with the same identifier already exists`, because the external IDs are taken. Use `cadenya config apply` for repeatable setup.

## Streaming objective events

Start and watch an objective with `createAndStream`:

- It needs `metadata.externalId`, the idempotency key. A repeat of the request, including the SDK's automatic reconnect, attaches to the existing objective instead of starting another.
- The first frame is `{ type: 'objective', objective }`, and every later frame is `{ type: 'event', event }`.
- The stream ends by itself once the objective is `OBJECTIVE_STATE_WAITING` (the turn is over) or terminal (`FINALIZED`, `FAILED`, `CANCELLED`, `TIMED_OUT`).

```ts
import { APIError, type ObjectiveEvent } from '@cadenya/cadenya';

const SETTLED = new Set(['OBJECTIVE_STATE_WAITING', 'OBJECTIVE_STATE_FINALIZED', 'OBJECTIVE_STATE_FAILED', 'OBJECTIVE_STATE_CANCELLED', 'OBJECTIVE_STATE_TIMED_OUT']);

// Returns true once the objective has settled.
async function handle(objectiveId: string, event: ObjectiveEvent): Promise<boolean> {
  const data = event.data; // discriminated on data.type; the payload is under the same-named key
  switch (data.type) {
    case 'toolApprovalRequested':
      try {
        await client.objectives.approveToolCall(objectiveId, data.toolApprovalRequested.toolCallId);
      } catch (err) {
        // A replayed request for a call already approved fails with 400 `not waiting for approval`.
        if (!(err instanceof APIError && err.status === 400)) throw err;
      }
      return false;
    case 'assistantMessage':
      if (data.assistantMessage.content) console.log(data.assistantMessage.content);
      return false;
    case 'stateChanged':
      return SETTLED.has(data.stateChanged.toState);
    default:
      return false;
  }
}

const stream = await client.objectives.createAndStream({
  agentId: 'external_id:support-triager',
  metadata: { externalId: 'ticket-4821' },
  systemPromptData: { customer_name: 'Ada' },
  firstUserMessage: 'Summarize the open tickets.',
});
let objectiveId = '';
for await (const frame of stream) {
  if (frame.type === 'objective') objectiveId = frame.objective.metadata.id;
  else await handle(objectiveId, frame.event);
}
let lastEventId = stream.lastEventId; // checkpoint for the next turn
```

To send the next turn, call `continue`, then watch with `streamEvents` from the checkpoint:

```ts
await client.objectives.continue(objectiveId, { message: 'Which one is most urgent?' });

let settled = false;
while (!settled) {
  const turn = await client.objectives.streamEvents(objectiveId, undefined, { lastEventId });
  try {
    for await (const event of turn) {
      if (await handle(objectiveId, event)) { settled = true; break; }
    }
  } finally {
    lastEventId = turn.lastEventId;
    await turn.close();
  }
}
```

`streamEvents` attaches to an existing objective. Code around these rules:

- Without `lastEventId` it delivers only events that arrive after it connects. With `lastEventId` it replays everything after that event, then goes live. For an objective you have no checkpoint for, read `listEvents(id, { sortOrder: 'asc' })` first and resume from the last item's `metadata.id`.
- The server never closes this stream. Break on a settling `stateChanged`, then `close()`.
- Only persisted `objevt_` IDs are resume points. The stream also yields heartbeat (`hb_`) and delta (`dlt_`) events, and resuming from one of their IDs fails with 400 `Last-Event-ID must be a persisted objevt_ event ID`. `stream.lastEventId` holds only persisted IDs, so checkpoint with it, not with `event.metadata.id`.
- A transport drop mid-stream reconnects from `stream.lastEventId`, up to 5 attempts per outage. Pass `{ reconnect: false }` to get `APIConnectionError` and handle drops yourself.
- Connections are cut after about 10 minutes. A clean end does not reconnect, and the loop ends without a settling event. The outer `while` above reopens from the checkpoint.
- A `Stream` can be iterated once. `stream.events()` yields the raw `{ event, data, id }` envelopes instead of decoded events.

## Reads, pagination and updates

List methods return `Promise<Page<T>>` with `items`, `nextCursor`, `hasNextPage()`, `getNextPage()`, and an async iterator over every page. Filters mirror the API query (`limit`, `cursor`, `prefix`, `query`, `labels`, `state`, `sortOrder`, `includeInfo`).

```ts
for await (const agent of await client.agents.list({ labels: 'env=prod', limit: 50 })) console.log(agent.metadata.id);
```

`update` sends `metadata`, `spec` and `updateMask` (comma-separated camelCase paths). Only masked paths change, and maps and lists are replaced whole. Verify with `retrieve` afterwards.

```ts
await client.agents.update(agentId, { metadata: { name: 'Support Triager v2' }, updateMask: 'metadata.name' });
```

## Errors, retries and options

Every error class extends `Error`; check with `instanceof`.

| Class | When | Fields |
| --- | --- | --- |
| `APIError` | non-2xx after retries | `status` (HTTP), `code` (google.rpc), `message`, `details` |
| `APIConnectionError` | `fetch` threw | `cause` |
| `APITimeoutError` | `timeout` elapsed | |
| `APIUserAbortError` | your `signal` aborted | |
| `APIRequestError` | body not serializable; nothing sent | |
| `APIResponseError` | 2xx with empty, `null` or malformed JSON | `status` |

- 400 with `message` `validation failed`: `details` holds a `google.rpc.BadRequest` whose `fieldViolations[]` give the proto path (`spec.model_config.model_id`) and a `description`.
- 403: the key lacks a scope; `err.details?.[0]?.reason` names it (for example `SCOPE_MISSING`). Errors from stream endpoints carry only `message`, with no `details`.
- 404 on an `external_id:` lookup: wrong workspace, or the external ID was never set.

`RequestOptions`, the last argument: `timeout`, `maxRetries`, `signal`, `headers`, `lastEventId`, `reconnect`.

- Retries are off by default (`maxRetries: 0`). When enabled, they cover GET, HEAD, PUT and DELETE on 408, 409, 429, 500, 502, 503, 504 and connection errors, and honor `Retry-After`. A POST or PATCH retries only when that call passes `{ maxRetries: n }`.
- For streams, `timeout` bounds only getting the response headers; the body runs until your `signal` aborts.
- `await` gives the value; `.withResponse()` gives `{ data, response }`; `.asResponse()`, called before any `await`, gives the raw `Response`. List methods return plain promises.
- `logLevel: 'debug'` logs one line per request and response (method, path, status, duration), never headers or bodies.

## Webhooks

```ts
app.post('/cadenya', express.raw({ type: 'application/json' }), async (req, res) => {
  const event = await client.webhooks.unwrap(req.body.toString('utf8'), req.headers); // or new Webhooks(secret).unwrap
  switch (event.data.objectiveEvent.data.type) { // every event kind, the same union as the stream
    case 'toolApprovalRequested': /* event.data.objective.id is the objective */ break;
  }
  res.sendStatus(200);
});
```

- Verification is Standard Webhooks: headers `webhook-id`, `webhook-timestamp` and `webhook-signature`, HMAC-SHA256, 300-second tolerance. Failures throw `WebhookVerificationError`.
- Pass the raw body. A re-serialized JSON body fails verification.
- The secret starts with `whsec_` and comes from `(await client.accounts.retrieve()).info.webhookEventsHmacSecret`. Put it in `CADENYA_WEBHOOK_SECRET`.
- `event.type` (`'objective_event.tool_approval_requested'`, …) is typed for only 14 kinds, so comparing it with `'objective_event.finalized'` is a type error although that delivery arrives. Switch on `event.data.objectiveEvent.data.type`.

## Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| 400 `validation failed` on `agent_id`: `agent must be published to create an objective` | Agent is `STATE_DRAFT` | `client.agents.publish(id)` |
| 400 on `spec.model_config.model_id` | wrong form, or model disabled | a `model_…` ID from `models.list({ state: 'STATE_ENABLED' })`, or `<provider-key-external-id>.<model-external-id>` |
| 429 `the account has reached its plan's limit of N for agent_variations` | the plan caps non-archived variations across the whole account; `defaultVariation` counts | edit an existing variation, or archive unused Agents |
| 409 `resource with the same identifier already exists` | the external ID is taken | `retrieve('external_id:…')` and `update`, or `cadenya config apply` |
| 400 `metadata.externalId is required` from `createAndStream` | no idempotency key | set `metadata.externalId` |
| `streamEvents` yields nothing for a settled objective | no `lastEventId` | replay with `listEvents`, then stream from the last ID |
| `streamEvents` never ends | that stream never closes | break on a settling `stateChanged` and `close()` |
| `stream already consumed` | iterated a `Stream` twice | open a new stream with `{ lastEventId: stream.lastEventId }` |
| POST not retried | retries cover idempotent methods only | pass `{ maxRetries: n }` on that call |

## Related skills

- `cadenya-api`: wire conventions and per-resource request shapes.
- `cadenya-cli`: the same operations from a terminal. `cadenya … --dry-run` prints the JSON body a request sends.
- `cadenya-widgets`: minting Widget Sessions with this SDK for a browser chat.
