---
name: cadenya-go-sdk
description: "Writes and debugs Go code that imports `go.cadenya.com/cadenya-go`, the official Cadenya Go SDK (Go 1.22+). Covers client options, resource accessors and method names, params structs, builders and unions, pagination, `*APIError` handling, objective event streams (`CreateAndStream`, `StreamEvents`), and Standard Webhooks verification. Use when a Go service creates Tool Sets, Agents, variations, or objectives, or when Go code hits `cadenya: missing API key`, `cadenya: missing \"workspaceId\"`, `must not be blank`, or an `*APIError` to classify. Not for other languages (use the TypeScript, Python, or Ruby SDK skills), raw HTTP (`cadenya-api`), or terminal work (`cadenya-cli`)."
---

# Cadenya Go SDK

`go.cadenya.com/cadenya-go` (package `cadenya`) is generated from the Cadenya OpenAPI contract, so accessors, methods, fields, and enum values match the REST API one-to-one. Every signature is in the module's `api.md`; `go doc go.cadenya.com/cadenya-go` lists the types. Wire conventions shared by every client (IDs and external IDs, field masks, error codes, streaming semantics) are in the `cadenya-api` skill.

## Install and construct

```sh
go get go.cadenya.com/cadenya-go
```

```go
client, err := cadenya.NewClient() // reads CADENYA_API_KEY, CADENYA_WORKSPACE_ID, ...
client, err = cadenya.NewClient(cadenya.WithAPIKey(key), cadenya.WithWorkspaceID("development"), cadenya.WithMaxRetries(2))
```

| Option | Env fallback | Notes |
| --- | --- | --- |
| `WithAPIKey` | `CADENYA_API_KEY` | required; missing everywhere returns `cadenya: missing API key: pass WithAPIKey or set CADENYA_API_KEY` |
| `WithWorkspaceID` | `CADENYA_WORKSPACE_ID` | `workspace_…` or the workspace external ID; default for every workspace-scoped call |
| `WithBaseURL` | `CADENYA_BASE_URL` | default `https://api.cadenya.com` |
| `WithWebhookSecret` | `CADENYA_WEBHOOK_SECRET` | for `client.Webhooks().Unwrap` |
| `WithMaxRetries(n)` | | default 0 |
| `WithHTTPClient(*http.Client)` | | the default has no `Timeout`, so streams can outlive it |
| `WithDebugLog(io.Writer)` | | logs every exchange with `Authorization: [redacted]`; SSE bodies are not consumed |

An option passed explicitly but blank returns `cadenya: <name> must not be blank`; omit it to fall back to the environment. There is no `WithTimeout`: non-stream calls get a 60 s deadline when `ctx` has none, so set your own with `context.WithTimeout`.

## API key and workspace

- A person creates the account at https://app.cadenya.com/signup (the Free plan needs no card). If there is no key yet, give your user that link.
- Keys are at https://app.cadenya.com/account/apiKeys. Put the key in `CADENYA_API_KEY` or a secret manager, never in code. The SDK never reads the CLI's stored login.
- `client.Profiles().Whoami(ctx)` returns `DefaultWorkspace.ID`, the value for `CADENYA_WORKSPACE_ID`.
- For setup that should live in the repository (Tool Sets, Agents, variations, memory layers, Widgets), prefer YAML in `.cadenya/` applied with `cadenya config apply` ([format](https://cadenya.com/docs/config-files)) over a one-off provisioning program.

## Accessors and methods

Accessors are methods on `*Client` that return interfaces, so they can be mocked: `Agents()`, `AgentPools()`, `ToolSets()`, `Objectives()`, `APIKeys()`, `AIProviderKeys()`, `WorkspaceSecrets()`, `MemoryLayers()`, `Models()`, `Tenants()`, `Widgets()`, `WidgetSessions()`, `Uploads()`, `TrustedEndpoints()`, `Workspaces()`, `WorkspaceAdmin()`, `Profiles()`, `Accounts()`, `ToolSearch()`, `Webhooks()`. Nested: `Agents().Variations()`, `Agents().Schedules()`, `ToolSets().Tools()`, `ToolSets().Secrets()`, `MemoryLayers().Entries()`.

Methods take `(ctx, <path IDs in order>, params *XParams, opts ...RequestOption)`, and `params` may be `nil`. A few take no params (`Accounts().Retrieve(ctx)`, `Profiles().Whoami(ctx)`, `APIKeys().Retrieve(ctx, id)`). Initialisms are upper-cased (`WorkspaceID`, `ToolSetID`, `OpenAPI`), and Get is `Retrieve`.

```go
client.Agents().Variations().Retrieve(ctx, agentID, variationID, nil)
client.Objectives().ApproveToolCall(ctx, objectiveID, toolCallID, nil)
client.Objectives().Continue(ctx, objectiveID, &cadenya.ObjectiveContinueParams{Message: "…"})
```

Params structs are `<Singular><Op>Params` (`AgentCreateParams`, `ObjectiveListParams`), each with a fluent `<Singular><Op>Builder` ending in `.ToParams()`. Every one has `WorkspaceID *string` to override the client default for one call.

## Request bodies

- Required scalars are plain fields; optional scalars are `omitempty` pointers, set with `cadenya.String`, `cadenya.Int32`, `cadenya.Bool`, `cadenya.Float64`, or `cadenya.Ptr[T]`. A nil pointer is omitted; there is no way to send JSON `null`.
- Resources nest `Metadata`, `Spec`, `Info` (and sometimes `State`). Enums are typed string constants named type + wire value: `cadenya.AgentStateStatePublished`, `cadenya.ObjectiveStateChangedToStateObjectiveStateWaiting`.
- Unions are structs with one pointer per variant, and constructors set the `type` tag: `cadenya.NewToolSetAdapterMCP(...)`, `cadenya.NewAddAgentVariationAssignmentRequestParamToolSetID(...)`. Setting two variants fails at marshal time.
- Request types whose shape differs from the response type get a `Param` suffix (`CreateAgentVariationRequestParam`).
- Durations are strings (`"3600s"`).

```go
// Tool Set. Headers reference secrets as {{ secrets.NAME }}; ${NAME} is rejected.
// Spec.Secrets stores tool-set-scoped secrets in the same call, so the live source check can use them.
toolSet, err := client.ToolSets().Create(ctx, &cadenya.ToolSetCreateParams{
    Metadata: &cadenya.CreateResourceMetadata{Name: "Support MCP", ExternalID: cadenya.String("support-mcp")},
    Spec: &cadenya.ToolSetSpec{
        Secrets: []cadenya.ToolSetSpec_Secret{{Name: "MCP_TOKEN", Value: cadenya.String(os.Getenv("MCP_TOKEN"))}},
        Adapter: cadenya.Ptr(cadenya.NewToolSetAdapterMCP(cadenya.ToolSetAdapter_MCPVariant{
            MCP: &cadenya.ToolSetAdapter_MCP{
                URL:     cadenya.String("https://mcp.example.com/mcp"),
                Headers: map[string]string{"Authorization": "Bearer {{ secrets.MCP_TOKEN }}"},
                ToolApprovals: cadenya.Ptr(cadenya.NewToolSetAdapter_ApprovalRequirementFilterAlways(
                    cadenya.ToolSetAdapter_ApprovalRequirementFilter_Always{Always: true})),
            },
        })),
    },
})

// Pick a model that exists in this workspace instead of hardcoding one.
models, err := client.Models().List(ctx, (&cadenya.ModelListBuilder{}).
    State(cadenya.ModelServiceListModelsStateStateEnabled).Limit(20).ToParams())
if len(models.Items) == 0 { return errors.New("no enabled models; omit ModelConfig to use the workspace default") }
modelID := models.Items[0].Metadata.ID // or "<provider-key-external-id>.<model-external-id>"

// Agent plus its default variation in one call. VariationSelectionMode defaults to WEIGHTED.
agent, err := client.Agents().Create(ctx, (&cadenya.AgentCreateBuilder{}).
    Metadata(&cadenya.CreateResourceMetadata{Name: "Support Triager", ExternalID: cadenya.String("support-triager")}).
    Spec(&cadenya.AgentSpec{Description: cadenya.String("Triages support tickets")}).
    DefaultVariation(&cadenya.CreateAgentVariationRequestParam{
        Metadata: &cadenya.CreateResourceMetadata{Name: "default"},
        Spec: &cadenya.AgentVariationSpec{
            SystemPromptTemplate: cadenya.String("You triage support tickets for {{ system_prompt_data.customer_name }}."),
            ModelConfig:          &cadenya.AgentVariationSpec_ModelConfig{ModelID: modelID},
            Constraints:          &cadenya.AgentVariationSpec_Constraints{InactivityTimeout: cadenya.String("3600s")},
        },
    }).ToParams())

// Tool Sets attach to variations, not Agents. Create returns no variation ID, so list them.
variations, err := client.Agents().Variations().List(ctx, agent.Metadata.ID, nil)
variationID := variations.Items[0].Metadata.ID
_, err = client.Agents().Variations().AddAssignment(ctx, agent.Metadata.ID, variationID,
    &cadenya.AgentVariationAddAssignmentParams{
        Body: cadenya.Ptr(cadenya.NewAddAgentVariationAssignmentRequestParamToolSetID(
            cadenya.AddAgentVariationAssignmentRequest_ToolSetIDParam{ToolSetID: toolSet.Metadata.ID})),
    })

// Objectives on a draft Agent are rejected.
_, err = client.Agents().Publish(ctx, agent.Metadata.ID, nil)
```

Tool Set create resolves the headers and checks the source live; an unreachable source or one with no tools is rejected. The check is skipped while a referenced secret is undefined, so a misspelled secret name is not caught at create. Doc comments inside the module that show `${SECRET_NAME}` are stale.

## Lists and updates

List methods return `*Page[T]` with `Items`, `NextCursor`, `HasNextPage()`, `GetNextPage(ctx)` (`nil, nil` when exhausted), and `All(ctx)`.

```go
page, err := client.Agents().List(ctx, &cadenya.AgentListParams{Labels: cadenya.String("env=prod"), Limit: cadenya.Int32(50)})
all, err := page.All(ctx)
```

`Update` params carry `Metadata`, `Spec`, and `UpdateMask *string` (comma-separated camelCase paths). Only masked paths change; maps and lists are replaced whole.

```go
_, err = client.Agents().Update(ctx, agentID, &cadenya.AgentUpdateParams{
    Metadata:   &cadenya.UpdateResourceMetadata{Name: "Support Triager v2"},
    UpdateMask: cadenya.String("metadata.name"),
})
```

## Errors, retries, request options

A non-2xx response (after retries) returns `*cadenya.APIError{StatusCode, Code, Message, Details}`, whose `Error()` reads `cadenya: <message> (http <status>, code <grpc code>)`. Other failures are wrapped errors (`cadenya: connection error: …`, `cadenya: protocol error: …`), or the context error itself on cancellation or deadline.

```go
var apiErr *cadenya.APIError
if errors.As(err, &apiErr) {
    switch apiErr.StatusCode {
    case 400: // Message "validation failed"; Details holds google.rpc.BadRequest fieldViolations (field + description)
    case 403: // Details holds an ErrorInfo whose reason is e.g. SCOPE_MISSING
    case 404: // wrong workspace, or an external ID that was never set
    case 409: // Message "resource with the same identifier already exists": the external ID is taken
    case 429: // ErrorInfo reason ENTITLEMENT_LIMIT_REACHED: a plan limit, not a rate limit; retrying won't help
    }
}
```

Request options: `WithRequestHeader(k, v)`, `WithRequestRetries(n)`, `WithReconnect(bool)`, `WithLastEventID(id)`. Retries apply only to GET, HEAD, PUT and DELETE, on 408, 409, 429, 500, 502, 503, 504 and transport errors, and honor `Retry-After`. `WithRequestRetries` opts a single POST or PATCH in.

## Streaming objective events

Default: start an objective and watch it on one connection with `Objectives().CreateAndStream` (`POST …/objectives:stream`).

- `Metadata.ExternalID` is required. It is the idempotency key: repeating the request, including the SDK's automatic reconnect (which re-sends the POST), attaches to the existing objective instead of starting another.
- The first item has `.Objective` set, and every later one has `.Event`. A reconnect sends the objective item again.
- The server ends the stream once the objective settles: a `StateChanged` event whose `ToState` is `OBJECTIVE_STATE_WAITING` (the turn is over), `FINALIZED`, `FAILED`, `CANCELLED` or `TIMED_OUT`. Terminal states also emit their own `Finalized`, `Error`, `Cancelled` or `TimedOut` event just before it.

```go
stream, err := client.Objectives().CreateAndStream(ctx, (&cadenya.ObjectiveCreateAndStreamBuilder{}).
    AgentID("external_id:support-triager").
    Metadata(&cadenya.CreateAndStreamObjectiveRequest_Metadata{ExternalID: "ticket-4821"}).
    SystemPromptData(map[string]any{"customer_name": "Ada"}).
    FirstUserMessage("Summarize the open tickets.").
    ToParams())
if err != nil { return err }
defer stream.Close()
var objectiveID string
settled := false
for stream.Next() {
    item := stream.Current()
    switch {
    case item.Objective != nil:
        objectiveID = item.Objective.Objective.Metadata.ID
    case item.Event != nil:
        if handle(objectiveID, *item.Event.Event) { settled = true }
    }
}
if err := stream.Err(); err != nil { return err }
last := stream.LastEventID()
if !settled { // the connection was cut before the objective settled
    if last, err = watch(ctx, objectiveID, last); err != nil { return err }
}

// Next turn: Continue needs OBJECTIVE_STATE_WAITING, then watch from the checkpoint.
_, err = client.Objectives().Continue(ctx, objectiveID, &cadenya.ObjectiveContinueParams{Message: "Which one is most urgent?"})
if err != nil { return err }
last, err = watch(ctx, objectiveID, last)
```

`Objectives().StreamEvents` attaches to an existing objective. Semantics to code around:

- Without `WithLastEventID` it delivers only events that arrive after the connection opens. With it, the server replays every event after that ID, then goes live.
- It never closes on its own. Stop on a settling `StateChanged`; `Close()` makes `Next()` return false with a nil `Err()`.
- Resume only from a durable `objevt_` ID. Heartbeat (`hb_`) and, with `IncludeDeltas`, delta (`dlt_`) events reach `Current()` but carry no SSE ID, and sending one fails with 400 `Last-Event-ID must be a persisted objevt_ event ID`. `stream.LastEventID()` only ever holds a durable ID, so checkpoint with it, not `ev.Metadata.ID`.
- Mid-stream transport drops reconnect from `LastEventID()` (5 attempts per outage). `WithReconnect(false)` returns them as errors instead.
- Connections are cut after about 10 minutes. That is a clean end of stream: `Next()` returns false with a nil `Err()` and no reconnect, so reopen from `LastEventID()` in an outer loop.
- To attach with no checkpoint, read history with `ListEvents` (`SortOrder: cadenya.String("asc")`, then `page.All(ctx)`), handle each event, and pass the last one's `Metadata.ID` (history holds only durable events).
- A replayed `ToolApprovalRequested` for a call already approved makes `ApproveToolCall` fail with 400 (code 9, `not waiting for approval`); treat that as handled.

```go
// watch follows an existing objective until it settles and returns the new checkpoint.
func watch(ctx context.Context, objectiveID, last string) (string, error) {
    for {
        s, err := client.Objectives().StreamEvents(ctx, objectiveID, nil, cadenya.WithLastEventID(last))
        if err != nil { return last, err }
        settled := false
        for s.Next() {
            if handle(objectiveID, s.Current()) { settled = true; break }
        }
        last = s.LastEventID()
        s.Close()
        if err := s.Err(); err != nil || settled { return last, err }
    }
}

// handle reports whether the objective settled. The payload sits one level down under the variant's name.
func handle(objectiveID string, ev cadenya.ObjectiveEvent) (settled bool) {
    d := ev.Data
    if d == nil { return false }
    switch {
    case d.ToolApprovalRequested != nil:
        _, _ = client.Objectives().ApproveToolCall(ctx, objectiveID, d.ToolApprovalRequested.ToolApprovalRequested.ToolCallID, nil)
    case d.AssistantMessage != nil:
        if c := d.AssistantMessage.AssistantMessage.Content; c != nil { fmt.Println(*c) }
    case d.Finalized != nil:
        fmt.Println(d.Finalized.Finalized.Output)
    case d.StateChanged != nil:
        switch d.StateChanged.StateChanged.ToState {
        case cadenya.ObjectiveStateChangedToStateObjectiveStateWaiting,
            cadenya.ObjectiveStateChangedToStateObjectiveStateFinalized,
            cadenya.ObjectiveStateChangedToStateObjectiveStateFailed,
            cadenya.ObjectiveStateChangedToStateObjectiveStateCancelled,
            cadenya.ObjectiveStateChangedToStateObjectiveStateTimedOut:
            return true
        }
    }
    return false
}
```

Use `Objectives().Create` instead only when nothing watches the objective (webhooks, polling); it takes the same fields with an optional external ID.

## Webhooks

```go
body, err := io.ReadAll(r.Body)                        // raw bytes; a re-serialized body fails verification
event, err := client.Webhooks().Unwrap(body, r.Header) // or cadenya.UnwrapWebhook(secret, body, r.Header)
// event.Type is e.g. "objective_event.tool_approval_requested"; event.Data.Objective.ID is the objective;
// event.Data.ObjectiveEvent.Data is the same union as the stream.
```

Deliveries follow Standard Webhooks: headers `webhook-id`, `webhook-timestamp`, `webhook-signature` (`v1,<base64>`), HMAC-SHA256 over `id.timestamp.body`, 5-minute tolerance. The secret starts with `whsec_`; read it from `client.Accounts().Retrieve(ctx)` → `.Info.WebhookEventsHMACSecret` and store it as `CADENYA_WEBHOOK_SECRET`. `cadenya.VerifyWebhook(secret, body, headers)` verifies without decoding; failures wrap `cadenya.ErrWebhookVerification`.

## Build checklist

1. `NewClient` with the key and workspace from the environment; `Profiles().Whoami(ctx)` confirms the key works.
2. Create the Tool Set with its secrets, then `ToolSets().Tools().List` to confirm it synced tools.
3. List enabled models and create the Agent with its default variation.
4. List variations, `AddAssignment` the Tool Set, then `Agents().Publish`; `Agents().Retrieve` should show `AgentStateStatePublished`.
5. `CreateAndStream` the objective and handle approvals; `Continue` plus `watch` for each later turn.
6. Optionally record a score with `Objectives().CreateFeedback`.

## Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| `cadenya: missing "workspaceId": pass it in params, set it on the client, or set the CADENYA_WORKSPACE_ID environment variable` | no client default and `params.WorkspaceID` is nil | `WithWorkspaceID`, `CADENYA_WORKSPACE_ID`, or set it on the params |
| 400 `validation failed`, violation on `agent_id`: `agent must be published to create an objective` | the Agent is a draft | `Agents().Publish` |
| 400 violation on `metadata.externalId` from `CreateAndStream` | no external ID | set `Metadata.ExternalID` |
| 400 violation on `spec.model_config.model_id` | wrong form, or the model is disabled | `model_…` from `Models().List`, or `<provider-key-external-id>.<model-external-id>` |
| 429 `the account has reached its plan's limit of N for agent_variations` (`ENTITLEMENT_LIMIT_REACHED`) | the plan caps non-archived variations across the account, and a default variation counts | update an existing variation, or archive one |
| `StreamEvents` yields nothing for a finished objective | no `WithLastEventID` | replay with `ListEvents`, then stream from the last ID |
| `StreamEvents` loop never ends | the server keeps that stream open | stop on a settling `StateChanged` and `Close()` |
| `context deadline exceeded` after 60 s | default deadline for non-stream calls when `ctx` has none | set your own deadline on `ctx` |
| a POST is not retried | retries cover idempotent methods only | `cadenya.WithRequestRetries(n)` on that call |
| `legacy dollar references are not supported` | `${NAME}` in a header | `{{ secrets.NAME }}` |

## Related skills

- `cadenya-api`: wire conventions and per-resource request shapes.
- `cadenya-cli`: the same operations from a terminal; `--dry-run` prints the request body without sending it.
