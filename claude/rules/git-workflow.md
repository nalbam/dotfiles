# Git Workflow

CLAUDE.md `## Git Safety` 의 *유일한 상세 source*. 모든 git 관련 규칙은 이 파일에서 정의된다.

## CRITICAL: Commit & Push Policy

**NEVER commit or push without explicit user permission.**

### 명시적 허가로 간주되는 신호

- 자연어: "커밋해", "커밋하세요", "commit", "push"
- 슬래시 커맨드: `/commit`, `/commit-push`, `/pr-create`

### 금지 행동 (사용자가 명시 요청한 경우만 예외)

- 코드 변경 후 자동 커밋
- 사용자 허가 없는 `git push`
- 메인/마스터 브랜치에 force push
- 시크릿(`.env`, API 키, 토큰)·바이너리·생성 파일 커밋
- 훅·서명 우회 (`--no-verify`, `--no-gpg-sign`, `--no-signoff`)
- 작업 트리의 다른 변경을 임의로 되돌리기

## 파괴적·되돌릴 수 없는 작업

다음은 사용자가 *분명히* 요청한 경우에만 실행한다. 작업 전 영향 범위를 짧게 보고하고 확인을 받는다.

- `git reset --hard`, `git checkout -- <path>`, `git restore --`
- `git push --force`, `git push --force-with-lease`
- 브랜치 삭제 (`git branch -D`, 원격 브랜치 삭제)
- 공개된 커밋 amend / rebase
- `git clean -f`

## Commits

- 작고 원자적인 변경, *단일 목적*
- Imperative mood: "Fix bug" not "Fixed bug"
- 형식: 프로젝트 관례 우선, 없으면 `<type>: <description>`
- Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

좋은 예: `feat: add retry logic for network timeouts`
나쁜 예: `update`, `fix stuff`, `WIP`

## Branches

- main에서 단명(short-lived) feature 브랜치
- 접두사 권장: `feat/`, `fix/`, `refactor/`, `docs/`
- 머지 후 삭제

## Pull Requests

PR 생성은 `/pr-create` 스킬이 처리한다. 수동 작성 시:

- One feature per PR
- 새 브랜치 첫 푸시는 `-u` 플래그
- *전체 커밋 이력*을 분석한다 — 최신 커밋만 보지 말 것. `git diff <base>...HEAD` 로 전체 확인.
- 본문 구성:
  1. **Summary** — 1~3 bullet, "왜" 중심
  2. **Test plan** — 체크리스트로 검증 단계
  3. **Screenshots** — UI 변경 시

## Implementation Workflow

각 단계의 도구·세부 규약은 링크된 파일이 source.

1. **Plan First** → `rules/claude-code.md#plan-mode--계획-모드`
2. **Implementation** → 신규 기능은 테스트 먼저 (`rules/testing.md`)
3. **Self-review** → `git diff` 확인, 디버그 코드·`console.log`·임시 TODO 제거
4. **Validate** → `/validate` 스킬 또는 프로젝트의 lint/test 명령
5. **Commit & Push** → *사용자 명시 요청 후*에만

## Anti-Patterns

git 관련 안티패턴은 `rules/anti-patterns.md#git--deployment` 가 source.
