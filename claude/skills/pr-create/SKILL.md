---
name: pr-create
description: Create pull request with proper format. PR 생성, 변경사항 분석, PR 메시지 작성.
allowed-tools: Read, Bash, Grep, Glob
---

# Create Pull Request

**한국어로 응답. 코드·명령어는 원문 유지** (`rules/language.md`).

git 안전 규칙은 `rules/git-workflow.md`, 변경 작업 자체는 `rules/coding-style.md#surgical-changes--외과적-변경` 을 따른다. 이 파일은 PR title / body 형식의 *유일한 source* 다 (`pr-summary` 가 이를 참조).

## Philosophy

- **PR은 코드 리뷰의 시작이다** — 리뷰어가 맥락을 이해할 수 있도록 작성한다
- **변경의 "왜"를 설명한다** — diff는 "무엇"을 보여주지만, PR은 "왜"를 설명해야 한다
- **영향 범위를 정직하게 밝힌다** — 변경의 리스크와 한계를 숨기지 않는다

## Workflow

### 0. Run Validation First
Before creating PR, run `/validate` to ensure all checks pass:
- Lint
- Typecheck
- Tests

**If validation fails, fix all issues before proceeding.**
**If the project has no lint/typecheck/test tooling (e.g., shell scripts, dotfiles), skip this step.**

### 1. Gather Context
```bash
# Detect base branch dynamically
BASE_BRANCH=$(gh pr view --json baseRefName -q '.baseRefName' 2>/dev/null || git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")

# Check current branch status
git status

# View commits since branching from base
git log origin/${BASE_BRANCH}..HEAD --oneline

# View full diff for PR description
git diff origin/${BASE_BRANCH}...HEAD --stat
git diff origin/${BASE_BRANCH}...HEAD
```

### 2. Deep Analysis — 변경사항 심층 분석

**CRITICAL: diff 통계만 보지 않는다. 변경의 의미를 이해한다.**

**For each changed file, read and understand:**
1. **Purpose** — why was this file changed?
2. **Impact** — what depends on this file? What could break?
3. **Completeness** — are there related changes that should be included?

**Deliberation questions:**
- What is the **single purpose** of this PR?
- Could this be broken into smaller PRs?
- What are the **risks** of merging this?
- What **edge cases** might be affected?
- Is there adequate **test coverage** for the changes?
- Are there any **breaking changes** for consumers?

### 3. Sync with Main (if needed)

**CRITICAL: rebase와 force push는 사용자 확인 후에만 실행한다.**

```bash
git fetch origin

# Check if rebase is needed
git log --oneline origin/${BASE_BRANCH}..HEAD
git log --oneline HEAD..origin/${BASE_BRANCH}
```

If the branch is behind `origin/${BASE_BRANCH}`:
1. **사용자에게 rebase 필요성을 알리고 확인을 요청한다**
2. 사용자가 승인하면 실행:
   ```bash
   git rebase origin/${BASE_BRANCH}
   # Resolve conflicts if any, then:
   git push --force-with-lease
   ```
3. 사용자가 거부하면 rebase 없이 PR을 생성한다

### 4. Craft PR Description

**Before writing, articulate:**
1. What problem does this PR solve? (Summary)
2. What specific changes were made and why? (Changes)
3. Are there any breaking changes? (Breaking Changes)
4. How should a reviewer verify this works? (Test Plan)
5. What risks or limitations exist? (if any)

```bash
gh pr create --title "<type>(<scope>): <subject>" --body "$(cat <<'EOF'
## Summary
- Brief description of what and WHY

## Changes
- Change 1: why this was needed
- Change 2: why this was needed

## Breaking Changes
- (if any) Description of breaking change and migration path
- (if none, omit this section entirely)

## Test Plan
- [ ] How to verify changes work
- [ ] Edge cases to test
EOF
)"
```

### 5. Verify

`gh pr view --web` 또는 `gh pr view {N}` 으로 결과 확인.

## PR Title Format
```
<type>(<scope>): <subject>
```

> **Note:** PR title에는 scope를 선택적으로 사용한다. 여러 커밋을 포괄하는 PR은 scope로 영향 범위를 명시하면 리뷰어에게 도움이 된다.
> Commit message는 scope 없이 `<type>: <subject>` 형식을 사용한다.

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

**Examples:**
```
feat(auth): add OAuth2 login support
fix(api): handle null response from server
refactor(utils): simplify date formatting logic
```

## PR Quality Checklist

Before creating:
- [ ] I can explain the purpose of every changed file
- [ ] Changes are focused (one purpose per PR)
- [ ] Test coverage exists for new/changed logic
- [ ] No secrets, debug code, or unintended files
- [ ] PR title accurately describes the change
- [ ] Description explains WHY, not just WHAT

## Rules

- Only include actual work done in the message
- Do NOT add unnecessary lines (Co-Authored-By, Generated with, etc.)
- Do NOT add promotional or attribution footers

## Anti-Patterns

- Do NOT create PR without reading the full diff
- Do NOT write vague descriptions like "various fixes"
- Do NOT include unrelated changes to pad the PR
- Do NOT skip the test plan — reviewers need it
- Do NOT hide risks or known issues from the description
