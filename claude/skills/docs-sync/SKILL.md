---
name: docs-sync
description: Analyze code and update documentation to stay in sync. Use when updating docs, syncing README, checking documentation accuracy, 문서 업데이트, README 동기화, 문서 확인, 코드 문서 일치.
allowed-tools: Read, Write, Edit, Bash, Grep, Glob
---

# Documentation Sync

Analyze code changes and update documentation to keep them synchronized.

**Important**: Always follow the project's existing documentation style.

## Documentation Structure

```
project/
├── README.md        # Project overview (root only)
├── CLAUDE.md        # AI assistant instructions (root only)
└── docs/            # All other documentation
    ├── ARCHITECTURE.md
    ├── API.md
    ├── CHANGELOG.md
    ├── CONTRIBUTING.md
    └── ...
```

**Rules**:
- Only `README.md` and `CLAUDE.md` in project root
- All other `.md` files must be in `docs/` directory
- If documentation exists outside `docs/`, suggest moving it

## Document Indexing

### docs/README.md (Index File)
Maintain an index file listing all documentation:

```markdown
# Documentation

## Getting Started
- [Installation](INSTALLATION.md)
- [Quick Start](QUICKSTART.md)

## Guides
- [Configuration](CONFIGURATION.md)
- [Deployment](DEPLOYMENT.md)

## Reference
- [API Reference](API.md)
- [CLI Reference](CLI.md)

## Development
- [Architecture](ARCHITECTURE.md)
- [Contributing](CONTRIBUTING.md)
```

### Auto-Generated TOC
Each document should have a table of contents for sections:
```markdown
## Table of Contents
- [Overview](#overview)
- [Installation](#installation)
- [Usage](#usage)
```

### Cross-References
- Use relative links between documents: `[See API docs](API.md#authentication)`
- Verify all internal links are valid
- Update links when files are renamed/moved

## Duplicate Prevention

### Single Source of Truth
- Each topic documented in ONE place only
- Other locations link to the source
- Never copy-paste content between docs

### Detect Duplicates
```bash
# Find similar content across docs
for file in docs/*.md; do
  echo "=== $file ==="
  grep -l "$(head -5 "$file" | tail -1)" docs/*.md 2>/dev/null
done
```

### When Duplication Found
- Identify the primary document
- Replace duplicates with links
- Example: "For installation details, see [INSTALLATION.md](INSTALLATION.md)"

## Document Quality Standards

### Required Metadata
Each document should start with:
```markdown
# Document Title

> Brief one-line description of this document.

**Last Updated**: 2024-01-15
**Maintainer**: @username
```

### Formatting Rules
- Use ATX-style headers (`#`, `##`, `###`)
- One blank line between sections
- Code blocks with language hints (```bash, ```python)
- Tables for structured data
- Lists for sequential steps

### Content Guidelines
- Start with "why" before "how"
- Include working examples
- Show expected output
- Note prerequisites upfront
- Add troubleshooting section

## Document Classification

### By Type (Prefix Convention)
| Prefix | Type | Purpose |
|--------|------|---------|
| (none) | Guide | Step-by-step instructions |
| `API-` | Reference | Complete API documentation |
| `ADR-` | Decision | Architecture Decision Record |
| `RFC-` | Proposal | Request for Comments |

### By Audience
- `docs/` - User documentation
- `docs/dev/` - Developer documentation
- `docs/ops/` - Operations/DevOps documentation

### Naming Convention
- Use UPPERCASE for top-level docs: `ARCHITECTURE.md`
- Use kebab-case for guides: `getting-started.md`
- Include date for ADRs: `ADR-001-database-choice.md`

## Search Optimization

### Clear Headings
- Descriptive, keyword-rich headings
- Hierarchical structure (H1 > H2 > H3)
- No skipped heading levels

### Anchor Links
- Use explicit anchors for important sections
- Keep anchor names stable (don't rename frequently)
- Document anchors used by external links

### Keywords
- Include common search terms
- Add "Also known as" for aliases
- Use consistent terminology throughout

## When Invoked

1. **Identify documentation files**
   - README.md, CHANGELOG.md, docs/
   - API documentation, inline comments
   - Configuration examples

2. **Analyze code changes**
   - Run `git diff` to see recent changes
   - Identify changed functions, APIs, options
   - Check for new/removed features

3. **Compare code vs docs**
   - Function signatures match documentation
   - CLI options/flags documented
   - Configuration options up to date
   - Examples still work

4. **Update documentation**
   - Fix outdated information
   - Add missing documentation
   - Remove obsolete content
   - Update version numbers

5. **Verify updates**
   - Code examples are correct
   - Links are valid
   - Formatting is consistent

## Detection Strategy

### Find Documentation Files
```bash
# Common documentation files
find . -name "README*" -o -name "CHANGELOG*" -o -name "*.md" | head -20

# API documentation
find . -path "./docs/*" -name "*.md"

# Config examples
find . -name "*.example" -o -name "*.sample"
```

### Identify Code-Doc Mismatches

**Function/API Changes**
- New parameters not documented
- Changed return types
- Deprecated functions still in docs
- New endpoints missing from API docs

**Configuration Changes**
- New environment variables
- Changed default values
- Removed options still documented

**CLI Changes**
- New commands/subcommands
- Changed flags or arguments
- Updated help text

## Update Checklist

See [CHECKLIST.md](CHECKLIST.md) for detailed verification steps.

### Quick Checks
- [ ] README installation steps work
- [ ] Code examples run without errors
- [ ] All CLI flags documented
- [ ] Environment variables listed
- [ ] Version numbers consistent
- [ ] Links not broken

## Documentation Sections to Check

### README.md
- Project description accurate
- Installation instructions current
- Quick start example works
- Configuration options complete
- Troubleshooting up to date

### API Documentation
- Endpoints list complete
- Request/response examples valid
- Authentication documented
- Error codes listed

### CHANGELOG.md
- Recent changes documented
- Version numbers correct
- Breaking changes highlighted

## Output Format

After sync, provide summary:

```markdown
## Documentation Sync Report

### Updated
- README.md: Updated installation command (line 25)
- docs/api.md: Added new endpoint /users/search

### Added
- docs/config.md: New CACHE_TTL environment variable

### Removed
- README.md: Removed deprecated --legacy flag

### Verified
- All code examples tested and working
- No broken links found
```

## Best Practices

- Keep documentation close to code
- Update docs in same commit as code changes
- Use consistent terminology
- Include practical examples
- Mark deprecated features clearly
- Date major documentation updates
