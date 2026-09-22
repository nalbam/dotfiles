---
name: commit
description: Commit requested changes using repository conventions. 요청한 변경을 커밋하며 push는 하지 않음.
---

# Create Commit

명시적으로 요청한 변경을 conventional 형식으로 커밋한다. Git 권한·기존 변경 보존·귀속 푸터 금지는 AGENTS.md 의 Git Safety를 따른다. 이 스킬은 push하지 않는다.

## Workflow

1. `git status`, `git diff`, `git diff --cached`, 최근 커밋을 확인한다. 각 변경의 목적·호출 맥락을 이해하고 요청 밖 파일·시크릿·임시 디버그 코드를 제외한다.
2. 저장소가 요구하는 검증과 이미 실행한 결과를 확인한다. 검증 이후 변경이 없으면 결과를 재사용한다. 필요한 검사 선택은 `skills/validate/SKILL.md`를 따른다.
3. 새 회귀나 원인 불명의 실패가 있으면 원인·영향을 보고하고 커밋을 보류한다. 기존 실패·환경 제약은 근거와 위험을 밝히고 사용자가 이미 그 상태로 진행하도록 지시했는지 확인한다. 커밋 작업에 무관한 코드 수정을 섞지 않는다.
4. index에 이미 있는 무관한 변경을 먼저 구분한다. 파일 일부만 요청 범위라면 해당 hunk만 stage한다. 기존 staging을 임의로 해제하지 말고, 분리할 수 없으면 커밋 전에 범위를 확인한다. `git diff --cached` 전체가 요청 범위인지 재확인한다.
5. 훅·서명을 우회하지 않고 커밋한다. 실패하면 원인을 확인하고 사용자 변경을 보존한다.
6. `git status`와 `git log -1 --oneline`으로 커밋과 남은 변경을 확인한다.

## Commit Message Format

프로젝트 관례를 우선한다. 관례가 없으면 영어 명령형 `<type>: <subject>`를 사용한다. scope는 구분에 유용할 때만 넣고 제목을 간결하게 쓴다. 본문은 이유·제약 설명이 필요할 때만 추가한다.

종류: `feat`, `fix`, `refactor`, `docs`, `test`, `chore`, `perf`, `ci`.

```bash
git commit -m "docs: simplify shared coding instructions"
```

여러 줄 본문은 임시 파일에 작성해 `git commit -F <message-file>`로 전달한다.
