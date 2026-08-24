---
name: code-review
description: Review the current diff or a pull request and report severity-ranked, actionable findings without changing code. 변경분·PR 코드 리뷰, 위험·회귀·테스트 누락 분석. 저장소 전체 감사는 code-audit, 검사 실행·수정은 validate.
---

# Code Review

**한국어로 응답. 코드·명령어는 원문 유지** (AGENTS.md 의 Language).

현재 작업 브랜치의 변경분 또는 지정한 PR을 읽기 전용으로 리뷰한다. 요약보다 실제 결함·회귀 위험·테스트 누락을 먼저 보고한다. 코드 수정은 사용자가 별도로 요청한 경우에만 후속 작업으로 수행한다.

## Scope

- **대상**: base branch 대비 현재 diff 또는 지정한 PR의 전체 diff
- **읽기 전용**: GitHub metadata와 코드를 읽되 파일·PR·리뷰 상태를 변경하지 않는다
- **경계**: 저장소 전체 감사는 `/code-audit`, lint·typecheck·test 실행과 수정은 `/validate`, CodeRabbit thread 처리는 `/resolve-coderabbit`

## Review Standard

다음 순서로 실제 영향이 있는 문제를 찾는다:

1. Correctness — 요구사항 불충족, 잘못된 분기·상태·오류 처리
2. Security — 신뢰 경계, 인증·인가, 입력 검증, secret·PII 노출
3. Architecture — 의존성 방향, 소유권 중복, 레이어·공용 모듈 침범
4. Reliability — race, retry, timeout, resource lifecycle, partial failure
5. Compatibility — API·schema·config·migration·offline 동작의 회귀
6. Tests — 변경 위험을 잡지 못하는 누락 또는 잘못된 assertion

스타일 선호, 근거 없는 미래 확장, 변경과 무관한 기존 문제는 finding으로 만들지 않는다.

## Workflow

### 1. Resolve the Review Target

PR 번호가 주어지면:

```bash
gh pr view {PR_NUMBER} --json number,title,body,baseRefName,headRefName,commits,files,statusCheckRollup
gh pr diff {PR_NUMBER}
```

현재 브랜치를 리뷰하면 base를 동적으로 찾는다:

```bash
BASE_BRANCH=$(gh pr view --json baseRefName -q '.baseRefName' 2>/dev/null || git symbolic-ref refs/remotes/origin/HEAD 2>/dev/null | sed 's@^refs/remotes/origin/@@' || echo "main")
git diff --stat origin/${BASE_BRANCH}...HEAD
git diff origin/${BASE_BRANCH}...HEAD
```

uncommitted 변경도 요청 범위에 포함되면 `git diff`와 `git diff --cached`를 추가로 읽는다.

### 2. Understand Intent and Constraints

- 사용자 요청, PR body, commit 목록, 저장소 지침을 대조한다
- changed file마다 변경 목적과 호출자·소비자를 추적한다
- architecture·security·test 규칙이 있는 저장소는 관련 규칙과 테스트를 먼저 읽는다
- 생성 파일·lockfile은 원본 변경과 일치하는지만 확인한다

### 3. Review the Full Change

각 변경에 대해 질문한다:

- 정상 경로와 실패 경로가 모두 보존되는가?
- 경계 입력과 권한이 올바른 위치에서 검증되는가?
- 같은 결정을 다른 레이어·모듈이 중복 소유하게 되었는가?
- 기존 caller, persisted data, deployment config와 호환되는가?
- 테스트가 구현 세부가 아니라 회귀 가능한 동작을 검증하는가?

의심 항목은 관련 정의·호출 지점·테스트까지 읽어 확인한다. diff만 보고 단정하지 않는다.

### 4. Classify Findings

| Severity | 기준 |
|----------|------|
| **CRITICAL** | 즉각적인 보안 사고·데이터 손실·서비스 불능 가능성 |
| **HIGH** | 일반적인 입력이나 운영 조건에서 기능·보안·데이터 정합성이 깨짐 |
| **MEDIUM** | 특정 조건에서 회귀하거나 유지보수 비용이 실제 결함으로 이어질 가능성 |
| **LOW** | 영향이 작지만 명확하고 수정 가치가 있는 문제 |

각 finding은 하나의 근본 문제만 담고 `{severity, file:line, 문제, 근거, 영향, 권장 수정}`을 제공한다. 정확한 줄을 특정할 수 없으면 finding을 더 조사한다.

### 5. Check Verification Evidence

- PR checks와 저장소가 요구하는 검증 명령을 확인한다
- 검증을 직접 실행하지 않았다면 통과했다고 표현하지 않는다
- 실패·미실행 검사는 finding과 분리해 residual risk로 보고한다

### 6. Report Findings First

finding이 있으면 심각도 순으로 보고한다:

```markdown
## Findings

### HIGH — <제목> — `path/file.ts:42`
- **문제**: ...
- **근거**: ...
- **영향**: ...
- **권장 수정**: ...

## Verification
- <확인한 checks/tests>

## Residual Risks
- <리뷰 범위 밖 또는 미검증 사항>
```

finding이 없으면 `발견 사항 없음`을 명시한 뒤 검증 상태와 남은 위험만 짧게 보고한다. 변경 요약은 마지막에 두고, findings를 가리지 않을 정도로만 작성한다.

## Anti-Patterns

- 요약부터 길게 쓰고 finding을 뒤로 미루지 않는다
- diff의 모든 줄을 칭찬하거나 재서술하지 않는다
- 실행하지 않은 테스트를 PASS로 보고하지 않는다
- 기존 문제를 이번 변경이 만든 것처럼 보고하지 않는다
- 사용자 요청 없이 코드를 수정하거나 PR review를 submit하지 않는다
- 확신이 낮은 가설을 사실처럼 단정하지 않는다
