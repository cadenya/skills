---
name: cadenya-widgets
description: Embeds a Cadenya Agent as a chat in a web app with Widgets. Covers creating the Widget server-side, minting Widget Sessions with `@cadenya/cadenya`, handing the browser only its short-lived credentials, rendering with the React UI kit `@cadenya/widgets-ui-react`, tenant and subject isolation, revocation and tenant erasure, origin allowlists and CSP, and widget errors such as `origin not allowed`, `unknown widget`, `TOKEN_EXPIRED` and `Session cannot create or continue conversations`. Use when a task mentions Cadenya Widgets, `widgetSessions.create`, `CadenyaWidgetProvider`, `ConversationsPanel`, `*.widgets.cadenya.com`, or putting an Agent in front of end users in a browser. Do not use for server-to-server objectives, tool sets or agents with no browser surface; use cadenya-api or an SDK skill such as cadenya-typescript-sdk.
---

# Cadenya Widgets

A **Widget** binds one Agent to its own host (`info.host`, such as `k7m2xq9fp4wn.widgets.cadenya.com`) and an origin allowlist. Your backend mints a **Widget Session** with the workspace API key and gives the browser only the session's short-lived token and host. Conversations, tool calls and event streams then go straight from the browser to the Widget host.

**Never send the workspace API key, or anything that holds it, to the browser.** Only `credentials.token` and `credentials.host` (plus the two expiry times) leave your server. Keep the key in `CADENYA_API_KEY` in server-side env (`.env.local`, Vercel env, a secret manager). Do not log or store the token.

For raw HTTP routes and the error envelope, see cadenya-api. For client setup, pagination and `APIError`, see cadenya-typescript-sdk.

## Checklist

1. A **published** Agent (`STATE_PUBLISHED`) with a variation and its Tool Sets.
2. A Widget, created server-side (key with `widgets:manage`), with the exact origins of every page that embeds it.
3. A backend route that authenticates the visitor and calls `widgetSessions.create` (key with `widget_sessions:manage` **and** `objectives:manage`).
4. A page that renders `CadenyaWidgetProvider` with the returned host and token, and a `getToken` that calls that route again.
5. Revocation on logout, and `deleteTenant` for erasure requests.
6. Check: a message sent from an allowlisted origin gets a reply.

## 1. Prerequisites: the Agent and the Widget

- `widgets.create` rejects an archived Agent (`archived agents cannot serve a widget; unarchive the agent first`), but it accepts a draft Agent. Every conversation on a draft Agent then fails with `agent must be published to create an objective`. Run `client.agents.publish(id)` first.
- `spec.variationId` is an optional pin. It must belong to the Agent. Without it, the Agent's variation selection mode chooses a variation for each conversation.
- `spec.originAllowlist` holds up to 32 exact origins that match `^https?://[A-Za-z0-9.-]+(:[0-9]{1,5})?$`. Paths, trailing slashes and wildcards are not allowed. The edge compares the browser's `Origin` header to each entry as a string, so write entries in lowercase and leave out default ports (`https://app.example.com`, not `https://App.example.com:443`). Each Vercel preview URL is a separate origin.
- A new hostname can take up to a minute to start serving. Until it does, the host answers `404 {"error":"unknown widget"}`.
- Changing a Widget's Agent or variation affects new sessions only. A session copies the Agent binding when it is minted.

```ts
import Cadenya from "@cadenya/cadenya"; // reads CADENYA_API_KEY and CADENYA_WORKSPACE_ID
const client = new Cadenya();

const widget = await client.widgets.create({
  metadata: { name: "Support chat", externalId: "support-chat" },
  spec: {
    agentId: "external_id:support-agent",
    originAllowlist: ["http://localhost:3000", "https://app.example.com"],
  },
});
// widget.info.host is the hostname. Never build it from the ID or DNS label.
```

The CLI equivalent is `cadenya widgets create --name … --agent-id … --origin-allowlist … --dry-run` (see cadenya-cli). To narrow the origins later, use `widgets.update` with a field mask (see cadenya-api).

## 2. Mint a Widget Session (server only)

- **Scopes.** Creating a session takes `widget_sessions:manage`. The session also inherits the minting key's scopes, frozen at mint. Visitors cannot start or continue conversations unless the key holds `objectives:manage`. Without it, the browser gets `403 Session cannot create or continue conversations`, or `Widget session cannot read conversations` without `objectives:read`.
- **Tenant and subject are required.** Use `spec.tenant.id` for your organization ID and `spec.subject.id` for your user ID: 1 to 64 characters of `[A-Za-z0-9._-]`, plus an optional `name` of up to 64 characters. The mint creates or updates the tenant and subject records. Take both IDs from your own authenticated session, never from the request body.
- **Lifetime.** The token lasts 15 minutes (`credentials.tokenExpiresAt`). The session lasts 24 hours unless `spec.expiresAt` (an RFC 3339 string, which must be in the future) sets a different deadline. Nothing extends that deadline. A session also ends after 200 visitor messages (`STATE_EXHAUSTED`).
- **Every call mints a new session**, with no dedupe. One subject can hold at most 10 live sessions per Widget, and minting an eleventh revokes the oldest.
- **Optional trusted context**, all fixed at mint:
  - `secrets: [{ name, value }]`: encrypted, never returned, and used ahead of workspace and Tool Set secrets with the same name.
  - `spec.pinnedParameters`: up to 32 tool arguments that the model cannot see or override.
  - `metadata.labels`.

```ts
// app/api/widget-session/route.ts (Next.js; any server framework works the same way)
import Cadenya from "@cadenya/cadenya";
const client = new Cadenya();

export async function POST() {
  const user = await requireUser(); // your auth; respond 401 if signed out
  const session = await client.widgetSessions.create({
    spec: {
      widgetId: process.env.CADENYA_WIDGET_ID!, // e.g. external_id:support-chat
      tenant: { id: user.orgId, name: user.orgName },
      subject: { id: user.id },
    },
  });
  const c = session.credentials; // returned only by create
  if (!c) return new Response("Widget Session returned no credentials", { status: 502 });
  await rememberWidgetSession(user, c.sessionId); // server-side, for revoke on logout
  return Response.json(
    { host: c.host, token: c.token, tokenExpiresAt: c.tokenExpiresAt, sessionExpiresAt: c.sessionExpiresAt },
    { headers: { "Cache-Control": "no-store" } },
  );
}
```

`credentials` is the current envelope. The older `spec.token`, `spec.tokenExpiresAt` and `info.host` fields hold the same values on create. Reads and lists never return a token.

## 3. Render with the React UI kit

```sh
npm install @cadenya/cadenya @cadenya/widgets-ui-react @radix-ui/themes
```

```tsx
"use client";
import "@radix-ui/themes/styles.css";
import "@cadenya/widgets-ui-react/styles.css";
import { useCallback, useEffect, useState } from "react";
import { Theme } from "@radix-ui/themes";
import { CadenyaWidgetProvider, ConversationsPanel } from "@cadenya/widgets-ui-react";

type Creds = { host: string; token: string };
const mint = async (): Promise<Creds> => {
  const r = await fetch("/api/widget-session", { method: "POST" });
  if (!r.ok) throw new Error(`widget session ${r.status}`);
  return r.json();
};

export function SupportChat() {
  const [creds, setCreds] = useState<Creds | null>(null);
  useEffect(() => { mint().then(setCreds); }, []);
  const getToken = useCallback(async () => (await mint()).token, []);
  if (!creds) return null;
  return (
    <Theme accentColor="teal" radius="large" style={{ height: "100%" }}>
      <CadenyaWidgetProvider host={creds.host} token={creds.token} getToken={getToken}>
        <ConversationsPanel />
      </CadenyaWidgetProvider>
    </Theme>
  );
}
```

- The provider calls `https://{host}`. When a request returns 401, it calls `getToken` once and retries. Open streams survive the token change.
- Each `getToken` call mints a **new** session for the same tenant and subject. Conversation history carries over, because history belongs to the identity, not to the session. Your route decides each time whether this visitor still gets access.
- The panel fills its container, so give the container a definite height.
- Page tools, client tools and the Widgets Tools template (`<WidgetTools>` from `@cadenya/widgets-ui-react/widget-tools`, under one `PageToolsProvider`) are covered in the [Widget quickstart](https://cadenya.com/docs/guides/getting-started/widget-quickstart.md).
- For a custom UI, use `@cadenya/widgets`: ``new CadenyaWidgets({ apiKey: token, baseURL: `https://${host}` })``.
- To renew a token without going back to your backend, call `client.session.renewWidget({ workspaceId })` on the Widget host before `tokenExpiresAt`. It accepts a token at most 60 seconds past expiry, allows 30 renewals per minute, and keeps the same session and deadline. The React kit does not call it.

## 4. Tenant and subject isolation

- Sessions with the same tenant and subject on the same Widget and Agent **share conversation history**. A hard-coded subject such as `"guest"` puts every visitor in one shared history. Use a distinct subject ID for each person.
- Subject IDs are scoped to their tenant, so `user-42` in tenant A is a different subject from `user-42` in tenant B.
- The browser cannot choose the tenant, subject, Agent, secrets or pinned parameters. Every conversation inherits them from the session. A conversation ID outside the session's identity returns 404, the same as one that does not exist.
- To scope tool calls to the visitor's own records, pin the ID instead of trusting the model: `pinnedParameters: { accountId: user.orgId }`.

## 5. Revocation and cleanup

| Goal | Call | Effect |
| --- | --- | --- |
| End one session now (logout, incident) | `widgetSessions.revoke(id)` | `STATE_REVOKED`. Its tokens fail with 401 and its secrets are deleted. Repeat calls succeed. |
| End all of a user's sessions | `list({ widgetId, tenantId: "external_id:<org>", subjectId: "external_id:<user>", state: "STATE_ACTIVE" })`, then `revoke` each | `subjectId` in the external-ID form needs `tenantId` |
| Remove a session record | `widgetSessions.delete(id)` | Its conversations are kept but no longer linked to the session |
| Erasure request for a tenant | `widgetSessions.deleteTenant({ tenantId: "external_id:<org>" })` | Deletes the tenant's sessions **and their conversations** on every Widget. Each call deletes at most 10,000 sessions, so repeat until `sessionsDeleted` is 0. |
| Turn off a Widget | `widgets.archive(id)` | The host returns 404 and its sessions are revoked. `unarchive` does not restore them, so mint new sessions. |

Ending your app's own login does not invalidate widget tokens. Revoke the session, and make the mint route refuse signed-out users; otherwise `getToken` mints a new session.

```ts
for await (const s of await client.widgetSessions.list({
  widgetId: "external_id:support-chat", tenantId: `external_id:${orgId}`,
  subjectId: `external_id:${userId}`, state: "STATE_ACTIVE",
})) await client.widgetSessions.revoke(s.metadata.id);
```

## 6. Origins, CSP and transport

- The page's origin must be on the allowlist. A non-GET request without an `Origin` header is refused, and the host accepts HTTPS only.
- With a Content Security Policy, allow the Widget host in `connect-src`: `connect-src 'self' https://k7m2xq9fp4wn.widgets.cadenya.com` (or `https://*.widgets.cadenya.com`). The kit uses `fetch` for requests and streams, and it uses no iframe. If you use the Widgets Tools display card, allow its image hosts in `img-src`.
- CORS allows the `GET`, `POST` and `OPTIONS` methods and the `Authorization`, `Content-Type` and `Last-Event-ID` headers.

## Troubleshooting

| Symptom (exact string) | Cause and fix |
| --- | --- |
| Browser shows a CORS error; the preflight returns `403 {"error":"origin not allowed"}` | The page origin is not an exact entry. Add it with `widgets.update`, matching scheme, case and port. |
| `403 {"error":"origin required"}` | A POST was sent without `Origin` (for example from a server or curl). Call the Widget host from the browser. |
| `403 {"error":"https required"}` | The request used `http://`. Use `https://{host}`. |
| `404 {"error":"unknown widget"}` | Wrong host, Widget archived or deleted, or a new Widget that is still propagating (up to a minute). |
| `400 validation failed`, `spec.widgetId`: `widget does not exist in this workspace` / `archived widgets cannot mint sessions; unarchive the widget first` | Wrong workspace or ID, or the Widget is archived. |
| `400 validation failed` on `spec.tenant` or `spec.subject` | One of them is missing or does not match `[A-Za-z0-9._-]{1,64}`. |
| `Session expiry must be in the future` | `spec.expiresAt` is in the past. |
| `agent must be published to create an objective` | The Widget's Agent is a draft. Publish it. |
| `403 Session cannot create or continue conversations` / `Widget session cannot read conversations` | The minting key lacks `objectives:manage` / `objectives:read`. Add the scope and mint a new session; the old session keeps its frozen scopes. |
| `401 Widget access token expired` (`TOKEN_EXPIRED`) | The token is past its expiry. Provide `getToken`, or renew before `tokenExpiresAt`. |
| `401` right after a revoke or an eviction (more than 10 live sessions) | Revocation rotates the session's signing key, so its tokens fail the signature check. The kit then calls `getToken`; mint again only if the visitor is still allowed. |
| `403 Widget session expired` (`SESSION_EXPIRED`) | The session's deadline passed. Mint a new session. |
| `403` with `SESSION_REVOKED` (`Widget session revoked`, `Widget session authorization revoked`) | The session, or the API key that minted it, no longer authorizes access. Mint with a valid key. |
| `429 Widget session has spent its message allowance` (`SESSION_EXHAUSTED`) | The session reached 200 messages. Minting a new session is an explicit app decision. |
| `Widget session requires tenant and subject identity; create a new session` | A legacy session without identity. Mint a new one. |
| `429 Widget session renewal rate limit exceeded` (`RATE_LIMITED`) | More than 30 renewals per minute. Honor `Retry-After`. |
| `This assistant is temporarily unavailable. Please try again later.` | The account's plan refused the request. Check the plan and usage. |
| Server-side `403` with reason `SCOPE_MISSING` | The key lacks `widgets:manage` or `widget_sessions:manage`. |

Match the `google.rpc.ErrorInfo` reason (domain `api.cadenya.com`), not the message text. The edge's `{"error": …}` bodies have no reason.

## End-to-end check

1. `client.agents.retrieve(agentId)` returns `state: "STATE_PUBLISHED"`.
2. `client.widgets.retrieve(widgetId)` returns `state: "STATE_ACTIVE"` and your origin in `spec.originAllowlist`.
3. `curl -X POST` your mint route while signed in. It returns `host` and `token`, and returns 401 when signed out.
4. Open the page on an allowlisted origin and send a message. The reply streams into the panel.
5. Call `widgetSessions.retrieve(sessionId)`. It returns `state: "STATE_ACTIVE"` and a nonzero `info.messageCount`. Revoke the session and confirm that it returns `STATE_REVOKED`.
