# Skills

작업에 맞는 스킬을 선택할 때 사용하는 안내다. 공통 작업·문서 작성 원칙은 [claude/CLAUDE.md](../claude/CLAUDE.md), 언어·Git·보안은 [claude/rules/](../claude/rules/)에서 관리한다. 스킬에는 작업별 절차와 비자명한 제약만 둔다.

| 요청 | 스킬 |
|------|------|
| 온보딩·프로젝트 개요 | [docs-read](../claude/skills/docs-read/SKILL.md) (읽기 전용) |
| 변경 커밋 | [commit](../claude/skills/commit/SKILL.md) |
| 커밋 후 푸시 | [commit-push](../claude/skills/commit-push/SKILL.md) |
| 변경분·PR 리뷰 | 도구 내장 리뷰 명령: Claude Code `/code-review`, Codex `/review` |
| 저장소 전체 감사 | [code-audit](../claude/skills/code-audit/SKILL.md) (읽기 전용) |
| PR 생성·설명 갱신 | [pr-create](../claude/skills/pr-create/SKILL.md)·[pr-summary](../claude/skills/pr-summary/SKILL.md) |
| CodeRabbit 평가·수정·resolve | [resolve-coderabbit](../claude/skills/resolve-coderabbit/SKILL.md) |
| 코드와 문서의 정합 확인·구조·표현 개선 | [docs-sync](../claude/skills/docs-sync/SKILL.md) |

에이전트는 책임과 검토 관점, 스킬은 반복 절차를 정의한다. 개발 전 과정의 역할 선택과 인계는 [Development Agents](DEVELOPMENT_AGENTS.md)를 참고한다.

## 관리

- `name`은 디렉터리명과 맞추고 `description`은 적용할 작업을 짧게 설명한다. 일반 원칙을 별도 스킬로 복제하지 않는다.
- `skills/<name>/...`는 세션의 스킬 위치, `references/...`는 해당 스킬 디렉터리, Claude의 `rules/...`는 설정 루트 기준이다.
- 선택 가능성과 실행 권한은 별개다. 외부 작업의 권한을 스킬 로딩만으로 추정하지 않는다.
- Claude·OpenCode의 `disable-model-invocation: true`와 Codex의 `policy.allow_implicit_invocation: false`는 명시 호출 정책이다. Codex의 `agents/openai.yaml`은 직접 관리하며 Claude 원본의 정책과 맞춘다.
- `allowed-tools`는 권한 사전 허용 목록이므로 단순 도구 설명으로 추가하지 않는다. 읽기 전용 스킬은 본문에도 상태 변경 금지를 명시한다.
- 원본은 `claude/skills/`다. 수정 후 `python3 scripts/gen-ai-tools.py`와 `--check`를 실행해 `codex/skills/`와 `opencode/skills/`를 갱신한다. 생성 파일은 직접 편집하지 않는다.
- 스킬 디렉터리에는 스킬 파일(`SKILL.md`, 참조 Markdown, 직접 관리하는 Codex `agents/openai.yaml`)만 두고 안내 문서는 두지 않는다. OpenCode는 스킬 디렉터리 최상위의 `*.md`도 스킬로 등록하므로 안내 문서는 이 파일처럼 `docs/`에 둔다.
