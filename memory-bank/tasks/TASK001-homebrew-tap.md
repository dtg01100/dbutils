# TASK001 - Homebrew tap distribution

**Status:** Completed  
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
- [x] Draft Homebrew formula at `Formula/dbutils.rb` using Python virtualenv helper.
- [x] Include Python dependency declaration (`python@3.13`) and install using `virtualenv_install_and_link`.
- [x] Add head block for bleeding-edge installs.
- [x] Update README with tap installation instructions and caveats (needs release for stable SHA).
- [x] Create v0.1.0 tagged release and push to GitHub.
- [x] Compute sha256 for v0.1.0 tarball and update formula.

## Progress Tracking

**Overall Status:** Completed - 100%

### Subtasks
| ID | Description | Status | Updated | Notes |
|----|-------------|--------|---------|-------|
| 1.1 | Create Homebrew formula file | Completed | 2025-12-09 | Created `homebrew-dbutils/Formula/dbutils.rb` with Python virtualenv helper |
| 1.2 | Add documentation for tap installation | Completed | 2025-12-09 | Updated README.md with tap instructions; created homebrew-dbutils/README.md |
| 1.3 | Plan for stable release URL/SHA | Completed | 2025-12-09 | Created v0.1.0 tag, computed sha256, updated formula |

## Progress Log
### 2025-12-09
- Initialized Memory Bank and created task record for Homebrew tap distribution.
- Created v0.1.0 release tag and pushed to GitHub.
- Computed sha256 for v0.1.0 tarball: `ab8466e147e9d9c668bb983696d1ab98943c53b7e7d65dc552bbe46d3037770c`
- Created `homebrew-dbutils/` directory with tap structure:
  - `Formula/dbutils.rb` — Homebrew formula using Python 3.13 virtualenv helper
  - `README.md` — Tap documentation with installation and usage instructions
- Updated main `README.md` with Homebrew tap installation as primary method (committed to GitHub).
- Added `HOMEBREW_TAP.md` comprehensive guide for formula maintenance and troubleshooting.
- Initialized separate git repo for homebrew-dbutils tap (ready to push as dtg01100/homebrew-dbutils).
- Formula configured to install dbutils package with symlinks to `db-browser` and `db-browser-gui` tools.
- All changes pushed to GitHub (commits: a70275c, 7efb20f).
- **Status**: Tap is ready for use once homebrew-dbutils repo is published to GitHub.
