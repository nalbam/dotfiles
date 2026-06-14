---
name: docs-read
description: Read README, CLAUDE.md, and docs/ to understand a project. 프로젝트 문서 읽고 파악, 온보딩, 구조 이해.
allowed-tools: Read, Bash, Grep, Glob
---

# Documentation Read

**한국어로 응답. 코드·명령어는 원문 유지** (`rules/language.md`).

프로젝트의 `README.md`, `CLAUDE.md`, `docs/` 를 체계적으로 읽고 프로젝트의 목적·구조·관례를 빠르게 파악한다. **읽기 전용** — 문서를 수정하지 않는다. 작업 시작 전 온보딩·컨텍스트 확보가 목적이다.

## Philosophy

- **문서부터 읽는다** — 코드를 뒤지기 전에 프로젝트가 스스로 설명한 진실을 먼저 흡수한다
- **전체 그림을 먼저 그린다** — 개별 파일이 아닌 목적·경계·진입점·관례를 파악한다
- **문서를 맹신하지 않는다** — 문서가 코드와 다를 수 있음을 인지하되, 검증·수정은 `/docs-sync` 의 몫이다
- **읽고 멈춘다** — 이 스킬은 이해·요약까지만. 변경은 별도 작업이다

## Scope

- **읽는 대상**: 프로젝트 루트 `README.md`·`CLAUDE.md`, `docs/` 디렉토리 전체, `AGENTS.md`·`CONTRIBUTING.md` 등 루트의 안내 문서
- **읽지 않는 대상**: 구현 소스 코드 (필요하면 진입점만 확인). 전체 코드 분석은 `/code-audit`, 코드↔문서 정합은 `/docs-sync`

## Exclude Patterns

문서 탐색 시 dependency / build / cache / VCS / IDE / 테스트 산출물 디렉토리는 제외한다. 전체 목록은 `code-audit` 스킬 (`~/.claude/skills/code-audit/SKILL.md`) 의 *Exclude Patterns* 표를 *유일한 source* 로 한다.

## Process

### 1. Discover — 문서 인벤토리
- 루트의 `README.md`·`CLAUDE.md`·`AGENTS.md`·`CONTRIBUTING.md` 존재 확인
- `docs/` 디렉토리 트리 스캔 (exclude 패턴 적용)
- 문서 목록과 구조를 파악

### 2. Read — 우선순위대로 읽기
1. **`README.md`** — 프로젝트 목적·설치·사용·아키텍처 개요
2. **`CLAUDE.md` / `AGENTS.md`** — AI 에이전트용 작업 지침·관례·gotcha
3. **`docs/README.md`** (있으면) — 문서 인덱스로 활용
4. **`docs/*.md`** — 아키텍처·API·가이드 등 세부 문서
5. **진입점 확인** — 문서가 가리키는 핵심 파일(예: `run.sh`, `main.go`)의 *존재와 역할*만 확인 (전체 정독 X)

### 3. Synthesize — 이해 종합
읽은 내용에서 다음을 추출한다:
- **What** — 프로젝트가 무엇인가 (한 문장)
- **Why** — 어떤 문제를 푸는가
- **Structure** — 주요 디렉토리·진입점·구성 요소
- **Conventions** — 코딩·테스트·git·배포 관례, 지켜야 할 규칙
- **Gotchas** — 문서가 강조하는 비자명한 함정·제약
- **Entry points** — 작업 시 먼저 봐야 할 파일

### 4. Report — 파악 결과 요약
```
## 프로젝트 파악: <name>

**What**: <한 문장 요약>
**Why**: <해결하는 문제>

**Structure**:
- <주요 디렉토리/진입점> — <역할>

**Conventions**:
- <지켜야 할 핵심 관례>

**Gotchas**:
- <비자명한 함정·제약>

**다음에 볼 곳**: <작업 성격에 따라 먼저 읽을 파일>

**문서 갭** (선택): <문서가 비어있거나 오래돼 보이는 영역 — 수정은 /docs-sync>
```

## Quality

- 문서가 길면 *요점만* 추린다 — 전문 복사 금지
- 문서 간 모순·공백을 발견하면 *언급만* 하고 단정하지 않는다
- 추측을 사실로 보고하지 않는다 — 문서에 없으면 "문서에 없음" 으로 표시
- 요약은 간결하게 — 사용자는 원문을 직접 열 수 있다

## Anti-Patterns

- 문서를 *수정* 하지 않는다 (이 스킬은 읽기 전용 — 수정은 `/docs-sync`)
- 전체 소스 코드를 정독하지 않는다 (그것은 `/code-audit`)
- 문서 내용을 그대로 복사·나열하지 않는다 — 종합·요약한다
- 문서에 없는 내용을 추측으로 채우지 않는다
- 새 문서 파일을 만들지 않는다
