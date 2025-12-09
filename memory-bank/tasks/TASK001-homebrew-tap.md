# TASK001 - Homebrew tap distribution

**Status:** In Progress  
**Added:** 2025-12-09  
**Updated:** 2025-12-09

## Original Request
"I'd like for this to be distributed as a tap."

## Thought Process
- Provide a Homebrew tap formula so users can install `dbutils` via `brew tap`/`brew install`.
- Need to rely on source tarball from GitHub (current repo) because no release tags exist yet; formula may start with current commit archive and should be updated when a tag is created.
- Use `Language::Python::Virtualenv` to install the package and its Python dependencies.
- Document tap usage and call out need to update URL/SHA when publishing a release.

## Implementation Plan
- [ ] Draft Homebrew formula at `Formula/dbutils.rb` pointing to a GitHub archive (commit or future tag) with sha256 placeholder/initial value.
- [ ] Include Python dependency declaration (`python@3.13`) and install using `virtualenv_install_with_resources`.
- [ ] Add head block for bleeding-edge installs.
- [ ] Update README with tap installation instructions and caveats (needs release for stable SHA).
- [ ] Revisit formula once a tagged release is published to update URL/sha256.

## Progress Tracking

**Overall Status:** In Progress - 20%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Create Homebrew formula file | Not Started | 2025-12-09 | Target `Formula/dbutils.rb` using Python virtualenv helper |
| 1.2 | Add documentation for tap installation | Not Started | 2025-12-09 | README instructions + caveats |
| 1.3 | Plan for stable release URL/SHA | Not Started | 2025-12-09 | Note to update once tag exists |

## Progress Log
### 2025-12-09
- Initialized Memory Bank and created task record for Homebrew tap distribution.
