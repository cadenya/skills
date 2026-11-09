# Command map

Groups mirror API resources, and nested resources are subgroups (`agents variations`, `tool-sets tools`). `cadenya schema` lists every command with its one-line purpose, and `cadenya schema <group> <command>` prints one command's full contract.

| Group | Commands |
| --- | --- |
| `auth` | `login`, `logout`, `status` |
| `config` | `set`, `get`, `unset`, `list`, `validate`, `plan`, `apply` |
| `whoami`, `profiles whoami` | the profile behind the credential |
| `accounts` | `retrieve`, `rotate-challenge-token`, `rotate-webhook-signing-key` |
| `workspaces` | `list`, `create --temporary` (a temporary workspace without an account, CLI 1.12.0 or later), `claim-status` (`--wait`); see `cadenya-start-without-account` |
| `workspace-admin` | `list-account`, `create`, `retrieve`, `update`, `archive`, `list-members`, `add-member`, `remove-member`, `list-profiles` (admin role) |
| `api-keys` | `list`, `create`, `retrieve`, `update`, `delete`, `enable`, `disable`, `rotate`, `reveal`, `add-workspace`, `remove-workspace` (account keys) |
| `trusted-endpoints` | `list`, `create`, `retrieve`, `delete`, `verify --url <url>` (account-wide hosts that Tool Sets may call; no workspace) |
| `ai-provider-keys` | `list`, `create`, `retrieve`, `update`, `delete` |
| `models` | `list`, `create`, `retrieve`, `update`, `enable`, `disable`, `swap-on-variations` |
| `tool-sets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive`, `list-events`, `list-usage`, `retrieve-open-api-spec` |
| `tool-sets tools` | `list`, `create`, `retrieve`, `update`, `delete`, `omit`, `restore` |
| `tool-sets secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `workspace-secrets` | `list`, `create`, `retrieve`, `update`, `delete` |
| `agents` | `list`, `create`, `retrieve`, `update`, `delete`, `publish`, `unpublish`, `archive`, `unarchive`, `list-feedback`, `list-webhook-deliveries` |
| `agent-pools` | `list`, `create`, `retrieve`, `update`, `delete`, `activate`, `deactivate`, `archive`, `unarchive` (a group of Agents assigned to a variation as one callable target) |
| `agents variations` | `list`, `create`, `retrieve`, `update`, `delete`, `add-assignment`, `remove-assignment`, `add-memory-layer`, `update-memory-layer`, `remove-memory-layer` |
| `agents schedules` | `list`, `create`, `retrieve`, `update`, `delete`, `pause`, `resume`, `archive` |
| `objectives` | `list`, `create`, `create-and-stream`, `retrieve`, `list-events`, `stream-events`, `continue` (`--enqueue`), `interrupt`, `cancel`, `compact`, `list-queued-actions`, `remove-queued-action`, `list-tool-calls`, `retrieve-tool-call`, `approve-tool-call`, `deny-tool-call`, `set-tool-call-content`, `list-tools`, `list-context-windows`, `retrieve-diagnostics`, `list-feedback`, `create-feedback` |
| `memory-layers` | `list`, `create`, `retrieve`, `update`, `delete` |
| `memory-layers entries` | `list`, `create`, `retrieve`, `update`, `delete` |
| `tenants` | `list`, `retrieve`, `delete`, `list-subjects` |
| `widgets` | `list`, `create`, `retrieve`, `update`, `delete`, `archive`, `unarchive` |
| `widget-sessions` | `list`, `create`, `retrieve`, `delete`, `revoke`, `delete-tenant` |
| `uploads` | `create`, `retrieve` |
| `tool-search` | `search-or-sets --query <text>` |
| `schema` | print any command's contract as markdown |
