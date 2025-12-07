#!/usr/bin/env python3
"""Verification script for multi-database test setup.

This script verifies that all configurations, dependencies, and test structures
are properly set up for multi-database testing.
"""

import json
import logging
import os
import sys
from typing import Any, Dict

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    return os.path.exists(file_path)

def check_dependencies() -> Dict[str, bool]:
    """Check if required dependencies are installed with detailed error handling."""
    dependencies = {
        'jaydebeapi': False,
        'jpype1': False,
        'PySide6': False
    }

    try:
        import jaydebeapi
        dependencies['jaydebeapi'] = True
    except ImportError as e:
        logger.warning(f"jaydebeapi not found: {e}")

    try:
        import jpype
        dependencies['jpype1'] = True
    except ImportError as e:
        logger.warning(f"jpype not found: {e}")

    try:
        import PySide6
        dependencies['PySide6'] = True
    except ImportError as e:
        logger.warning(f"PySide6 not found: {e}")

    return dependencies

def check_database_jar_files() -> Dict[str, bool]:
    """Check if database JAR files exist with detailed error handling."""
    jar_files = {
        "sqlite": "jars/sqlite-jdbc.jar",
        "h2": "jars/h2.jar",
        "derby": "jars/derby.jar",
        "hsqldb": "jars/hsqldb.jar",
        "duckdb": "jars/duckdb_jdbc.jar"
    }

    results = {}
    for db_type, jar_path in jar_files.items():
        exists = check_file_exists(jar_path)
        results[db_type] = exists
        if not exists:
            logger.warning(f"JAR file missing for {db_type}: {jar_path}")

    return results

def check_test_files() -> Dict[str, bool]:
    """Check if required test files exist."""
    test_files = {
        "setup_multi_database_test.py": "setup_multi_database_test.py",
        "test_multi_database_integration.py": "tests/test_multi_database_integration.py",
        "database_test_utils.py": "tests/database_test_utils.py",
        "conftest.py": "conftest.py"
    }

    results = {}
    for file_name, file_path in test_files.items():
        results[file_name] = check_file_exists(file_path)

    return results

def check_provider_configurations() -> Dict[str, bool]:
    """Check if database providers are properly configured."""
    try:
        sys.path.insert(0, 'src')
        from dbutils.jdbc_provider import ProviderRegistry

        registry = ProviderRegistry()
        required_providers = [
            "SQLite (Test Integration)",
            "H2 (Test Integration)",
            "Apache Derby (Test Integration)",
            "HSQLDB (Test Integration)",
            "DuckDB (Test Integration)"
        ]

        results = {}
        for provider_name in required_providers:
            results[provider_name] = provider_name in registry.providers

        return results

    except Exception as e:
        logger.error(f"Error checking provider configurations: {e}")
        return dict.fromkeys(["SQLite (Test Integration)", "H2 (Test Integration)", "Apache Derby (Test Integration)", "HSQLDB (Test Integration)", "DuckDB (Test Integration)"], False)

def check_test_structure() -> Dict[str, Any]:
    """Check the overall test structure and configuration."""
    structure_check = {
        "dependencies": check_dependencies(),
        "jar_files": check_database_jar_files(),
        "test_files": check_test_files(),
        "providers": check_provider_configurations()
    }

    return structure_check

def verify_database_configurations() -> Dict[str, Dict[str, Any]]:
    """Verify database configurations are correct."""
    expected_configs = {
        "sqlite": {
            "driver_class": "org.sqlite.JDBC",
            "url_template": "jdbc:sqlite:{database}",
            "user": None,
            "password": None
        },
        "h2": {
            "driver_class": "org.h2.Driver",
            "url_template": "jdbc:h2:mem:{database};DB_CLOSE_DELAY=-1",
            "user": "sa",
            "password": ""
        },
        "derby": {
            "driver_class": "org.apache.derby.jdbc.EmbeddedDriver",
            "url_template": "jdbc:derby:{database};create=true",
            "user": None,
            "password": None
        },
        "hsqldb": {
            "driver_class": "org.hsqldb.jdbc.JDBCDriver",
            "url_template": "jdbc:hsqldb:mem:{database}",
            "user": "SA",
            "password": ""
        },
        "duckdb": {
            "driver_class": "org.duckdb.DuckDBDriver",
            "url_template": "jdbc:duckdb:{database}",
            "user": None,
            "password": None
        }
    }

    try:
        sys.path.insert(0, 'src')
        from dbutils.jdbc_provider import ProviderRegistry

        registry = ProviderRegistry()
        verification_results = {}

        for db_type, expected_config in expected_configs.items():
            # Map database types to their proper provider names
            provider_mapping = {
                "sqlite": "SQLite (Test Integration)",
                "h2": "H2 (Test Integration)",
                "derby": "Apache Derby (Test Integration)",
                "hsqldb": "HSQLDB (Test Integration)",
                "duckdb": "DuckDB (Test Integration)"
            }
            provider_name = provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)")
            provider = registry.get(provider_name)

            if provider:
                verification_results[db_type] = {
                    "found": True,
                    "driver_class_match": provider.driver_class == expected_config["driver_class"],
                    "url_template_match": provider.url_template == expected_config["url_template"],
                    "user_match": provider.default_user == expected_config["user"],
                    "password_match": provider.default_password == expected_config["password"]
                }
            else:
                verification_results[db_type] = {
                    "found": False,
                    "driver_class_match": False,
                    "url_template_match": False,
                    "user_match": False,
                    "password_match": False
                }

        return verification_results

    except Exception as e:
        logger.error(f"Error verifying database configurations: {e}")
        return {db_type: {"found": False, "driver_class_match": False, "url_template_match": False, "user_match": False, "password_match": False}
                for db_type in expected_configs.keys()}

def test_database_connections() -> Dict[str, bool]:
    """Test database connections for all configured databases."""
    try:
        sys.path.insert(0, 'src')
        from dbutils.jdbc_provider import connect

        results = {}
        test_db_names = {
            "sqlite": "verify_test.db",
            "h2": "verify_test_mem",
            "derby": "verify_test_derby",
            "hsqldb": "verify_test_hsqldb",
            "duckdb": "verify_test_duckdb"
        }

        for db_type, db_name in test_db_names.items():
            try:
                # Map database types to their proper provider names
                provider_mapping = {
                    "sqlite": "SQLite (Test Integration)",
                    "h2": "H2 (Test Integration)",
                    "derby": "Apache Derby (Test Integration)",
                    "hsqldb": "HSQLDB (Test Integration)",
                    "duckdb": "DuckDB (Test Integration)"
                }
                provider_name = provider_mapping.get(db_type, f"{db_type.capitalize()} (Test Integration)")
                conn = connect(provider_name, {"database": db_name})

                # Test simple query - use database-specific syntax
                db_type_lower = db_type.lower()
                if db_type_lower == "hsqldb":
                    result = conn.query("SELECT 1 as test FROM (VALUES(0))")
                else:
                    result = conn.query("SELECT 1 as test")
                logger.info(f"{db_type} connection successful: {result[0] if result else 'No result'}")
                conn.close()

                results[db_type] = True

            except Exception as e:
                logger.error(f"{db_type} connection test failed: {e}")
                results[db_type] = False

        return results

    except Exception as e:
        logger.error(f"Database connection testing failed: {e}")
        return dict.fromkeys(["sqlite", "h2", "derby", "hsqldb", "duckdb"], False)

def generate_verification_report() -> Dict[str, Any]:
    """Generate a comprehensive verification report with detailed error information."""
    report = {
        "metadata": {
            "timestamp": __import__('datetime').datetime.now().isoformat(),
            "python_version": sys.version,
            "working_directory": os.getcwd()
        },
        "structure_check": check_test_structure(),
        "configuration_verification": verify_database_configurations(),
        "connection_tests": test_database_connections(),
        "errors": []
    }

    # Calculate summary statistics
    total_checks = 0
    passed_checks = 0

    # Count dependencies
    deps = report["structure_check"]["dependencies"]
    total_checks += len(deps)
    passed_checks += sum(1 for v in deps.values() if v)

    # Count JAR files
    jars = report["structure_check"]["jar_files"]
    total_checks += len(jars)
    passed_checks += sum(1 for v in jars.values() if v)

    # Count test files
    test_files = report["structure_check"]["test_files"]
    total_checks += len(test_files)
    passed_checks += sum(1 for v in test_files.values() if v)

    # Count providers
    providers = report["structure_check"]["providers"]
    total_checks += len(providers)
    passed_checks += sum(1 for v in providers.values() if v)

    # Count configuration verifications
    configs = report["configuration_verification"]
    total_checks += len(configs) * 5  # 5 checks per database
    for config in configs.values():
        passed_checks += sum(1 for v in config.values() if v)

    # Count connection tests
    connections = report["connection_tests"]
    total_checks += len(connections)
    passed_checks += sum(1 for v in connections.values() if v)

    # Add detailed error information
    if not all(deps.values()):
        missing_deps = [name for name, installed in deps.items() if not installed]
        report["errors"].append(f"Missing dependencies: {', '.join(missing_deps)}")

    if not all(jars.values()):
        missing_jars = [db_type for db_type, exists in jars.items() if not exists]
        report["errors"].append(f"Missing JAR files: {', '.join(missing_jars)}")

    if not all(test_files.values()):
        missing_files = [file_name for file_name, exists in test_files.items() if not exists]
        report["errors"].append(f"Missing test files: {', '.join(missing_files)}")

    if not all(providers.values()):
        missing_providers = [provider for provider, configured in providers.items() if not configured]
        report["errors"].append(f"Missing database providers: {', '.join(missing_providers)}")

    report["summary"] = {
        "total_checks": total_checks,
        "passed_checks": passed_checks,
        "pass_rate": passed_checks / total_checks if total_checks > 0 else 0,
        "status": "PASS" if passed_checks == total_checks else "PARTIAL" if passed_checks > 0 else "FAIL",
        "error_count": len(report["errors"]),
        "errors": report["errors"]
    }

    return report

def print_verification_report(report: Dict[str, Any]):
    """Print the verification report in a readable format."""
    print("=" * 80)
    print("MULTI-DATABASE TEST SETUP VERIFICATION REPORT")
    print("=" * 80)

    # Print metadata
    print(f"Generated: {report['metadata']['timestamp']}")
    print(f"Python: {report['metadata']['python_version']}")
    print(f"Working Directory: {report['metadata']['working_directory']}")
    print()

    # Print summary
    summary = report['summary']
    print(f"SUMMARY: {summary['status']}")
    print(f"Total Checks: {summary['total_checks']}")
    print(f"Passed Checks: {summary['passed_checks']}")
    print(f"Pass Rate: {summary['pass_rate']:.1%}")
    print()

    # Print structure check
    print("STRUCTURE CHECK:")
    structure = report['structure_check']

    print("  Dependencies:")
    for dep, installed in structure['dependencies'].items():
        print(f"    {dep}: {'✓' if installed else '✗'}")

    print("  JAR Files:")
    for db_type, exists in structure['jar_files'].items():
        print(f"    {db_type}: {'✓' if exists else '✗'}")

    print("  Test Files:")
    for file_name, exists in structure['test_files'].items():
        print(f"    {file_name}: {'✓' if exists else '✗'}")

    print("  Providers:")
    for provider_name, configured in structure['providers'].items():
        print(f"    {provider_name}: {'✓' if configured else '✗'}")

    print()

    # Print configuration verification
    print("CONFIGURATION VERIFICATION:")
    configs = report['configuration_verification']
    for db_type, verification in configs.items():
        print(f"  {db_type.upper()}:")
        print(f"    Found: {'✓' if verification['found'] else '✗'}")
        print(f"    Driver Class: {'✓' if verification['driver_class_match'] else '✗'}")
        print(f"    URL Template: {'✓' if verification['url_template_match'] else '✗'}")
        print(f"    User: {'✓' if verification['user_match'] else '✗'}")
        print(f"    Password: {'✓' if verification['password_match'] else '✗'}")

    print()

    # Print connection tests
    print("CONNECTION TESTS:")
    connections = report['connection_tests']
    for db_type, success in connections.items():
        print(f"  {db_type.upper()}: {'✓' if success else '✗'}")

    print()

    # Print final status
    print("=" * 80)
    if summary['status'] == "PASS":
        print("✓ ALL CHECKS PASSED - Multi-database testing is ready!")
    elif summary['status'] == "PARTIAL":
        print("⚠ SOME CHECKS FAILED - Multi-database testing may have limitations")
        if summary.get('error_count', 0) > 0:
            print("\nERRORS DETECTED:")
            for error in summary.get('errors', []):
                print(f"  - {error}")
    else:
        print("✗ SETUP FAILED - Multi-database testing cannot proceed")
        if summary.get('error_count', 0) > 0:
            print("\nERRORS DETECTED:")
            for error in summary.get('errors', []):
                print(f"  - {error}")

    print("=" * 80)

def save_verification_report(report: Dict[str, Any], file_path: str = "multi_database_verification_report.json"):
    """Save the verification report to a JSON file."""
    try:
        with open(file_path, 'w') as f:
            json.dump(report, f, indent=2)
        logger.info(f"Verification report saved to: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving verification report: {e}")
        return False

def main():
    """Main verification function."""
    print("Verifying multi-database test setup...")
    print("This may take a few moments as we test database connections...")

    # Generate comprehensive report
    report = generate_verification_report()

    # Print report
    print_verification_report(report)

    # Save report
    save_verification_report(report)

    # Return exit code based on status
    if report['summary']['status'] == "PASS":
        return 0
    elif report['summary']['status'] == "PARTIAL":
        return 1
    else:
        return 2

if __name__ == "__main__":
    sys.exit(main())
