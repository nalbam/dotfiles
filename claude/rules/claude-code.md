# Claude Code Usage

Claude Code 고유 기능을 언제·어떻게 써야 하는지 정리한다. `settings.json`에서 활성화된 기능(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `context7` plugin 등)과 `claude/agents/`, `claude/skills/`에 배치된 자산을 전제로 한다.

## Plan Mode / 계획 모드

구현 전 설계를 완성한 후 사용자 승인을 받는 단계.

- `EnterPlanMode` 툴로 진입
- 탐색·계획 수립 후 `ExitPlanMode`로 승인 요청
- 사용자 승인 이후에만 파일 수정 시작

### When to enter plan mode

- 새로운 기능 구현
- 의미 있는 구조 변경이 2곳 이상
- 아키텍처 결정 또는 리팩토링
- 요구사항이 모호하거나 복수 접근이 가능
- 기존 동작을 바꾸는 수정

### When plan mode is not required

- 오타·명백한 한 줄 수정
- 순수 탐색/조사 작업 (코드 변경 없음)
- 사용자가 상세한 지시를 제공한 단순 작업
- 문서 문구 교정 수준의 사소한 편집

### Plan quality checklist

- 변경 대상 파일·라인 명시
- 영향 범위와 리스크 기록
- 테스트·검증 전략 포함
- 대안 접근을 최소 1개 비교 후 선택 근거 기술

## Subagents / 서브에이전트

독립적 탐색·분석 작업을 메인 컨텍스트에서 분리.

### 사용 기준

- **Explore**: 3개 이상 쿼리가 필요한 코드베이스 탐색
- **Plan**: 구현 전략 설계 (Plan Mode 내부에서 활용 가능)
- **general-purpose**: 다단계 리서치, 불확실한 탐색
- **debugger**: 에러·테스트 실패 디버깅
- **code-reviewer**: 품질·보안 리뷰
- **planner**, **architect**, **refactorer**, **builder**, **test-writer**, **doc-writer**: 명시된 역할에 맞게

### 원칙

- 작업 목표가 명확히 알려진 경우(특정 파일·심볼)는 직접 툴 사용 (Read, Grep)
- 독립적 서브에이전트는 한 메시지에 다중 tool call로 **병렬 spawn**
- 서브에이전트가 이미 하고 있는 탐색을 메인에서 중복 수행하지 않는다
- 프롬프트에 맥락·원하는 산출물 형식·분량을 명시

## Skills / 스킬

사용자가 `/<name>` 형태로 호출하거나, 작업에 매치되는 스킬이 있을 때 사용.

- `/validate`, `/commit`, `/commit-push`, `/pr-create`, `/pr-summary`, `/review`, `/security-review`, `/docs-sync`, `/code-audit`, `/init`, `/resolve-coderabbit` 등
- 사용자가 `/<name>`을 타이핑하면 **반드시** Skill 툴로 호출
- 추측해서 존재하지 않는 스킬을 호출하지 않는다 (available-skills 리스트 확인)
- 이미 실행 중인 스킬을 재호출하지 않는다

## Tasks / 작업 추적

`TaskCreate` / `TaskUpdate`를 통한 진행 관리.

### 사용 기준

- 3단계 이상 분리된 작업
- 복수 작업 동시 진행
- 계획 기반 구현 중 진행 상황 추적
- 사용자가 목록 형태로 요구사항 제공

### 원칙

- 작업 시작 직전에 `in_progress`로 변경
- 완료 즉시 `completed` (배치 처리 금지)
- 독립 작업은 한 번에 여러 `TaskCreate` 호출

## 병렬 도구 호출

독립 호출은 한 어시스턴트 메시지에 동시 배치.

- 예: `git status`, `git diff`, `git log`를 병렬 실행
- 예: 여러 파일을 동시 Read
- 의존 관계가 있으면 순차로 유지 (이전 결과가 다음 입력인 경우)
- 서브에이전트도 독립적이면 병렬 spawn

## Context7 MCP

라이브러리·프레임워크·SDK·CLI·클라우드 서비스 문서 조회는 Context7 우선.

- React, Next.js, Prisma, Express, Django 같이 익숙한 라이브러리도 대상
- 훈련 데이터 대신 최신 문서 신뢰
- 호출 순서: `resolve-library-id` → `query-docs`
- 사용자가 `/org/project` 형식으로 직접 ID를 제공하면 resolve 단계 생략
- 다음은 제외: 리팩토링, 스크립트 작성, 비즈니스 로직 디버깅, 코드 리뷰, 일반 프로그래밍 개념

## 위험 행동 확인

되돌릴 수 없거나 외부에 가시적인 행동은 실행 전 사용자 확인.

### 확인 필수

- 파괴적 작업: `rm -rf`, `git reset --hard`, `DROP TABLE`, 브랜치 삭제, 프로세스 킬
- 되돌리기 어려운 작업: `git push --force`, amend된 공개 커밋, 패키지 다운그레이드
- 외부 가시 작업: `git push`, PR/이슈 생성·댓글·클로즈, Slack/이메일 전송
- 공유 인프라·권한 변경

### 절대 금지

- `--no-verify`, `--no-gpg-sign` 등 훅·서명 우회 (사용자가 명시 요청한 경우만 허용)
- 사용자 허가 없는 `git commit`, `git push`
- 메인/마스터에 force push
- 시크릿·`.env` 파일 커밋

## UI·프론트엔드 검증

- 타입체크·테스트는 코드의 정확성만 검증한다. 기능 동작은 별도 검증 필요.
- UI 변경 시 가능하면 dev 서버 실행 후 브라우저에서 정상 경로·엣지 케이스 확인
- 직접 확인 불가능하면 "UI 검증 미완료"임을 명시 (성공 주장 금지)

## Performance — Model Selection

- **Opus** — 깊은 추론, 복잡 아키텍처, 에이전트 워크플로우
- **Sonnet** — 빠른 코드 생성, 단순 수정, 오케스트레이션
- **Haiku** — 유틸리티 함수, 문서 갱신, 짧은 질의

## Context Window Management

- 컨텍스트 마지막 20%에서는 대규모 리팩토링·다중 파일 구현을 피한다
- 단일 파일 수정·독립 유틸·문서 갱신은 컨텍스트 소모가 적음
- 대형 탐색은 subagent로 위임하여 메인 컨텍스트 보호
