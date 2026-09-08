---
name: validate
description: Run lint, typecheck, and tests. Fix issues at root cause; stop and report when unfixable. 린트, 타입체크, 테스트 실행. 문제 자동 수정, 수정 불가 시 보고.
---

# Validate

저장소의 lint·타입 검사·테스트를 실행하고 승인된 범위의 실패 원인을 수정한다. 변경은 AGENTS.md 의 Surgical Changes, 실패 분류는 `skills/testing-rules/SKILL.md#failure-triage--실패-분류`를 따른다.

## 검사 선택

- 저장소 지침·CI·manifest·스크립트를 먼저 읽고 실제 설정된 명령을 찾는다. 파일 확장자만으로 검사기를 가정하지 않는다.
- Node.js는 `packageManager`와 lockfile을 대조한다. `pnpm-lock.yaml`은 pnpm, `yarn.lock`은 Yarn, `bun.lock`/`bun.lockb`는 Bun, `package-lock.json`은 npm의 근거다. 충돌하면 저장소 지침·CI를 확인한다.
- Python·Go·Rust·shell도 기존 테스트·Makefile·스크립트를 찾는다. `pyproject.toml`이나 패키지 그래프가 없다는 이유로 검사가 없다고 판단하지 않는다.
- 설정되지 않은 검사는 `SKIP (not configured)`로 구분한다. 새 검사기를 설치해 범위를 넓히지 않는다.

## 실행 전

1. `git status --short`로 기존 변경을 확인한다.
2. runtime·package manager 버전과 의존성 설치 상태를 검사한다.
3. 검사가 의존성 설치·삭제·lockfile 변경을 요구하면 원인을 확인하고 기존 권한 범위에서 처리한다. 임의의 전역 도구나 다운로드형 fallback으로 결과를 왜곡하지 않는다.
4. 운영 데이터·사용자 데이터에 영향을 주지 않는 격리된 환경을 사용한다.

## 실행과 수정

- 요청 범위와 위험에 맞는 검사를 실행한다. 독립적인 검사는 병렬 처리하되 같은 DB·출력 경로를 공유하면 순서대로 실행한다.
- 실패 출력·관련 구현·기대 계약을 읽고 공통 원인과 연쇄 실패를 구별한다.
- 구현의 회귀는 구현에서 수정한다. 규칙·테스트의 오류가 입증된 경우에만 설정이나 기대값을 고친다.
- `any`, `@ts-ignore`, skip, timeout 증가만으로 실패를 가리지 않는다. 필요한 예외는 근거와 범위를 명시한다.
- 수정 후 관련 검사를 다시 실행한다. 새로운 변경·실패·미해결 위험이 있을 때만 검사를 확대하거나 반복한다.
- 외부 의존·미설치 도구 등으로 진행할 수 없으면 해당 검사의 원인과 필요한 조건을 보고한다. 독립적으로 가능한 검사는 계속한다.

## 완료 보고

검사별 PASS·FAIL·SKIP과 실행 명령, 수정한 원인, 미검증 위험을 짧게 보고한다. 일부 실패·미실행이 있으면 전체 검증 완료로 표현하지 않는다. 검증 전후 diff를 비교해 의도하지 않은 변경이 없는지 확인한다.
