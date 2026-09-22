#!/usr/bin/env python3
"""Generate codex/skills/*/SKILL.md from claude/skills/*/SKILL.md.

claude/skills is the single source of truth. This script applies the
Claude -> Codex transformations (frontmatter, Git rules references, and
skill invocation syntax) and writes the results to
codex/skills. Skill-local reference docs (*.md next to SKILL.md, e.g.
references/) are mirrored with the same body transformations. Codex-only
files (e.g. agents/openai.yaml) are preserved as-is.

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

# Translate only tool-specific instructions; project filenames stay intact.
REPLACEMENTS = [
    ("`rules/git-workflow.md`", "AGENTS.md 의 Git Safety"),
    ("`/validate`", "`$validate`"),
    ("PR 번호 인자: `$ARGUMENTS`", "PR 번호 인자: 사용자가 스킬 호출 시 함께 제공한 값"),
]


def strip_claude_frontmatter(text):
    """Remove Claude-only frontmatter fields, keep name/description."""
    lines = text.split("\n")
    if lines[0] != "---":
        return text
    out = [lines[0]]
    in_frontmatter = True
    skipping = False
    for line in lines[1:]:
        if in_frontmatter:
            if line == "---":
                in_frontmatter = False
                out.append(line)
                continue
            if line.startswith(CLAUDE_ONLY_FRONTMATTER):
                skipping = True
                continue
            if skipping and (not line.strip() or line.startswith((" ", "\t"))):
                continue
            skipping = False
        out.append(line)
    return "\n".join(out)


def transform(text):
    text = strip_claude_frontmatter(text)
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
    expected = set()
    for skill_dir in skill_dirs:
        name = skill_dir.name
        sources = [skill_dir / "SKILL.md"] + sorted(
            p for p in skill_dir.rglob("*.md") if p != skill_dir / "SKILL.md"
        )
        for src in sources:
            rel = src.relative_to(skill_dir)
            label = name if str(rel) == "SKILL.md" else f"{name}/{rel}"
            generated = transform(src.read_text(encoding="utf-8"))
            dst = CODEX_SKILLS / name / rel
            expected.add(dst)
            if check_mode:
                current = dst.read_text(encoding="utf-8") if dst.is_file() else None
                if current != generated:
                    failed.append(label)
                    print(f"MISMATCH: {dst.relative_to(REPO_ROOT)}")
                else:
                    print(f"OK: {label}")
            else:
                dst.parent.mkdir(parents=True, exist_ok=True)
                if not dst.is_file() or dst.read_text(encoding="utf-8") != generated:
                    dst.write_text(generated, encoding="utf-8")
                print(f"generated: {dst.relative_to(REPO_ROOT)}")

    # Markdown under each skill is generated; Codex-only metadata is preserved.
    for stale in sorted(path for path in CODEX_SKILLS.rglob("*.md")
                        if len(path.relative_to(CODEX_SKILLS).parts) > 1):
        if stale not in expected:
            if check_mode:
                failed.append(str(stale.relative_to(CODEX_SKILLS)))
                print(f"STALE: {stale.relative_to(REPO_ROOT)}")
            else:
                stale.unlink()
                print(f"removed: {stale.relative_to(REPO_ROOT)}")

    if check_mode and failed:
        print(f"\n{len(failed)} skill(s) out of date — run: python3 scripts/gen-codex-skills.py", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
