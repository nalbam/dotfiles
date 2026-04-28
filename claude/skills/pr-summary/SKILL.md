---
name: pr-summary
description: Analyze all PR changes and update PR description with accurate summary. PR 변경사항 분석 후 정확한 요약으로 PR 설명 업데이트.
allowed-tools: Read, Bash, Grep, Glob
---

# PR Summary Update

**한국어로 응답. 코드·명령어는 원문 유지** (`rules/language.md`).

기존 PR 의 description 을 *실제 변경사항*에 맞게 갱신한다. PR body / title 형식은 `pr-create` 스킬을 *유일한 source* 로 한다 — 이 파일은 *분석·갱신 절차*만 담는다. 변경 작업 자체는 `rules/coding-style.md#surgical-changes--외과적-변경` 을 따른다.

## Philosophy

- **모든 변경사항을 빠짐없이 분석한다** — 최신 커밋만이 아니라, PR 에 포함된 모든 커밋을 추적한다
- **추측하지 않는다** — 실제 diff 와 코드를 읽고 기술한다
- **리뷰어 관점에서 작성한다** — "왜" 이 변경이 필요했는지, 어떤 영향이 있는지를 설명한다

## Rules

- 모든 changed files 를 읽은 뒤 요약을 작성한다
- 모든 commits 를 분석한다 (최신 커밋만 보지 말 것)
- 기존 PR metadata (labels, assignees, reviewers) 는 보존한다

## Process

### Step 1: Identify PR

```bash
# 인자가 있으면 사용
PR_NUMBER={argument}

# 없으면 현재 브랜치에서 추론
gh pr view --json number -q '.number'
```

### Step 2: Gather PR Context

```bash
gh pr view {PR_NUMBER} --json title,body,baseRefName,headRefName,commits,files

BASE_BRANCH=$(gh pr view {PR_NUMBER} --json baseRefName -q '.baseRefName')

gh pr view {PR_NUMBER} --json commits -q '.commits[] | "\(.oid[:7]) \(.messageHeadline)"'

gh pr diff {PR_NUMBER} --stat
gh pr diff {PR_NUMBER}
```

### Step 3: Analyze Existing PR Body

**CRITICAL: 기존 PR body 를 먼저 확인한다.**

```bash
EXISTING_BODY=$(gh pr view {PR_NUMBER} --json body -q '.body')
```

**보존 대상:**
- 작성자가 직접 추가한 메모·맥락
- 관련 이슈·디자인·논의 링크
- 이 스킬이 생성하지 않는 커스텀 섹션

작성자가 추가한 내용이 있으면 새 body 의 `## Notes` 섹션 하단에 보존한다.

### Step 4: Deep Analysis — 변경사항 심층 분석

**CRITICAL: diff 통계만 보지 않는다. 변경의 의미를 이해한다.**

**For large PRs (>20 files or >1000 lines changed):**

- 디렉터리·모듈별로 그룹화하여 분석
- 구조적 변경을 먼저, 그 다음 세부 변경
- 모듈 단위로 요약 (파일 단위 X)

**For each changed file:**

1. Read the full diff
2. Read the file (변경 주변 맥락 이해)
3. Identify the purpose
4. Assess impact (의존하는 코드, 깨질 가능성)

**카테고리:**

| Category | Description |
|----------|-------------|
| New Feature | 새 기능 추가 |
| Bug Fix | 기존 동작 교정 |
| Refactor | 동작 변경 없는 재구성 |
| Performance | 최적화 |
| Documentation | 문서·주석·README |
| Test | 테스트 추가/수정 |
| Configuration | 설정·CI/CD·빌드 |
| Dependency | 패키지 추가/갱신/제거 |
| Breaking Change | 기존 API/동작을 깨는 변경 |

**Deliberation:**

- 이 PR 의 *single purpose* 는?
- Breaking changes 가 있는가?
- 영향받는 edge cases 는?
- 알려진 risk 또는 limitations 는?

### Step 5: Craft & Update

PR body / title 형식은 `pr-create` 스킬과 동일하다 (Summary / Changes / Breaking Changes / Test Plan + `<type>(<scope>): <subject>` title). 형식 정의·예시는 `pr-create` 를 참조한다.

```bash
gh pr edit {PR_NUMBER} --body "$(cat <<'EOF'
## Summary
- {accurate summary based on analysis}

## Changes
- {change 1}: {why}
- {change 2}: {why}

## Breaking Changes
- {if any, otherwise omit this section}

## Test Plan
- [ ] {verification step 1}
- [ ] {verification step 2}
EOF
)"
```

PR title 이 모호한 경우(`update`, `fix`, `WIP` 등)에만 *사용자에게 확인 후* 변경:

```bash
gh pr edit {PR_NUMBER} --title "<type>(<scope>): <subject>"
```

### Step 6: Verify & Report

`gh pr view {PR_NUMBER}` 로 갱신을 확인하고, 다음 형식으로 짧게 보고한다.

```
## PR Summary Updated

**PR**: #{PR_NUMBER}  **Title**: {title}
**Base**: {base_branch} ← {head_branch}

- Commits: {N}, Files: {N}, +{N}/-{N}
- Categories: feat {N} · fix {N} · refactor {N} · ...
```

## Anti-Patterns

- Do NOT write a summary without reading ALL changed files
- Do NOT rely only on commit messages — verify against actual diff
- Do NOT include changes that don't exist in the PR
- Do NOT use vague descriptions like "various improvements"
- Do NOT overwrite existing PR body without analyzing it first
- Do NOT skip reading file context — diffs alone can be misleading
- Do NOT add information that isn't supported by the code changes
- Do NOT change PR title without explicit user confirmation
