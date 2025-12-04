# Test Suite for dbutils

This directory contains comprehensive tests for the dbutils project covering all major functionality.

## Test Organization

### Core Functionality Tests
- `test_db_browser_functionality.py`: Tests for the main db_browser module including:
  - Data structures (TableInfo, ColumnInfo)
  - Search functionality (TrieNode, SearchIndex)
  - Database schema loading functions
  - Fuzzy matching and edit distance algorithms
  - Mock data generation
  - Caching functionality

### JDBC Provider Tests
- `test_jdbc_provider.py`: Complete tests for JDBC connectivity including:
  - Provider configuration and registry
  - Connection management
  - Query execution
  - Provider persistence
  - Error handling

### JDBC Driver Downloader Tests
- `test_jdbc_driver_downloader.py`: Tests for automatic JDBC driver download functionality including:
  - Driver registry and information management
  - Download URL generation
  - Driver filename suggestion
  - Directory management
  - Download process (with mocking)
  - Driver detection and listing

### Utility Tests
- `test_utils.py`: Tests for utility functions including:
  - Edit distance calculations
  - Fuzzy matching algorithms
  - Query runner functionality

### GUI Tests
- `test_qt_gui.py`: Tests for Qt GUI components (where testable without UI):
  - Model classes (DatabaseModel, ColumnModel, TableContentsModel)
  - Helper functions (highlight_text_as_html)
  - Graceful degradation handling

### Integration Tests
- `test_integration_workflows.py`: End-to-end workflow tests covering:
  - Multi-component integration
  - Error propagation
  - Caching integration
  - Provider configuration workflows

### Initialization Tests
- `test_module_initialization.py`: Tests for module imports and basic functionality

## Running Tests

### Complete Test Suite
```bash
python run_tests.py
# or
python -m pytest tests/test_db_browser_functionality.py tests/test_jdbc_provider.py tests/test_utils.py tests/test_qt_gui.py tests/test_integration_workflows.py tests/test_module_initialization.py -v
```

### Individual Test Files
```bash
python -m pytest tests/test_jdbc_provider.py -v
```

## Test Coverage

The test suite provides comprehensive coverage including:

- **Unit Tests**: Individual functions and classes
- **Integration Tests**: Multi-component workflows  
- **Edge Cases**: Error conditions, empty data, large inputs
- **Performance**: Caching, search optimization
- **Async Operations**: Where applicable
- **Mock Data**: Testing with realistic sample schema data

## Requirements

- Python 3.7+
- pytest
- Any existing project dependencies (JPype1, JayDeBeApi, etc.)

## Configuration

Tests use the configuration in `pytest.ini` which sets appropriate paths and options for the dbutils project structure.