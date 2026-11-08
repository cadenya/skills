---
name: cadenya-go-sdk
description: "Build Cadenya integrations with the official Go SDK, `go.cadenya.com/cadenya-go` (Go 1.22+, stdlib HTTP, typed params and builders). Covers client options, resource accessors and method names, request structs and unions, pagination, `*APIError` handling, SSE objective event streams, and Standard Webhooks verification. Use when writing or debugging Go that imports `go.cadenya.com/cadenya-go`, when a Go service needs to create tool sets, agents, or objectives, or when hitting `cadenya: missing API key`, `missing workspaceId`, `must not be blank`, or an `*APIError` you need to classify."
---

# Cadenya Go SDK usage

## Overview

`go.cadenya.com/cadenya-go` (package `cadenya`) is generated from the Cadenya OpenAPI contract, so accessors, methods, field names, and enum values match the REST API one-to-one. Every signature is in the module's `api.md`; run `go doc go.cadenya.com/cadenya-go` for types.

For wire conventions shared by every client (IDs and external IDs, field masks, error codes, pagination, streaming semantics, webhooks) see the `cadenya-api` skill. This skill covers what is specific to Go.

## Install and construct

```sh
go get go.cadenya.com/cadenya-go
```

```go
import cadenya "go.cadenya.com/cadenya-go"

client, err := cadenya.NewClient()                      // reads env
client, err := cadenya.NewClient(cadenya.WithAPIKey(key), cadenya.WithWorkspaceID("development"), cadenya.WithMaxRetries(2))
```

| Option | Env fallback | Notes |
| --- | --- | --- |
| `WithAPIKey` | `CADENYA_API_KEY` | required; missing everywhere returns `cadenya: missing API key: pass WithAPIKey or set CADENYA_API_KEY` |
| `WithWorkspaceID` | `CADENYA_WORKSPACE_ID` | `workspace_…` or the external ID; default for every workspace-scoped call |
| `WithBaseURL` | `CADENYA_BASE_URL` | default `https://api.cadenya.com` |
| `WithWebhookSecret` | `CADENYA_WEBHOOK_SECRET` | for `client.Webhooks().Unwrap` |
| `WithMaxRetries(n)` | | default 0; 0 to 10 |
| `WithHTTPClient(*http.Client)` | | default has no `Timeout` on purpose (streams) |
| `WithDebugLog(io.Writer)` | | every exchange, `Authorization: [redacted]`; SSE bodies not consumed |

An option passed explicitly but blank returns `cadenya: <name> must not be blank`; omit it to fall back to env. There is no `WithTimeout`: non-stream calls get a 60 s deadline when the `ctx` has none, so set your own via `context.WithTimeout`.

## Account and API key

- A person creates the account at https://app.cadenya.com/signup, and the Free plan needs no card. When there is no key yet, give your user that link.
- The API keys page, https://app.cadenya.com/account/apiKeys, lists the account's keys. Sign-up creates a default key that reaches every workspace. Set the key as `CADENYA_API_KEY`: the SDK reads its options and the environment, never the CLI's stored login.
- The `DefaultWorkspace.ID` of `client.Profiles().Whoami(ctx)` is the default workspace ID, the value for `CADENYA_WORKSPACE_ID`, and `cadenya workspaces list` lists the others.
- From a terminal, `cadenya auth login` signs in through the browser with a one-time code (see `cadenya-cli`).
- Keep tool sets, agents, variations, memory layers and widgets as YAML files in `.cadenya/` next to a `cadenya.yaml`, and apply them with `cadenya config apply` ([format](https://cadenya.com/docs/config-files), [GitHub Action](https://github.com/cadenya/cadenya-config-loader)). That keeps the setup in the repository instead of in a one-off provisioning script.

## Resources and method names

Accessors are methods on `*Client` returning interfaces (mockable): `client.Agents()`, `client.ToolSets()`, `client.Objectives()`, `client.APIKeys()`, `client.AIProviderKeys()`, `client.WorkspaceSecrets()`, `client.MemoryLayers()`, `client.Models()`, `client.Tenants()`, `client.Widgets()`, `client.WidgetSessions()`, `client.Uploads()`, `client.Workspaces()`, `client.WorkspaceAdmin()`, `client.Profiles()`, `client.Accounts()`, `client.ToolSearch()`, `client.Webhooks()`. Nested: `client.Agents().Variations()`, `client.Agents().Schedules()`, `client.ToolSets().Tools()`, `client.ToolSets().Secrets()`, `client.MemoryLayers().Entries()`.

Every method is `(ctx, <path IDs in order>, params *XParams, opts ...RequestOption)`; `params` may be `nil`. Initialisms are upper-cased (`WorkspaceID`, `ToolSetID`, `OpenAPI`). `Get` is `Retrieve`.

```go
client.Agents().Retrieve(ctx, id, nil)
client.Agents().Variations().Retrieve(ctx, agentID, id, nil)
client.Objectives().ApproveToolCall(ctx, objectiveID, toolCallID, nil)
client.Objectives().StreamEvents(ctx, objectiveID, nil)                 // *Stream[ObjectiveEvent]
client.Agents().Publish(ctx, id, nil)
client.Objectives().Continue(ctx, objectiveID, &cadenya.ObjectiveContinueParams{Message: "…"})
```

Params structs are `<Singular><Op>Params` (`AgentCreateParams`, `ObjectiveListParams`) with a fluent `<Singular><Op>Builder` (`(&cadenya.ObjectiveCreateBuilder{}).AgentID(id).SystemPromptData(m).ToParams()`). Each has `WorkspaceID *string` to override the client default per call.

## Request bodies

- Required scalars are plain fields; optional scalars are pointers with `omitempty`. Helpers: `cadenya.String`, `cadenya.Int32`, `cadenya.Bool`, `cadenya.Float64`, `cadenya.Ptr[T]`. There is no "send null"; a nil pointer is omitted.
- Response types nest `Metadata` + `Spec` + `Info` (+ `State`); enums are typed string constants prefixed with the type name: `cadenya.ObjectiveStateStateFinalized`, `cadenya.AgentStateStatePublished`, `cadenya.AgentSpecVariationSelectionModeVariationSelectionModeRandom`.
- Unions are structs with one pointer per variant; constructors set the `type` tag: `cadenya.NewToolSetAdapterMCP(...)`, `cadenya.NewAddAgentVariationAssignmentRequestParamToolSetID(...)`. Setting more than one variant fails at marshal time.
- Types whose request shape differs from the response get a `Param` suffix (`CreateAgentVariationRequestParam`).

```go
// Tool set. Secrets interpolate as {{ secrets.NAME }} (workspace or tool set secret).
toolSet, err := client.ToolSets().Create(ctx, &cadenya.ToolSetCreateParams{
    Metadata: &cadenya.CreateResourceMetadata{Name: "Support MCP", ExternalID: cadenya.String("support-mcp")},
    Spec: &cadenya.ToolSetSpec{
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

// Agent plus default variation in one call. VariationSelectionMode is required.
agent, err := client.Agents().Create(ctx, (&cadenya.AgentCreateBuilder{}).
    Metadata(&cadenya.CreateResourceMetadata{Name: "Support Triager", ExternalID: cadenya.String("support-triager")}).
    Spec(&cadenya.AgentSpec{VariationSelectionMode: cadenya.AgentSpecVariationSelectionModeVariationSelectionModeRandom}).
    DefaultVariation(&cadenya.CreateAgentVariationRequestParam{
        Metadata: &cadenya.CreateResourceMetadata{Name: "default"},
        Spec: &cadenya.AgentVariationSpec{
            SystemPromptTemplate: cadenya.String("You triage support tickets for {{ system_prompt_data.customer_name }}."),
            ModelConfig:          &cadenya.AgentVariationSpec_ModelConfig{ModelID: "getting-started-key.claude-opus-5"}, // "<provider-key-slug>.<model-slug>" or model_…
            Constraints:          &cadenya.AgentVariationSpec_Constraints{InactivityTimeout: cadenya.String("3600s")},   // durations are strings
        },
    }).ToParams())

// Assignment (tools attach to variations, not agents). Body is a union.
_, err = client.Agents().Variations().AddAssignment(ctx, agent.Metadata.ID, variationID,
    &cadenya.AgentVariationAddAssignmentParams{
        Body: cadenya.Ptr(cadenya.NewAddAgentVariationAssignmentRequestParamToolSetID(
            cadenya.AddAgentVariationAssignmentRequest_ToolSetIDParam{ToolSetID: toolSet.Metadata.ID})),
    })

// Objective
objective, err := client.Objectives().Create(ctx, (&cadenya.ObjectiveCreateBuilder{}).
    AgentID("external_id:support-triager").
    SystemPromptData(map[string]any{"customer_name": "Ada"}).
    FirstUserMessage("Summarize the open tickets.").
    Metadata(&cadenya.CreateOperationMetadata{ExternalID: cadenya.String("ticket-4821")}).
    ToParams())
```

Doc comments inside the module that mention `${SECRET_NAME}` are stale; the server accepts only `{{ secrets.NAME }}`. Create a secret before the tool set that references it: the create performs a live sync with those headers.

## Reads and pagination

List methods return `*Page[T]` with `Items`, `NextCursor`, `HasNextPage()`, `GetNextPage(ctx)` (`nil, nil` when exhausted), and `All(ctx)`.

```go
page, err := client.Agents().List(ctx, &cadenya.AgentListParams{Labels: cadenya.String("env=prod"), Limit: cadenya.Int32(50)})
all, err := page.All(ctx)
events, err := client.Objectives().ListEvents(ctx, objectiveID, &cadenya.ObjectiveListEventsParams{SortOrder: cadenya.String("asc")})
```

## Updates

`Update` params carry `Metadata`, `Spec`, and `UpdateMask *string` (comma-separated camelCase paths). Only masked paths change; maps and lists are replaced whole.

```go
_, err = client.Agents().Update(ctx, agentID, &cadenya.AgentUpdateParams{
    Metadata:   &cadenya.UpdateResourceMetadata{Name: "Support Triager v2"},
    UpdateMask: cadenya.String("metadata.name"),
})
```

## Errors

Non-2xx responses (after retries) return `*cadenya.APIError{StatusCode, Code, Message, Details}`; `Error()` reads `cadenya: <message> (http <status>, code <grpc code>)`. Everything else is a wrapped `error`: `cadenya: connection error: …`, `cadenya: protocol error: …`, and the context error itself on cancellation or deadline (`errors.Is(err, context.DeadlineExceeded)`).

```go
var apiErr *cadenya.APIError
if errors.As(err, &apiErr) {
    switch apiErr.StatusCode {
    case 404: // wrong workspace, or an external ID that was never set
    case 403: // key lacks the scope; apiErr.Details[0]["reason"] names it
    case 400: // apiErr.Details holds google.rpc.BadRequest fieldViolations with proto paths such as spec.model_config.model_id
    }
}
```

## Retries and per-request options

`RequestOption`s: `WithRequestHeader(k, v)`, `WithRequestRetries(n)`, `WithReconnect(bool)`, `WithLastEventID(id)`.

Retries default to 0 and only ever apply to GET/HEAD/PUT/DELETE (408, 409, 429, 5xx, transport errors), honoring `Retry-After`. `WithMaxRetries` enables them client-wide; `WithRequestRetries` opts a single POST or PATCH in.

## Streaming objective events

Semantics you must code around:

- `StreamEvents` without `WithLastEventID` delivers only events that arrive after the connection opens. With it, the server replays everything after that ID, then goes live.
- The server never closes the stream. Call `stream.Close()` when you see a terminal event (`Finalized`, `Error`, `Cancelled`, `TimedOut`); `Next()` then returns false with a nil `Err()`.
- An `AssistantMessage` with no `ToolCalls` ends the turn; the objective is `STATE_WAITING` until you `Continue` it or the inactivity timeout fires.
- Mid-stream transport drops reconnect from the last received ID (5 attempts per outage); `WithReconnect(false)` surfaces them as errors so you can resume with `WithLastEventID(stream.LastEventID())` on a new stream.
- A replayed `toolApprovalRequested` for a call you already approved makes the approve call fail with 400 (code 9, not waiting for approval); treat that as already handled.
- A clean end of stream (load balancers cut connections after about 10 minutes) makes `Next()` return false with a nil `Err()` and no terminal event. Track `ev.Metadata.ID` as your checkpoint and reopen from it in an outer loop until you have seen a terminal event.

```go
page, err := client.Objectives().ListEvents(ctx, objectiveID, &cadenya.ObjectiveListEventsParams{SortOrder: cadenya.String("asc")})
history, err := page.All(ctx)   // every page, not just the first 20
var last string
for _, ev := range history { handle(ev); last = ev.Metadata.ID }

stream, err := client.Objectives().StreamEvents(ctx, objectiveID, nil, cadenya.WithLastEventID(last))
if err != nil { return err }
defer stream.Close()
for stream.Next() {
    if handle(stream.Current()) { stream.Close() }
}
if err := stream.Err(); err != nil { return err }

// The union is a struct of variant pointers; the payload sits one level down under the same name.
func handle(ev cadenya.ObjectiveEvent) (done bool) {
    d := ev.Data
    switch {
    case d.ToolApprovalRequested != nil:
        _, _ = client.Objectives().ApproveToolCall(ctx, objectiveID, d.ToolApprovalRequested.ToolApprovalRequested.ToolCallID, nil)
    case d.AssistantMessage != nil:
        m := d.AssistantMessage.AssistantMessage
        if m.Content != nil { fmt.Println(*m.Content) }
        return len(m.ToolCalls) == 0
    case d.Finalized != nil:
        fmt.Println(d.Finalized.Finalized.Output); return true
    case d.Error != nil, d.Cancelled != nil, d.TimedOut != nil:
        return true
    }
    return false
}
```

`ev.Metadata.ID` is the SSE event ID (`objevt_…`); `stream.LastEventID()` tracks the checkpoint. Housekeeping frames (`open`, `ping`) are skipped.

## Webhooks

```go
body, _ := io.ReadAll(r.Body)                                  // raw bytes; a re-serialized body fails verification
event, err := client.Webhooks().Unwrap(body, r.Header)         // or cadenya.UnwrapWebhook(secret, body, r.Header)
// event.Type is "objective_event.tool_approval_requested" etc.; event.Data.Objective.ID is the objective,
// event.Data.ObjectiveEvent.Data the same union as the stream
```

Standard Webhooks: headers `webhook-id`, `webhook-timestamp`, `webhook-signature` (`v1,<base64>`), HMAC-SHA256 over `id.timestamp.body`, secret `whsec_…` (the account's `webhookEventsHmacSecret`), 5-minute tolerance. `cadenya.VerifyWebhook(secret, body, headers)` verifies without decoding; failures wrap `cadenya.ErrWebhookVerification`.

## End to end

```go
ctx, cancel := context.WithTimeout(context.Background(), 5*time.Minute)
defer cancel()
client, err := cadenya.NewClient(cadenya.WithWorkspaceID("development"))

_, err = client.WorkspaceSecrets().Create(ctx, &cadenya.WorkspaceSecretCreateParams{
    Metadata: &cadenya.CreateResourceMetadata{Name: "MCP_TOKEN"},
    Spec:     &cadenya.WorkspaceSecretSpec{Value: cadenya.String(os.Getenv("MCP_TOKEN"))},
})
// … toolSet and agent as in "Request bodies" …

models, err := client.Models().List(ctx, (&cadenya.ModelListBuilder{}).Prefix("claude").State(cadenya.ModelServiceListModelsStateStateEnabled).Limit(1).ToParams())
if len(models.Items) == 0 { log.Fatal("no enabled model matches") }
variations, err := client.Agents().Variations().List(ctx, agent.Metadata.ID, nil)   // Create returns the agent only
variationID := variations.Items[0].Metadata.ID
// … AddAssignment as above …
_, err = client.Agents().Publish(ctx, agent.Metadata.ID, nil)                        // objectives on a STATE_DRAFT agent are rejected

// … Create objective, stream as above …
_, err = client.Objectives().CreateFeedback(ctx, objective.Metadata.ID, &cadenya.ObjectiveCreateFeedbackParams{
    Metadata: &cadenya.CreateOperationMetadata{},
    Data:     &cadenya.ObjectiveFeedbackData{Score: cadenya.Ptr(float32(1)), Comment: cadenya.String("Accurate summary")},
})
_, err = client.Objectives().Continue(ctx, objective.Metadata.ID, &cadenya.ObjectiveContinueParams{Message: "Which one is most urgent?"})
```

## Gotchas

| Symptom | Cause | Fix |
| --- | --- | --- |
| `cadenya: missing workspaceId` | no client default and `params.WorkspaceID` nil | `WithWorkspaceID`, `CADENYA_WORKSPACE_ID`, or set it on the params |
| 400 `agent must be published to create an objective` | agent is `STATE_DRAFT` | `Agents().Publish` |
| 400 on `spec.model_config.model_id` | wrong `ModelID` form | `model_…` from `Models().List`, or `<provider-key-slug>.<model-slug>` |
| `ResourceExhausted` creating a second variation | default plan allows 1 variation per agent | use `DefaultVariation` on create; update it |
| stream yields nothing for a finished objective | no `WithLastEventID` | replay via `ListEvents` (`SortOrder: asc`), then stream from the last ID |
| `Next()` never returns false | the server keeps the stream open | `Close()` on terminal events |
| a call hangs past a minute | `http.Client` has no timeout by design | deadline on `ctx`; keep it open for streams |
| POST silently not retried | retries apply to idempotent methods only | `cadenya.WithRequestRetries(n)` on that call |
| header secret not resolved | `${NAME}` syntax | use `{{ secrets.NAME }}` |
| `Agents().Create` result has no variation ID | `Agent.Info` only has `VariationCount` | `Agents().Variations().List(ctx, agentID, nil)` |

## Related skills

- `cadenya-api`: wire conventions and per-resource request shapes.
- `cadenya-cli`: the same operations from a terminal; `cadenya … --dry-run` prints the exact JSON body the SDK sends.
