---
name: commit-push
description: Create git commit and push to remote. 커밋 생성 후 리모트에 푸시.
allowed-tools: Read, Bash, Grep, Glob
disable-model-invocation: true
---

# Commit and Push

명시적으로 요청한 변경을 커밋하고 원격에 푸시한다. 커밋은 `skills/commit/SKILL.md`, Git 안전은 `rules/git-workflow.md`를 따른다.

## Workflow

1. 미커밋 변경이 있으면 `commit` 절차를 수행한다. 이미 커밋된 변경만 푸시하는 요청이면 이 단계를 생략한다.
2. `git branch --show-current`, `git status -sb`, upstream·remote를 확인한다. 푸시 대상과 원격에 없는 커밋 전체가 요청 범위인지 검토한다.
3. 최신 원격 상태가 필요하면 fetch한 뒤 차이를 확인한다. 다른 커밋이 섞여 있거나 대상이 불명확하면 푸시 전에 해결한다.
4. 기존 upstream이 있으면 일반 push를 사용한다. 신규 브랜치는 대상 원격을 확인한 뒤 `git push -u <remote> <branch>`로 설정한다.
5. push가 거부되면 원인을 조사한다. force push·공개 이력 재작성은 별도 명시적 허가 없이는 수행하지 않는다.
6. `git status -sb`와 최근 커밋으로 결과를 확인하고 원격·브랜치·커밋을 보고한다.

검증 결과는 커밋 단계에서 확인한다. 같은 변경에 대한 검사를 이유 없이 반복하거나 이미 받은 푸시 권한을 다시 묻지 않는다.
