---
name: validate
description: Run lint, typecheck, and tests. Fix issues at root cause; stop and report when unfixable. 린트, 타입체크, 테스트 실행. 문제 자동 수정, 수정 불가 시 보고.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Validate

**한국어로 응답. 코드·명령어는 원문 유지** (`rules/language.md`).

Run lint, typecheck, and tests. Fix failures at their root cause, re-running after each fix until all pass. **수정 불가능한 실패** — 외부 의존(네트워크·미설치 도구·환경) 또는 반복 시도 후에도 변하지 않는 실패 — 는 무시하지 말고 *멈추고* 원인과 잔여 리스크를 사용자에게 보고한다.

Package manager 감지 로직은 이 스킬이 *유일한 source* 다 (다른 스킬은 여기를 참조). 수정은 `rules/coding-style.md#surgical-changes--외과적-변경` 원칙을 따른다 — 실패 원인을 고치되 무관한 코드는 손대지 않는다.

## Philosophy

- **증상이 아니라 근본원인을 고친다** — lint 경고를 suppress하는 것이 아니라, 경고의 원인을 제거한다
- **실패 메시지를 끝까지 읽는다** — 에러 메시지에 답이 있다
- **연쇄 실패를 구별한다** — 하나의 근본원인이 여러 실패를 만들 수 있다

## Rules

- Read files completely before fixing
- Fix root causes, not symptoms
- Make minimal, focused changes
- Never silently skip or ignore failures
- Re-run checks after each fix
- 수정 불가 실패는 silent skip 하지 말고 *멈추고 보고* — "무시"와 "보고 후 중단"은 다르다

## Process

### 1. Detect Project Type
Scan for configuration files to determine project type:

| File | Project Type | Tools |
|------|--------------|-------|
| `package.json` | Node.js | npm/pnpm scripts |
| `pyproject.toml` / `setup.py` | Python | pytest, mypy, ruff/pylint |
| `go.mod` | Go | go vet, golangci-lint, go test |
| `Cargo.toml` | Rust | cargo clippy, cargo check, cargo test |

**프로젝트 타입이 감지되지 않거나, lint/typecheck/test 스크립트가 없는 경우:**
- 해당 단계를 건너뛰고 다음 단계로 진행한다
- 건너뛴 단계를 최종 보고서에 `SKIP (not configured)` 으로 표시한다
- 예: shell script 프로젝트, dotfiles 등은 lint/typecheck/test가 없을 수 있다

### 2. Detect Package Manager (Node.js)

Before running any Node.js commands, detect the package manager:

```bash
# Detect by lockfile
if [ -f "pnpm-lock.yaml" ]; then
  PM="pnpm"
elif [ -f "yarn.lock" ]; then
  PM="yarn"
elif [ -f "bun.lockb" ]; then
  PM="bun"
else
  PM="npm"
fi
```

Use the detected `$PM` for all subsequent commands.

### 3. Run Lint
```bash
# Node.js — use detected package manager
$PM run lint

# Python
ruff check .
pylint **/*.py

# Go
golangci-lint run
go vet ./...
```

On failure — **Root Cause Analysis:**
1. Read error messages carefully — what rule is violated and why?
2. Read the entire affected file — understand the context
3. **Ask "Why?"** — why does this code violate the rule?
   - Is it a genuine issue? → Fix the code
   - Is the rule misconfigured? → Fix the config (rare, justify clearly)
   - Is it a false positive? → Add targeted exception with comment explaining why
4. Fix with minimal changes
5. Re-run lint

### 4. Run Typecheck
```bash
# Node.js (TypeScript) — use detected package manager
$PM run typecheck
# Fallback if no typecheck script
npx tsc --noEmit

# Python
mypy .
pyright

# Go (built-in)
go build ./...
```

On failure — **Root Cause Analysis:**
1. Read type error messages — trace the type flow
2. **Identify the root error** — one type error can cascade into many
   - Fix the earliest error first, then re-run (cascading failures may resolve)
3. Read the file and understand what the code is trying to do
4. **Ask "Why?"** — why does the type not match?
   - Is the type definition wrong? → Fix the definition
   - Is the usage wrong? → Fix the usage
   - Is a dependency's type incomplete? → Add declaration or fix import
5. Do NOT use `any` or `@ts-ignore` to silence errors — fix the actual type
6. Re-run typecheck

### 5. Run Tests
```bash
# Node.js — use detected package manager
$PM test
# Or specific test runner
$PM run test

# Python
pytest

# Go
go test ./...
```

On failure — **Root Cause Analysis:**
1. Read test failure output completely
2. **Identify: is the test wrong or the implementation wrong?**
   - Read the test code — what behavior does it expect?
   - Read the implementation — what does it actually do?
   - Read recent changes — did a change break the contract?
3. **Apply 5 Whys:**
   ```
   Test fails: expected "hello" got "Hello"
   └── Why? → Function now capitalizes first letter
       └── Why? → Recent refactor changed string handling
           └── Why? → Root cause: refactor didn't update test expectations
   ```
4. Fix the root cause (update test if spec changed, fix code if regression)
5. Re-run tests

### 6. Identify Cascading Failures

**Before fixing each failure individually, look for patterns:**

- Do multiple lint errors come from the same root cause?
- Do type errors cascade from a single type definition?
- Do test failures share a common setup or dependency?

**Fix the root cause first**, then re-run to see how many other failures resolve automatically.

### 7. Final Validation
Re-run all checks in sequence:
1. Lint
2. Typecheck
3. Tests

All must pass before completion.

### 8. Report Summary
```
## Validation Summary

Checks Run:
- Lint: PASS (fixed 3 issues)
- Typecheck: PASS
- Tests: PASS (15 tests)

Root Causes Fixed:
- [Root cause 1]: description (resolved N lint/type/test failures)
- [Root cause 2]: description

Files Modified:
- src/utils.ts: Fixed unused variable
- src/api.ts: Fixed type error
- src/config.ts: Fixed missing return type
```

## Common Fixes

### Lint Issues
- Unused variables: Remove or use them
- Missing semicolons: Add them (if required by style)
- Inconsistent quotes: Standardize
- Import order: Sort alphabetically

### Type Issues
- Missing types: Add explicit type annotations
- Type mismatch: Fix the source of mismatch
- Null/undefined: Add proper null checks
- Generic inference: Add explicit type parameters

### Test Issues
- Assertion failures: Fix code or update test expectation
- Timeout: Optimize or increase timeout
- Missing mocks: Add proper mocks/stubs
- Flaky tests: Fix race conditions

## Anti-Patterns

- Do NOT disable lint rules without justification
- Do NOT use `any` type to bypass type errors
- Do NOT skip failing tests
- Do NOT add `// @ts-ignore` without fixing root cause
- Do NOT modify test expectations without understanding why
- Do NOT fix each failure in isolation — look for shared root causes first
