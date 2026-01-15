---
name: git-workflow
description: Git workflow for commits, PRs, branches. 커밋 메시지, PR 생성, 브랜치 전략.
allowed-tools: Read, Bash, Grep, Glob
---

# Git Workflow

## Commit Message
```
<type>(<scope>): <subject>

<body>
```

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`

```bash
git commit -m "feat(auth): add OAuth2 login"
```

## Branch Naming
```
feature/ABC-123-description
bugfix/ABC-456-fix-issue
hotfix/critical-patch
```

## PR Flow
1. Create branch from `main`
2. Make small, focused commits
3. Rebase on `main` before PR
4. Keep PRs small (< 400 lines)

## Rebase
```bash
git fetch origin
git rebase origin/main

# Interactive
git rebase -i HEAD~3

# Abort if issues
git rebase --abort
```

## Useful Commands
```bash
# Undo last commit (keep changes)
git reset --soft HEAD~1

# Amend last commit
git commit --amend

# Stash
git stash push -m "description"
git stash pop

# Cherry-pick
git cherry-pick <hash>
```

## Conflict Resolution
1. `git status` - identify conflicts
2. Edit files, resolve markers
3. `git add <file>`
4. `git rebase --continue`
