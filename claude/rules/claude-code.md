# Claude Code Usage

Claude Code 고유 기능의 *유일한 상세 source*. CLAUDE.md `## Claude Code Usage` 는 이 파일의 한 줄 요약이다.

전제: `settings.json`에서 활성화된 기능(`CLAUDE_CODE_EXPERIMENTAL_AGENT_TEAMS`, `context7` 플러그인 등)과 `claude/agents/`, `claude/skills/`에 배치된 자산.

## Plan Mode / 계획 모드

구현 전 설계를 완성한 뒤 사용자 승인을 받는 단계.

### 호출

- `EnterPlanMode` 도구로 진입
- 탐색·계획 수립 후 `ExitPlanMode` 로 승인 요청
- 사용자 승인 후에만 파일 수정 시작

### 진입 기준 (둘 중 하나라도 해당)

- 새 기능 구현
- 의미 있는 구조 변경 (2곳 이상)
- 아키텍처 결정 또는 리팩토링
- 모호하거나 복수 접근이 가능한 요구
- 기존 동작을 바꾸는 수정

### 생략 가능

- 오타·명백한 한 줄 수정
- 순수 탐색/조사 (코드 변경 없음)
- 사용자가 상세 지시를 제공한 단순 작업
- 문구 교정 수준의 사소한 편집

### 계획 품질 체크리스트

- [ ] 변경 대상 파일·라인 명시
- [ ] 영향 범위·리스크
- [ ] 테스트·검증 전략
- [ ] 대안 접근 최소 1개 비교 후 선택 근거

## Subagents / 서브에이전트

독립 탐색·분석·검증을 메인 컨텍스트에서 분리.

### 사용 시점

| 에이전트 | 사용 시점 |
|---------|----------|
| `Explore` | 3개 이상 쿼리가 필요한 코드베이스 탐색 |
| `Plan` | 구현 전략 설계 (Plan Mode 내부) |
| `general-purpose` | 다단계 리서치, 불확실한 탐색 |
| `debugger` | 에러·테스트 실패 디버깅 |
| `code-reviewer` | 품질·보안 리뷰 |
| `planner` / `architect` / `refactorer` / `builder` / `test-writer` / `doc-writer` | 명시된 역할에 매칭 |

### 원칙

- 목표가 명확한 단일 파일·심볼 작업은 직접 도구 사용 (Read, Grep)
- 독립 서브에이전트는 *한 메시지에 다중 호출*로 병렬 spawn
- 메인에서 서브에이전트와 같은 탐색을 중복하지 않는다
- 프롬프트에 맥락·산출물 형식·분량을 명시
- **추측해서 존재하지 않는 에이전트를 호출하지 않는다**

## Skills / 스킬

- 사용자가 `/<name>` 을 타이핑하면 *반드시* Skill 도구로 호출
- available-skills 리스트에 없는 스킬은 추측 호출 금지
- 이미 실행 중인 스킬을 재호출하지 않는다

대표 스킬: `/validate`, `/commit`, `/commit-push`, `/pr-create`, `/pr-summary`, `/review`, `/security-review`, `/docs-sync`, `/code-audit`, `/init`, `/resolve-coderabbit`

## Tasks / 작업 추적

`TaskCreate` / `TaskUpdate` 로 진행 관리.

### 사용 기준

- 3단계 이상 분리된 작업
- 복수 작업 동시 진행
- 계획 기반 구현의 진척 추적
- 사용자가 목록 형태로 요구

### 원칙

- 작업 시작 *직전*에 `in_progress`
- 완료 *즉시* `completed` (배치 처리 금지)
- 독립 작업은 한 메시지에 여러 `TaskCreate`

## 병렬 도구 호출

독립 호출은 한 어시스턴트 메시지에 동시 배치한다.

- 예: `git status` + `git diff` + `git log` 동시 실행
- 예: 여러 파일 동시 Read
- 의존 관계가 있으면(이전 결과가 다음 입력) 순차 유지
- 서브에이전트도 독립적이면 병렬 spawn

## Context7 MCP

라이브러리·프레임워크·SDK·CLI·클라우드 서비스 문서는 훈련 데이터 대신 Context7 을 우선한다.

- 익숙한 라이브러리(React, Next.js, Prisma, Express, Django 등)도 대상
- 호출 순서: `resolve-library-id` → `query-docs`
- 사용자가 `/org/project` 형식으로 ID를 직접 제공하면 resolve 생략
- *제외*: 리팩토링, 스크립트 작성, 비즈니스 로직 디버깅, 코드 리뷰, 일반 프로그래밍 개념

## 위험 행동 확인

되돌릴 수 없거나 외부에 가시적인 행동은 실행 *전* 사용자 확인.

- 파괴적: `rm -rf`, `git reset --hard`, `DROP TABLE`, 브랜치 삭제, 프로세스 킬
- 되돌리기 어려운: `git push --force`, amend된 공개 커밋, 패키지 다운그레이드
- 외부 가시: `git push`, PR/이슈 생성·댓글·클로즈, Slack/이메일 전송
- 공유 인프라·권한 변경

git 관련 규약은 `rules/git-workflow.md` 가 source.

## UI·프론트엔드 검증

- 타입체크·테스트는 코드의 정확성만 검증한다. 기능 동작은 별도 검증 필요.
- UI 변경 시 가능하면 dev 서버 + 브라우저로 정상 경로·엣지 케이스 확인
- 직접 확인 불가능하면 *"UI 검증 미완료"* 임을 명시 (성공 주장 금지)

## Context Window Management

- 컨텍스트 마지막 ~20% 에서는 대규모 리팩토링·다중 파일 구현 회피
- 단일 파일 수정·독립 유틸·문서 갱신은 컨텍스트 부담 적음
- 대형 탐색은 subagent 로 위임해 메인 컨텍스트를 보호

## Anti-Patterns

이 주제 안티패턴은 `rules/anti-patterns.md#claude-code-고유` 가 source.
