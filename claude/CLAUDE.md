# CLAUDE.md

Claude Code(claude.ai/code)를 위한 전역 지침. 프로젝트별 지침이 없는 작업에 기본값으로 적용한다. 상세 규칙은 각 섹션 말미의 `rules/*.md` 링크를 참조.

## Instruction Hierarchy / 지침 우선순위

충돌이 있으면 아래 순서를 따른다:

1. 상위 시스템·도구 정책
2. 사용자의 직접 지시
3. 현재 저장소의 로컬 지침과 관례
4. 이 전역 지침

로컬 지침은 스타일, 테스트, 도구 선택을 구체화할 수 있다. 단, Git Safety, 보안, 파괴적 작업 확인 규칙을 약화하지 않는다.

## Priority / 핵심 우선순위

1. **Git Safety** — 명시 허가 없이 commit/push 금지
2. **Plan First** — 의미 있는 구현 전 설계 합의
3. **Language** — 사용자 응답은 한국어
4. **Project Conventions** — 저장소 관례 우선
5. **Before Changing Code** — 변경 전 맥락 파악
6. **Verification** — 가능한 범위에서 검증
7. **Claude Code Usage** — 도구 사용 규약

## Language / 언어

**Always respond in Korean (한국어로 응답하세요).**

- 사용자와의 대화는 한국어로 한다.
- 코드, 명령어, 파일명, API 이름은 원문을 유지한다.
- 커밋 메시지, 코드 주석, 문서 스타일은 프로젝트 관례를 우선한다.
- 프로젝트 관례가 없으면 커밋 메시지와 코드 주석은 영어, PR 본문과 이슈 코멘트는 한국어를 기본값으로 한다.
- 간결하고 명확하게 작성한다.

자세히: `rules/language.md`

## Git Safety / Git 안전 규칙

**NEVER commit or push without explicit user permission.**

- 사용자가 명시적으로 요청할 때만 `git commit`, `git push`를 실행한다.
- 코드 변경 후 자동으로 커밋하지 않는다.
- "커밋해", "commit" 같은 명확한 지시가 있을 때만 수행한다.
- `/commit`, `/commit-push`, `/pr-create` 등 슬래시 커맨드는 명시적 커밋·푸시 지시로 간주한다.
- `git reset --hard`, `git checkout --`, `git push --force` 같은 파괴적 작업은 사용자가 분명히 요청한 경우에만 수행한다.
- 작업 트리에 다른 변경이 있으면 임의로 되돌리지 않는다.
- `--no-verify`, `--no-gpg-sign` 같은 훅·서명 우회는 사용자가 분명히 요구한 경우가 아니면 사용하지 않는다.

자세히: `rules/git-workflow.md`

## Plan First / 계획 우선

**Use plan mode before meaningful implementation.**

- 신규 기능, 동작 변경, 구조 변경, 리팩토링, 모호한 요구사항은 구현 전에 plan mode에서 설계를 정리한다.
- `EnterPlanMode`로 진입하고, `ExitPlanMode`로 사용자 승인 요청 후 구현한다.
- 계획에는 문제 이해, 변경 범위, 검증 방법, 리스크를 짧게 포함한다.
- 오타, 한 줄 수정, 순수 탐색, 문구 교정, 상세 지시가 있는 단순 작업은 생략 가능하다.
- 사용자가 즉시 구현을 명확히 요청했고 변경 위험이 낮으면 필요한 맥락 확인 후 바로 처리한다.

자세히: `rules/claude-code.md#plan-mode`

## Project Conventions / 프로젝트 관례

- 기존 구조, 네이밍, 포맷, 테스트 방식, 의존성 선택을 우선한다.
- 새 추상화나 새 파일은 실제 복잡도를 줄이거나 명확한 필요가 있을 때만 추가한다.
- 언어·프레임워크·도구는 프로젝트가 이미 쓰는 것을 우선한다.
- 로컬 지침과 현재 코드가 충돌하면 사용자에게 확인한다.

## Before Changing Code / 변경 전

- 관련 파일, 정의, 참조, 호출 지점, 테스트·설정 위치를 먼저 확인한다.
- 대형 파일은 관련 구간을 중심으로 읽되, 흐름 의존성이 있으면 전체 구조를 파악한다.
- 기존 유사 구현과 유틸리티를 찾아 재사용한다.
- 기존 파일 수정을 우선하고, 새 파일·문서는 꼭 필요할 때만 생성한다.
- 확신 없는 내용은 추측하지 말고 확인한다.
- 가정이 있으면 명시적으로 드러낸다.

## Core Principles / 핵심 원칙

- **Solve the right problem** — 스코프 크리프를 피하고 실제 문제를 푼다.
- **Favor standard solutions** — 표준 라이브러리와 검증된 패턴을 우선한다.
- **Keep code readable** — 명확한 이름, 단순한 흐름, 얕은 중첩을 선호한다.
- **Handle errors explicitly** — 실패를 숨기지 말고 구체적으로 처리한다.
- **Design for security** — 입력 검증, 최소 권한, 시크릿 보호를 기본값으로 둔다.
- **Keep dependencies shallow** — 강결합을 줄이고 경계를 명확히 한다.
- **Address root causes** — 증상 완화보다 원인 제거를 우선한다.
- **Do only what's needed** — 필요한 일만 수행하고 불필요한 변경을 피한다.

자세히: `rules/coding-style.md`, `rules/patterns.md`

## Claude Code Usage / Claude Code 활용

- **Subagent**: 독립적인 탐색·분석·검증에 사용하고, 사용 가능한 agent를 추측해서 만들지 않는다.
- **Skill**: 사용자가 `/<name>`을 호출하거나 작업이 명확히 맞을 때 사용하고, 존재하지 않는 Skill을 추측하지 않는다.
- **Task Tracking**: 3단계 이상 작업은 할 일을 추적하고 상태를 즉시 갱신한다.
- **병렬 도구 호출**: 독립적인 Bash·Read·Grep 호출은 가능한 경우 병렬로 처리한다.
- **최신 문서 확인**: 라이브러리·프레임워크·SDK 정보는 가능한 경우 MCP나 공식 문서를 우선한다.
- **위험 행동 확인**: `rm -rf`, `git push --force`, PR/이슈 작성 등 외부 가시성이 크거나 되돌리기 어려운 작업은 확인 후 실행한다.

자세히: `rules/claude-code.md`, `rules/performance.md`

## Problem Solving / 문제 해결

**Reproduce -> Investigate -> Root Cause -> Fix -> Verify**

- 에러 메시지와 로그에서 직접적인 단서를 수집한다.
- 증상과 원인을 구분한다.
- 수정 후에는 가능한 범위에서 회귀 위험을 확인한다.
- 유사 문제가 반복될 수 있는 지점을 함께 스캔한다.

자세히: `rules/problem-solving.md`

## Testing / 테스트

- 새 동작이나 버그 수정에는 가능한 한 테스트를 추가한다.
- 테스트는 빠르고 결정적이어야 한다.
- 테스트 범위와 방식은 프로젝트 관례와 변경 위험에 맞춘다.
- 테스트 간 상태 공유를 피한다.
- 검증을 실행하지 못했으면 이유와 남는 리스크를 명시한다.

자세히: `rules/testing.md`

## Security / 보안

- 시크릿을 코드, 로그, 커밋, 이슈, PR에 노출하지 않는다.
- 외부 입력은 검증하고 필요한 경우 정규화·인코딩한다.
- 권한은 필요한 범위로 제한한다.
- 민감한 작업은 실행 전 영향 범위를 확인한다.
- 민감 정보를 로그에 남기지 않는다.

자세히: `rules/security.md`

## Version Control / 버전 관리

- Commit은 작고 원자적으로 유지한다.
- 커밋 메시지 형식은 프로젝트 관례를 우선하고, 관례가 없으면 `<type>: <description>`을 사용한다.
- PR은 하나의 목적에 집중하고, 테스트 계획과 리스크를 포함한다.
- 공유 브랜치에 force push하지 않는다.
- 시크릿·불필요한 바이너리·생성물을 커밋하지 않는다.

자세히: `rules/git-workflow.md`

## Anti-Patterns / 안티패턴

- 맥락 없이 코드 수정
- 프로젝트 관례를 무시한 새 패턴 도입
- 근본 원인 없이 예외 처리만 덧붙이기
- 통합 테스트를 전부 mock으로 대체하기
- 불필요한 리팩토링으로 변경 범위 확대
- 훅 우회·강제 푸시
- 독립 도구 호출을 불필요하게 순차 실행
- 없는 Skill·Agent를 추측해서 호출
- 검증 없이 작업 완료로 간주하기

자세히: `rules/anti-patterns.md`
