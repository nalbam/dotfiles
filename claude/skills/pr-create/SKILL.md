---
name: pr-create
description: Create pull request with proper format. PR 생성, 변경사항 분석, PR 메시지 작성.
allowed-tools: Read, Bash, Grep, Glob
disable-model-invocation: true
---

# Create Pull Request

명시적으로 요청한 PR을 생성한다. Git 권한은 `rules/git-workflow.md`, 커밋·푸시가 필요하면 해당 스킬의 절차를 따른다. PR title/body의 공통 형식은 이 파일에서 관리한다.

## Workflow

1. 현재 브랜치·작업 트리·remote·기존 PR을 확인한다. base는 기존 PR, 원격 기본 브랜치, 저장소 관례로 판단하며 `main`을 가정하지 않는다.
2. 실제 base 대비 전체 diff와 커밋 목록을 읽는다. 변경된 코드의 호출자·영향·호환성·검증 결과를 확인한다.
3. 저장소가 요구하는 검증을 확인한다. 변경 이후 유효한 결과는 재사용하고, 추가 검사는 `skills/validate/SKILL.md`를 따른다. 새 회귀·원인 불명의 실패는 먼저 해결한다. 알려진 기존 실패·환경 제약은 숨기지 않는다.
4. base가 앞섰다는 이유만으로 rebase하지 않는다. 충돌 등 필요성이 있으면 확인하고, 공개 이력 재작성·force push는 명시적 허가가 있을 때만 수행한다.
5. 저장소 PR 템플릿에 맞춰 설명을 작성한다. 요청 범위의 커밋만 푸시됐는지 확인한 뒤 PR을 생성한다.
6. `gh pr view <number>`로 제목·본문·base/head를 확인하고 URL을 보고한다.

## PR Title / Body

프로젝트 관례가 없으면 제목은 `<type>(<scope>): <subject>`로 쓴다. scope는 선택이며 type은 `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `perf`, `ci` 중 목적에 맞게 고른다.

본문은 해결한 문제와 최종 동작을 먼저 설명한다. 간단한 변경은 한두 문장과 검증 결과로 충분하다. 복잡할 때만 다음 항목으로 나눈다.

- Summary: 문제와 결과
- Changes: 리뷰어가 알아야 할 주요 변경과 이유
- Breaking Changes: 호환성 영향과 이행 방법이 있을 때만
- Test Plan: 실제 실행 결과와 미실행 항목을 구분
- Screenshots: UI 변경을 설명하는 데 도움이 될 때만

추측·대화 이력·폐기한 접근·귀속 푸터를 넣지 않는다. 알려진 위험과 제한은 관련 내용 옆에 명시한다.

## 명령 전달

여러 줄 본문은 임시 파일에 정확한 줄바꿈으로 작성하고 `--body-file`로 전달한다. 동적 본문을 셸 코드에 보간하지 않는다.

```bash
gh pr create --base <base> --head <head> --title "<title>" --body-file <body-file>
```
