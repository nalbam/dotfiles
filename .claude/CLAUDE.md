# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Project Code Guidelines

**Important: Always refer to the main development documentation in the `docs/` directory.**

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

## File Size Guidelines

- Keep source code files under 700 lines.
- Consider refactoring when files approach 500+ lines.
- Split large components into smaller, focused modules.

## Testing Strategy

- Write tests for important logic and user flows.
- Bug fixes must include a regression test.
- Keep tests fast, isolated, and deterministic.

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
