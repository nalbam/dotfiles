---
name: docs-sync
description: Verify docs against code and fix gaps. 코드↔문서 정합 검증·수정, 문서 동기화, 문서 갱신. 읽고 파악만 하려면 docs-read.
---

# Documentation Sync

**한국어로 응답. 코드·명령어는 원문 유지** (AGENTS.md 의 Language).

코드와 문서를 대조해 틀린 문서를 찾아 고친다. 문서 수정도 AGENTS.md 의 Surgical Changes 를 따른다 — 요청 외 인접 문서를 임의로 손보지 않는다.

## Philosophy

- **문서는 코드의 진실을 반영한다** — 코드와 다른 문서는 문서가 없는 것보다 해롭다
- **빠진 것보다 틀린 것이 먼저다** — 정확성 교정이 항상 최우선
- **양은 목표가 아니다** — 정확하게, 장황하지 않게, 꼭 필요한 내용만. 의미 없는 내용은 삭제가 개선이다
- **삭제는 한 번 더 생각한다** — 코드 부재를 입증하고, 의도적으로 남긴 것이 아닌지 자문한 뒤 지운다
- **현재 상태만 기록한다** — 변경 이력·시행착오는 git 의 몫 (AGENTS.md 의 Anti-Patterns — 현재 상태만 기록)

## Scope

- **대상**: 루트 안내 문서 (`README.md`·`AGENTS.md`·`CONTRIBUTING.md` 등), `docs/` 전체
- **제외**: docstring·코드 주석·CHANGELOG — 명시 요청 시에만
- **경계**: 문서 읽고 파악만 → `/docs-read`. 코드 자체의 품질 → `/code-audit`. 이 스킬은 코드↔문서 *정합*만 다룬다.

## Rules

- **생성된 문서는 직접 수정하지 않는다** — 생성 마커·"do not edit" 안내가 있으면 소스를 고치고 재생성한다
- **새 문서 파일은 명시 요청 시에만 생성** — 담을 곳 없는 항목은 Gap Report 에 제안으로만 남긴다
- **문서 구조는 프로젝트 관례 우선** — 루트 vs `docs/` 배치를 임의로 재편하지 않는다 (재배치는 요청 시에만)
- Single source of truth — 같은 내용을 두 곳에 쓰지 않고 링크한다
- Exclude patterns 적용 후 스캔

## Exclude Patterns

dependency / build / cache / VCS / IDE / 테스트 산출물은 제외한다. 전체 목록은 `code-audit` 스킬 (`~/.agents/skills/code-audit/SKILL.md`) 의 *Exclude Patterns* 표가 *유일한 source* 다.

## Process

### 1. Inventory — 코드·문서 인벤토리

- 코드: public API·함수·CLI 플래그·환경변수·설치/실행 명령 추출
- 문서: 루트 안내 문서·`docs/*` 에서 문서화된 항목 추출
- 대형 저장소는 인벤토리 수집을 subagent 에 위임해 메인 컨텍스트를 보호한다

### 2. Verify — 정확성 검증

사용자가 그대로 복사해 쓰는 것부터 검증한다: 설치·실행 명령 → CLI 플래그·환경변수 → API 시그니처·기본값 → 아키텍처 서술.

문서화된 각 항목에 대해:
1. 대응 코드가 실제 존재하는가
2. 코드가 문서대로 동작하는가 (파라미터·기본값·예시 포함)
3. 불일치마다 원인을 남긴다 — 코드 변경 후 미갱신 / 계획 기반 서술 / 의존성 변경

### 3. Report — 갭 보고 후 사용자 확인

모든 항목에 문서 위치와 코드 근거(file:line)를 붙인다.

```
## Gap Report

Inaccurate (최우선):
- README.md:42 "MAX_RETRY=3" ↔ src/config.ts:17 은 5 — 원인: 코드 변경 후 미갱신

Orphaned (삭제 후보 — 코드 부재 근거 필수):
- docs/API.md:88 `/api/legacy` — 라우트 정의 없음 (grep 으로 확인)

Undocumented (사용자 결정):
- src/config.ts:30 `parseConfig()` — 문서화 여부 결정 필요
```

**보고 후 멈춘다** — 수정 범위(특히 삭제와 Undocumented 처분)는 사용자 확인 후 진행한다.

### 4. Update — 승인된 범위만 수정

1. Inaccurate 교정 (최우선)
2. Orphaned 제거 — 삭제 직전 한 번 더 확인: 근거가 여전히 유효한가, 의도적으로 남긴 문서는 아닌가
3. 승인된 Undocumented 추가 — 간결하게, 꼭 필요한 내용만

### 5. Verify — 수정 검증

- 링크: 대상 파일·앵커 존재 확인
- 예시: read-only 명령만 실행해 확인. 상태를 바꾸는 명령은 실행하지 않고 코드 대조로 검증
- 수정한 서술을 코드와 재대조

**종료 조건**: Inaccurate 0 · Orphaned 0 · Undocumented 전부 사용자 결정 반영.

## Anti-Patterns

- 문서가 맞다고 가정하지 않는다 — 코드로 검증한다
- 자명한 코드·자주 바뀌는 구현 세부는 문서화하지 않는다
- 코드를 문서에 복사하지 않는다 — 참조한다
- 분량 증가를 개선으로 착각하지 않는다 — 기준은 정확·간결
- 사용자 확인 없이 문서 내용을 삭제하지 않는다
