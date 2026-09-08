---
name: pr-summary
description: Analyze all PR changes and update PR description with accurate summary. PR 변경사항 분석 후 정확한 요약으로 PR 설명 업데이트.
allowed-tools: Read, Bash, Grep, Glob
disable-model-invocation: true
argument-hint: [pr-number]
---

# PR Summary Update

기존 PR 설명을 최종 변경사항에 맞게 갱신한다. 형식은 `skills/pr-create/SKILL.md`를 따르고 Git 권한은 `rules/git-workflow.md`를 따른다.

## 대상과 맥락

PR 번호 인자: `$ARGUMENTS`

번호가 없으면 현재 브랜치의 PR을 조회한다. 대상이 여러 개이거나 확인되지 않으면 사용자에게 묻는다.

```bash
gh pr view <number> --json title,body,baseRefName,headRefName,commits,files
gh pr diff <number>
```

## 분석과 갱신

1. 기존 본문과 전체 diff·커밋 목록을 읽고 필요한 파일 맥락을 확인한다. 최신 커밋이나 통계만으로 요약하지 않는다.
2. 작성자의 메모·이슈·설계 링크·커스텀 섹션을 보존한다. 현재 동작과 충돌하는 내용은 근거에 맞게 갱신한다.
3. 최종 목적·동작·검증·영향을 기준으로 본문을 다시 쓴다. 큰 변경은 모듈·기능별로 묶되 변경 이력을 장황하게 나열하지 않는다.
4. 본문을 임시 파일로 작성하고 `gh pr edit <number> --body-file <body-file>`로 전달한다.
5. 제목 변경이 요청 범위에 포함된 경우에만 제목도 갱신한다. labels·assignees·reviewers 등 무관한 metadata는 보존한다.
6. PR을 다시 조회해 결과를 확인하고 URL과 주요 수정 사항을 짧게 보고한다.
