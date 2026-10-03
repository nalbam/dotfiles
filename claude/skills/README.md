# Skills

작업에 맞는 스킬을 선택할 때 사용하는 안내다. 공통 작업·문서 작성 원칙은 [CLAUDE.md](../CLAUDE.md), 언어·Git·보안은 [rules/](../rules/)에서 관리한다. 스킬에는 작업별 절차와 비자명한 제약만 둔다.

| 요청 | 스킬 |
|------|------|
| 지정 스택으로 새 Next.js 프로젝트 생성 | [nextjs-init](nextjs-init/SKILL.md) |
| Laya 도입·기존 통합 수정 | [laya-integration](laya-integration/SKILL.md) |
| 온보딩·프로젝트 개요 | [docs-read](docs-read/SKILL.md) (읽기 전용) |
| 변경 커밋 | [commit](commit/SKILL.md) |
| 커밋 후 푸시 | [commit-push](commit-push/SKILL.md) |
| lint·타입·테스트 실행·수정 | [validate](validate/SKILL.md) |
| 변경분·PR 리뷰 | [code-review](code-review/SKILL.md) (읽기 전용) |
| 저장소 전체 감사 | [code-audit](code-audit/SKILL.md) (읽기 전용) |
| PR 생성·설명 갱신 | [pr-create](pr-create/SKILL.md)·[pr-summary](pr-summary/SKILL.md) |
| CodeRabbit 평가·수정·resolve | [resolve-coderabbit](resolve-coderabbit/SKILL.md) |
| 코드와 문서의 정합 확인·구조·표현 개선 | [docs-sync](docs-sync/SKILL.md) |

## 관리

- `name`은 디렉터리명과 맞추고 `description`은 적용할 작업을 짧게 설명한다. 일반 원칙을 별도 스킬로 복제하지 않는다.
- `skills/<name>/...`는 세션의 스킬 위치, `references/...`는 해당 스킬 디렉터리, Claude의 `rules/...`는 설정 루트 기준이다.
- 선택 가능성과 실행 권한은 별개다. 외부 작업의 권한을 스킬 로딩만으로 추정하지 않는다.
- Claude의 `disable-model-invocation: true`와 Codex의 `policy.allow_implicit_invocation: false`는 명시 호출 정책이다. `agents/openai.yaml`은 직접 관리하며 두 도구의 정책을 맞춘다.
- `allowed-tools`는 권한 사전 허용 목록이므로 단순 도구 설명으로 추가하지 않는다. 읽기 전용 스킬은 본문에도 상태 변경 금지를 명시한다.
- Codex Markdown은 이 디렉터리가 원본이다. 수정 후 `python3 scripts/gen-codex-skills.py`와 `--check`를 실행한다. 생성 파일은 직접 편집하지 않는다.
