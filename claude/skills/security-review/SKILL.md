---
name: security-review
description: Security review checklist for code and configuration. Use when reviewing code for security vulnerabilities, checking for credential exposure, or auditing security.
allowed-tools: Read, Grep, Glob
---

# Security Review Checklist

## Quick Scan

```bash
# Exposed secrets
grep -rE "(password|secret|api.?key|token|credential).*[=:].*['\"]" .

# Hardcoded IPs/URLs
grep -rE "https?://[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+" .

# TODO/FIXME security
grep -rE "(TODO|FIXME).*(security|auth|password)" .
```

## Credential Exposure

### Must Check
- [ ] No hardcoded passwords, API keys, tokens
- [ ] No secrets in code comments
- [ ] No credentials in logs
- [ ] Environment variables for sensitive data
- [ ] `.env` files in `.gitignore`

### Patterns to Find
```bash
# AWS keys
grep -rE "AKIA[0-9A-Z]{16}" .

# Private keys
grep -rE "BEGIN (RSA|DSA|EC|OPENSSH) PRIVATE KEY" .

# Generic secrets
grep -rE "(password|passwd|pwd)\s*=\s*['\"][^'\"]+['\"]" .
```

## Input Validation

### Must Check
- [ ] All user inputs validated
- [ ] Inputs sanitized before use
- [ ] Length limits enforced
- [ ] Type checking implemented
- [ ] Whitelist over blacklist

### Injection Prevention

**SQL Injection**
```bash
# Find raw queries
grep -rE "execute.*\+.*\"|format.*SELECT|f\".*SELECT" .
```
- Use parameterized queries
- Never concatenate user input

**Command Injection**
```bash
# Find shell calls
grep -rE "subprocess|os\.system|exec\(|eval\(" .
```
- Avoid shell=True
- Use argument lists
- Validate input strictly

**XSS Prevention**
- Encode output in HTML context
- Use Content Security Policy
- Validate and sanitize HTML input

## Authentication & Authorization

### Must Check
- [ ] Strong password requirements
- [ ] Rate limiting on auth endpoints
- [ ] Secure session management
- [ ] CSRF protection enabled
- [ ] Proper role-based access control

### Common Issues
- Broken access control (IDOR)
- Missing authorization checks
- Session fixation
- Insecure password reset

## API Security

### Must Check
- [ ] Authentication on all endpoints
- [ ] Authorization checked per resource
- [ ] Rate limiting implemented
- [ ] Input validation on all params
- [ ] Sensitive data not in URLs

### Headers
```
# Required security headers
Content-Security-Policy
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
Strict-Transport-Security
```

## Data Protection

### Must Check
- [ ] Sensitive data encrypted at rest
- [ ] TLS for data in transit
- [ ] Minimal data collection
- [ ] Proper data retention policies
- [ ] No sensitive data in logs

### Logging Security
```bash
# Find logging statements
grep -rE "log\.(info|debug|error).*password" .
```
- No passwords in logs
- No tokens in logs
- No PII without masking

## Dependency Security

### Must Check
- [ ] Dependencies up to date
- [ ] No known vulnerabilities
- [ ] Lockfile committed
- [ ] Source verification

### Commands
```bash
# Node.js
npm audit

# Python
pip-audit
safety check

# Go
go list -m all | nancy

# General
snyk test
```

## Configuration Security

### Must Check
- [ ] Debug mode disabled in production
- [ ] Default credentials changed
- [ ] Unnecessary features disabled
- [ ] Error messages don't leak info
- [ ] CORS configured properly

### Environment Files
```bash
# Check for committed env files
git ls-files | grep -E "\.env|\.env\."

# Check gitignore
grep -E "\.env" .gitignore
```

## Kubernetes/Docker Security

### Container Security
- [ ] Non-root user
- [ ] Read-only root filesystem
- [ ] No privileged containers
- [ ] Resource limits set
- [ ] No secrets in image

### K8s Security
```yaml
# Required pod security
securityContext:
  runAsNonRoot: true
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
```

## Code Review Triggers

### High Priority (Stop & Fix)
- Hardcoded credentials
- SQL/command injection
- Missing authentication
- Sensitive data exposure

### Medium Priority (Should Fix)
- Missing input validation
- Weak cryptography
- Verbose error messages
- Missing rate limiting

### Low Priority (Consider)
- Missing security headers
- Outdated dependencies
- Overly permissive CORS

## Reporting Format

```markdown
## Security Finding

**Severity**: Critical/High/Medium/Low
**Location**: file.py:42
**Issue**: Description of the vulnerability
**Impact**: What an attacker could do
**Recommendation**: How to fix it
**Example**:
```code
// Fixed code
```
```
