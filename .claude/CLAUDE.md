# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

# Project Code Guidelines

**Important: Always refer to the main development documentation and documents in the `docs/` directory.**

**Important: Before writing new code, search for similar existing code and maintain consistent logic and style patterns.**

**Important: Perform only the necessary work. If work is not needed, stop.**

## Core Principles

- **Solve the right problem**: Avoid unnecessary complexity or scope creep.
- **Favor standard solutions**: Use well-known libraries and documented patterns before writing custom code.
- **Keep code clean and readable**: Use clear naming, logical structure, and avoid deeply nested logic. Write code that is easy for humans to understand through clear naming, logical structure, avoiding deep nesting, etc. Prioritize code for humans over machines.
- **Ensure consistent style**: Apply formatters (e.g. Prettier, Black) and linters (e.g. ESLint, Flake8) across the codebase.
- **Maintain Consistency**: When adding new code or modifying existing code, always refer to similar existing code within the project to maintain consistent logic, style patterns, and architectural choices. If existing patterns are suboptimal, discuss potential improvements with the team before introducing new patterns.
- **Handle errors thoughtfully**: Consider edge cases and fail gracefully.
- **Comment with intent**: Use comments to clarify non-obvious logic. Prefer expressive code over excessive comments.
- **Design for change**: Structure code to be modular and adaptable to future changes. Build modular components and use abstractions to isolate parts with high potential for change.
- **Keep dependencies shallow**: Minimize tight coupling between modules. Maintain clear boundaries.
- **Design for Security**: Prioritize security in all aspects of design and development. Consider potential vulnerabilities, follow secure coding practices, and ensure proper authentication and authorization mechanisms are in place.
- **Consider Performance Early**: Design and implement features with performance in mind. Be mindful of resource usage (CPU, memory, network bandwidth), optimize critical code paths, and consider caching strategies where appropriate.
- **Fail fast and visibly**: Surface errors early with meaningful messages or logs.
- **Automate where practical**: Use automation for formatting, testing, and deployment to reduce manual effort and error.
- **Address Root Causes**: When encountering issues or bugs, prioritize identifying and resolving the root cause rather than implementing temporary workarounds. This ensures long-term stability and maintainability.
- **Use Realistic Data**: Avoid using placeholder or dummy data in development and testing environments where possible. Strive to use data that accurately reflects real-world scenarios to ensure robustness and identify potential issues early. (Sensitive production data should never be used directly in non-production environments without proper anonymization and security measures.)
- **Maintain file size limits**: Keep source code files under 500 lines for readability, maintainability, and collaboration efficiency. (See 'File Size Guidelines' for details)

## SOLID Principles

- **Single Responsibility Principle (SRP)**: Each class or module should have only one reason to change.
- **Open/Closed Principle (OCP)**: Software entities should be open for extension but closed for modification.
- **Liskov Substitution Principle (LSP)**: Objects of a superclass should be replaceable with objects of its subclasses without breaking the application.
- **Interface Segregation Principle (ISP)**: Clients should not be forced to depend on interfaces they do not use.
- **Dependency Inversion Principle (DIP)**: High-level modules should not depend on low-level modules. Both should depend on abstractions.

## File Size Guidelines

- **Maximum file length**: Limit all source code files to under 500 lines.
- **Split large components**: Break down large components into smaller, reusable pieces.
- **Organize by responsibility**: Separate files by logical function or domain.
- **Extract utilities**: Move reusable helper functions to dedicated utility files.
- **Use composition**: Compose functionality through smaller, focused modules rather than large monolithic files.
- **Refactor when approaching limits**: Proactively monitor file sizes and plan refactoring before hitting the hard limit to maintain a healthy codebase. Consider refactoring when files approach 400+ lines.

## Documentation Standards

- Keep all documentation up to date and version-controlled. Code changes impacting documented features or architecture must be accompanied by corresponding updates to the relevant documents in the `docs/` directory. Pull requests should include documentation changes if applicable.
- Always check the existing documentation in the `docs/` directory for reference before creating new content.
- New team members should thoroughly review all documentation in the `docs/` directory as part of onboarding.
- Each document should serve a clear purpose.

## Testing Strategy

- Write automated tests for important logic and user flows.
- Include unit tests for core functions, integration tests for data flow, and E2E tests for key scenarios.
- Keep tests fast, isolated, and reliable.
- Run tests continuously in CI.
