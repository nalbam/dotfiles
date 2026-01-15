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
