# Git Workflow

## CRITICAL: Commit & Push Policy

**NEVER commit or push without explicit user permission.**

- 사용자가 명시적으로 요청할 때만 `git commit` 실행
- 사용자가 명시적으로 요청할 때만 `git push` 실행
- 코드 변경 후 자동으로 커밋하지 않음
- "커밋해", "커밋하세요", "commit" 등 명확한 지시가 있을 때만 수행

## Commits

- Small, atomic changes with single purpose
- Imperative mood: "Fix bug" not "Fixed bug"
- Format: "verb + what + why if not obvious"
  - Good: "Add retry logic to handle network timeouts"
  - Bad: "Update code", "Fix stuff", "WIP"

### Commit Message Format

```
<type>: <description>

<optional body>
```

Types: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`

## Branches

- Short-lived feature branches from `main`
- 이름 규칙: `feat/`, `fix/`, `refactor/`, `docs/` 접두사 권장
- 머지 후 삭제

## Pull Requests

### 작성 시

- One feature per PR
- 자기 리뷰 후 제출
- 설명, 테스트 단계, 스크린샷(UI 변경 시) 포함
- 전체 커밋 이력 분석 (최신 커밋만 보지 말 것)
- `git diff [base-branch]...HEAD`로 모든 변경사항 확인
- 새 브랜치는 `-u` 플래그로 푸시

### PR 본문 구성

1. **Summary**: 1~3 bullet, "왜" 중심
2. **Test plan**: 체크리스트 형태로 검증 단계 명시
3. **Screenshots**: UI 변경이 있으면 첨부

## Feature Implementation Workflow

1. **Plan First** (`rules/claude-code.md#plan-mode` 참조)
   - planner/Plan 서브에이전트로 계획 수립
   - 의존성·리스크 식별
   - 단계로 분해

2. **Implementation**
   - 신규 기능의 테스트부터 작성
   - 구현 후 테스트로 검증
   - 테스트 전략 상세: `rules/testing.md`

3. **Code Review**
   - code-reviewer 서브에이전트로 품질·보안 검토
   - CRITICAL, HIGH 이슈는 반드시 수정
   - MEDIUM 이슈는 가능한 한 수정

4. **Commit & Push**
   - Conventional Commits 형식
   - 상세한 커밋 메시지

## Code Review & Collaboration

### Before Submitting

- 자기 diff 먼저 리뷰
- 테스트·린트 통과 확인
- 디버그 코드, `console.log`, TODO 제거

### As Reviewer

- 로직, 엣지 케이스, 유지보수성에 집중
- 비판이 아닌 질문 형태로 피드백
- 이해·검증한 변경만 승인

### Receiving Feedback

- 신속하고 전문적으로 응답
- 자신의 근거를 설명하되 더 나은 접근에 열려 있을 것
- 해결한 대화만 "resolved" 마킹

## Best Practices

- Never commit secrets, binaries, or generated files
- Avoid force push to shared branches
- Rebase local branches, merge to `main`
- 훅 우회 금지 (`--no-verify`, `--no-gpg-sign` 등)
