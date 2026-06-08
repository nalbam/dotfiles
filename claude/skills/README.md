# Skills

프로젝트 생명주기 단계별로 어떤 스킬을 쓰는지 정리한다.

**Skill vs Agent**
- **Skill** (`/<name>`) — 반복되는 *절차*를 규약화한 명시적 워크플로우(커밋·PR·검증·감사 등). 사용자가 직접 호출한다.
- **Agent** (`../agents/`) — 코드를 실제로 *작성·수정·분석*하는 작업 역할. 필요 시 자동 위임된다.

코드를 새로 짜거나 고치는 일은 Claude 본체와 agent가 맡고, 스킬은 그 주변의 *되풀이되는 단계*를 담당한다. 그래서 앞단(목표·스펙)과 일부 단계는 스킬 대신 agent가 채운다.

## 단계별 매핑

| 단계 | Skill | 작업 수행 (Agent) |
|------|-------|-------------------|
| **1. 목표** | — | `planner`, `architect` |
| **2. 스펙** | — | `architect`, `doc-writer` |
| **3. 구현** | `/commit`, `/commit-push` | `builder`, `refactorer`, `debugger` |
| **4. 테스트** | `/validate` | `test-writer`, `code-reviewer`, `debugger` |
| **5. 릴리즈** | `/pr-create`, `/pr-summary`, `/resolve-coderabbit`, `/docs-sync` | `code-reviewer`, `doc-writer` |
| **6. 유지보수** | `/code-audit`, `/docs-sync` | `code-reviewer`, `refactorer` |

> `/validate` 는 특정 단계 전용이 아니라 **구현~릴리즈 전 구간의 공통 게이트**다. `/commit`·`/pr-create` 직전에도 먼저 실행한다.

## 단계별 상세

### 1. 목표
계획 수립 단계. 전용 스킬은 없고 `planner`·`architect` agent 가 요구 분석·접근 설계를 담당한다.

### 2. 스펙
설계·명세 작성 단계. `architect`(구조 결정)·`doc-writer`(명세 문서) agent 가 담당한다. `/docs-sync` 는 *코드가 이미 있는* 상태에서 문서를 맞추는 스킬이라 이 단계에는 쓰지 않는다.

### 3. 구현
- `/commit` — 변경의 *의미*를 이해한 뒤 conventional 형식으로 커밋
- `/commit-push` — `/commit` 절차 + 원격 push (push 전 추가 점검)

실제 코드 작성·리팩토링·디버깅은 `builder`·`refactorer`·`debugger` agent 와 Claude 본체가 수행한다.

### 4. 테스트
- `/validate` — lint·typecheck·test 실행 후 **근본원인 수정**, 전부 통과까지 반복 (수정 불가 실패는 멈추고 보고)

테스트 작성은 `test-writer`, 품질·보안 리뷰는 `code-reviewer`, 실패 디버깅은 `debugger` agent.

### 5. 릴리즈
- `/pr-create` — 전체 diff 분석 후 PR 생성 (Summary / Changes / Breaking / Test Plan)
- `/pr-summary` — 기존 PR 설명을 실제 변경에 맞게 갱신
- `/resolve-coderabbit` — CodeRabbit 리뷰 코멘트를 평가(ACCEPT/REJECT/SKIP)·수정·resolve
- `/docs-sync` — 릴리즈 전 코드↔문서 갭 정합

### 6. 유지보수
- `/code-audit` — 전체 코드 심층 감사 (보안·아키텍처·품질·테스트 4축 병렬 분석 → 근본원인 → 심각도별 보고)
- `/docs-sync` — 문서 정확성 유지 (틀린 문서 우선 교정)

## 빠른 참조 (상황 → 스킬)

| 하고 싶은 일 | 스킬 |
|-------------|------|
| 변경 커밋 | `/commit` |
| 커밋 후 푸시 | `/commit-push` |
| lint·타입·테스트 검증·수정 | `/validate` |
| PR 생성 | `/pr-create` |
| PR 설명 갱신 | `/pr-summary` |
| CodeRabbit 리뷰 정리 | `/resolve-coderabbit` |
| 코드 전체 감사 | `/code-audit` |
| 문서-코드 동기화 | `/docs-sync` |

## 규약

- 각 스킬의 세부 절차는 `<name>/SKILL.md` 가 단일 source.
- 공통 규칙은 `../rules/*.md` 참조 (git 안전·언어·외과적 변경 등).
- 파괴적·외부 가시 작업(push, PR publish, thread resolve)은 스킬이 후보만 제시하고 **사용자가 확인**한다.
