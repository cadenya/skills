# Troubleshooting CLI errors

Errors print to stderr as `error: cadenya: <message> (http <status>, code <grpc-code>)`, followed by the `details` list. Errors on stream commands carry only the message, as `(http <status>, code 0)` with no details, so a field violation reads as a bare `validation failed`.

| Symptom | Cause | Fix |
| --- | --- | --- |
| ``missing credentials: pass --api-key, set CADENYA_API_KEY, or run `cadenya auth login` `` | no `--api-key`, no `CADENYA_API_KEY`, no stored login, no `.cadenya/temporary.json` | `cadenya auth login`, or set `CADENYA_API_KEY` to a key from https://app.cadenya.com/account/apiKeys |
| `invalid authentication token provided (http 403, code 7)`, reason `AUTH_TOKEN_INVALID` (HTTP 401 with no reason on stream commands), even though `auth login` worked | `CADENYA_API_KEY` (or `--api-key`) is set and overrides the stored login | `cadenya auth status` shows the source; unset the variable or pass the right key |
| `admin role required (http 403, code 7)`, reason `ADMIN_ROLE_REQUIRED` | `workspace-admin` commands need the account admin role | use an admin profile, or the non-admin `workspaces list` |
| `not found (http 404, code 5)` on a resource you can see in the UI | wrong workspace, or an external ID that was never set | check `cadenya config list`; pass `--workspace-id`; use `external_id:` |
| `validation failed (http 400, code 3)` with `fieldViolations` | body rejected server-side; `field` names the proto path | fix that field; `--dry-run` to inspect what was sent |
| `validation failed` with field `agent_id`: `agent must be published to create an objective` (on `create-and-stream`: `validation failed (http 400, code 0)` alone) | the Agent is `STATE_DRAFT` | `cadenya agents publish <agent>` |
| `model_id must be a reference key in the form <provider-key-slug>.<model-slug> or a canonical model_ ID` | wrong `modelId` form | take `metadata.id` from `models list --state STATE_ENABLED --display json` |
| `model_id is required; no default model is configured for this workspace` | `modelId` omitted and the workspace has no default model | pass a model ID from `models list` |
| `resource with the same identifier already exists (http 409, code 6)` | a create reused an external ID | `retrieve <external-id>` and update it instead |
| `required flag(s) not set: --name` on `update --label …` | `metadata.name` is required whenever `metadata` is sent | pass the current name |
| `expected exactly 1 positional argument(s) (<id>), got 0` | missing positional | put positionals before flags: `retrieve <id> --workspace-id …` |
| `flag provided but not defined` | typo, or a flag that belongs to another arm or command | `cadenya schema <group> <command>` |
| `stream-events` prints nothing for a finished objective | no `--last-event-id`, so only new events are sent | `list-events --sort-order asc` for history, or resume from an `objevt_` ID |
| `Last-Event-ID must be a persisted objevt_ event ID` | `--last-event-id` got a heartbeat (`hb_`) or delta (`dlt_`) ID | resume from the last `objevt_` ID |
| `--spec: expected an object (YAML mapping or JSON object)` | a document flag got a bare path, which parses as a string | `--spec @spec.yml`; only `-f` takes a plain path |
| `'-' (stdin) may supply at most one input per command` | two inputs set to `-` | read the others from `@path` |
| `streaming commands support only --display json` | the root or command `--display` is not `json` | drop `--display` on stream commands |
