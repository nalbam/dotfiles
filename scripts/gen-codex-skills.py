#!/usr/bin/env python3
"""Generate codex/skills/*/SKILL.md from claude/skills/*/SKILL.md.

claude/skills is the single source of truth. This script applies the
Claude -> Codex transformations (frontmatter fields, rules/*.md -> AGENTS.md
references, Team mode -> generic multi-agent) and writes the results to
codex/skills. Files other than SKILL.md (e.g. agents/openai.yaml) are
preserved as-is.

Usage:
    python3 scripts/gen-codex-skills.py          # regenerate codex/skills
    python3 scripts/gen-codex-skills.py --check  # verify committed files match
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
CLAUDE_SKILLS = REPO_ROOT / "claude" / "skills"
CODEX_SKILLS = REPO_ROOT / "codex" / "skills"

# Frontmatter fields that only Claude Code understands.
CLAUDE_ONLY_FRONTMATTER = ("allowed-tools:", "argument-hint:", "disable-model-invocation:")

# Ordered literal replacements applied to every skill body
# (specific phrases first, generic fallbacks last).
REPLACEMENTS = [
    # language
    ("(`rules/language.md`)", "(AGENTS.md 의 Language)"),
    # code-audit: combined rules reference
    (
        "`rules/coding-style.md`, `rules/testing.md`, `rules/security.md` 와 일관해야 한다",
        "AGENTS.md 의 Coding / Testing / Security 원칙과 일관해야 한다",
    ),
    (
        "(`rules/testing.md`, `rules/coding-style.md#file--function-organization`)",
        "(AGENTS.md 의 Testing / Coding 원칙)",
    ),
    ("— `rules/testing.md`)", "— AGENTS.md 의 Testing 원칙)"),
    # surgical changes (particle variants)
    (
        "`rules/coding-style.md#surgical-changes--외과적-변경` 원칙",
        "AGENTS.md 의 Surgical Changes 원칙",
    ),
    (
        "`rules/coding-style.md#surgical-changes--외과적-변경` 을",
        "AGENTS.md 의 Surgical Changes 를",
    ),
    (
        "`rules/coding-style.md#surgical-changes--외과적-변경`을",
        "AGENTS.md 의 Surgical Changes 를",
    ),
    (
        "(rules/coding-style.md#surgical-changes--외과적-변경)",
        "(AGENTS.md Surgical Changes)",
    ),
    (
        "`rules/coding-style.md#surgical-changes--외과적-변경`",
        "AGENTS.md 의 Surgical Changes",
    ),
    # docs-sync: current-state-only documentation rule
    (
        "(`rules/coding-style.md#documentation`)",
        "(AGENTS.md 의 Anti-Patterns — 현재 상태만 기록)",
    ),
    # git safety
    ("`rules/git-workflow.md`", "AGENTS.md 의 Git Safety"),
    # anti-patterns
    ("`rules/anti-patterns.md#git--deployment`", "AGENTS.md 의 Anti-Patterns"),
    # generic instruction-file rename (after the specific rules above)
    ("CLAUDE.md", "AGENTS.md"),
    # deployed skill path (Codex scans ~/.agents/skills)
    ("~/.claude/skills/", "~/.agents/skills/"),
    # $ARGUMENTS is a Claude Code placeholder; Codex passes arguments as plain text
    ("PR 번호 인자: `$ARGUMENTS`", "PR 번호 인자: 사용자가 스킬 호출 시 함께 제공한 값"),
]

# code-audit Phase 2: Claude Team mode -> generic multi-agent wording.
TEAM_INTRO_START = "**Team 모드를 사용하여 4개의 전문 에이전트를 병렬로 실행합니다.**"
TEAM_INTRO_END = "`TeamCreate`가 없는 경우 Agent 도구로 병렬 에이전트를 직접 스폰합니다."
TEAM_INTRO_REPLACEMENT = """가능하면 Codex multi-agent 도구로 4개의 전문 분석을 병렬 실행합니다. multi-agent 도구가 없으면 같은 기준으로 직접 분석합니다.

Codex에서 multi-agent 도구가 사용 가능한 경우:

```
1. 코드 감사 목적의 팀/작업 컨텍스트를 만든다
2. 4개 감사 태스크를 병렬로 실행한다
3. 각 에이전트의 결과를 수집한다
4. 사용한 팀/세션 리소스를 정리한다
```"""

TEAM_SHUTDOWN_START = "#### Team 종료"
TEAM_SHUTDOWN_END = "```"  # second fence after the start marker closes the block


def strip_claude_frontmatter(text):
    """Remove Claude-only frontmatter fields, keep name/description."""
    lines = text.split("\n")
    if lines[0] != "---":
        return text
    out = [lines[0]]
    in_frontmatter = True
    for line in lines[1:]:
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
                out.append(line)
                continue
            if line.startswith(CLAUDE_ONLY_FRONTMATTER):
                continue
        out.append(line)
    return "\n".join(out)


def replace_region(text, start_marker, end_marker, replacement):
    """Replace the inclusive line range [start_marker, end_marker] with replacement."""
    lines = text.split("\n")
    try:
        start = lines.index(start_marker)
    except ValueError:
        return text
    end = start + 1 + lines[start + 1:].index(end_marker)
    return "\n".join(lines[:start] + replacement.split("\n") + lines[end + 1:])


def remove_region(text, start_marker, end_marker, occurrence=1):
    """Remove lines from start_marker through the Nth end_marker, plus one trailing blank line."""
    lines = text.split("\n")
    try:
        start = lines.index(start_marker)
    except ValueError:
        return text
    end = start
    for _ in range(occurrence):
        end = end + 1 + lines[end + 1:].index(end_marker)
    if end + 1 < len(lines) and lines[end + 1] == "":
        end += 1
    return "\n".join(lines[:start] + lines[end + 1:])


def transform(name, text):
    text = strip_claude_frontmatter(text)
    if name == "code-audit":
        text = replace_region(text, TEAM_INTRO_START, TEAM_INTRO_END, TEAM_INTRO_REPLACEMENT)
        text = remove_region(text, TEAM_SHUTDOWN_START, TEAM_SHUTDOWN_END, occurrence=2)
        for n in range(1, 5):
            text = text.replace(f"#### Agent {n}:", f"#### Analysis {n}:")
    for old, new in REPLACEMENTS:
        text = text.replace(old, new)
    return text


def main():
    check_mode = "--check" in sys.argv[1:]
    skill_dirs = sorted(d for d in CLAUDE_SKILLS.iterdir() if (d / "SKILL.md").is_file())
    if not skill_dirs:
        print(f"ERROR: no skills found under {CLAUDE_SKILLS}", file=sys.stderr)
        return 1

    failed = []
    for skill_dir in skill_dirs:
        name = skill_dir.name
        generated = transform(name, (skill_dir / "SKILL.md").read_text(encoding="utf-8"))
        dst = CODEX_SKILLS / name / "SKILL.md"
        if check_mode:
            current = dst.read_text(encoding="utf-8") if dst.is_file() else None
            if current != generated:
                failed.append(name)
                print(f"MISMATCH: {dst.relative_to(REPO_ROOT)}")
            else:
                print(f"OK: {name}")
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(generated, encoding="utf-8")
            print(f"generated: {dst.relative_to(REPO_ROOT)}")

    # codex-only skill dirs are suspicious (claude/skills is the source of truth)
    for d in sorted(CODEX_SKILLS.iterdir()):
        if d.is_dir() and not (CLAUDE_SKILLS / d.name / "SKILL.md").is_file():
            print(f"WARNING: {d.relative_to(REPO_ROOT)} has no claude/skills counterpart", file=sys.stderr)

    if check_mode and failed:
        print(f"\n{len(failed)} skill(s) out of date — run: python3 scripts/gen-codex-skills.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
