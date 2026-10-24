#!/usr/bin/env python3
"""Generate Codex and OpenCode files from the Claude sources.

Sources (edit these):
    claude/CLAUDE.md, claude/rules/*.md  global instructions
    claude/skills/<name>/                shared skills and their Markdown references
    claude/agents/*.md                   subagents
    claude/settings.json                 `permissions.deny` shell rules

Generated (do not edit):
    codex/AGENTS.md, codex/agents/       Codex instructions and standalone TOML agents
    codex/skills/                       Codex skills; hand-maintained agents/openai.yaml is kept
    opencode/                            OpenCode AGENTS.md, opencode.json, agents/, skills/

Each tool gets its own copy because tool-specific syntax differs: skill
invocation (`/name`, `$name`, `@name`), where the rules live, and the
frontmatter fields and permission formats each tool understands.

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
CLAUDE = REPO_ROOT / "claude"
CODEX = REPO_ROOT / "codex"
OPENCODE = REPO_ROOT / "opencode"

# drop: frontmatter fields the tool does not understand.
# invoke: prefix that replaces Claude's `/` in skill invocations.
Tool = namedtuple("Tool", "drop invoke")
CODEX_TOOL = Tool(("allowed-tools", "argument-hint", "disable-model-invocation"), "$")
# OpenCode V2 honors disable-model-invocation, so manual-only skills stay manual.
OPENCODE_TOOL = Tool(("allowed-tools", "argument-hint"), "@")

# skills: skill names; rules: {rule file stem: rule title}.
Sources = namedtuple("Sources", "skills rules")

ARGUMENTS = ("PR 번호 인자: `$ARGUMENTS`", "PR 번호 인자: 사용자가 스킬 호출 시 함께 제공한 값")

# Claude Code tool name -> OpenCode V2 permission action.
AGENT_TOOL_ACTIONS = {
    "Read": "read", "Grep": "grep", "Glob": "glob", "Bash": "shell",
    "Edit": "edit", "Write": "edit", "WebFetch": "webfetch", "WebSearch": "websearch",
}
AGENT_FIELDS = {"name", "description", "tools"}
# OpenCode's default .env guard, which a later read allowance would override.
ENV_GUARD = [("read", "*.env", "ask"), ("read", "*.env.*", "ask"), ("read", "*.env.example", "allow")]


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


def translate(text, tool, sources, rule_prefix="AGENTS.md의 "):
    text = text.replace(*ARGUMENTS)
    if tool == CODEX_TOOL:
        text = text.replace("`agents/<name>.md`", "`agents/<name>.toml`의 `developer_instructions`")

    # Claude loads rules from separate files; the other tools get them as AGENTS.md sections.
    def rule(match):
        if match.group(1) not in sources.rules:
            raise ValueError(f"Unknown rule reference: {match.group(0)}")
        return rule_prefix + sources.rules[match.group(1)]

    text = re.sub(r"`rules/([\w-]+)\.md`", rule, text)
    # `/name` invokes a skill only when it is not part of a path or word.
    pattern = r"(?<![\w./-])/(" + "|".join(map(re.escape, sources.skills)) + r")(?![\w-])"
    return re.sub(pattern, lambda match: tool.invoke + match.group(1), text)


def transform(text, tool, sources):
    return translate(strip_frontmatter(text, tool.drop), tool, sources)


def require_replace(text, old, new, source):
    if old not in text:
        raise ValueError(f"{source} no longer contains: {old}")
    return text.replace(old, new)


def instructions(tool, sources):
    """Compose AGENTS.md from CLAUDE.md followed by the rules, in Claude's load order."""
    source = "claude/CLAUDE.md"
    text = (CLAUDE / "CLAUDE.md").read_text(encoding="utf-8")
    text = require_replace(text, "# CLAUDE.md\n", "# AGENTS.md\n", source)
    text = require_replace(text, " 언어·Git·보안 규칙은 자동 로드되는 `rules/`에서 관리한다.", "", source)
    text = require_replace(text, "`/<name>` 호출은 제공된 Skill 도구로 실행한다.",
                           f"명시 호출은 `{tool.invoke}<name>`을 사용한다.", source)
    parts = [text.rstrip("\n")]
    for path in sorted((CLAUDE / "rules").glob("*.md")):
        # Each rule file becomes a second-level section.
        rule = re.sub(r"^(#+ )", r"#\1", path.read_text(encoding="utf-8"), flags=re.MULTILINE)
        parts.append(rule.rstrip("\n"))
    # Inside AGENTS.md, a rule reference names its section only.
    return translate("\n\n".join(parts) + "\n", tool, sources, rule_prefix="")


def rule_title(path):
    match = re.match(r"# (.+)\n", path.read_text(encoding="utf-8"))
    if not match:
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must start with a '# ' title")
    return match.group(1)


def shell_denies():
    """Translate Claude `Bash(...)` deny rules into OpenCode shell patterns."""
    settings = json.loads((CLAUDE / "settings.json").read_text(encoding="utf-8"))
    patterns = []
    for entry in settings.get("permissions", {}).get("deny", []):
        match = re.fullmatch(r"Bash\((.+)\)", entry)
        if not match:
            raise ValueError(f"claude/settings.json deny rule has no OpenCode equivalent: {entry}")
        # Claude `cmd:*` is a prefix rule; an OpenCode pattern ending in ` *` also matches bare `cmd`.
        pattern = match.group(1)
        patterns.append(pattern[:-2] + " *" if pattern.endswith(":*") else pattern)
    return patterns


def opencode_config(denies):
    rules = [{"action": "shell", "resource": pattern, "effect": "deny"} for pattern in denies]
    return json.dumps({"$schema": "https://opencode.ai/config.json", "permissions": rules},
                      ensure_ascii=False, indent=2) + "\n"


def agent_permissions(tools, denies):
    """Allowlist the agent's Claude tools.

    OpenCode applies agent rules after global rules and uses the last match, so an
    allowance overrides earlier guards for its action. Restate the guards after it.
    """
    actions = []
    for name in tools:
        if name not in AGENT_TOOL_ACTIONS:
            raise ValueError(f"No OpenCode permission for Claude tool: {name}")
        if AGENT_TOOL_ACTIONS[name] not in actions:
            actions.append(AGENT_TOOL_ACTIONS[name])
    rules = [("*", "*", "deny")] + [(action, "*", "allow") for action in actions]
    if "read" in actions:
        rules += ENV_GUARD
    if "shell" in actions:
        rules += [("shell", pattern, "deny") for pattern in denies]
    # Restore the default prompt for paths outside the project.
    return rules + [("external_directory", "*", "ask")]


def read_agent(path):
    """Read our deliberately small subset of Claude agent frontmatter."""
    frontmatter, body = split_frontmatter(path.read_text(encoding="utf-8"))
    if frontmatter is None:
        raise ValueError(f"{path.name}: missing frontmatter")
    fields = {}
    for line in frontmatter:
        key, separator, value = line.partition(":")
        if not separator or key not in AGENT_FIELDS:
            raise ValueError(f"{path.name}: unsupported frontmatter line: {line}")
        if key in fields:
            raise ValueError(f"{path.name}: duplicate frontmatter field: {key}")
        fields[key] = value.strip()
    if fields.get("name") != path.stem or not re.fullmatch(r"[a-z][a-z0-9-]*", path.stem):
        raise ValueError(f"{path.name}: name must match the filename")
    if not fields.get("description"):
        raise ValueError(f"{path.name}: description is required")
    if not body.strip():
        raise ValueError(f"{path.name}: instructions are required")
    # Omission inherits the client's tools (including configured MCP tools).
    tools = None
    if "tools" in fields:
        tools = [name.strip() for name in fields["tools"].split(",")]
        if not all(tools):
            raise ValueError(f"{path.name}: tools must be omitted or nonempty")
        for name in tools:
            if name not in AGENT_TOOL_ACTIONS:
                raise ValueError(f"{path.name}: unsupported Claude tool: {name}")
    return fields, body, tools


def convert_agent(path, sources, denies):
    """Convert a Claude Code agent into an OpenCode V2 agent."""
    fields, body, tools = read_agent(path)
    lines = ["---",
             "description: " + json.dumps(translate(fields["description"], OPENCODE_TOOL, sources), ensure_ascii=False),
             "mode: all" if path.stem == "master" else "mode: subagent"]
    if tools is not None:
        lines.append("permissions:")
        lines += [f"  - {{action: {json.dumps(action)}, resource: {json.dumps(resource)}, effect: {json.dumps(effect)}}}"
                  for action, resource, effect in agent_permissions(tools, denies)]
    return "\n".join(lines + ["---"]) + "\n" + translate(body, OPENCODE_TOOL, sources)


def codex_agent(path, sources):
    """Codex inherits parent permissions; Claude tool lists are not sandbox rules."""
    fields, body, _ = read_agent(path)
    lines = ["# Generated from claude/agents/" + path.name + "; do not edit."]
    for key in ("name", "description"):
        lines.append(f"{key} = {json.dumps(translate(fields[key], CODEX_TOOL, sources), ensure_ascii=False)}")
    # Encode line by line to preserve literal backslashes, quotes and control
    # characters while keeping the instructions readable in multiline TOML.
    body = translate(body, CODEX_TOOL, sources).lstrip("\n")
    escaped = "\n".join(json.dumps(line, ensure_ascii=False)[1:-1] for line in body.split("\n"))
    lines.append('developer_instructions = """\n' + escaped + '"""')
    return "\n".join(lines) + "\n"


def generated_files():
    """Return {path: content} for every generated file."""
    skill_dirs = sorted(path for path in (CLAUDE / "skills").iterdir() if (path / "SKILL.md").is_file())
    if not skill_dirs:
        raise ValueError("No skills found under claude/skills")
    sources = Sources([path.name for path in skill_dirs],
                      {path.stem: rule_title(path) for path in (CLAUDE / "rules").glob("*.md")})
    denies = shell_denies()
    files = {CODEX / "AGENTS.md": instructions(CODEX_TOOL, sources),
             OPENCODE / "AGENTS.md": instructions(OPENCODE_TOOL, sources),
             OPENCODE / "opencode.json": opencode_config(denies)}
    for skill_dir in skill_dirs:
        for source in sorted(path for path in skill_dir.rglob("*") if path.is_file()):
            if source.suffix != ".md":
                raise ValueError(f"Only Markdown skill files are generated: {source.relative_to(REPO_ROOT)}")
            relative = source.relative_to(CLAUDE / "skills")
            text = source.read_text(encoding="utf-8")
            files[CODEX / "skills" / relative] = transform(text, CODEX_TOOL, sources)
            files[OPENCODE / "skills" / relative] = transform(text, OPENCODE_TOOL, sources)
    for agent in sorted((CLAUDE / "agents").glob("*.md")):
        files[CODEX / "agents" / (agent.stem + ".toml")] = codex_agent(agent, sources)
        files[OPENCODE / "agents" / agent.name] = convert_agent(agent, sources, denies)
    return files


def owned_files():
    """Existing files the generator owns; Codex metadata such as openai.yaml is excluded."""
    skills = CODEX / "skills"
    codex = {path for path in skills.rglob("*.md") if len(path.relative_to(skills).parts) > 1}
    codex |= {CODEX / "AGENTS.md"} if (CODEX / "AGENTS.md").is_file() else set()
    codex |= set((CODEX / "agents").glob("*.toml"))
    return codex | {path for path in OPENCODE.rglob("*") if path.is_file()}


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
