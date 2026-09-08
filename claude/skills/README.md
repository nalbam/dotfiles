# Skills

스킬은 반복 작업의 절차·판단 기준을 제공하고, 에이전트는 위임받은 작업을 수행한다. 사용 가능한 기능과 위임 권한은 현재 세션을 기준으로 확인한다.

## 실행 스킬

| 요청 | 스킬 |
|------|------|
| 새 Next.js 프로젝트 생성 | `nextjs-init` |
| 온보딩·프로젝트 개요 | `docs-read` (읽기 전용) |
| 변경 커밋 | `commit` |
| 커밋 후 푸시 | `commit-push` |
| lint·타입·테스트 실행·수정 | `validate` |
| 변경분·PR 리뷰 | `code-review` (읽기 전용) |
| 저장소 전체 감사 | `code-audit` (읽기 전용) |
| PR 생성·설명 갱신 | `pr-create`·`pr-summary` |
| CodeRabbit 평가·수정·resolve | `resolve-coderabbit` |
| 코드와 문서의 정합 확인·수정 | `docs-sync` |

## 참조 스킬

| 주제 | 스킬 |
|------|------|
| 변경 범위·구조·오류·문서화 | `coding-style` |
| 요구 해석·종료 조건·원인 조사 | `problem-solving` |
| 테스트 선택·품질·실패 분류 | `testing-rules` |
| 도구·계획·위임·병렬 처리 | `claude-code-usage` |
| 완료 전 자가 리뷰 | `anti-patterns` |

## 관리 규칙

- 공통 기본 지침은 `../CLAUDE.md`, 언어·Git·보안 상세는 `../rules/`에서 관리한다. 스킬에는 해당 작업의 절차와 비자명한 제약만 둔다.
- 각 `<name>/SKILL.md`가 절차의 원본이다. 공통 내용은 참조한다: 탐색 제외 → `code-audit`, 검사 선택 → `validate`, PR 형식 → `pr-create`.
- 스킬 본문의 `skills/...`·`rules/...`는 Claude 설정 루트 기준이다. 스킬 내부 `references/...`는 해당 스킬 디렉터리 기준이다.
- 사용자 요청·기존 권한을 우선한다. 스킬을 읽었다는 이유로 commit·push·외부 게시 권한을 추정하거나 이미 받은 권한을 반복 확인하지 않는다.
- frontmatter의 `name`은 디렉터리명과 맞추고, `description`은 기능·적용 시점·혼동하기 쉬운 인접 작업과의 경계를 간결하게 설명한다.
- `allowed-tools`는 실제 사용하는 도구를 나열한다. 읽기 전용 경계는 본문에도 명시한다. Bash가 있으면 Write·Edit 제외만으로 쓰기가 차단된다고 가정하지 않는다.
- 기존 `disable-model-invocation` 정책은 유지한다. 스킬의 선택 가능성과 외부 작업 실행 권한은 별개다.
- 형식·단계 수를 고정하지 않는다. 긴 절차는 필요할 때 읽는 `references/`로 나누되 불필요한 파일은 추가하지 않는다.
- 위임 시 필요한 지침·범위·산출물을 전달하고 메인이 최종 검증을 책임진다.
- Codex 미러는 이 디렉터리에서 생성한다. 수정 후 `python3 scripts/gen-codex-skills.py`와 `--check`를 실행한다. 생성된 Markdown은 직접 편집하지 않는다.
