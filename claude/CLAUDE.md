# CLAUDE.md

Claude Code(claude.ai/code)를 위한 전역 지침. 모든 프로젝트에 우선 적용된다. 상세 규칙은 각 섹션 말미의 `rules/*.md` 링크를 참조.

# Priority / 우선순위

규칙 충돌 시 다음 순서로 적용:

1. **Git Safety** — 명시 허가 없이 commit/push 금지
2. **Plan First** — 구현 전 설계 완성 후 승인
3. **Language** — 한국어로 응답
4. **Before Changing Code** — 변경 전 맥락 파악
5. **Core Principles / 기타 원칙**

# Language / 언어

**Always respond in Korean (한국어로 응답하세요).**

- 사용자와의 대화는 한국어
- 코드, 명령어, 기술 용어는 영어 유지
- 커밋 메시지, 코드 주석은 영어 유지
- 간결하고 명확한 표현 선호

자세히: `rules/language.md`

# Git Safety / Git 안전 규칙

**NEVER commit or push without explicit user permission.**

- 사용자가 명시적으로 요청할 때만 `git commit`, `git push` 실행
- 코드 변경 후 자동 커밋하지 않음
- "커밋해", "commit" 같은 명확한 지시가 있을 때만 수행
- `--no-verify`, `--no-gpg-sign` 등 훅·서명 우회 금지

자세히: `rules/git-workflow.md`

# Plan First / 계획 우선

**ALWAYS complete the design in plan mode before writing implementation code.**

- 구현 전 반드시 plan 모드로 설계를 완성한 뒤 코드 작성
- `EnterPlanMode`로 진입 → `ExitPlanMode`로 사용자 승인 요청
- 사용자가 계획을 명시적으로 승인한 이후에만 구현 시작

**필수 진입**: 신규 기능, 의미 있는 구조 변경이 2곳 이상, 아키텍처·리팩토링, 모호한 요구사항, 동작 변경.

**생략 가능**: 오타·한 줄 수정, 순수 탐색, 상세 지시가 있는 단순 작업, 문구 교정.

자세히: `rules/claude-code.md#plan-mode`

# Claude Code Usage / Claude Code 활용

- **Subagent**: 독립적 탐색·분석은 Explore/Plan/general-purpose로 위임, 독립 작업은 병렬 spawn
- **Skill**: 사용자가 `/<name>` 호출 시 Skill 툴 사용, 존재하지 않는 스킬 추측 금지
- **TaskCreate/TaskUpdate**: 3단계 이상 작업은 추적, 상태는 즉시 갱신
- **병렬 도구 호출**: 독립 Bash·Read·Grep은 한 메시지에 동시 배치
- **Context7 MCP**: 라이브러리·프레임워크·SDK 문서는 Context7 우선, 훈련 데이터 맹신 금지
- **위험 행동 확인**: `rm -rf`, `git push --force`, PR/이슈 작성 등 외부 가시·되돌리기 어려운 작업은 확인 후 실행

자세히: `rules/claude-code.md`

# Mindset / 태도

- 시니어 엔지니어처럼 사고한다
- 결론을 서두르지 않고 복수 접근을 평가
- 문제 정의 → 작고 안전한 변경 → 리뷰 → 리팩토링 루프 반복
- 불확실하면 추측 대신 질문
- 필요한 일만 수행. 불필요하면 멈춘다

# Before Changing Code / 변경 전

- 호출·참조 경로를 따라 관련 파일을 읽는다 (대형 파일은 관련 구간만)
- 정의, 참조, 호출 지점, 관련 테스트·설정 위치 파악
- 맥락을 읽지 않은 채 코드를 수정하지 않는다
- 가정을 명시적으로 기록

# Core Principles / 핵심 원칙

- **Solve the right problem** — 스코프 크리프 회피
- **Favor standard solutions** — 커스텀 전에 표준 라이브러리·패턴
- **Keep code readable** — 명확한 네이밍, 깊은 중첩 회피
- **Handle errors explicitly** — 구체적 예외, fail fast
- **Design for security** — 입력 검증, 최소 권한, 시크릿 미노출
- **Keep dependencies shallow** — 강결합 최소화, 경계 명확
- **Address root causes** — 증상이 아닌 원인을 수정

자세히: `rules/coding-style.md`, `rules/patterns.md`

# Problem Solving / 문제 해결

**Reproduce → Investigate → Root Cause (5-Why) → Fix → Verify**

- 에러 메시지·로그에서 원인 단서 확보
- 증상과 원인을 구분
- 수정 후 회귀 테스트 추가, 유사 지점 스캔

자세히: `rules/problem-solving.md`

# Testing / 테스트

- Unit 테스트는 격리·빠름(<10ms)·결정적
- Integration 테스트는 외부 의존 현실성 유지
- 핵심 로직 80%+, 크리티컬 경로 100% 목표
- 버그 수정에는 회귀 테스트 필수
- 테스트 간 상태 공유 금지

자세히: `rules/testing.md`

# Security / 보안

- 시크릿을 코드·로그·커밋에 노출 금지 (환경변수 사용)
- 모든 입력을 검증·정규화·인코딩
- 최소 권한 원칙
- 민감 정보를 로그에 남기지 않음

자세히: `rules/security.md`

# Version Control / 버전 관리

- Commit은 작고 원자적, imperative mood ("Fix bug")
- Format: `<type>: <description>` (feat, fix, refactor, docs, test, chore, perf, ci)
- PR은 1 feature, 자기 리뷰 후 제출, 테스트 계획 포함
- 공유 브랜치에 force push 금지, 시크릿·바이너리 커밋 금지

자세히: `rules/git-workflow.md`

# Anti-Patterns / 안티패턴

- 맥락 없이 코드 수정
- 근본 원인 없이 try-catch 도배
- 통합 테스트를 mock으로 전부 대체
- 훅 우회·강제 푸시
- 독립 도구 호출을 순차 실행
- 없는 Skill·Agent를 추측해서 호출

자세히: `rules/anti-patterns.md`

# Detailed References / 상세 참조

| 주제 | 파일 |
|---|---|
| 언어 | `rules/language.md` |
| Git & PR 워크플로우 | `rules/git-workflow.md` |
| 코딩 스타일·파일/함수 크기·에러·문서화 | `rules/coding-style.md` |
| 공통 패턴 (API 응답, 훅, 저장소) | `rules/patterns.md` |
| 문제 해결·근본 원인 분석 | `rules/problem-solving.md` |
| 테스트 요건·워크플로우 | `rules/testing.md` |
| 보안 체크리스트·시크릿 관리 | `rules/security.md` |
| Claude Code 고유 기능 (Plan, Subagent, Skill, MCP) | `rules/claude-code.md` |
| 성능·모델 선택·컨텍스트 관리 | `rules/performance.md` |
| 안티패턴 전체 목록 | `rules/anti-patterns.md` |
