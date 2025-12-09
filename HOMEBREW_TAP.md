# Homebrew Tap Distribution

dbutils is now distributed as a Homebrew tap for easy installation on macOS and Linux.

## Installation

```bash
brew tap dtg01100/dbutils
brew install dbutils
```

## Tap Repository

The tap formula is maintained in the separate repository:
- **Repository**: [dtg01100/homebrew-dbutils](https://github.com/dtg01100/homebrew-dbutils)
- **Formula**: `Formula/dbutils.rb`

## What's Included

The Homebrew formula installs:
- `db-browser` — Interactive TUI for searching and browsing database tables and columns
- `db-browser-gui` — Qt GUI database browser (requires PySide6)

## Updating the Formula

The formula points to a specific release tag and sha256. To update for a new version:

1. Create a new release tag in the main repository:
   ```bash
   git tag -a v0.2.0 -m "Release v0.2.0"
   git push origin v0.2.0
   ```

2. Compute the sha256 for the new release:
   ```bash
   curl -sL https://codeload.github.com/dtg01100/dbutils/tar.gz/v0.2.0 | shasum -a 256
   ```

3. Update `Formula/dbutils.rb` in the homebrew-dbutils repository:
   - Change the `url` to point to the new tag
   - Update the `sha256` with the computed value
   - Create a new commit and push

4. Users can update via:
   ```bash
   brew upgrade dbutils
   ```

## Formula Details

- **Language**: Python with Cython extensions
- **Python Requirement**: Python 3.13+
- **Dependencies**: Resolved automatically by pip during installation
- **Installation Method**: Uses Homebrew's `virtualenv_create` and `pip_install_and_link` helpers

## Requirements

- Python 3.13 or later (installed as a Homebrew dependency)
- JDBC drivers configured via environment variables (see main README for details)
- Qt libraries (if using `db-browser-gui`)

## Troubleshooting

If you encounter issues with the Homebrew installation:

1. Ensure Python 3.13 is installed:
   ```bash
   brew install python@3.13
   ```

2. Check that JDBC drivers are properly configured:
   ```bash
   echo $JDBC_DRIVER_PATH
   ```

3. For GUI issues, ensure PySide6 dependencies are available:
   ```bash
   brew install qt
   ```

4. Re-install from source to diagnose:
   ```bash
   brew untap dtg01100/dbutils
   pip install git+https://github.com/dtg01100/dbutils.git
   ```

## See Also

- [Main dbutils README](README.md)
- [Homebrew Tap Repository](https://github.com/dtg01100/homebrew-dbutils)
