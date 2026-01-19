---
name: security-review
description: Security review checklist. 보안 검토, 취약점 확인, 시크릿 노출 체크.
allowed-tools: Read, Grep, Glob
---

# Security Review

Read-only analysis for security vulnerabilities.

## Quick Scan
```bash
# Secrets/credentials
grep -rE "(password|secret|api.?key|token).*[=:].*['\"]" .

# AWS keys
grep -rE "AKIA[0-9A-Z]{16}" .

# Private keys
grep -rE "BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY" .

# JWT tokens
grep -rE "eyJ[A-Za-z0-9_-]*\.eyJ[A-Za-z0-9_-]*\.[A-Za-z0-9_-]*" .

# GitHub tokens
grep -rE "(ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9_]{36}" .

# Generic high-entropy strings (potential secrets)
grep -rE "['\"][A-Za-z0-9+/]{40,}['\"]" .
```

## Checklist

### Credentials
- [ ] No hardcoded passwords/keys
- [ ] No secrets in logs
- [ ] `.env` in `.gitignore`

### Input Validation
- [ ] All inputs validated
- [ ] Parameterized queries (no SQL injection)
- [ ] No `eval()` with user input

### Auth
- [ ] Rate limiting on auth endpoints
- [ ] Secure session management
- [ ] CSRF protection

### Data
- [ ] Sensitive data encrypted
- [ ] TLS for data in transit
- [ ] No PII in logs

## Severity Levels

| Level | Examples |
|-------|----------|
| Critical | Hardcoded credentials, SQL injection |
| High | Missing auth, command injection |
| Medium | Missing rate limiting, verbose errors |
| Low | Missing security headers |

## Report Format
```
**Severity**: High
**Location**: file.py:42
**Issue**: SQL injection via user input
**Fix**: Use parameterized query
```

## Dependency Scanning
```bash
# Node.js
npm audit
npm audit --audit-level=high
npx snyk test

# Python
pip-audit
safety check
pipenv check

# Go
go list -json -m all | nancy sleuth
govulncheck ./...

# Ruby
bundle audit check --update

# Java
./mvnw dependency-check:check
./gradlew dependencyCheckAnalyze
```

## Container Security
```bash
# Scan container images
trivy image <image>
grype <image>
docker scout cves <image>

# Dockerfile best practices
# - Use specific image tags, not :latest
# - Run as non-root user
# - Use multi-stage builds
# - Minimize installed packages
# - Don't store secrets in images
```

### Container Checklist
- [ ] Base image from trusted source
- [ ] Non-root user in Dockerfile
- [ ] No secrets in image layers
- [ ] Minimal packages installed
- [ ] Read-only root filesystem (if possible)
- [ ] Resource limits defined

## OWASP Top 10 Reference

| # | Category | Key Checks |
|---|----------|------------|
| 1 | Broken Access Control | Auth on all endpoints, RBAC |
| 2 | Cryptographic Failures | TLS, proper encryption |
| 3 | Injection | Parameterized queries, input validation |
| 4 | Insecure Design | Threat modeling, secure defaults |
| 5 | Security Misconfiguration | Hardened configs, no defaults |
| 6 | Vulnerable Components | Dependency scanning |
| 7 | Auth Failures | Strong passwords, MFA, rate limiting |
| 8 | Data Integrity Failures | Signed updates, CI/CD security |
| 9 | Logging Failures | Audit logs, no sensitive data |
| 10 | SSRF | Validate URLs, allowlist |
