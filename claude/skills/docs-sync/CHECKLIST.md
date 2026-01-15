# Documentation Sync Checklist

## Documentation Structure Validation

### Check File Locations
```bash
# Find .md files outside docs/ (excluding README.md, CLAUDE.md)
find . -maxdepth 1 -name "*.md" ! -name "README.md" ! -name "CLAUDE.md" -type f

# Should only have README.md and CLAUDE.md in root
ls -la *.md 2>/dev/null
```

### Expected Structure
- [ ] `README.md` in project root
- [ ] `CLAUDE.md` in project root (if exists)
- [ ] All other `.md` files in `docs/` directory
- [ ] No stray documentation files in root

### If Misplaced Files Found
```bash
# Move to docs/
mkdir -p docs
mv CONTRIBUTING.md docs/
mv CHANGELOG.md docs/
```

## Document Indexing Checklist

### Index File (docs/README.md)
- [ ] `docs/README.md` exists as index
- [ ] All documents listed in index
- [ ] Links are valid and working
- [ ] Logical grouping (Getting Started, Guides, Reference)

### Verify Index Completeness
```bash
# List all docs
ls docs/*.md

# Check if all are in index
for f in docs/*.md; do
  name=$(basename "$f")
  grep -q "$name" docs/README.md || echo "Missing from index: $name"
done
```

### Table of Contents
- [ ] Each document has TOC for 3+ sections
- [ ] TOC links match actual headings
- [ ] Anchor links work correctly

### Cross-References
- [ ] Internal links use relative paths
- [ ] No broken links between documents
- [ ] Renamed files have updated references

```bash
# Find all internal links
grep -roh '\[.*\](\..*\.md' docs/ | sort -u

# Verify each link target exists
grep -roh '(\./[^)]*\.md)' docs/ | tr -d '()' | while read link; do
  [ -f "docs/$link" ] || echo "Broken: $link"
done
```

## Duplicate Prevention Checklist

### Single Source of Truth
- [ ] No copy-pasted content between docs
- [ ] Each topic in ONE location only
- [ ] Duplicates replaced with links

### Detect Duplicates
```bash
# Find files with similar first lines
for f in docs/*.md; do
  first_line=$(grep -m1 "^#" "$f" | head -1)
  echo "$first_line -> $f"
done | sort | uniq -d -f1

# Find repeated paragraphs (3+ lines)
awk 'NF {p=p$0"\n"; c++} !NF {if(c>=3) print p; p=""; c=0}' docs/*.md | sort | uniq -d
```

### When Duplicates Found
- [ ] Identify primary document
- [ ] Replace copies with: "See [Primary Doc](PRIMARY.md)"
- [ ] Update all references

## Document Quality Checklist

### Required Metadata
- [ ] Title as H1 (`# Title`)
- [ ] One-line description (blockquote)
- [ ] Last Updated date
- [ ] Maintainer (optional)

```bash
# Check for metadata
for f in docs/*.md; do
  echo "=== $f ==="
  head -10 "$f" | grep -E "(^#|^>|Last Updated|Maintainer)" || echo "Missing metadata"
done
```

### Formatting Standards
- [ ] ATX-style headers only (`#`, not underlines)
- [ ] Blank line between sections
- [ ] Code blocks have language hints
- [ ] Tables properly formatted
- [ ] Consistent list style (-, not *)

### Content Quality
- [ ] Starts with "why" before "how"
- [ ] Includes working examples
- [ ] Shows expected output
- [ ] Lists prerequisites
- [ ] Has troubleshooting section (if applicable)

## Document Classification Checklist

### Naming Convention
- [ ] Top-level docs: UPPERCASE (`ARCHITECTURE.md`)
- [ ] Guides: kebab-case (`getting-started.md`)
- [ ] ADRs: numbered (`ADR-001-title.md`)

### Directory Structure
- [ ] `docs/` - User documentation
- [ ] `docs/dev/` - Developer docs (if needed)
- [ ] `docs/ops/` - Operations docs (if needed)

### Type Prefixes
- [ ] API docs: `API-*.md`
- [ ] ADRs: `ADR-###-*.md`
- [ ] RFCs: `RFC-###-*.md`

## Search Optimization Checklist

### Heading Structure
- [ ] Clear, descriptive headings
- [ ] Keyword-rich titles
- [ ] No skipped levels (H1 > H2 > H3)

### Anchor Links
- [ ] Important sections have stable anchors
- [ ] External links documented
- [ ] Anchors not renamed unnecessarily

### Keywords & Terminology
- [ ] Common search terms included
- [ ] Aliases noted ("Also known as")
- [ ] Consistent terminology throughout

```bash
# Find inconsistent terminology
grep -roh '\b[A-Z][a-z]*[A-Z][a-z]*\b' docs/ | sort | uniq -c | sort -rn | head -20
```

## Pre-Sync Analysis

### 1. Gather Context
```bash
# Recent commits
git log --oneline -10

# Changed files
git diff --name-only HEAD~5

# Find all documentation
find . -name "*.md" -not -path "./node_modules/*" -not -path "./.git/*"
```

### 2. Identify Documentation Types
- [ ] README.md - Project overview
- [ ] CHANGELOG.md - Version history
- [ ] CONTRIBUTING.md - Contribution guide
- [ ] docs/ - Detailed documentation
- [ ] API docs - Endpoint documentation
- [ ] Inline comments - Code documentation

## README.md Checklist

### Header Section
- [ ] Project name matches package.json/pyproject.toml
- [ ] Description is accurate and current
- [ ] Badges show correct status

### Installation
- [ ] Package manager commands correct
- [ ] Version requirements accurate
- [ ] Prerequisites listed
- [ ] All steps tested and working

### Usage
- [ ] Basic example runs without errors
- [ ] Import/require statements correct
- [ ] Output examples match actual output

### Configuration
- [ ] All environment variables listed
- [ ] Default values documented
- [ ] Required vs optional clearly marked
- [ ] Example config file up to date

### CLI Documentation
- [ ] All commands listed
- [ ] All flags/options documented
- [ ] Help text matches implementation
- [ ] Examples work as shown

## API Documentation Checklist

### Endpoints
- [ ] All endpoints listed
- [ ] HTTP methods correct
- [ ] URL paths accurate
- [ ] Query parameters documented

### Request/Response
- [ ] Request body schema current
- [ ] Response schema accurate
- [ ] Example requests work
- [ ] Example responses match actual

### Authentication
- [ ] Auth methods documented
- [ ] Token format explained
- [ ] Error responses listed

## Code Comments Checklist

### Functions/Methods
- [ ] Public functions have docstrings
- [ ] Parameters documented
- [ ] Return values described
- [ ] Exceptions/errors listed

### Complex Logic
- [ ] Non-obvious code explained
- [ ] Business rules documented
- [ ] Edge cases noted

## Cross-Reference Checks

### Version Consistency
```bash
# Check version in different files
grep -r "version" package.json pyproject.toml README.md
```

### Link Validation
```bash
# Find markdown links
grep -oE '\[.*\]\(.*\)' README.md

# Check for broken relative links
for link in $(grep -oE '\]\([^http][^)]+\)' README.md | tr -d '()]'); do
  [ -f "$link" ] || echo "Broken: $link"
done
```

### Code Example Validation
- [ ] Extract code blocks from docs
- [ ] Run examples in test environment
- [ ] Verify output matches documentation

## Post-Sync Verification

### Formatting
- [ ] Markdown renders correctly
- [ ] Code blocks have language hints
- [ ] Tables format properly
- [ ] Lists are consistent

### Completeness
- [ ] No TODO/FIXME in documentation
- [ ] No placeholder text
- [ ] No outdated dates

### Final Review
- [ ] Read through as new user would
- [ ] Check mobile/narrow viewport rendering
- [ ] Verify search-friendliness (clear headings)
