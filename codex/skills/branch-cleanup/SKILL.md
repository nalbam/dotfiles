---
name: branch-cleanup
description: Identify and delete merged local/remote branches with explicit user confirmation. 머지된 로컬·원격 브랜치 식별 후 사용자 확인을 받아 삭제.
---

# Branch Cleanup

**한국어로 응답. 코드·명령어는 원문 유지** (AGENTS.md 의 Language).

머지된 로컬·원격 브랜치를 식별하여 *사용자 확인 후* 삭제한다. git 안전 규칙은 AGENTS.md 의 Git Safety 가 source — 브랜치 삭제는 *파괴적 작업* 으로 사용자 명시 요청 시에만 수행한다.

## Philosophy

- **사용자 확인 없는 삭제 금지** — 브랜치 삭제는 되돌리기 어렵다 (특히 원격)
- **보호 브랜치 자동 제외** — main / master / develop / 현재 체크아웃된 브랜치
- **로컬·원격 분리** — 로컬 삭제와 원격 삭제는 *각각 따로* 확인

## Process

### Step 1: Identify Base Branch

```bash
# 기본 base 브랜치 자동 감지
BASE_BRANCH=$(git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@')
[ -z "$BASE_BRANCH" ] && BASE_BRANCH="main"

# 현재 브랜치 (보호 대상)
CURRENT=$(git branch --show-current)
```

### Step 2: Refresh Remote Tracking

```bash
git fetch --all --prune
```

`--prune` 으로 원격에서 삭제된 브랜치의 추적 정보 정리.

### Step 3: Identify Merged Local Branches

```bash
# base 에 머지된 로컬 브랜치 (현재·main·master·develop 제외)
git branch --merged "$BASE_BRANCH" \
  | grep -vE "^\*|(^|\s)(main|master|develop|release|$BASE_BRANCH|$CURRENT)\s*$" \
  | sed 's/^[[:space:]]*//'
```

추가로 *squash-merge* 된 브랜치도 확인 (merged 표시 안 됨):

```bash
# 모든 로컬 브랜치 중, base 와의 patch-id 가 동일한 commit 이 base 에 있는지 확인
# 간단 휴리스틱: HEAD 가 base 에 reachable 한지 + diff 가 비어있는지
for b in $(git branch --format='%(refname:short)' | grep -vE "^(main|master|develop|$BASE_BRANCH|$CURRENT)$"); do
  ahead=$(git rev-list --count "$BASE_BRANCH..$b" 2>/dev/null)
  diff=$(git diff "$BASE_BRANCH...$b" --shortstat)
  [ -z "$diff" ] && echo "$b (squashed?)"
done
```

### Step 4: Identify Merged Remote Branches

```bash
# 원격 머지된 브랜치
git branch -r --merged "origin/$BASE_BRANCH" \
  | grep -vE "origin/(HEAD|main|master|develop|release|$BASE_BRANCH)"
```

### Step 5: Identify Stale Branches (선택적)

마지막 commit 이 오래된 브랜치 (참고용 — 자동 삭제 X):

```bash
# 90일 이상 commit 없는 로컬 브랜치
for b in $(git branch --format='%(refname:short)'); do
  last=$(git log -1 --format='%cr' "$b")
  echo "$b: $last"
done
```

### Step 6: Present to User (필수)

*후보를 보여주기만 하고* 사용자 확인 받는다:

```
## 정리 후보

### 🟢 머지된 로컬 브랜치 ({N}개)
- feat/checkout-v2 (머지: 3일 전)
- fix/null-pointer (머지: 1주 전)
- refactor/auth (머지: 2주 전)

### 🟡 Squash-merge 추정 로컬 ({N}개) — 확인 필요
- feat/quick-fix (diff empty, but git이 "merged" 표시 안 함)

### 🟢 머지된 원격 브랜치 ({N}개)
- origin/feat/checkout-v2
- origin/fix/null-pointer

### ⚪ 오래된 브랜치 (참고용 — 90일 이상)
- old-experiment (마지막 commit: 6 months ago)

### 🔒 보호됨 (삭제 안 함)
- main / master / develop / $CURRENT

다음 중 어떻게 처리할지 알려주세요:
- (a) 머지된 로컬만 삭제
- (b) 머지된 로컬 + 원격 모두 삭제
- (c) Squash-merge 추정 포함 모두 삭제 (확인했음)
- (d) 특정 브랜치만 (목록 지정)
- (e) 취소
```

### Step 7: Delete (선택된 항목만, 단계적)

#### Local

```bash
# 안전한 삭제 (-d): 머지된 브랜치만 삭제됨, 안 머지면 실패
git branch -d <branch>

# 강제 삭제 (-D): 사용자가 명시 요청한 squash-merge 추정 브랜치만
# Do NOT 자동으로 -D 사용
```

#### Remote

```bash
# 원격 브랜치 삭제 — git push --delete
git push origin --delete <branch>
```

원격 삭제는 *되돌리기 매우 어려움* (다른 사람이 fork·clone 했다면 영향). 한 번 더 확인 표시:

```
원격 브랜치 {N}개를 삭제합니다 (되돌리기 어려움):
- origin/feat/checkout-v2
- origin/fix/null-pointer

진행하시겠습니까? (yes/no)
```

### Step 8: Verify

```bash
# 삭제 후 결과 확인
git branch --merged "$BASE_BRANCH"
git fetch --prune
git branch -r --merged "origin/$BASE_BRANCH"
```

### Step 9: Report

```
## Branch Cleanup 완료

### 삭제됨
- 로컬: {N}개
- 원격: {N}개

### 유지됨
- 보호 브랜치: main / master / develop / $CURRENT
- 안 머지된 브랜치: {N}개 (목록 별도 표시)
- 사용자가 제외한 브랜치: {N}개

### 다음 단계
- (필요 시) `git remote prune origin` 으로 원격 추적 정리
```

## Safety Rules

| Rule | 이유 |
|------|------|
| 사용자 확인 없이 삭제 금지 | 파괴적 작업 (AGENTS.md 의 Git Safety) |
| `-D` (force) 자동 사용 금지 | 안 머지된 코드 손실 위험 — 사용자 명시 요청 시에만 |
| 보호 브랜치 자동 제외 | main / master / develop / 현재 체크아웃 |
| 원격 삭제는 별도 확인 | 되돌리기 어려움 |
| `--all` 또는 `xargs` 일괄 삭제 금지 | 의도치 않은 브랜치 포함 위험 |
| Squash-merge 추정은 사용자에게 명시 | 추정이므로 false positive 가능 |

## Anti-Patterns

- Do NOT 사용자 확인 없이 브랜치 삭제
- Do NOT `git branch -D`(force) 를 자동으로 사용
- Do NOT 보호 브랜치(main/master/develop/현재)를 삭제 후보에 포함
- Do NOT 로컬·원격 삭제를 한 번에 묶어 처리 (각각 확인)
- Do NOT 90일 미만 stale 브랜치를 정리 후보로 표시 (작업 중일 가능성)
- Do NOT 삭제 후 검증 생략
- Do NOT `git remote prune origin` 류 추적 정리를 사용자 동의 없이 실행
