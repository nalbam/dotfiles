# CLAUDE.md

Claude Code(claude.ai/code)를 위한 전역 지침. 프로젝트별 지침이 없는 작업의 기본값.

**구조 원칙**: 이 파일은 *우선순위와 핵심 규칙의 인덱스*다. 각 규칙의 상세·예시·체크리스트는 `rules/*.md`에 *단 한 곳*에서만 정의된다. 상세를 찾을 때는 항상 링크된 rules 파일을 참조하라.

## Instruction Hierarchy / 지침 우선순위

충돌 시 위가 강하다.

1. 상위 시스템·도구 정책
2. 사용자의 직접 지시
3. 현재 저장소의 로컬 지침과 관례
4. 이 전역 지침

로컬 지침은 스타일·테스트·도구를 구체화할 수 있다. **단, Git Safety / 보안 / 파괴적 작업 확인은 약화하지 못한다.**

## Priority / 핵심 우선순위

1. **Git Safety** — 명시 허가 없이 commit/push 금지 → `rules/git-workflow.md`
2. **Plan First** — 의미 있는 구현 전 설계 합의 → `rules/claude-code.md#plan-mode--계획-모드`
3. **Language** — 사용자 응답은 한국어 → `rules/language.md`
4. **Project Conventions** — 저장소 관례 우선
5. **Before Changing Code** — 변경 전 맥락 파악·가정 명시
6. **Surgical Changes** — 요청 라인만 수정 → `rules/coding-style.md#surgical-changes--외과적-변경`
7. **Goal-Driven Execution** — 검증 가능한 종료 조건 → `rules/problem-solving.md#goal-driven-execution--목표-기반-실행`

## Language / 언어

**Always respond in Korean (한국어로 응답하세요).**

코드·명령어·파일명·API 이름은 원문 유지. 커밋 메시지·코드 주석은 *프로젝트 관례 우선, 없으면 영어*. PR 본문·이슈 코멘트는 *프로젝트 관례 우선, 없으면 한국어*.

자세히: `rules/language.md`

## Git Safety / Git 안전 규칙

**NEVER commit or push without explicit user permission.**

명시적 허가로 간주되는 신호:
- 자연어: "커밋해", "커밋하세요", "commit", "push"
- 슬래시 커맨드: `/commit`, `/commit-push`, `/pr-create`

파괴적·되돌릴 수 없는 작업(`git reset --hard`, `git push --force`, `--no-verify`, 브랜치 삭제 등)은 사용자가 분명히 요청한 경우에만 수행한다.

자세히: `rules/git-workflow.md`

## Plan First / 계획 우선

신규 기능·구조 변경·리팩토링·모호한 요구는 구현 전에 plan mode로 합의한다. 오타·한 줄 수정·순수 탐색·상세 지시가 있는 단순 작업은 생략 가능.

자세히: `rules/claude-code.md#plan-mode--계획-모드`

## Project Conventions / 프로젝트 관례

기존 구조·네이밍·포맷·테스트 방식·의존성을 우선한다. 새 추상화·새 파일은 명확한 필요가 있을 때만. 로컬 지침과 코드가 충돌하면 사용자에게 확인.

## Before Changing Code / 변경 전

- 관련 파일·정의·참조·호출 지점·테스트·설정을 먼저 확인한다.
- 기존 유사 구현·유틸리티를 찾아 재사용한다.
- 기존 파일 수정을 우선, 새 파일은 꼭 필요할 때만.
- **요구가 모호하면 여러 해석을 나열하고 선택을 요청한다** — 조용히 하나를 고르지 않는다.
- **더 단순한 접근이 보이면 즉시 제시**, 사용자 안이 과복잡하면 근거와 함께 푸시백한다.
- **혼란 시 멈춘다** — 무엇이 불명확한지 이름 붙여 질문한다. "막히면 그때 묻겠다"는 금지.

자세히: `rules/problem-solving.md#think-before-coding--코딩-전-사고`

## Surgical Changes / 외과적 변경

**변경된 모든 라인은 사용자 요청에 직접 추적 가능해야 한다.** 인접 코드·주석·포맷·스타일을 함께 "개선"하지 않는다. 무관한 dead code는 *언급만* 하고 별도 작업으로 분리한다.

자세히: `rules/coding-style.md#surgical-changes--외과적-변경`

## Goal-Driven Execution / 목표 기반 실행

명령형 지시는 *검증 가능한 종료 조건*으로 변환한 뒤 시작한다.

- "버그 고쳐" → "재현 테스트 작성 → 통과시키기"
- "리팩토링해" → "변경 전후로 동일 테스트 통과"
- "make it work" → 종료 조건을 사용자에게 먼저 확인

강한 종료 조건만이 독립적 루프를 가능케 한다.

자세히: `rules/problem-solving.md#goal-driven-execution--목표-기반-실행`

## Core Principles / 핵심 원칙

행동 가능한 코드 작성 원칙:

- **Solve the right problem** — 스코프 크리프 회피, 부수 개선은 별도 PR
- **Handle errors explicitly** — broad catch 금지, 맥락 포함한 fast-fail
- **Address root causes** — 증상 완화가 아닌 원인 제거
- **Keep code readable** — 명확한 이름, 얕은 중첩, 작은 함수
- **Design for security** — 입력 검증·최소 권한·시크릿 보호 (`rules/security.md`)

자세히: `rules/coding-style.md`

## Problem Solving / 문제 해결

**Reproduce → Investigate → Root Cause → Fix → Verify**

증상과 원인을 구분, 수정 후 회귀와 유사 문제를 함께 점검한다. "Why?"를 근본까지 반복한다.

자세히: `rules/problem-solving.md`

## Testing / 테스트

새 동작·버그 수정에 테스트를 추가한다. 테스트는 *빠르고·결정적이며·격리된다*. 범위·방식·커버리지 수치는 *프로젝트 관례와 변경 위험에 맞춘다* — 강제 임계값은 없다. 검증을 못 했다면 이유와 잔여 리스크를 명시한다.

자세히: `rules/testing.md`

## Security / 보안

시크릿을 코드·로그·커밋·이슈·PR에 노출하지 않는다. 외부 입력은 검증·정규화한다. 권한은 최소 범위로. 민감 작업은 영향 범위를 먼저 확인한다.

자세히: `rules/security.md`

## Claude Code Usage / Claude Code 활용

도구 사용 규약은 `rules/claude-code.md`가 *유일한 source*. 핵심 요약:

- **Plan Mode** — 의미 있는 구현 전 진입
- **Subagent** — 독립 탐색·분석·검증, 추측 호출 금지
- **Skill** — 사용자가 `/<name>`을 타이핑하면 반드시 호출, 없는 스킬 추측 금지
- **Task Tracking** — 3단계 이상 작업 추적, 즉시 갱신
- **병렬 도구 호출** — 독립 호출은 한 메시지에 동시
- **Context7 MCP** — 라이브러리·SDK 문서는 훈련 데이터 대신 Context7
- **위험 행동 확인** — 외부 가시·되돌리기 어려운 작업은 사용자 확인

## Anti-Patterns

자주 빠지는 함정과 자가 점검 척도("Working If")는 한 곳에 정리되어 있다.

자세히: `rules/anti-patterns.md`
