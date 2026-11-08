#!/usr/bin/env python3
"""Validate the skills in this repository.

Checks each skills/<name>/ directory against the Agent Skills specification
(https://agentskills.io/specification) and this repository's conventions:

- SKILL.md has YAML frontmatter with `name` (matches the directory, lowercase
  letters, digits and single hyphens, at most 64 characters) and `description`
  (1-1024 characters, no XML tags).
- The SKILL.md body is under 500 lines.
- Relative links resolve to files in the repository, and skill files link to
  references at most one level deep.
- Backticked skill names that look like `cadenya-*` refer to skills that exist.
- agents/openai.yaml, when present, invokes the skill by its own name.
- With --check-urls, every https://cadenya.com link returns HTTP 200.

Exit status is 1 if any check fails.
"""

import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SKILLS = ROOT / "skills"
NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
MAX_BODY_LINES = 500
LINK_RE = re.compile(r"\[[^\]]*\]\(([^)\s]+)\)")
SKILL_REF_RE = re.compile(r"`(cadenya(?:-[a-z0-9]+)+)`")


def frontmatter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not match:
        return None, text
    fields = {}
    for line in match.group(1).splitlines():
        pair = re.match(r"^([a-z_-]+):\s*(.*)$", line)
        if pair:
            value = pair.group(2).strip()
            if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
                value = value[1:-1].replace('\\"', '"')
            fields[pair.group(1)] = value
    return fields, text[match.end():]


def main():
    check_urls = "--check-urls" in sys.argv
    errors = []
    names = {p.name for p in SKILLS.iterdir() if p.is_dir()}
    urls = set()

    for skill in sorted(SKILLS.iterdir()):
        if not skill.is_dir():
            continue
        md = skill / "SKILL.md"
        if not md.exists():
            errors.append(f"{skill.name}: missing SKILL.md")
            continue
        text = md.read_text()
        fields, body = frontmatter(text)
        if fields is None:
            errors.append(f"{skill.name}: SKILL.md has no frontmatter")
            continue
        name, description = fields.get("name", ""), fields.get("description", "")
        if name != skill.name:
            errors.append(f"{skill.name}: frontmatter name {name!r} does not match the directory")
        if not NAME_RE.match(name) or len(name) > 64:
            errors.append(f"{skill.name}: invalid name {name!r}")
        if not 1 <= len(description) <= 1024:
            errors.append(f"{skill.name}: description is {len(description)} characters (1-1024 allowed)")
        if re.search(r"<[a-zA-Z/][^>]*>", description):
            errors.append(f"{skill.name}: description contains an XML tag")
        body_lines = body.count("\n")
        if body_lines >= MAX_BODY_LINES:
            errors.append(f"{skill.name}: SKILL.md body is {body_lines} lines (limit {MAX_BODY_LINES})")

        for path in sorted(skill.rglob("*.md")):
            content = path.read_text()
            rel = path.relative_to(ROOT)
            for target in LINK_RE.findall(content):
                if target.startswith(("http://", "https://")):
                    if target.startswith("https://cadenya.com"):
                        urls.add(target.split("#")[0])
                    continue
                if target.startswith(("#", "mailto:")):
                    continue
                resolved = (path.parent / target.split("#")[0]).resolve()
                if not resolved.exists():
                    errors.append(f"{rel}: broken link {target}")
                elif path != md and resolved.parent == skill / "references" and path.parent == skill / "references":
                    errors.append(f"{rel}: links to another reference file ({target}); link references from SKILL.md only")
            for ref in SKILL_REF_RE.findall(content):
                if ref not in names:
                    errors.append(f"{rel}: refers to unknown skill `{ref}`")

        openai = skill / "agents" / "openai.yaml"
        if openai.exists():
            prompts = re.findall(r"\$([a-z0-9-]+)", openai.read_text())
            if prompts and any(p != skill.name for p in prompts):
                errors.append(f"{openai.relative_to(ROOT)}: default_prompt invokes ${prompts[0]}, expected ${skill.name}")

    for doc in [ROOT / "README.md", ROOT / "rules" / "cadenya.mdc"]:
        for ref in SKILL_REF_RE.findall(doc.read_text()) + re.findall(r"skills/([a-z0-9-]+)/SKILL\.md", doc.read_text()):
            if ref not in names:
                errors.append(f"{doc.relative_to(ROOT)}: refers to unknown skill {ref}")
        for skill_name in names:
            if f"skills/{skill_name}/SKILL.md" not in doc.read_text() and doc.name == "README.md":
                errors.append(f"README.md: skills table is missing {skill_name}")

    if check_urls:
        for url in sorted(urls):
            try:
                request = urllib.request.Request(url, method="GET", headers={"User-Agent": "cadenya-skills-validator"})
                with urllib.request.urlopen(request, timeout=20) as response:
                    if response.status != 200:
                        errors.append(f"{url}: HTTP {response.status}")
            except Exception as exc:  # noqa: BLE001 - report every failure
                errors.append(f"{url}: {exc}")

    for error in errors:
        print(f"error: {error}")
    print(f"{len(names)} skills checked, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
