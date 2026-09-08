# Git Workflow

## Git Safety

- **사용자의 명시적 지시 없이 commit·push하지 않는다.** 코드 수정 요청은 커밋 허가가 아니다.
- `commit`·`commit-push`·`pr-create` 요청에 필요한 권한만 사용한다. 커밋 허가를 push 허가로 확대하지 않는다.
- 기존 작업 트리의 다른 변경을 되돌리거나 본인 변경과 섞지 않는다.
- `git reset --hard`, 파일 변경 폐기, force push, 브랜치 삭제, 공개된 커밋 amend/rebase, `git clean -f`는 사용자가 분명히 요청한 경우에만 수행한다.
- 훅·서명 우회(`--no-verify`, `--no-gpg-sign`, `--no-signoff`)는 사용자가 분명히 요구한 경우에만 사용한다.
- 파괴적 작업은 영향 범위를 짧게 보고한다. 이미 받은 권한과 범위는 다시 확인하지 않는다.
- 시크릿을 커밋하지 않는다. 바이너리·생성 파일은 저장소가 추적하는 배포 자산인지 확인한다.

## Commits

- 한 커밋에 한 목적만 담고, 메시지는 프로젝트 관례를 따른다. 관례가 없으면 영어 명령형 `<type>: <subject>`를 사용한다.
- 커밋 메시지·PR 본문에 `Co-Authored-By`, `Generated with`, 도구·모델 귀속 트레일러·배지를 넣지 않는다. 과거 귀속 푸터를 관례로 삼지 않는다.
- 커밋 절차는 `skills/commit/SKILL.md`, 푸시 절차는 `skills/commit-push/SKILL.md`를 따른다.

## Branches / Pull Requests

- 브랜치 전략과 PR 템플릿은 저장소 관례를 따른다.
- PR은 실제 base와의 전체 diff·커밋 목록을 분석한다. 최신 커밋만 요약하지 않는다.
- PR title/body 형식은 `skills/pr-create/SKILL.md`, 기존 설명 갱신은 `skills/pr-summary/SKILL.md`를 따른다.
