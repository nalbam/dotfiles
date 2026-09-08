---
name: commit
description: Create git commit with conventional format. 커밋 생성, 변경사항 분석, 커밋 메시지 작성.
allowed-tools: Read, Bash, Grep, Glob
disable-model-invocation: true
---

# Create Commit

명시적으로 요청한 변경을 conventional 형식으로 커밋한다. Git 권한·기존 변경 보존·귀속 푸터 금지는 `rules/git-workflow.md`를 따른다. 이 스킬은 push하지 않는다.

## Workflow

1. `git status`, `git diff`, `git diff --cached`, 최근 커밋을 확인한다. 각 변경의 목적·호출 맥락을 이해하고 요청 밖 파일·시크릿·임시 디버그 코드를 제외한다.
2. 저장소가 요구하는 검증과 이미 실행한 결과를 확인한다. 검증 이후 변경이 없으면 결과를 재사용한다. 필요한 검사 선택은 `skills/validate/SKILL.md`를 따른다.
3. 새 회귀나 원인 불명의 실패가 있으면 원인·영향을 보고하고 커밋을 보류한다. 기존 실패·환경 제약은 근거와 위험을 밝히고 사용자가 이미 그 상태로 진행하도록 지시했는지 확인한다. 커밋 작업에 무관한 코드 수정을 섞지 않는다.
4. 요청에 해당하는 파일만 `git add <paths>`로 stage하고 `git diff --cached`를 다시 확인한다.
5. 훅·서명을 우회하지 않고 커밋한다. 실패하면 원인을 확인하고 사용자 변경을 보존한다.
6. `git status`와 `git log -1 --oneline`으로 커밋과 남은 변경을 확인한다.

## Commit Message Format

프로젝트 관례를 우선한다. 관례가 없으면 scope 없이 영어 명령형 `<type>: <subject>`를 사용하고 제목은 50자 이내로 쓴다. 본문은 이유·제약 설명이 필요할 때만 추가한다.

종류: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.

```bash
git commit -m "docs: simplify shared coding instructions"
```

여러 줄 본문은 임시 파일에 작성해 `git commit -F <message-file>`로 전달한다.
