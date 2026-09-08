---
name: resolve-coderabbit
description: Fetch, evaluate, fix, and resolve CodeRabbit review comments on a PR. CodeRabbit 리뷰 코멘트를 가져와 평가, 수정, 해결.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
disable-model-invocation: true
argument-hint: [pr-number]
---

# Resolve CodeRabbit Reviews

**한국어로 응답. 코드·명령어는 원문 유지** (`rules/language.md`).

Fetch CodeRabbit inline review comments from a PR, technically evaluate each one, fix valid issues, and resolve completed threads. 수정 자체는 `skills/coding-style/SKILL.md#surgical-changes--외과적-변경` 을 따른다.

## Rules

- 제안을 현재 코드·PR 범위·기존 계약과 대조한 뒤 판단한다.
- 수정은 검증하고, REJECT 항목은 resolve하지 않는다.
- 커밋·푸시 권한은 `rules/git-workflow.md`를 따른다.

## Process

### Step 1: Identify PR

PR 번호 인자: `$ARGUMENTS`

- 위 값이 비어 있지 않으면 그 번호를 `{pr_number}` 로 사용한다
- 비어 있으면 현재 브랜치에서 추론한다:

```bash
gh pr view --json number -q '.number'
```

Also extract owner and repo:

```bash
gh repo view --json owner,name -q '"\(.owner.login) \(.name)"'
```

### Step 2: Fetch CodeRabbit Comments

Fetch all inline review comments and filter for CodeRabbit:

```bash
gh api repos/{owner}/{repo}/pulls/{pr_number}/comments \
  --paginate \
  --jq '[.[] | select(.user.login == "coderabbitai[bot]") | {id: .id, node_id: .node_id, path: .path, line: .line, original_line: .original_line, body: .body, in_reply_to_id: .in_reply_to_id, created_at: .created_at}]'
```

Filter out reply comments (keep only top-level comments where `in_reply_to_id` is null).

If no CodeRabbit comments found, report and stop.

### Step 3: Map Review Threads

Query GraphQL to get review thread IDs and resolution status:

```bash
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          pageInfo { hasNextPage endCursor }
          nodes {
            id
            isResolved
            comments(first: 1) {
              nodes {
                id
                databaseId
                body
                path
                line
              }
            }
          }
        }
      }
    }
  }
' -f owner='{owner}' -f repo='{repo}' -F pr={pr_number}
```

**100개 초과 시**: `pageInfo.hasNextPage` 가 true 면 `reviewThreads(first: 100, after: "<endCursor>")` 로 다음 페이지를 모두 조회해 합친다 (대형 PR thread 누락 방지).

Build a mapping: `comment databaseId → thread node ID`.

**Exclude already-resolved threads** from further processing.

### Step 4: Technical Evaluation

For each unresolved CodeRabbit comment, evaluate against the codebase:

**Evaluation checklist:**

1. **Read the target file** — check current state (may already be fixed)
2. **Understand the suggestion** — what exactly is being asked?
3. **Check technical validity** — is this correct for THIS codebase?
4. **Check YAGNI** — does the suggestion add unused complexity?
5. **Check architecture alignment** — conflicts with CLAUDE.md or project conventions?
6. **Check scope** — is this within the PR's intent or scope creep?

**Classification:**

| Decision | Criteria | Action |
|----------|----------|--------|
| **SKIP** | 문제가 PR의 현재 원격 코드에서 해결됐음을 확인함 | Resolve only |
| **ACCEPT** | Technically valid, improves code quality, aligns with project conventions | Fix then resolve |
| **REJECT** | YAGNI, technically incorrect, conflicts with architecture, reviewer lacks context | Do NOT resolve |

**Severity for ACCEPT items:**

| Severity | Examples |
|----------|----------|
| HIGH | Security issues, bugs, data loss risks |
| MEDIUM | Missing error handling, type safety gaps, logic improvements |
| LOW | Style suggestions, minor readability improvements, naming |

**분류와 근거를 짧게 공유하고 승인된 범위의 수정을 진행한다:**

```
## CodeRabbit Review Analysis

| # | File | Line | Summary | Decision | Severity | Reason |
|---|------|------|---------|----------|----------|--------|
| 1 | src/foo.ts | 42 | Add null check | ACCEPT | HIGH | Valid — unhandled null |
| 2 | src/bar.ts | 15 | Extract interface | REJECT | - | YAGNI — single implementation |
| 3 | src/baz.ts | 8 | Fix typo | SKIP | - | Already fixed |
```

### Step 5: Apply Fixes

For ACCEPT items, fix in severity order (HIGH → MEDIUM → LOW).

관련 파일·호출자·테스트를 읽고 수정한다. 같은 근본 원인의 항목은 함께 처리할 수 있으며 관련 검사는 `skills/validate/SKILL.md`에 따라 실행한다. 실패하면 원인을 조사하고 사용자 변경을 임의로 되돌리지 않는다.

### Step 6: Resolve Threads

SKIP은 원격 PR에서 이미 해결된 항목만 resolve한다. ACCEPT는 수정·검증 후 원격 PR에도 반영됐을 때 resolve한다. 로컬에서만 수정됐거나 별도 push 권한이 없으면 미해결로 남기고 보고한다. 코드가 삭제·이동됐다는 이유만으로 해결로 간주하지 않는다.

```bash
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { isResolved }
    }
  }
' -f threadId='{THREAD_NODE_ID}'
```

**Do NOT resolve REJECT items** — leave for human judgment.

### Step 7: Final Summary

항목별 ACCEPT·SKIP·REJECT와 근거, 수정·원격 반영·resolve 상태, 검증 결과를 보고한다. resolve 후 반환된 `isResolved`를 확인한다. 요청에 포함되지 않은 답글·리뷰 메시지는 게시하지 않는다.
