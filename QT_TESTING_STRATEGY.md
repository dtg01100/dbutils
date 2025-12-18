# Qt Testing Strategy for dbutils

## Overview

This document outlines the comprehensive Qt testing strategy implemented for the dbutils project using pytest-qt and uv for Python interactions.

## Test Architecture

### Core Components Tested

1. **QtDBBrowser** - Main database browser window
   - Window initialization and lifecycle
   - Search functionality (tables and columns mode)
   - UI component interactions
   - Data loading with mock data

2. **Qt Models** - Data models for Qt views
   - DatabaseModel - for table display
   - ColumnModel - for column display
   - TableContentsModel - for table contents preview

3. **Qt Workers** - Background processing threads
   - Search workers
   - Data loading workers
   - Table contents workers

4. **Provider Configuration Dialog** - Dialog for JDBC provider configuration
   - Form field interactions
   - Provider management
   - Validation and error handling

## Testing Approach

### Qt Testing with pytest-qt

- All Qt tests use the `qtbot` fixture for safe widget interaction
- Proper event loop handling with `qapp.processEvents()`
- Widget lifecycle management with `qtbot.addWidget()`
- Safe cleanup to prevent segmentation faults

### Mock Data Strategy

- Use `use_mock=True` parameter to avoid database dependencies
- Mock data provides comprehensive test coverage without external dependencies
- Test modes enabled via `DBUTILS_TEST_MODE=1` environment variable

## Test Execution

### Using uv for Python Interactions

All tests are executed using uv with the following command pattern:

```bash
# Standard test execution
uv run python -m pytest tests/test_comprehensive_qt_browser.py

# With display and test mode
DISPLAY=:0 DBUTILS_TEST_MODE=1 uv run python -m pytest tests/ -k qt

# Specific test execution
DISPLAY=:0 DBUTILS_TEST_MODE=1 uv run python -m pytest tests/test_comprehensive_qt_browser.py -v
```

### Environment Setup

- PySide6 and pytest-qt properly installed via uv
- Virtual environment managed by uv
- All dependencies specified in pyproject.toml

## Key Test Files

1. `tests/test_comprehensive_qt_browser.py` - Main QtDBBrowser functionality
2. `tests/test_comprehensive_qt_workers.py` - Qt models and threading
3. `tests/test_comprehensive_provider_dialog.py` - Provider configuration dialog
4. Existing test files like `tests/test_qt_integration.py`, etc.

## Best Practices

### Qt-Specific Testing

- Always use `qtbot.addWidget()` to register widgets for proper cleanup
- Use `qtbot.mouseClick()` and `qtbot.keyClicks()` for safe widget interactions
- Handle event processing with `qapp.processEvents()` between interactions
- Close widgets properly in try/finally blocks

### Test Isolation

- Each test creates its own instance of Qt components
- Proper cleanup prevents widget conflicts between tests
- Use of test fixtures (`qapp`, `qtbot`) for consistent environment

### Error Handling

- Graceful failure handling in headless environments
- Mock-based testing for isolated functionality
- Dependency injection for external services