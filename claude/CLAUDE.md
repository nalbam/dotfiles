# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in any project.

# Project Code Guidelines

**Important: Refer to project-specific documentation (e.g., docs/, README.md) when available.**

**Important: Before writing new code, search for similar existing code and maintain consistent patterns.**

**Important: Perform only the necessary work. If work is not needed, stop.**

## Mindset

- Think like a senior engineer.
- Don't rush to conclusions; evaluate multiple approaches before deciding.
- Problem definition → small, safe change → review → refactor — repeat the loop.
- Keep commits and PRs small and focused.

## Before Changing Code

- Read relevant files end to end, including call/reference paths.
- Locate definitions, references, call sites, related tests, and configs.
- Do not change code without having read the entire file.
- Record assumptions clearly.

## Core Principles

- **Solve the right problem**: Avoid unnecessary complexity or scope creep.
- **Favor standard solutions**: Use well-known libraries and patterns before writing custom code.
- **Keep code readable**: Use clear naming, logical structure, and avoid deep nesting.
- **Handle errors explicitly**: Catch specific exceptions, fail fast with meaningful messages.
- **Design for security**: Validate inputs, apply least privilege, never expose secrets.
- **Keep dependencies shallow**: Minimize tight coupling, maintain clear boundaries.
- **Address root causes**: Fix the underlying issue, not symptoms.

## Problem Solving & Root Cause Analysis

When troubleshooting issues, follow this systematic process:

### Investigation Steps
1. **Reproduce**: Document exact error messages, stack traces, and environment details
2. **Investigate**:
   - Read error messages carefully - they often contain the root cause
   - Check logs for patterns, warnings, or errors leading up to failure
   - Trace execution path from entry point to failure point
   - Verify assumptions with minimal experiments
3. **Root Cause**:
   - Ask "Why?" 5 times until reaching the fundamental issue
   - Distinguish symptoms from causes (e.g., "API returns 500" vs "connection pool exhausted")
   - Look for systemic issues, not one-off failures
4. **Fix**: Address root cause, not symptoms; document workarounds if necessary
5. **Verify**: Test thoroughly, add regression tests, check for similar issues elsewhere

### Anti-Patterns to Avoid
- ❌ Quick fixes without understanding the issue
- ❌ Treating symptoms (try-catch everywhere) instead of fixing causes
- ❌ Stopping at the first plausible explanation
- ❌ Skipping verification after implementing a fix

### Example
**Symptom**: Intermittent crashes in production
**Bad**: Add error handling + auto-restart
**Good**: Profile → identify memory leak (temp files not cleaned) → fix cleanup + add limits → verify with load test

## File Size Guidelines

- Keep source code files under 700 lines.
- Consider refactoring when files approach 500+ lines.
- Split large components into smaller, focused modules.

## Testing Strategy

- **Unit tests**: Test logic in isolation, fast (<10ms), deterministic
- **Integration tests**: Test component interactions with realistic scenarios
- **E2E tests**: Critical user flows only, expensive to maintain
- **Coverage**: Aim for 80%+ on core logic, 100% on critical paths
- **Bug fixes**: Must include regression tests
- **Dependencies**: Use mocks/stubs for external services
- **Independence**: Tests should not share state or depend on execution order
- Keep tests readable - they serve as documentation

## Documentation

- Write self-documenting code: clear names, logical structure
- Add comments only for non-obvious logic (explain "why", not "what")
- Keep README.md updated with setup instructions, usage examples, and architecture overview
- Document APIs with request/response examples and error cases
- Update documentation when changing behavior or adding features
- Avoid outdated comments - delete rather than leave incorrect information

## Security Rules

- Never expose secrets in code, logs, or commits.
- Validate, sanitize, and encode all inputs.
- Apply the Principle of Least Privilege.
- Do not log sensitive data.

## Anti-Patterns to Avoid

- Modifying code without reading the full context.
- Ignoring failures, warnings, or edge cases.
- Premature optimization or abstraction.
- Using broad exception handlers.
