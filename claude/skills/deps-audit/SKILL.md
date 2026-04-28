---
name: deps-audit
description: Audit dependencies for vulnerabilities and outdated versions, apply safe updates. 의존성 취약점·구버전 감사 후 안전한 업데이트 자동 적용.
allowed-tools: Read, Edit, Bash, Grep, Glob
---

# Dependency Audit

**한국어로 응답. 코드·명령어는 원문 유지** (`rules/language.md`).

의존성의 보안 취약점·구버전을 감지하고 *안전한 업데이트*는 자동 적용, *위험한 업데이트*는 사용자 결정에 맡긴다. PM 자동 감지는 `validate` 스킬을 *유일한 source* 로 한다.

## Philosophy

- **보안 우선** — CVE / 알려진 취약점은 다른 변경보다 먼저
- **semver 기반 분리** — patch/minor 는 보통 안전, major 는 위험 — 자동 vs 수동 결정 기준
- **검증 필수** — 업데이트 후 `/validate` 통과해야 완료

## Process

### Step 1: Detect Project Type & Package Manager

`validate` 스킬의 PM 감지 로직을 그대로 사용한다 (`$PM` 변수). 추가로 다른 언어 PM 감지:

| 파일 | PM | Audit 명령 |
|------|------|-----------|
| `package.json` + `pnpm-lock.yaml` | pnpm | `pnpm audit --json` |
| `package.json` + `yarn.lock` | yarn | `yarn audit --json` |
| `package.json` + `bun.lockb` | bun | `bun pm audit` |
| `package.json` (그 외) | npm | `npm audit --json` |
| `pyproject.toml` / `requirements.txt` | pip | `pip-audit --format json` |
| `Pipfile` | pipenv | `pipenv check` |
| `poetry.lock` | poetry | `poetry export | pip-audit` |
| `go.mod` | go | `govulncheck ./...` |
| `Cargo.toml` | cargo | `cargo audit --json` |
| `Gemfile.lock` | bundler | `bundle audit check` |

**도구가 설치되지 않았으면 SKIP** + 보고서에 "tool not installed" 명시.

### Step 2: Run Security Audit

```bash
# 예: Node.js
$PM audit --json > audit.json 2>&1 || true

# 예: Python
pip-audit --format json > audit.json 2>&1 || true

# 예: Go
govulncheck ./... > audit.txt 2>&1 || true

# 예: Rust
cargo audit --json > audit.json 2>&1 || true
```

결과를 파싱하여 *severity* 별로 분류:

| Severity | 처리 |
|----------|------|
| CRITICAL / HIGH | 즉시 수정 후보. 사용자에게 강조 표시 |
| MODERATE / MEDIUM | 가능하면 수정 |
| LOW / INFO | 보고만 |

### Step 3: Check Outdated (security 외 일반 갱신)

```bash
# Node.js
$PM outdated --json > outdated.json 2>&1 || true

# Python (pip)
pip list --outdated --format=json > outdated.json 2>&1 || true

# Go
go list -m -u all > outdated.txt 2>&1 || true
```

### Step 4: Classify by semver

각 업데이트를 다음 분류:

| 분류 | 정의 | 적용 정책 |
|------|------|----------|
| **patch** | x.y.Z 변경 | *안전* — 자동 적용 후보 |
| **minor** | x.Y.z 변경 | *대체로 안전* — 자동 적용 후보 (단 사용자가 보수적이면 확인) |
| **major** | X.y.z 변경 | *위험* — 항상 사용자 확인. CHANGELOG·migration guide 확인 필요 |
| **pre-release** | -alpha/-beta/-rc | 사용자 명시 요청 시에만 |

**보안 패치는 분류와 무관하게 우선** — major 라도 보안 수정이라면 별도 표기.

### Step 5: Present Findings (사용자 확인 전)

```
## Dependency Audit 결과

### 🔴 보안 취약점 ({N}건)
| Package | Current | Patched | Severity | CVE |
|---------|---------|---------|----------|-----|
| ... | ... | ... | HIGH | CVE-2024-... |

### 🟡 안전한 업데이트 (patch/minor, {N}건)
| Package | Current | Latest | Type |
|---------|---------|--------|------|
| ... | 1.2.3 | 1.2.5 | patch |
| ... | 2.4.0 | 2.5.1 | minor |

### 🟠 Major 업데이트 ({N}건 — 사용자 결정)
| Package | Current | Latest | Breaking changes? |
|---------|---------|--------|-------------------|
| ... | 3.x | 4.x | (CHANGELOG 확인 필요) |

다음 중 진행할 항목을 알려주세요:
- a) 보안 취약점만 수정
- b) 보안 + 안전한 업데이트 (patch/minor)
- c) 모두 (major 포함, 각 CHANGELOG 확인 후)
- d) 특정 항목만 (목록 지정)
```

### Step 6: Apply Updates (선택된 항목만)

```bash
# 예: Node.js — 안전 업데이트
$PM update <package1> <package2>

# 또는 lockfile 갱신
$PM install

# Python
pip install --upgrade <package>

# Go
go get -u <package>
go mod tidy
```

**한 번에 모든 패키지 일괄 업데이트 금지** — 그룹별로 단계적 적용 (각 단계마다 검증).

### Step 7: Validate

각 업데이트 그룹 적용 후 `/validate` 호출:

- Lint / Typecheck / Test 모두 통과해야 다음 그룹
- 실패하면 *해당 그룹 롤백* 후 사용자에게 보고

```bash
# 롤백 (Node.js 예시)
git checkout <package-manifest> <lockfile>
$PM install
```

### Step 8: Final Report

```
## Audit Report

### 적용됨
- {N} 보안 취약점 수정
- {N} 안전한 업데이트 (patch/minor)

### 보류 (사용자 결정 필요)
- {N} major 업데이트
- {N} 도구 미설치로 SKIP

### Validation
- /validate: PASS
- 변경 파일: package.json, pnpm-lock.yaml
```

이 결과를 *별도 PR* 로 분리한다 (다른 변경과 섞지 않음).

## Safety Rules

| Rule | 이유 |
|------|------|
| 한 번에 모든 dep 업데이트 금지 | 어느 게 깨뜨렸는지 추적 불가 |
| Major 자동 적용 금지 | Breaking change 가능성 |
| 업데이트 후 validate 필수 | 빌드·테스트가 깨지면 즉시 인지 |
| 보안 패치는 별도 PR | 긴급도 다름 + 빠른 머지 필요 |
| pre-release 자동 적용 금지 | 안정성 미보장 |

## Anti-Patterns

- Do NOT `npm update` 류로 일괄 업데이트
- Do NOT major 버전을 사용자 확인 없이 자동 적용
- Do NOT lockfile 만 변경하고 manifest 안 맞춤
- Do NOT audit 결과를 검증 없이 신뢰 (false positive 가능 — 사용자에게 표시)
- Do NOT 의존성 업데이트 PR 에 다른 변경 섞기
- Do NOT 도구 미설치 시 무시 — 보고서에 명시
