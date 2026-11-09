# `@cadenya/cadenya` resource accessors

Every accessor on the client and its methods. Exact signatures are in `node_modules/@cadenya/cadenya/api.md`.

| Accessor | Methods |
| --- | --- |
| `accounts` | `retrieve`, `rotateChallengeToken`, `rotateWebhookSigningKey` |
| `profiles` | `whoami` |
| `workspaces` | `list`, `retrieveTemporary` |
| `workspaceAdmin` | `listAccount`, `create`, `retrieve`, `update`, `archive`, `listMembers`, `addMember`, `removeMember`, `listProfiles` |
| `apiKeys` | `list`, `create`, `retrieve`, `update`, `delete`, `enable`, `disable`, `rotate`, `reveal`, `addWorkspace`, `removeWorkspace` (account keys) |
| `aiProviderKeys` | CRUD |
| `models` | `list`, `create`, `retrieve`, `update`, `enable`, `disable`, `swapOnVariations` (no `delete`) |
| `toolSets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive`, `listEvents`, `listUsage`, `retrieveOpenApiSpec` |
| `toolSets.tools` | `list`, `create`, `retrieve`, `update`, `delete`, `omit`, `restore` |
| `toolSets.secrets`, `workspaceSecrets` | CRUD |
| `agents` | `list`, `create`, `retrieve`, `update`, `delete`, `publish`, `unpublish`, `archive`, `unarchive`, `listFeedback`, `listWebhookDeliveries` |
| `agents.variations` | CRUD, `addAssignment`, `removeAssignment`, `addMemoryLayer`, `updateMemoryLayer`, `removeMemoryLayer` |
| `agents.schedules` | CRUD, `pause`, `resume`, `archive` |
| `objectives` | `list`, `create`, `createAndStream`, `retrieve`, `listEvents`, `streamEvents`, `continue`, `interrupt`, `cancel`, `compact`, `listQueuedActions`, `removeQueuedAction`, `listToolCalls`, `retrieveToolCall`, `approveToolCall`, `denyToolCall`, `setToolCallContent`, `listTools`, `listContextWindows`, `retrieveDiagnostics`, `listFeedback`, `createFeedback` |
| `memoryLayers`, `memoryLayers.entries` | CRUD |
| `tenants` | `list`, `retrieve`, `delete`, `listSubjects` |
| `widgets` | CRUD, `archive`, `unarchive` |
| `widgetSessions` | `list`, `create`, `retrieve`, `delete`, `revoke`, `deleteTenant` (no `update`) |
| `agentPools` | CRUD, `activate`, `deactivate`, `archive`, `unarchive` |
| `trustedEndpoints` | `list`, `create`, `retrieve`, `delete`, `verify` |
| `uploads` | `create`, `retrieve` |
| `toolSearch` | `searchOrSets` |
| `webhooks` | `unwrap` (pre-wired with the `webhookSecret` option) |

CRUD means `list`, `create`, `retrieve`, `update`, `delete`.

## Type names

- Params types are `<Singular><Op>Params`: `AgentCreateParams`, `ObjectiveStreamEventsParams`.
- Model types keep their wire names: `Agent`, `AgentVariationSpec_ModelConfig`.
- Enums are string literal unions: `'STATE_PUBLISHED'`, `'OBJECTIVE_STATE_WAITING'`.
- A type whose request shape differs from the response gets a `Param` suffix: `CreateAgentVariationRequestParam`. Read-only fields on `Param` types are stripped on send, so a fetched resource can be edited and sent back.
