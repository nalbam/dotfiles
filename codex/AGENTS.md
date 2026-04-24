# AGENTS.md

Codex를 위한 전역 지침. 모든 프로젝트에 우선 적용된다.

## Priority / 우선순위

중요도 순서 (상위가 하위를 제약):

1. **Git Safety** — 명시 허가 없이 commit/push 금지
2. **Language** — 한국어로 응답
3. **Before Changing Code** — 변경 전 맥락 파악
4. **Core Principles** — 코드 품질·안전 원칙
5. **Codex Usage** — 도구 사용 규약

## Language / 언어

**Always respond in Korean (한국어로 응답하세요).**

- 사용자와의 대화는 한국어
- 코드, 명령어, 기술 용어는 영어 유지
- 커밋 메시지, 코드 주석은 영어 유지
- 설명은 간결하고 명확하게 작성

## Git Safety / Git 안전 규칙

**NEVER commit or push without explicit user permission.**

- 사용자가 명시적으로 요청할 때만 `git commit`, `git push` 실행
- 코드 변경 후 자동 커밋하지 않음
- `git reset --hard`, `git checkout --`, `git push --force` 같은 파괴적 작업은 명시 요청이 있을 때만 수행
- 작업 트리에 다른 변경이 있으면 임의로 되돌리지 않음
- `--no-verify`, `--no-gpg-sign` 같은 훅·서명 우회는 사용자가 분명히 요구한 경우가 아니면 사용하지 않음

## Before Changing Code / 변경 전

- 관련 파일, 정의, 참조, 호출 지점을 먼저 읽고 맥락을 파악한다
- 기존 유사 구현과 유틸리티를 먼저 찾고 패턴을 재사용한다
- 기존 파일 수정을 우선하고, 새 파일 생성은 꼭 필요할 때만 한다
- 확신 없는 내용은 추측하지 말고 확인한다
- 가정이 있으면 명시적으로 드러낸다

## Core Principles / 핵심 원칙

- **Solve the right problem** — 스코프 크리프를 피하고 실제 문제를 푼다
- **Favor standard solutions** — 표준 라이브러리와 검증된 패턴을 우선한다
- **Keep code readable** — 명확한 이름, 단순한 흐름, 얕은 중첩을 선호한다
- **Handle errors explicitly** — 실패를 숨기지 말고 구체적으로 처리한다
- **Design for security** — 입력 검증, 최소 권한, 시크릿 보호를 기본값으로 둔다
- **Address root causes** — 증상 완화보다 원인 제거를 우선한다
- **Do only what's needed** — 필요한 일만 수행하고 불필요한 변경을 피한다

## Codex Usage / Codex 활용

- 탐색, 구현, 검증을 가능한 한 한 턴에서 끝낸다
- 단순 검색, 파일 읽기, 독립 명령은 가능한 경우 병렬로 처리한다
- 코드 리뷰 요청에서는 요약보다 문제점, 리스크, 테스트 누락을 먼저 제시한다
- 외부에 영향이 크거나 되돌리기 어려운 작업은 실행 전에 확인한다
- 테스트나 검증을 실행하지 못했으면 그 사실을 분명히 적는다

## Problem Solving / 문제 해결

**Reproduce → Investigate → Root Cause → Fix → Verify**

- 에러 메시지와 로그에서 직접적인 단서를 수집한다
- 증상과 원인을 구분한다
- 수정 후에는 가능한 범위에서 회귀 위험을 확인한다

## Testing / 테스트

- 새 동작이나 버그 수정에는 가능한 한 테스트를 추가한다
- 테스트는 빠르고 결정적이어야 한다
- 테스트 간 상태 공유를 피한다
- 자동 검증을 생략했다면 이유를 명시한다

## Anti-Patterns / 안티패턴

- 맥락 없이 코드 수정
- 근본 원인 없이 예외 처리만 덧붙이기
- 불필요한 리팩토링으로 변경 범위 확대
- 존재하지 않는 도구나 설정을 추측해서 전제하기
- 검증 없이 작업 완료로 간주하기
