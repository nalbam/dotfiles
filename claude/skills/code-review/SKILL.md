---
name: code-review
description: Review the current diff or a pull request and report severity-ranked, actionable findings without changing code. 변경분·PR 코드 리뷰, 위험·회귀·테스트 누락 분석. 저장소 전체 감사는 code-audit, 검사 실행·수정은 validate.
allowed-tools: Read, Bash, Grep, Glob
---

# Code Review

현재 변경분 또는 지정한 PR을 읽기 전용으로 리뷰한다. 코드·PR·리뷰 상태를 변경하지 않는다. 저장소 전체 감사는 `code-audit`, 검사 실행·수정은 `validate`, CodeRabbit thread 처리는 `resolve-coderabbit`의 범위다.

## 대상 확인

- PR이면 `gh pr view <number> --json title,body,baseRefName,headRefName,commits,files,statusCheckRollup`과 `gh pr diff <number>`로 실제 base·전체 변경을 확인한다.
- 현재 변경이면 `git status`, `git diff`, `git diff --cached`와 관련 미추적 파일을 확인한다. 브랜치 비교가 필요하면 PR 또는 원격 기본 브랜치로 base를 정한다. `main`을 추측하지 않는다.
- 사용자 요청·저장소 지침·관련 정의·호출자·테스트를 함께 읽는다. 흐름 의존성이 있으면 조사 범위를 넓힌다.

## Review Standard

1. Correctness: 정상·실패 경로, 경계 입력, 상태 변화가 계약에 맞는가?
2. Security: 신뢰 경계·권한·민감 정보 처리가 올바른가?
3. Reliability: 경쟁 상태·재시도·timeout·자원 수명·부분 실패가 안전한가?
4. Compatibility: API·저장 데이터·설정·배포·offline 동작이 보존되는가?
5. Tests: 회귀 가능한 동작을 실제로 검증하는가?

스타일 취향·추측성 확장·변경과 무관한 기존 문제는 finding으로 만들지 않는다. 의심 항목은 호출 흐름과 근거를 확인한 뒤 보고한다. 생성물·lockfile도 원본과의 일치 및 실제 영향이 있으면 검토한다.

## Severity

| Severity | 기준 |
|----------|------|
| CRITICAL | 즉각적인 보안 사고·데이터 손실·서비스 불능 위험 |
| HIGH | 일반 입력·운영 조건에서 기능·보안·정합성 손상 |
| MEDIUM | 특정 조건에서 발생하는 명확한 결함·회귀 |
| LOW | 영향은 작지만 근거와 수정 가치가 있는 문제 |

## 보고

심각도 순으로 `{severity, file:line, 문제, 발생 조건·근거, 영향, 권장 수정}`을 보고한다. 하나의 finding에는 하나의 근본 문제만 담는다.

발견 사항이 없으면 이를 명시한다. 확인한 검사 결과와 미실행·잔여 위험은 findings와 구분하고, 직접 실행하지 않은 테스트를 통과했다고 표현하지 않는다. 필수 칭찬·변경 내역 재서술로 보고서를 늘리지 않는다.
