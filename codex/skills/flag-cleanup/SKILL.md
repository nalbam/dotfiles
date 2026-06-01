---
name: flag-cleanup
description: Identify and safely remove stale feature flags, gates, experiments. 활성/비활성이 결정된 feature flag·gate·experiment·staged rollout을 식별하고 안전하게 제거.
---

# Feature Flag Cleanup

**한국어로 응답. 코드·명령어는 원문 유지** (AGENTS.md 의 Language).

활성/비활성이 결정된 feature flag·gate·experiment·staged rollout을 식별하고 *안전한 제거 PR*을 만든다. 변경 작업은 AGENTS.md 의 Surgical Changes 를 따른다 — flag 정리 PR에는 *flag 정리 외* 변경이 섞이지 않는다.

## Philosophy

- **잊혀진 flag 는 영원한 부채** — 정리 안 하면 분기·경로·테스트가 누적
- **flag 제거는 행동 보존** — 현재 *실제 동작* 분기만 남기고 반대 분기를 제거 (동작 변경 X)
- **사용자가 결정** — *후보를 식별*만 한다. 어느 flag 를 제거할지·어느 분기가 활성인지는 사용자 확인

## Detection Patterns

### 자체 flag (가장 흔함)

```
- 환경 변수: process.env.FEATURE_X / os.getenv("FEATURE_X")
- 설정 객체: config.features.X / settings.FEATURES["X"]
- 상수 플래그: const ENABLE_X = true
- 함수 호출: isEnabled("x") / featureFlag.check("x")
```

### 서드파티 SDK

| 서비스 | 호출 패턴 |
|--------|---------|
| LaunchDarkly | `ldClient.variation("flag-key", ...)`, `useFlags()`, `LDClient` |
| GrowthBook | `growthbook.isOn("...")`, `growthbook.getFeatureValue` |
| Statsig | `Statsig.checkGate(...)`, `Statsig.getExperiment(...)` |
| Optimizely | `optimizely.isFeatureEnabled(...)`, `decide()` |
| Unleash | `unleash.isEnabled(...)` |
| ConfigCat | `configCat.getValue(...)` |
| Split | `splitClient.getTreatment(...)` |

## Process

### Step 1: Identify Flag Usages

```bash
# 일반적 패턴 grep — 프로젝트에 맞게 조정
grep -rn -E "(isEnabled|checkGate|featureFlag|isOn|getTreatment|variation)\s*\(" \
  --include="*.{ts,tsx,js,jsx,py,go,rb,kt,swift}" \
  --exclude-dir={node_modules,.git,dist,build,.next}

grep -rn -E "process\.env\.(ENABLE_|FEATURE_|USE_)|os\.(getenv|environ)\(.+(ENABLE_|FEATURE_|USE_)" \
  --include="*.{ts,tsx,js,jsx,py,go}"
```

테스트·설정 파일도 확인:

```bash
grep -rn "feature" --include="*.{yaml,yml,toml,json}" -l
```

### Step 2: Group by Flag Key

각 flag 키별로 사용 위치를 모은다:

```
flag-key-x:
  src/api/route.ts:42
  src/components/Foo.tsx:18
  src/services/handler.py:67
  tests/api.test.ts:91
```

### Step 3: User Confirmation (필수)

*어느 flag 를 정리할지 결정하지 않는다*. 사용자에게 식별 결과를 표로 제시하고 확인 받는다:

```
## 발견된 Feature Flags

| Key | 사용 위치 (개) | 추정 SDK | 비고 |
|-----|--------------|---------|------|
| use-new-checkout | 8 | LaunchDarkly | (분석 필요) |
| enable-v2-api | 3 | env var | 모든 분기에서 enabled=true 처리됨 |
| experiment-banner | 12 | Statsig | (분석 필요) |

각 flag 에 대해 다음을 알려주세요:
1. 현재 *실제* 활성 상태 (on / off / 일부)
2. 정리 의도 (제거 / 유지 / 추후 결정)
3. 활성 분기만 남길 것인지 vs flag 자체를 default 로 둘 것인지
```

### Step 4: Safe Removal (per flag)

사용자가 정리할 flag 와 활성 분기를 확정하면, *flag 1개씩* 제거한다.

#### 4-1. Branch Identification

```typescript
// 예: ENABLE_NEW_CHECKOUT=true 가 활성 결정됨
if (isEnabled("new-checkout")) {
  return newCheckoutFlow(order);   // ← 활성 분기 (남김)
} else {
  return legacyCheckoutFlow(order); // ← 비활성 분기 (제거)
}
```

#### 4-2. Surgical Edit

각 사용 위치에서:

- **활성 분기 코드만 남기고** 조건문·반대 분기·dead import 제거
- 함수 시그니처·호출자에 영향이 없도록 보존
- 무관한 인접 코드는 *손대지 않는다* (AGENTS.md 의 Surgical Changes)
- 발견한 무관 이슈는 *언급만* 하고 별도 작업으로 분리

#### 4-3. Sweep

```bash
# flag key 가 어디에도 없는지 확인
grep -rn "new-checkout" --include="*.{ts,tsx,js,jsx,py,go}"

# Dead import / unused 변수·함수 정리 (이번 변경으로 *발생한* 것만)
```

테스트·설정·문서·환경변수 파일도 확인:

```bash
grep -rn "NEW_CHECKOUT\|new-checkout" \
  --include="*.{yaml,yml,toml,json,md}" \
  -l
```

### Step 5: Validate

`/validate` 스킬 또는 프로젝트의 lint/typecheck/test 명령 실행. 모두 통과해야 다음 flag 진행.

### Step 6: PR per Flag

flag 1개당 PR 1개 (리뷰 가능 단위). PR 본문은 `pr-create` 스킬 형식 사용.

```
## Summary
- Remove `<flag-key>` (이미 100% rollout, <기간> 동안 stable)

## Changes
- 활성 분기 (X) 만 남김
- 비활성 분기·dead code·flag SDK 호출 제거
- 환경변수·설정·테스트 fixture 정리

## Test Plan
- [ ] `/validate` 통과
- [ ] flag 가 코드베이스에 더 이상 없음 (`grep <key>` 결과 없음)
- [ ] 기존 동작 회귀 테스트 통과
```

## Safety Rules

| Rule | 이유 |
|------|------|
| 사용자 확인 없이 flag 제거 금지 | 활성 분기를 잘못 추정할 수 있음 |
| flag 1개 = PR 1개 | 롤백 단위 보존 |
| 분석 후 확신 없으면 사용자에게 환원 | "어느 분기가 활성?"이 불명확하면 멈춤 |
| 외과적 변경 — 무관한 리팩토링 금지 | AGENTS.md 의 Surgical Changes |
| 정리 가능 여부는 *데이터*에 근거 | 롤아웃 모니터링 / 분석 결과 / 사용자 확인 |

## Anti-Patterns

- Do NOT 활성 분기를 추정만으로 결정 — 사용자 확인 필수
- Do NOT 한 PR 에 여러 flag 정리 묶기
- Do NOT flag 제거하면서 무관한 리팩토링·rename·스타일 변경
- Do NOT 환경변수·설정·테스트 fixture 누락 (코드만 정리하고 끝)
- Do NOT flag SDK 의존성을 자동 제거 (다른 flag 가 쓸 수 있음)
- Do NOT "이 flag 는 더 이상 안 쓸 것 같다" 같은 추정으로 진행
