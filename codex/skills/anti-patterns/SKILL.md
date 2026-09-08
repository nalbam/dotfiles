---
name: anti-patterns
description: 자주 빠지는 함정 카탈로그와 'Working If' 자가 점검 척도 — PR·커밋 전 자가 리뷰용. Anti-pattern catalog and self-check scale.
---

# Anti-Patterns

완료 전 필요할 때 확인하는 자가 리뷰 기준이다. 실제 결함과 요청 범위 이탈을 찾고 취향 차이를 문제로 만들지 않는다.

## Code Quality

- 기존 정의·호출 지점·유틸리티를 확인하지 않고 새 구현을 추가한다.
- 오류를 성공 값으로 숨기거나 원인 없이 catch·재시도만 추가한다.
- 문서에 현재 계약 대신 에이전트의 추측·시행착오를 남긴다.

## Surgical / 외과적 변경 위반

요청 밖의 스타일 통일·이름 변경·추상화·dead code 정리를 섞는다. 판단 기준은 AGENTS.md 의 Surgical Changes 를 따른다.

## Think Before Coding

결과를 바꿀 모호함을 숨기거나, 반대로 되돌릴 수 있는 세부 선택까지 매번 사용자에게 묻는다.

## Goal-Driven Execution

종료 조건 없이 시작하거나 검증 근거 없이 완료를 선언한다.

## Problem Solving

첫 가설을 사실로 단정하거나 같은 실패에 근거 없는 재시도를 반복한다.

## Testing

- 테스트를 약화하거나 skip 처리해 실패를 감춘다.
- 구현의 사본을 테스트하거나 통합 흐름 전체를 mock한다.
- 통과한 검사를 변경·새로운 근거 없이 반복한다.

## Git & Deployment

- 허가 없이 commit·push·force push·변경 폐기·훅 우회를 수행한다.
- 시크릿·무관한 파일을 포함하거나 최신 커밋만 보고 PR을 설명한다.
- 이미 받은 권한을 스킬 절차를 이유로 반복 요청한다.

## Communication & Process

- 없는 도구·모델·설치 상태를 가정한다.
- 사용자 요청보다 스킬의 고정 절차·보고서 형식을 우선한다.
- 실행하지 않은 검사를 통과했다고 쓰거나 추측을 사실로 보고한다.

## Working If / 잘 작동하고 있다는 신호

요청에 필요한 diff만 남고, 검증 근거와 남은 위험을 설명할 수 있으며, 사용자가 이미 결정한 일을 다시 묻지 않는다.
