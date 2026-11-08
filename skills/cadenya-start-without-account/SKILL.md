---
name: cadenya-start-without-account
description: Get a working Cadenya workspace for a user who has no Cadenya account, with no signup step. The CLI creates a temporary workspace and API key and returns a claim URL; the user opens it to keep the workspace, and an unclaimed workspace is permanently deleted 24 hours after creation. Use when a task needs Cadenya and `cadenya whoami` fails or no Cadenya credential exists, when the user says they don't have an account yet, on a `REQUIRES_CLAIM` or `TEMPORARY_WORKSPACE_CLAIMED` error, or on a question about a claim link.
---

# Start with Cadenya without an account

## Overview

A user without a Cadenya account can still have you build with Cadenya. One command creates a **temporary workspace**: a real workspace, with an API key that reaches only that workspace, plus a **claim URL**. When the user opens the claim URL and signs in or signs up, the workspace becomes theirs.

What the user needs to know:

- **24 hours.** A workspace nobody claims is permanently deleted 24 hours after it was created, with its agents, tool sets, objectives and secrets. It can't be recovered.
- **Only a demo model until claimed.** A temporary workspace has no Cadenya-provided model and no model credit. A free demo model shows the agent loop with scripted output. For real model output before claiming, the user adds their own provider key. Claiming adds Cadenya's promotional model credit.
- **The claim URL is a secret.** Whoever opens it and signs in becomes the owner of the workspace.
- **Claiming needs a person without a Cadenya account.** Someone who already has one gets refused, and should use their own account instead.

For everything after setup (tool sets, agents, objectives, config files), use the `cadenya-cli` skill.

## Decide whether to use this at all

```sh
cadenya whoami --display json   # exits 0 only with a working credential
cadenya auth status             # names the credential source in effect; always exits 0
```

- **`whoami --display json` fails, or `cadenya` isn't installed:** continue below. If the user mentions having an account, offer `cadenya auth login` instead: an existing account holder can't claim a temporary workspace.
- **`whoami` exits 0 and `auth status` names a stored login or `$CADENYA_API_KEY`:** the user already has an account. Don't create a temporary workspace; follow `cadenya-cli`. `--temporary` refuses to run while such a credential is configured.
- **`whoami` exits 0 and `auth status` names `temporary workspace … (.cadenya/temporary.json)`:** this directory already has a live temporary workspace. Run the create command below anyway: it returns that workspace with `"reused": true` and creates nothing, which gives you the claim URL and deadline to re-share.

Install the CLI if needed:

```sh
brew install cadenya/tools/cadenya    # macOS/Linux; Windows: choco install cadenya
```

## Create the temporary workspace

Run this from the project's root directory:

```sh
cadenya workspaces create --temporary --display json | jq 'del(.apiKey)'
```

It prints one JSON object: `status` (`created` or `reused`), `workspaceId`, `claimUrl`, `expiresAt` (UTC, RFC 3339), `apiKey`, `reused`, `nextStep`, and `next` (follow-up commands, each with `command` and `when`). The CLI has already saved `apiKey` in `.cadenya/temporary.json`, so strip it before the output reaches your transcript. Without `jq`, use `python3 -c 'import json,sys; d=json.load(sys.stdin); d.pop("apiKey",None); print(json.dumps(d,indent=2))'`.

`nextStep` repeats the claim URL, and a notice with the claim URL also goes to stderr. Don't redirect either output to a file or a log, and don't discard stderr: errors go there too.

- The CLI stores the credential in `.cadenya/temporary.json` in the current directory and adds `.cadenya/temporary.json` to `.gitignore` (only that file, because `.cadenya/` also holds the committed `cadenya config apply` files). It does this in a directory that isn't a git repository too, so the file stays ignored if one is created later.
- Check it before anything else: `git check-ignore .cadenya/temporary.json` must print the path. If the CLI printed `warning: could not make git ignore .cadenya/temporary.json`, fix `.gitignore` (look for a negation rule or a symlinked `.gitignore`) before any `git add`. Later `cadenya` commands run from this directory use it and its workspace on their own: don't pass `--api-key` or `--workspace-id`, and don't export the key into your shell.
- Never move, copy, print or commit `.cadenya/temporary.json`. Don't echo `apiKey` back to the user.
- If this directory already has a live temporary workspace, the command returns it with `"reused": true`. Don't pass `--fresh` unless the user asks for a second workspace.
- `--temporary` refuses to run in CI (`$CI` set) and when a credential is configured.
- `--expire-after` takes a lifetime from `1h` to `24h` (the default is `24h`). It can shorten the window, never extend it.

## Give the user the claim URL right away

First, decide where your reply goes. If anyone besides the user can read it (a PR, issue or Slack thread, a bot posting to a channel, a shared transcript), don't print the claim URL. Tell the user to run `cadenya auth login` in the project directory instead, which claims the workspace without the link. Otherwise, show the claim URL and deadline as soon as you have them, before you build anything. Fill in `CLAIM_URL` and `DEADLINE`, the expiry in local time with its zone (the stderr notice prints it that way, for example `Mon Nov 9 14:07 EST`). For a reused workspace, say you found and reused it instead of "created":

> I created a temporary Cadenya workspace. To keep it, open this link and sign in or sign up before **DEADLINE**: CLAIM_URL
> Keep the link private: whoever opens it can take the workspace. If nobody claims it by then, it's deleted along with everything I build in it. You can also claim it by running `cadenya auth login` in this directory.

- Put the claim URL only in your private reply to the user. Never write it to a file in the repository, a commit, a PR, an issue, a code comment or a log.
- The CLI prints the claim URL again in other places: `claim-status --wait` on stderr each time the state changes, and every `REQUIRES_CLAIM` error. Never tee, redirect or background these into a file or a retained log, and don't run `--wait` where output is collected (CI, shared terminals, log shippers).
- If application code needs the API key, write `CADENYA_API_KEY` and `CADENYA_WORKSPACE_ID` to an env file that git ignores (check with `git check-ignore <file>`, and add it to `.gitignore` if needed, even in a directory that isn't a repository yet). Read the key from `.cadenya/temporary.json` or the create output; never hard-code it in source.
- Never source or export that env file into the shell that runs `cadenya`. A `CADENYA_API_KEY` in the environment makes `--temporary` refuse, outranks `.cadenya/temporary.json`, and after the claim outranks the new login. Let the application load the file itself.

## What works before the claim

You can create tool sets, agents and variations, publish agents and run objectives. Some things wait for the claim, and small caps apply to the rest.

- **Tool set hosts.** Tool sets only reach hosts on the account's trusted endpoints, and `cadenya trusted-endpoints create` fails before the claim. Before the claim, tool sets can call Cadenya-hosted endpoints such as the Faker MCP server at `https://free.cadenya.com/faker-mcp`, and Bare tool sets (`--adapter bare`) work because your application supplies each result. An HTTP, OpenAPI or MCP tool set pointed at any other host is refused at call time until the user claims and trusts the host.
- **Needs a claim:** widgets, memory layers, agent pools, workspace members, more API keys, tool set templates and more workspaces. These return `REQUIRES_CLAIM`. The temporary key also lacks some scopes (trusted endpoints, for one), which fail with HTTP 403 and a missing-scope message instead; treat that the same way.
- **Capped:** agents, variations, tool sets, provider keys, objectives, uploads and loops per month. Going past a cap also returns `REQUIRES_CLAIM`.

## Running objectives before the claim

Before you run an objective, ask the user which option they want:

1. **Use the demo model.** It's the default model in a temporary workspace and costs nothing. It doesn't reason. When the variation has a read-only tool assigned (a GET operation, a read-only MCP tool, or a Bare tool, with no approval required), it calls one with made-up arguments, then returns a templated summary of the result. With no such tool, it returns a scripted reply and calls nothing. To show the full loop (tool call, events, completion), assign a read-only tool set first, for example an MCP tool set on the Faker MCP server (`--mcp-url https://free.cadenya.com/faker-mcp`). Tell the user so, and don't present its output as a real model's. Its model ID is `demo.demo` (provider key `demo`, model `demo`; `cadenya models list` also shows the canonical `model_…` ID), for example `--default-variation-model-id demo.demo` on `agents create`.
2. **Use their own provider key now.** Ask the user to put the key in an environment variable themselves; never ask them to paste it into the chat. Build the command with `cadenya schema ai-provider-keys create`, and pass the key on stdin so it stays off the command line, for example `printf '%s' "$ANTHROPIC_API_KEY" | cadenya ai-provider-keys create --name "Anthropic" --external-id anthropic --provider anthropic --api-key -`. Then `cadenya models list` shows the new models.
3. **Claim first.** After the claim, the workspace gets Cadenya's promotional model credit and objectives run with no key of their own.

Whichever model you use, publish the agent (`cadenya agents publish <agent>`) before you create an objective. The `cadenya-cli` skill covers building and running.

## Checking the claim

```sh
cadenya workspaces claim-status --display json   # state, expiresAt, claimedAt
cadenya workspaces claim-status --wait           # blocks until claimed or expired
```

`state` is `STATE_UNCLAIMED`, `STATE_PENDING` (a claim is finishing), `STATE_CLAIMED` or `STATE_EXPIRED`. The command exits 4 on `STATE_EXPIRED`. Check before long-running work and when the user says they've claimed. Use `--wait` rather than a polling loop of your own. Once it reports `STATE_CLAIMED`, the CLI removes `.cadenya/temporary.json`.

## Errors

| Error | Meaning | What to do |
| --- | --- | --- |
| `REQUIRES_CLAIM` | The feature or amount needs a claimed workspace | Tell the user what it unlocks and how to claim (privately, as above), keep working on everything else |
| HTTP 429 on create, "too many temporary workspaces were created from this network" | This network holds the most live temporary workspaces allowed, or created too many too fast | Tell the user, and stop. They can claim a workspace they already have a link for (that frees a slot), wait for one to expire, or sign up and use `cadenya auth login`. Don't retry in a loop, and never work around it |
| `ACCOUNT_PROVISIONING` | The new workspace is still being set up | Retry after the delay the error gives (a few seconds), at most three times. If it still fails, tell the user and stop |
| HTTP 503 on create, "temporary workspaces are unavailable right now" (`PROVISIONING_DISABLED`) | Creating temporary workspaces is switched off | Tell the user. Don't retry in a loop. Offer signup at https://app.cadenya.com/signup followed by `cadenya auth login` |
| `TEMPORARY_WORKSPACE_EXPIRED`, `state: STATE_EXPIRED`, or a rejected credential after `expiresAt` | The workspace was deleted | Tell the user what was lost. Create a new one only if they want it |
| `--temporary` refused because a credential is configured | The user already has an account | Use `cadenya-cli` with their login |
| `TEMPORARY_WORKSPACE_CLAIMED` (exit code 3) | The user claimed the workspace, which revoked the temporary key. The CLI removed `.cadenya/temporary.json` | Tell the user it's claimed. Ask them to run `cadenya auth login` in this directory, or to create an API key in the dashboard. Continue with the new credential |
| `auth login` says "you already have a Cadenya account" | Someone with an account can't claim a temporary workspace | The login still works: create a workspace in their account and rebuild there. The temporary one expires |

## After the claim

- The workspace no longer expires. **The temporary API key stops working**, and the next request with it returns `TEMPORARY_WORKSPACE_CLAIMED`.
- The simplest way to claim is for the user to run `cadenya auth login` in the project directory: approving that login claims the workspace and logs them in, in one step. If they claimed through the link, they still run `cadenya auth login`, or create an API key in the dashboard.
- Any env file holding the old key needs the new one. A stale `CADENYA_API_KEY` in the environment also outranks the stored login, so unset it after `auth login`.
- Promotional model credit is added on claim. `cadenya models list` shows the models, and the demo model stays but is no longer the default.
