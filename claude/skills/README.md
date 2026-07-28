# Skills

어떤 스킬이 있고 언제 쓰는지, 그리고 새 스킬을 어떻게 쓰는지 정리한다.

**Skill vs Agent**
- **Skill** (`/<name>`) — 반복되는 *절차* 또는 *판단 기준*을 규약화한 문서(커밋·PR·검증·감사·스타일 등).
- **Agent** (`../agents/`) — 코드를 실제로 *작성·수정·분석*하는 작업 역할. 필요 시 자동 위임된다.

코드를 새로 짜거나 고치는 일은 Claude 본체와 agent가 맡고, 스킬은 그 주변의 *되풀이되는 단계*를 담당한다. 그래서 앞단(목표·스펙)과 일부 단계는 스킬 대신 agent가 채운다.

## 두 종류의 스킬

| 종류 | 무엇인가 | 호출 | 목록 |
|------|---------|------|------|
| **실행 스킬** | 절차를 수행한다 — 읽고, 고치고, 명령을 돌린다 | `/<name>` (일부는 모델 자동 호출도 허용) | 아래 단계별 매핑 |
| **참조 스킬** | 판단 기준을 제공한다 — 절차를 수행하지 않는다 | 필요할 때 모델이 로드 | `anti-patterns`, `claude-code-usage`, `coding-style`, `problem-solving`, `testing-rules` |

참조 스킬은 `../CLAUDE.md` 각 섹션의 *유일한 상세 source* 다. hub(CLAUDE.md)에는 한 줄 요약만 상주하고 본문은 호출 시 로드된다 — 그래서 이름이 동사가 아니라 주제다.

| 참조 스킬 | 무엇의 source 인가 |
|-----------|-------------------|
| `coding-style` | Core Principles · Surgical Changes |
| `problem-solving` | Before Changing Code · Problem Solving · Goal-Driven Execution |
| `testing-rules` | Testing |
| `claude-code-usage` | Claude Code Usage (plan mode·서브에이전트·병렬 호출·Context7) |
| `anti-patterns` | 전 주제의 안티패턴 카탈로그 + Working If 자가 점검 |

## 단계별 매핑

| 단계 | Skill | 작업 수행 (Agent) |
|------|-------|-------------------|
| **0. 부트스트랩** | `/nextjs-init` | `architect` |
| **1. 목표** | — | `planner`, `architect` |
| **2. 스펙** | — | `architect`, `doc-writer` |
| **3. 구현** | `/commit`, `/commit-push` | `builder`, `refactorer`, `debugger` |
| **4. 테스트** | `/validate` | `test-writer`, `code-reviewer`, `debugger` |
| **5. 릴리즈** | `/pr-create`, `/pr-summary`, `/resolve-coderabbit`, `/docs-sync` | `code-reviewer`, `doc-writer` |
| **6. 유지보수** | `/code-audit`, `/docs-sync` | `code-reviewer`, `refactorer` |

> `/validate` 는 특정 단계 전용이 아니라 **구현~릴리즈 전 구간의 공통 게이트**다. `/commit`·`/pr-create` 직전에도 먼저 실행한다.
>
> `/docs-read` 는 특정 단계 전용이 아니라 **작업 시작 전 공통 온보딩**이다. 낯선 저장소에서 코드를 건드리기 전에 문서로 프로젝트를 파악한다 (읽기 전용 — 수정은 `/docs-sync`).

## 단계별 상세

### 0. 부트스트랩
새 프로젝트를 정해진 스택으로 생성하는 단계. 기존 프로젝트에는 쓰지 않는다.

- `/nextjs-init` — Next.js 16 프로젝트 생성 (App Router · TS strict · Mantine 9 · Better Auth + Google OAuth on DynamoDB · Clean Architecture · Docker/ECR)

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
| 새 Next.js 프로젝트 생성 | `/nextjs-init` |
| 문서 읽고 프로젝트 파악 | `/docs-read` |
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
- 같은 내용을 두 스킬에 쓰지 않는다 — 한쪽을 source 로 선언하고 다른 쪽은 `skills/<name>/SKILL.md#anchor` 로 참조한다 (예: Exclude Patterns → `code-audit`, package manager 감지 → `validate`, PR body 형식 → `pr-create`).
- Codex 미러(`codex/skills/*/SKILL.md`)는 이 디렉토리에서 생성된다 — 스킬 수정 후 `python3 scripts/gen-codex-skills.py` 실행 (직접 편집 금지).

### frontmatter

```yaml
name: <디렉토리명과 동일한 kebab-case>
description: <영문 한 문장> <한국어 트리거 어구>. <인접 스킬과의 경계>
allowed-tools: <실제로 쓰는 도구만>
disable-model-invocation: true   # 아래 조건일 때만
argument-hint: [pr-number]       # 인자를 받을 때만
```

- **description 은 모델이 호출 여부를 판단하는 유일한 근거다.** *무엇을* 하는지에 더해 *언제* 쓰는지, 그리고 헷갈리는 이웃 스킬과의 경계를 넣는다 — `docs-read` ↔ `docs-sync`, `code-audit` ↔ `/review` ↔ `/validate` 처럼.
- **한국어·영어를 함께 적는다.** 사용자는 한국어로 요청하고 스킬 목록은 영어로 검색된다.
- **`allowed-tools` 로 경계를 강제한다.** "읽기 전용" 이라고 본문에 쓰는 것보다 `Write`·`Edit` 를 빼는 쪽이 확실하다 (`docs-read`, `code-audit`).
- **`disable-model-invocation: true` 는 git·GitHub 상태를 바꾸는 스킬에만 붙인다** — `commit`, `commit-push`, `pr-create`, `pr-summary`, `resolve-coderabbit`. 이들은 명시적 사용자 지시가 곧 실행 허가이므로 모델이 스스로 부르면 안 된다 (`../rules/git-workflow.md`).

### 본문

실행 스킬은 `Philosophy → Scope/Rules → Process(또는 Workflow) → Anti-Patterns` 순서를 따른다. 각 단계에는 *다음 단계로 넘어가도 되는지 판단할 종료 조건*을 붙인다 (`problem-solving/SKILL.md#goal-driven-execution--목표-기반-실행`).

서브에이전트를 스폰하는 스킬은 **서브에이전트가 SKILL.md 를 보지 못한다**는 점을 전제로 프롬프트에 기준·제외 패턴·산출물 형식을 직접 실어 보낸다.
