---
name: release-notes
description: Generate release notes / CHANGELOG from commits since last tag. 마지막 태그 이후 commit 분석 후 릴리스 노트·CHANGELOG 생성.
allowed-tools: Read, Edit, Bash, Grep, Glob
---

# Release Notes

**한국어로 응답. 코드·명령어는 원문 유지** (`rules/language.md`).

마지막 태그 이후의 commit·PR 을 분석하여 릴리스 노트 또는 `CHANGELOG.md` 항목을 생성한다. PR 단위 분석은 `pr-summary` 가 source — 이 스킬은 *릴리스(태그 단위)* 를 다룬다.

## Philosophy

- **모든 commit 을 정확히 반영** — 추측하지 않고 *실제 commit 기록*에 근거
- **사용자 가독성 우선** — 내부 구현 세부보다 *사용자 관점 변화*를 강조
- **Breaking change 는 최상단** — 업그레이드 시 가장 먼저 봐야 할 정보

## Process

### Step 1: Identify Range

```bash
# 마지막 태그 자동 감지 (annotated/lightweight 모두)
LAST_TAG=$(git describe --tags --abbrev=0 2>/dev/null)

# 인자가 있으면 사용 (예: v1.2.0..v1.3.0 또는 v1.2.0..HEAD)
RANGE="${argument:-${LAST_TAG}..HEAD}"

# 태그가 전혀 없으면 첫 commit 부터
[ -z "$LAST_TAG" ] && RANGE="$(git rev-list --max-parents=0 HEAD | head -1)..HEAD"
```

### Step 2: Gather Commits

```bash
# 모든 commit (merge 포함)
git log --pretty=format:'%H%x09%s%x09%an%x09%ai' "$RANGE"

# Merge commit 만 (PR 단위 워크플로우인 경우)
git log --merges --pretty=format:'%H%x09%s' "$RANGE"

# 변경 파일 통계
git diff --stat "$RANGE"

# Breaking change 마커 검색 (commit body 포함)
git log --pretty=full "$RANGE" | grep -i "BREAKING CHANGE\|BREAKING-CHANGE"
```

GitHub PR 정보가 필요하면:

```bash
# range 안의 PR 목록 (gh CLI)
gh pr list --state merged --search "merged:>=$(git log -1 --format=%aI $LAST_TAG 2>/dev/null || echo 1970-01-01)" \
  --limit 100 --json number,title,labels,author,mergedAt
```

### Step 3: Parse Conventional Commits

각 commit subject 를 파싱:

```
<type>(<scope>)?: <subject>          ← scope 는 선택
<type>!: <subject>                   ← `!` 는 breaking change
```

**Types** (`rules/git-workflow.md` 와 일치):

| Type | 그룹 | 표시 |
|------|------|------|
| `feat` | Features | 사용자 가시 신규 기능 |
| `fix` | Bug Fixes | 버그 수정 |
| `perf` | Performance | 성능 개선 |
| `refactor` | Refactor | 동작 변경 없는 재구성 (대체로 사용자 가시 X) |
| `docs` | Documentation | 문서 |
| `test` | Tests | 테스트 |
| `chore` | Chores | 의존성·빌드·기타 |
| `ci` | CI/CD | 파이프라인 |

### Step 4: Detect Breaking Changes

다음 표지 중 하나라도 있으면 *Breaking*:

- subject 의 `<type>!:` (예: `feat!: drop legacy API`)
- commit body 에 `BREAKING CHANGE:` 또는 `BREAKING-CHANGE:` 라인
- PR 라벨 `breaking` / `major`
- API 삭제·시그니처 변경·설정 형식 변경

### Step 5: Group & Format

```markdown
## [vX.Y.Z] — YYYY-MM-DD

### ⚠️ Breaking Changes
- {description} ({commit-or-PR-ref})
  - Migration: {how to upgrade}

### ✨ Features
- {subject} ({ref})

### 🐛 Bug Fixes
- {subject} ({ref})

### ⚡ Performance
- {subject} ({ref})

### ♻️ Refactor
- {subject} ({ref})

### 📚 Documentation
- {subject} ({ref})

### 🧰 Chores / CI
- {subject} ({ref})

### Contributors
- @{author1}, @{author2}, ...
```

**Formatting 규칙:**

- subject 는 *원문 그대로* (재해석·요약 금지) — 정확성 우선
- ref: `(#123)` PR 또는 `(abc1234)` commit hash 짧은 형식
- subject 가 모호하면 (`update`, `fix`, `wip`) 해당 항목은 *별도 그룹*에 두고 사용자에게 보강 요청
- Breaking 의 Migration 섹션은 commit body 또는 PR description 에서 추출 (없으면 사용자에게 요청)

### Step 6: Output (두 가지 모드)

#### 모드 A: CHANGELOG.md 갱신

```bash
# CHANGELOG.md 가 있으면 새 버전을 *맨 위*에 삽입
# Keep a Changelog 형식 (https://keepachangelog.com) 호환
```

기존 `CHANGELOG.md` 의 형식·헤더·들여쓰기를 *그대로 매치* (`rules/coding-style.md#surgical-changes--외과적-변경` — 기존 파일 스타일 보존).

#### 모드 B: GitHub Release 본문

```bash
# 태그 생성 후 release 작성 (사용자 확인 후)
gh release create vX.Y.Z --title "vX.Y.Z" --notes-file release-notes.md --draft

# 또는 기존 release 갱신
gh release edit vX.Y.Z --notes-file release-notes.md
```

draft 로 먼저 만들고 사용자 확인 후 publish.

### Step 7: User Review

다음을 사용자에게 표시한 뒤 확인:

```
## 생성된 Release Notes

[전체 내용]

### 분석 통계
- 범위: {LAST_TAG}..HEAD
- Commits: {N} (merge: {N})
- Authors: {N}
- Breaking changes: {N}
- 모호한 commit: {N}건 — 보강 필요 시 알려주세요

다음 중 선택:
- (a) CHANGELOG.md 갱신
- (b) GitHub Release draft 생성
- (c) 출력만 (붙여넣기용)
```

## Anti-Patterns

- Do NOT commit subject 를 임의로 재해석·요약
- Do NOT 모호한 commit 을 "추정"으로 채우기 — 사용자 확인 요청
- Do NOT Breaking change 를 일반 항목에 묻기 — 항상 최상단·강조
- Do NOT 한 PR 의 commit 들을 *합치지 않고* 모두 나열 (소음)
  - merge commit 또는 PR 단위로 그룹화 권장
- Do NOT GitHub Release 를 사용자 확인 없이 publish (draft → 확인 → publish)
- Do NOT CHANGELOG.md 의 기존 스타일을 본인 선호로 변경
- Do NOT 모든 chore/test/ci 항목을 사용자 가시 섹션에 포함 (필요 시 *축약 표시* 또는 "기타" 섹션)
