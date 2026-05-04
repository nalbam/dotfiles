# CLAUDE.md

Claude Code(claude.ai/code)를 위한 전역 지침. 프로젝트별 지침이 없는 작업의 기본값.

**구조 원칙**: 이 파일은 *우선순위와 자주 참조될 행동 규칙*을 담는다. 깊은 예시·근거·체크리스트는 `rules/*.md`에 *단 한 곳*에서만 정의된다 — 상세를 찾을 때는 항상 링크된 rules 파일을 참조하라.

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

- 사용자와의 대화는 한국어로 한다.
- 코드·명령어·파일명·API 이름·기술 용어는 원문(영어) 유지.
- 커밋 메시지·코드 주석은 *프로젝트 관례 우선, 없으면 영어*.
- PR 본문·이슈 코멘트는 *프로젝트 관례 우선, 없으면 한국어*.
- 간결하고 명확하게 작성한다 — 장황한 인사·요약 생략.

자세히: `rules/language.md`

## Git Safety / Git 안전 규칙

**NEVER commit or push without explicit user permission.**

- 사용자가 명시적으로 요청할 때만 `git commit`, `git push` 실행.
- "커밋해", "commit", "push" 같은 자연어 또는 `/commit`, `/commit-push`, `/pr-create` 슬래시 커맨드만 명시적 지시로 간주.
- 코드 변경 후 자동으로 커밋하지 않는다.
- 파괴적 작업(`git reset --hard`, `git checkout --`, `git push --force`, 브랜치 삭제 등)은 사용자가 분명히 요청한 경우에만.
- 훅·서명 우회(`--no-verify`, `--no-gpg-sign`)는 사용자가 명시 요청한 경우만.
- 작업 트리에 다른 변경이 있으면 임의로 되돌리지 않는다.

자세히: `rules/git-workflow.md`

## Plan First / 계획 우선

**Use plan mode before meaningful implementation.**

- 신규 기능·동작 변경·구조 변경·리팩토링·모호한 요구는 구현 전 plan mode 로 설계 합의.
- `EnterPlanMode` 진입 → 탐색·설계 → `ExitPlanMode` 로 사용자 승인 요청 → 승인 후 구현.
- 계획에는 문제 이해·변경 범위·검증 방법·리스크를 짧게 포함.
- 오타·한 줄 수정·순수 탐색·문구 교정·상세 지시가 있는 단순 작업은 생략 가능.
- 사용자가 즉시 구현을 명확히 요청했고 변경 위험이 낮으면 필요한 맥락 확인 후 바로 처리.

자세히: `rules/claude-code.md#plan-mode--계획-모드`

## Project Conventions / 프로젝트 관례

- 기존 구조·네이밍·포맷·테스트 방식·의존성 선택을 우선한다.
- 새 추상화·새 파일은 실제 복잡도를 줄이거나 명확한 필요가 있을 때만 추가.
- 언어·프레임워크·도구는 프로젝트가 이미 쓰는 것을 우선.
- 로컬 지침과 현재 코드가 충돌하면 사용자에게 확인.

## Before Changing Code / 변경 전

- 관련 파일·정의·참조·호출 지점·테스트·설정 위치를 먼저 확인한다.
- 대형 파일은 관련 구간을 중심으로 읽되, 흐름 의존성이 있으면 전체 구조 파악.
- 기존 유사 구현·유틸리티를 찾아 재사용한다.
- 기존 파일 수정을 우선하고, 새 파일·문서는 꼭 필요할 때만 생성.
- 확신 없는 내용은 추측하지 말고 확인. 가정이 있으면 명시적으로 드러낸다.
- **요구가 모호하면 여러 해석을 나열하고 선택을 요청한다** — 조용히 하나를 고르지 않는다.
- **더 단순한 접근이 보이면 즉시 제시**, 사용자 안이 과복잡하면 근거와 함께 푸시백.
- **혼란 시 멈춘다** — 무엇이 불명확한지 이름 붙여 질문. "막히면 그때 묻겠다"는 금지.

자세히: `rules/problem-solving.md#think-before-coding--코딩-전-사고`

## Surgical Changes / 외과적 변경

**변경된 모든 라인은 사용자 요청에 직접 추적 가능해야 한다.**

- 인접한 코드·주석·포맷팅을 같이 "개선"하지 않는다.
- 고장 나지 않은 것을 리팩토링하지 않는다.
- 기존 스타일(따옴표·들여쓰기·import 순서·컨벤션)을 본인 선호로 바꾸지 않는다.
- 요청에 없는 타입 힌트·docstring·주석을 새로 추가하지 않는다.
- 사용자가 묻지 않은 새 추상화·플래그·설정 옵션을 끼워 넣지 않는다.
- 무관한 dead code 는 *언급만* 하고 별도 작업으로 분리.
- 한 PR/커밋에 두 가지 이상 목적을 섞지 않는다.

자세히: `rules/coding-style.md#surgical-changes--외과적-변경`

## Goal-Driven Execution / 목표 기반 실행

**명령형 지시는 *검증 가능한 종료 조건* 으로 변환한 뒤 시작한다.** 강한 종료 조건만이 독립 루프를 가능케 한다.

변환 예시:
- "버그 고쳐" → "재현 테스트 작성 → 통과시키기"
- "리팩토링해" → "변경 전후로 동일 테스트 통과"
- "성능 개선" → "측정 baseline + 목표 수치 정의 → 측정으로 검증"
- "make it work" → 종료 조건을 사용자에게 먼저 확인

다단계 작업은 단계마다 검증 방법을 명시한다 — `1. [단계] → 검증: [방법]`. 검증이 정해지지 않은 단계는 계획에 넣지 않는다.

자세히: `rules/problem-solving.md#goal-driven-execution--목표-기반-실행`

## Core Principles / 핵심 원칙

- **Solve the right problem** — 스코프 크리프 회피, 부수 개선은 별도 PR.
- **Handle errors explicitly** — broad catch 금지, 맥락 포함한 fast-fail.
- **Address root causes** — 증상 완화가 아닌 원인 제거.
- **Keep code readable** — 명확한 이름, 얕은 중첩(>4단계 회피), 작은 함수.
- **Design for security** — 입력 검증·최소 권한·시크릿 보호 (`rules/security.md`).
- **Favor immutability** — 새 객체를 만들고 mutate 하지 않는다.
- **Do only what's needed** — 요청 범위만 처리, 불필요한 변경 회피.

자세히: `rules/coding-style.md`

## Problem Solving / 문제 해결

**Reproduce → Investigate → Root Cause → Fix → Verify**

- 에러 메시지·로그에서 직접적인 단서를 먼저 수집한다.
- 증상과 원인을 구분 (예: "API 500" vs. "커넥션 풀 고갈").
- "Why?" 를 근본 이슈에 도달할 때까지 반복.
- 수정 후 회귀 테스트 추가, 같은 원인이 다른 코드 경로에 있는지 스캔.
- 워크어라운드는 *임시* 임을 명시 + 후속 작업 등록.

자세히: `rules/problem-solving.md`

## Testing / 테스트

- 새 동작·버그 수정에 테스트를 추가한다.
- 테스트는 *Fast / Isolated / Deterministic / Readable / Focused*.
- 범위·방식·커버리지 수치는 *프로젝트 관례와 변경 위험에 맞춘다* — 강제 임계값 없음.
- 테스트 간 상태 공유를 피한다.
- 검증을 못 했다면 이유와 잔여 리스크를 명시한다.

자세히: `rules/testing.md`

## Security / 보안

- 시크릿(API 키·패스워드·토큰)을 코드·로그·커밋·이슈·PR 에 노출하지 않는다.
- 외부 입력은 시스템 경계에서 검증·정규화·인코딩한다.
- 권한은 필요한 최소 범위로 제한한다.
- 민감 작업(인증·권한·암호화·PII)은 실행 전 영향 범위를 사용자에게 확인.
- 노출된 시크릿은 즉시 rotate — 코드 수정만으론 부족.

자세히: `rules/security.md`

## Claude Code Usage / Claude Code 활용

도구 사용 규약은 `rules/claude-code.md` 가 *유일한 source*. 핵심 행동 규칙:

- **Plan Mode**: 의미 있는 구현 전 진입.
- **Subagent**: 독립 탐색·분석·검증에 사용. 추측해서 존재하지 않는 에이전트 호출 금지.
- **Skill**: 사용자가 `/<name>` 을 타이핑하면 *반드시* Skill 도구로 호출. 없는 스킬 추측 금지.
- **Task Tracking**: 3단계 이상 작업은 `TaskCreate` 로 추적. 시작 *직전* `in_progress`, 완료 *즉시* `completed`.
- **병렬 도구 호출**: 독립적인 Bash·Read·Grep 호출은 한 메시지에 동시 배치. 의존 관계가 있을 때만 순차.
- **최신 문서 확인**: 라이브러리·SDK·CLI 문서는 훈련 데이터 대신 Context7 우선.
- **위험 행동 확인**: `rm -rf`, `git push --force`, PR/이슈 작성 등 외부 가시·되돌리기 어려운 작업은 사용자 확인 후 실행.
- **Context Window**: 마지막 ~20% 에서 대규모 리팩토링 회피, 대형 탐색은 subagent 위임.

자세히: `rules/claude-code.md`, `rules/performance.md`

## Anti-Patterns / 안티패턴

- 맥락 없이 코드 수정
- 프로젝트 관례를 무시한 새 패턴 도입
- 근본 원인 없이 예외 처리만 덧붙이기
- 통합 테스트를 전부 mock 으로 대체
- 요청 범위를 넘어선 인접 리팩토링·스타일 변경
- 훅 우회·강제 푸시·사용자 허가 없는 commit/push
- 독립 도구 호출을 불필요하게 순차 실행
- 없는 Skill·Agent 를 추측해서 호출
- 종료 조건 없이 시작 ("일단 해보고 안 되면 다시")
- 검증 없이 작업 완료로 간주
- 문서·주석에 변경 이력·시행착오를 누적 (현재 상태만 기록)

자세히 + Working If 자가 점검 척도: `rules/anti-patterns.md`
