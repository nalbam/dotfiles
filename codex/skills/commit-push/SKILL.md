---
name: commit-push
description: Create git commit and push to remote. 커밋 생성 후 리모트에 푸시.
---

# Commit and Push

**한국어로 응답. 코드·명령어는 원문 유지** (AGENTS.md 의 Language).

`commit` 스킬의 절차를 그대로 수행한 뒤 push 한다. **이 파일은 push 고유 절차만 담는다** — commit 단계의 세부는 `commit` 스킬을 *유일한 source*로 한다. 변경 작업 자체는 AGENTS.md 의 Surgical Changes 를 따른다.

## Philosophy

- **푸시는 되돌리기 어렵다** — 커밋보다 더 신중해야 한다
- **공유 브랜치에 영향을 준다** — 내 변경이 팀 전체에 전파된다
- **푸시 전에 한 번 더 확인한다** — 커밋 후 push 전 최종 점검

## Workflow

### Phase 1: Commit

`commit` 스킬의 전 절차(Validation → Gather → Understand → Security Review → Stage & Commit → Verify)를 그대로 수행한다.

세부 규약·예시·메시지 형식은 `commit` 스킬을 참조한다. **이곳에 중복 기재하지 않는다.**

### Phase 2: Pre-Push Deliberation — 푸시 전 숙고

**CRITICAL: 커밋 후 바로 푸시하지 않는다. 한 번 더 생각한다.**

```bash
# Review what will be pushed
git log origin/$(git branch --show-current)..HEAD --oneline 2>/dev/null || git log --oneline -3

# Verify branch
git branch --show-current
```

**Push deliberation checklist:**

- [ ] Correct branch? (main/master 직접 push가 의도된 것인지 확인)
- [ ] All commits are intentional? (실수로 포함된 커밋 없는지)
- [ ] No force push needed? (force push는 사용자 명시 요청 시에만)
- [ ] CI/CD will be triggered — are changes ready for that?
- [ ] No secrets in committed history? (한 번 push 되면 노출됨)

### Phase 3: Push

```bash
# Push to remote (set upstream if new branch)
git push -u origin $(git branch --show-current)
```

푸시 후 `git status` 와 `git log --oneline -3` 으로 결과 확인.

## Pre-Push Safety Rules

| Rule | Reason |
|------|--------|
| No force push to main/master | Shared history destruction |
| No push with failing tests | Breaks CI for entire team |
| No push of secrets | Once pushed, consider compromised — rotate immediately |
| Verify target branch | Wrong branch push is hard to undo |

git 안전 규칙 전체는 AGENTS.md 의 Git Safety 가 source.

## Anti-Patterns

- Do NOT push without understanding what will be pushed
- Do NOT push immediately after commit without reviewing
- Do NOT force push (`--force`) unless explicitly requested by user
- Do NOT force push to main/master branches
- Do NOT skip pre-commit hooks (`--no-verify`) — AGENTS.md 의 Git Safety
- Do NOT amend commits already pushed to shared branches

commit 단계의 안티패턴은 `commit` 스킬과 AGENTS.md 의 Anti-Patterns 참조.
