# Homebrew Distribution Guide

This document explains the various ways to distribute dbutils via Homebrew and the recommended approach.

## Current Setup

You now have **two ways** to distribute dbutils via Homebrew:

### Option 1: Formula in Main Repository (✅ Recommended)

**Location:** `Formula/dbutils.rb` in this repository

**User Installation:**
```bash
# Method A: Via tap (recommended)
brew tap dtg01100/dbutils
brew install dbutils

# Method B: Direct install (no tap needed)
brew install dtg01100/dbutils/dbutils

# Method C: Direct URL
brew install https://raw.githubusercontent.com/dtg01100/dbutils/master/Formula/dbutils.rb
```

**Advantages:**
- ✅ Single repository to maintain
- ✅ Formula version-controlled with source code
- ✅ Automatic updates via GitHub Actions (see `.github/workflows/update-homebrew-formula.yml`)
- ✅ Simpler maintenance workflow

**Workflow:**
1. Create a release tag (e.g., `git tag v0.2.0 && git push --tags`)
2. GitHub Actions automatically updates the formula with new version and SHA256
3. Users run `brew upgrade dbutils` to get the latest version

### Option 2: Separate Tap Repository

**Location:** `homebrew-dbutils/` directory → separate repository

**User Installation:**
```bash
brew tap dtg01100/dbutils
brew install dbutils
```

**Advantages:**
- ✅ Traditional Homebrew approach
- ✅ Can include multiple formulas in one tap
- ✅ Clear separation of concerns

**Disadvantages:**
- ❌ Two repositories to maintain
- ❌ Manual formula updates required
- ❌ More complex release process

## Automated Formula Updates

The GitHub Actions workflow (`.github/workflows/update-homebrew-formula.yml`) automatically:

1. Triggers when you publish a new release
2. Downloads the release tarball
3. Computes the SHA256 checksum
4. Updates `Formula/dbutils.rb` with new version and SHA256
5. Commits and pushes the changes

**To create a new release:**
```bash
# Create and push a tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0

# Or create a GitHub release via the web UI
# The workflow will trigger automatically
```

## Manual Formula Updates

If you prefer manual updates, follow these steps:

```bash
# 1. Create new release tag
git tag -a v0.2.0 -m "Release v0.2.0"
git push origin v0.2.0

# 2. Compute SHA256 for the new release
curl -sL https://github.com/dtg01100/dbutils/archive/v0.2.0.tar.gz | sha256sum

# 3. Update Formula/dbutils.rb
# - Change version in URL
# - Update sha256 value

# 4. Commit and push
git add Formula/dbutils.rb
git commit -m "chore: Update formula to v0.2.0"
git push
```

## Testing the Formula

```bash
# Test installation from local formula
brew install --build-from-source Formula/dbutils.rb

# Or test from GitHub
brew install --build-from-source dtg01100/dbutils/dbutils

# Run formula tests
brew test dbutils

# Audit formula for issues
brew audit --strict --online dtg01100/dbutils/dbutils
```

## Publishing to Homebrew Core (Advanced)

To make dbutils available without a tap (just `brew install dbutils`):

1. Meet Homebrew's requirements:
   - Well-maintained project with stable release history
   - Proper license (✅ MIT)
   - No dependencies on closed-source software
   - Pass `brew audit --strict --online`
   - Create bottles (pre-compiled binaries) for supported platforms

2. Submit a pull request to [Homebrew/homebrew-core](https://github.com/Homebrew/homebrew-core)

3. Address review feedback from Homebrew maintainers

**Benefits:** Maximum distribution, no tap needed
**Effort:** High - requires bottles and ongoing maintenance coordination

## Recommended Workflow

**For dbutils, we recommend:**

1. **Use Formula in Main Repo** (`Formula/dbutils.rb`)
   - Simple, automated, single repository
   - GitHub Actions handles updates automatically

2. **Keep separate tap as backup** (`homebrew-dbutils/`)
   - Can be published if you want traditional tap experience
   - Useful if you plan to distribute multiple tools

3. **Eventual goal: Homebrew Core**
   - Once the project is stable and widely used
   - Provides maximum distribution with `brew install dbutils`

## Current Status

- ✅ Formula created and tested
- ✅ Works with both tap and direct install methods
- ✅ GitHub Actions workflow ready for automatic updates
- ✅ Version v0.1.0 released and working
- ⏳ Waiting: Publish separate tap repo (optional)
- ⏳ Future: Submit to Homebrew Core (when ready)

## See Also

- [HOMEBREW_TAP.md](HOMEBREW_TAP.md) - Detailed tap maintenance guide
- [Homebrew Formula Cookbook](https://docs.brew.sh/Formula-Cookbook)
- [Homebrew Python Guide](https://docs.brew.sh/Python-for-Formula-Authors)
