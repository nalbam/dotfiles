#!/usr/bin/env python3
"""Generate Codex and OpenCode files from the shared sources.

Sources (edit these):
    claude/skills/<name>/  shared skills and their Markdown references
    claude/agents/*.md     Claude Code subagents
    codex/AGENTS.md        global instructions

Generated (do not edit):
    codex/skills/          Codex skills; hand-maintained agents/openai.yaml is kept
    opencode/              OpenCode AGENTS.md, agents/, and skills/

Each tool gets its own copy because tool-specific syntax differs: skill
invocation (`/name`, `$name`, `@name`), the Git rules location, and the
frontmatter fields each tool understands.

Usage:
    python3 scripts/gen-ai-tools.py          # regenerate
    python3 scripts/gen-ai-tools.py --check  # verify committed files match
"""

from collections import namedtuple
import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_SKILLS = REPO_ROOT / "claude" / "skills"
CLAUDE_AGENTS = REPO_ROOT / "claude" / "agents"
CODEX_INSTRUCTIONS = REPO_ROOT / "codex" / "AGENTS.md"
CODEX_SKILLS = REPO_ROOT / "codex" / "skills"
OPENCODE = REPO_ROOT / "opencode"

# drop: frontmatter fields the tool does not understand.
# invoke: prefix that replaces Claude's `/` in skill invocations.
Tool = namedtuple("Tool", "drop replacements invoke")

SHARED_REPLACEMENTS = (
    ("`rules/git-workflow.md`", "AGENTS.md 의 Git Safety"),
    ("PR 번호 인자: `$ARGUMENTS`", "PR 번호 인자: 사용자가 스킬 호출 시 함께 제공한 값"),
)
CODEX = Tool(("allowed-tools", "argument-hint", "disable-model-invocation"), SHARED_REPLACEMENTS, "$")
# OpenCode V2 honors disable-model-invocation, so manual-only skills stay manual.
OPENCODE_TOOL = Tool(("allowed-tools", "argument-hint"), SHARED_REPLACEMENTS, "@")

# Codex instructions name Codex invocation syntax; each entry must match.
OPENCODE_INSTRUCTION_REPLACEMENTS = (("명시 호출은 `$<name>`을", "명시 호출은 `@<name>`을"),)

# Claude Code tool name -> OpenCode V2 permission action.
AGENT_TOOL_ACTIONS = {
    "Read": "read", "Grep": "grep", "Glob": "glob", "Bash": "shell",
    "Edit": "edit", "Write": "edit", "WebFetch": "webfetch", "WebSearch": "websearch",
}
AGENT_FIELDS = {"name", "description", "tools"}


def split_frontmatter(text):
    """Return (frontmatter lines, body) or (None, text) without frontmatter."""
    lines = text.split("\n")
    if lines[0] != "---" or "---" not in lines[1:]:
        return None, text
    end = lines.index("---", 1)
    return lines[1:end], "\n".join(lines[end + 1:])


def strip_frontmatter(text, fields):
    """Remove the given top-level fields, including their indented values."""
    frontmatter, body = split_frontmatter(text)
    if frontmatter is None:
        return text
    kept, skipping = [], False
    for line in frontmatter:
        if line.startswith(tuple(f"{field}:" for field in fields)):
            skipping = True
            continue
        if skipping and (not line.strip() or line.startswith((" ", "\t"))):
            continue
        skipping = False
        kept.append(line)
    return "\n".join(["---", *kept, "---", body])


def translate(text, tool, skills):
    for old, new in tool.replacements:
        text = text.replace(old, new)
    # `/name` invokes a skill only when it is not part of a path or word.
    pattern = r"(?<![\w./-])/(" + "|".join(map(re.escape, skills)) + r")(?![\w-])"
    return re.sub(pattern, lambda match: tool.invoke + match.group(1), text)


def transform(text, tool, skills):
    return translate(strip_frontmatter(text, tool.drop), tool, skills)


def agent_permissions(tools):
    """Allowlist the agent's Claude tools; OpenCode applies the last matching rule."""
    actions = []
    for name in tools:
        if name not in AGENT_TOOL_ACTIONS:
            raise ValueError(f"No OpenCode permission for Claude tool: {name}")
        if AGENT_TOOL_ACTIONS[name] not in actions:
            actions.append(AGENT_TOOL_ACTIONS[name])
    rules = [("*", "*", "deny")] + [(action, "*", "allow") for action in actions]
    if "read" in actions:
        # The read allowance overrides OpenCode's default .env guard; restate it
        # as OpenCode's built-in explore agent does.
        rules += [("read", "*.env", "ask"), ("read", "*.env.*", "ask"), ("read", "*.env.example", "allow")]
    # Restore the default prompt for paths outside the project.
    return rules + [("external_directory", "*", "ask")]


def convert_agent(path, skills):
    """Convert a Claude Code subagent into an OpenCode V2 subagent."""
    frontmatter, body = split_frontmatter(path.read_text(encoding="utf-8"))
    if frontmatter is None:
        raise ValueError(f"{path.name}: missing frontmatter")
    fields = {}
    for line in frontmatter:
        key, separator, value = line.partition(":")
        if not separator or key not in AGENT_FIELDS:
            raise ValueError(f"{path.name}: unsupported frontmatter line: {line}")
        fields[key] = value.strip()
    # OpenCode takes the agent ID from the filename.
    if fields.get("name") != path.stem:
        raise ValueError(f"{path.name}: name must match the filename")
    if not fields.get("description"):
        raise ValueError(f"{path.name}: description is required")
    tools = [name.strip() for name in fields.get("tools", "").split(",") if name.strip()]
    if not tools:
        raise ValueError(f"{path.name}: tools is required")
    lines = ["---",
             "description: " + json.dumps(translate(fields["description"], OPENCODE_TOOL, skills), ensure_ascii=False),
             "mode: subagent",
             "permissions:"]
    lines += [f"  - {{action: {json.dumps(action)}, resource: {json.dumps(resource)}, effect: {json.dumps(effect)}}}"
              for action, resource, effect in agent_permissions(tools)]
    return "\n".join(lines + ["---"]) + "\n" + translate(body, OPENCODE_TOOL, skills)


def opencode_instructions():
    text = CODEX_INSTRUCTIONS.read_text(encoding="utf-8")
    for old, new in OPENCODE_INSTRUCTION_REPLACEMENTS:
        if old not in text:
            raise ValueError(f"codex/AGENTS.md no longer contains: {old}")
        text = text.replace(old, new)
    return text


def generated_files():
    """Return {path: content} for every generated file."""
    skill_dirs = sorted(path for path in CLAUDE_SKILLS.iterdir() if (path / "SKILL.md").is_file())
    if not skill_dirs:
        raise ValueError(f"No skills found under {CLAUDE_SKILLS}")
    skills = [path.name for path in skill_dirs]
    files = {}
    for skill_dir in skill_dirs:
        for source in sorted(path for path in skill_dir.rglob("*") if path.is_file()):
            if source.suffix != ".md":
                raise ValueError(f"Only Markdown skill files are generated: {source.relative_to(REPO_ROOT)}")
            relative = source.relative_to(CLAUDE_SKILLS)
            text = source.read_text(encoding="utf-8")
            files[CODEX_SKILLS / relative] = transform(text, CODEX, skills)
            files[OPENCODE / "skills" / relative] = transform(text, OPENCODE_TOOL, skills)
    for agent in sorted(CLAUDE_AGENTS.glob("*.md")):
        files[OPENCODE / "agents" / agent.name] = convert_agent(agent, skills)
    files[OPENCODE / "AGENTS.md"] = opencode_instructions()
    return files


def owned_files():
    """Existing files the generator owns; Codex metadata such as openai.yaml is excluded."""
    codex = [path for path in CODEX_SKILLS.rglob("*.md") if len(path.relative_to(CODEX_SKILLS).parts) > 1]
    return set(codex) | {path for path in OPENCODE.rglob("*") if path.is_file()}


def main():
    check = "--check" in sys.argv[1:]
    try:
        expected = generated_files()
    except ValueError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1
    changed = [path for path, text in expected.items()
               if not path.is_file() or path.read_text(encoding="utf-8") != text]
    stale = sorted(owned_files() - expected.keys())
    for path in changed:
        print(f"{'MISMATCH' if check else 'generated'}: {path.relative_to(REPO_ROOT)}")
    for path in stale:
        print(f"{'STALE' if check else 'removed'}: {path.relative_to(REPO_ROOT)}")
    if check:
        if changed or stale:
            print(f"\n{len(changed) + len(stale)} file(s) out of date — run: python3 scripts/gen-ai-tools.py",
                  file=sys.stderr)
            return 1
        print(f"OK: {len(expected)} generated files are current")
        return 0
    for path in changed:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(expected[path], encoding="utf-8")
    for path in stale:
        path.unlink()
    # Remove directories left empty by deleted skills.
    for directory in sorted((p for p in OPENCODE.rglob("*") if p.is_dir()), reverse=True):
        if not any(directory.iterdir()):
            directory.rmdir()
    return 0


if __name__ == "__main__":
    sys.exit(main())
