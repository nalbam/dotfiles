---
name: git-workflow
description: Git workflow guidance for commits, PRs, branches, and rebasing. Use when writing commit messages, creating PRs, managing branches, resolving merge conflicts, 커밋 메시지 작성, PR 생성, 브랜치 전략, 머지 충돌 해결.
allowed-tools: Read, Bash, Grep, Glob
---

# Git Workflow

## Commit Messages

### Format
```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting (no code change)
- `refactor`: Code restructuring
- `test`: Adding tests
- `chore`: Maintenance

### Rules
- Subject: 50 chars max, imperative mood ("Add" not "Added")
- Body: Explain what and why, not how
- One logical change per commit

### Examples
```
feat(auth): add OAuth2 login support

Implement Google and GitHub OAuth2 providers.
Users can now link multiple social accounts.

Closes #123
```

```
fix(api): handle null response from payment gateway

The gateway returns null on timeout instead of error.
Added null check and retry logic.
```

## Branch Strategy

### Naming
```
feature/ABC-123-short-description
bugfix/ABC-456-fix-login-error
hotfix/critical-security-patch
release/v1.2.0
```

### Workflow
1. Create branch from `main`
2. Make small, focused commits
3. Rebase on `main` before PR
4. Squash if needed for clean history

## Pull Requests

### Title
Same format as commit: `type(scope): description`

### Body Template
```markdown
## Summary
Brief description of changes (1-3 bullets)

## Changes
- Specific change 1
- Specific change 2

## Test Plan
- [ ] Unit tests added/updated
- [ ] Manual testing completed
- [ ] Edge cases verified
```

### Best Practices
- Keep PRs small (< 400 lines ideal)
- One concern per PR
- Self-review before requesting review
- Respond to all comments

## Rebase vs Merge

### Use Rebase
- Updating feature branch with main
- Cleaning up local commits before PR
- Linear history preference

### Use Merge
- Merging PR to main (squash merge)
- Preserving branch history intentionally

### Rebase Commands
```bash
# Update feature branch
git fetch origin
git rebase origin/main

# Interactive rebase (squash/edit)
git rebase -i HEAD~3

# Abort if issues
git rebase --abort
```

## Conflict Resolution

1. Identify conflicting files: `git status`
2. Open each file and resolve markers
3. Stage resolved files: `git add <file>`
4. Continue: `git rebase --continue` or `git merge --continue`
5. Test before pushing

## Useful Commands

```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Amend last commit
git commit --amend

# Stash changes
git stash push -m "description"
git stash pop

# Cherry-pick commit
git cherry-pick <commit-hash>

# View branch graph
git log --oneline --graph --all
```
