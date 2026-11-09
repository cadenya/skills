# Contributing

Keep skills small: help agents find the right documentation instead of maintaining another copy of it.

For changes to skills, rules, or plugin manifests:

- Read the relevant page in [Cadenya's documentation](https://cadenya.com/docs) and verify that it supports the proposed guidance; a working URL alone is not enough.
- Link directly to the relevant page. Prefer links over duplicated API signatures, limits, pricing, or examples that can become stale.
- In skills and rules, link `cadenya.com/docs` pages by their markdown route (`<route>.md`, e.g. `https://cadenya.com/docs/mcp-server.md`), not the HTML route. Not every agent does content negotiation, so the explicit route guarantees markdown. Use `https://cadenya.com/docs/llms.txt` for the docs index. Keep human-facing files (README, plugin manifests) on HTML routes.
- When correcting outdated content, replace it with a short pointer to the current documentation where possible.
- If the required guidance is missing from the documentation, describe the gap in the pull request rather than adding unsupported guidance to a skill.
- Never commit API keys or other credentials, including in examples and plugin manifests.
