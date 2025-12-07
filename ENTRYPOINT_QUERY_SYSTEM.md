# Entrypoint Query System Documentation

## Overview

The Entrypoint Query System provides a flexible and configurable way to manage database schema discovery queries for different database types. This system allows for:

1. **Default entrypoint queries** for each supported database type
2. **Custom entrypoint queries** that can be defined by users
3. **Configuration management** with fallback to hardcoded defaults
4. **Integration with the JDBC provider system**

## Key Components

### 1. EntrypointQuerySet

A data class that represents a set of entrypoint queries for a database type:

```python
@dataclass
class EntrypointQuerySet:
    identity_query: str = ""          # Query to validate connection and get identity
    schema_query: str = ""           # Query to discover database schema
    database_info_query: str = ""    # Query to get database version/info
```

### 2. EntrypointQueryManager

The main manager class that handles loading, saving, and retrieving entrypoint queries.

**Key Features:**

- **Default Queries**: Pre-configured queries for 8 database types (PostgreSQL, MySQL, MariaDB, Oracle, SQL Server, DB2, SQLite, H2)
- **Custom Queries**: User-defined query sets for specific use cases
- **Configuration**: JSON-based configuration with automatic fallback
- **Caching**: Persistent storage of custom query sets

### 3. EnhancedProviderRegistry Integration

The JDBC provider registry has been enhanced to support entrypoint queries:

- Each provider can specify a `custom_entrypoint_query_set`
- Automatic query resolution based on provider category
- Seamless integration with existing provider management

## Supported Database Types

The system includes default entrypoint queries for these database types:

| Database Type | Identity Query | Schema Query | Database Info Query |
|---------------|----------------|---------------|---------------------|
| **PostgreSQL** | `SELECT CURRENT_TIMESTAMP` | `information_schema.tables` | `version()` |
| **MySQL** | `SELECT NOW()` | `information_schema.tables` | `VERSION()` |
| **MariaDB** | `SELECT NOW()` | `information_schema.tables` | `VERSION()` |
| **Oracle** | `SELECT SYSTIMESTAMP FROM dual` | `all_tables` | `v$version` |
| **SQL Server** | `SELECT GETDATE()` | `information_schema.tables` | `@@VERSION` |
| **DB2** | `SELECT CURRENT_TIMESTAMP FROM SYSIBM.SYSDUMMY1` | `syscat.tables` | `sysibm.sysversions` |
| **SQLite** | `SELECT datetime('now')` | `sqlite_master` | `sqlite_version()` |
| **H2** | `SELECT CURRENT_TIMESTAMP` | `information_schema.tables` | `H2VERSION()` |

## Configuration Files

### 1. Package Default Configuration

Location: `src/dbutils/config/entrypoint_queries.json`

This file contains the default entrypoint queries for all supported database types and serves as the fallback when no user configuration exists.

### 2. User Configuration

Location: `~/.config/dbutils/entrypoint_queries.json`

This file stores:
- Custom entrypoint query sets defined by the user
- Any overrides to default queries

## Usage Examples

### Basic Usage

```python
from dbutils.config.entrypoint_query_manager import get_default_entrypoint_query_manager

# Get the default manager
manager = get_default_entrypoint_query_manager()

# Get queries for a specific database type
postgres_queries = manager.get_query_set_or_default("PostgreSQL")

# Access individual queries
identity_query = manager.get_identity_query("MySQL")
schema_query = manager.get_schema_query("PostgreSQL")
db_info_query = manager.get_database_info_query("SQLite")
```

### Custom Query Sets

```python
from dbutils.config.entrypoint_query_manager import EntrypointQuerySet

# Create a custom query set
custom_set = EntrypointQuerySet(
    identity_query="SELECT CURRENT_TIMESTAMP as custom_identity",
    schema_query="SELECT * FROM custom_schema_tables WHERE schema = 'MYAPP'",
    database_info_query="SELECT 'Custom DB v1.0' as db_version"
)

# Add the custom query set
manager.add_custom_query_set("MyApp Queries", custom_set)

# Use the custom query set
queries = manager.get_query_set("PostgreSQL", "MyApp Queries")
```

### Integration with JDBC Providers

```python
from dbutils.enhanced_jdbc_provider import EnhancedProviderRegistry

# Get the provider registry
registry = EnhancedProviderRegistry()

# Create a provider with custom entrypoint queries
provider = JDBCProvider(
    name="My Production DB",
    category="PostgreSQL",
    driver_class="org.postgresql.Driver",
    jar_path="/path/to/postgresql.jar",
    url_template="jdbc:postgresql://{host}:{port}/{database}",
    custom_entrypoint_query_set="MyApp Queries"  # Use custom queries
)

# Add the provider
registry.add_provider(provider)

# Get entrypoint queries for this provider
query_set = registry.get_entrypoint_query_set("My Production DB")

# The registry will automatically use the custom query set
# specified in the provider configuration
```

## API Reference

### EntrypointQueryManager Methods

#### Configuration Management

- `save_configuration()`: Save current configuration to file
- `_load_configuration()`: Load configuration from file (internal)
- `_load_package_defaults()`: Load defaults from package (internal)
- `_load_hardcoded_defaults()`: Fallback to hardcoded defaults (internal)

#### Query Retrieval

- `get_query_set(db_type: str, custom_name: str = None) -> Optional[EntrypointQuerySet]`
  - Get query set for database type, optionally using custom set
- `get_query_set_or_default(db_type: str, custom_name: str = None) -> EntrypointQuerySet`
  - Get query set with fallback to generic queries
- `get_identity_query(db_type: str, custom_name: str = None) -> str`
  - Get just the identity query
- `get_schema_query(db_type: str, custom_name: str = None) -> str`
  - Get just the schema query
- `get_database_info_query(db_type: str, custom_name: str = None) -> str`
  - Get just the database info query

#### Custom Query Management

- `add_custom_query_set(name: str, query_set: EntrypointQuerySet) -> bool`
  - Add a new custom query set
- `update_custom_query_set(name: str, query_set: EntrypointQuerySet) -> bool`
  - Update an existing custom query set
- `remove_custom_query_set(name: str) -> bool`
  - Remove a custom query set
- `list_custom_query_sets() -> List[str]`
  - List all custom query set names

#### Information Methods

- `list_supported_database_types() -> List[str]`
  - List all supported database types with default queries

### EnhancedProviderRegistry Methods

- `get_entrypoint_query_set(provider_name: str) -> Optional[Dict[str, str]]`
  - Get entrypoint queries for a specific provider
- `get_identity_query(provider_name: str) -> Optional[str]`
  - Get identity query for a provider
- `get_schema_query(provider_name: str) -> Optional[str]`
  - Get schema query for a provider
- `get_database_info_query(provider_name: str) -> Optional[str]`
  - Get database info query for a provider
- `list_available_entrypoint_query_sets() -> List[str]`
  - List all available query sets (default + custom)
- `add_custom_entrypoint_query_set(name: str, query_set: Dict[str, str]) -> bool`
  - Add a custom query set via registry
- `update_custom_entrypoint_query_set(name: str, query_set: Dict[str, str]) -> bool`
  - Update a custom query set via registry
- `remove_custom_entrypoint_query_set(name: str) -> bool`
  - Remove a custom query set via registry

## Configuration File Format

The configuration file uses JSON format with two main sections:

```json
{
  "default_entrypoint_queries": {
    "PostgreSQL": {
      "identity_query": "SELECT CURRENT_TIMESTAMP as current_timestamp",
      "schema_query": "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog', 'information_schema')",
      "database_info_query": "SELECT version() as database_version"
    },
    "MySQL": {
      "identity_query": "SELECT NOW() as current_timestamp",
      "schema_query": "SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('information_schema', 'mysql', 'performance_schema', 'sys')",
      "database_info_query": "SELECT VERSION() as database_version"
    }
  },
  "custom_entrypoint_queries": {
    "MyApp Queries": {
      "identity_query": "SELECT CURRENT_TIMESTAMP as custom_identity",
      "schema_query": "SELECT * FROM custom_schema_tables WHERE schema = 'MYAPP'",
      "database_info_query": "SELECT 'Custom DB v1.0' as db_version"
    }
  }
}
```

## Fallback Behavior

The system has a robust fallback mechanism:

1. **User Configuration** → 2. **Package Configuration** → 3. **Hardcoded Defaults**

If any step fails, the system automatically falls back to the next level, ensuring that entrypoint queries are always available.

## Error Handling

The system includes comprehensive error handling:

- Graceful degradation when configuration files are missing
- Automatic fallback to defaults
- Detailed logging for debugging
- Clear error messages

## Integration Points

### Database Browser

The entrypoint query system integrates with the database browser for:

- **Schema discovery**: Using schema queries to find available tables
- **Connection validation**: Using identity queries to test connections
- **Database information**: Using database info queries for version detection

### JDBC Provider System

- Each provider can specify custom entrypoint queries
- Automatic query resolution based on provider category
- Seamless integration with connection management

## Best Practices

### Creating Effective Entrypoint Queries

1. **Identity Queries**: Should be lightweight and fast-executing
2. **Schema Queries**: Should filter out system tables/schemas
3. **Database Info Queries**: Should return version information

### Performance Considerations

- Avoid complex joins in entrypoint queries
- Filter out system schemas/tables to reduce result size
- Use appropriate database-specific system views

### Security Considerations

- Use parameterized queries where possible
- Avoid queries that require elevated privileges
- Filter sensitive system information

## Troubleshooting

### Common Issues

1. **Custom queries not found**: Check that the custom query set name is spelled correctly
2. **Database type not supported**: The system will fall back to generic queries
3. **Configuration not saved**: Check file permissions in `~/.config/dbutils/`

### Debugging

Enable debug logging:

```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## Future Enhancements

Potential areas for future development:

1. **Query validation**: Validate queries before saving
2. **Query testing**: Test queries against actual database connections
3. **Query performance metrics**: Track and optimize query performance
4. **Query versioning**: Support multiple versions of query sets
5. **Query sharing**: Export/import query sets between installations

## Migration Guide

### From Previous Versions

The entrypoint query system is designed to be backward compatible:

1. Existing providers will continue to work with default queries
2. Custom queries are opt-in functionality
3. No breaking changes to existing APIs

### Configuration Migration

If you have existing custom configurations, they can be migrated by:

1. Creating a custom query set with your existing queries
2. Assigning the custom query set to your providers
3. Testing the new configuration

## Examples

### Example: Custom Oracle Queries

```python
# Create custom Oracle queries for a specific application
oracle_app_queries = EntrypointQuerySet(
    identity_query="SELECT SYSTIMESTAMP as app_timestamp FROM dual",
    schema_query="SELECT owner, table_name FROM all_tables WHERE owner = 'MYAPP'",
    database_info_query="SELECT banner || ' - Custom App' as db_version FROM v$version WHERE rownum = 1"
)

# Add to manager
manager.add_custom_query_set("Oracle App Queries", oracle_app_queries)

# Use with a provider
provider = JDBCProvider(
    name="Oracle Production",
    category="Oracle",
    custom_entrypoint_query_set="Oracle App Queries"
    # ... other provider settings
)
```

### Example: SQLite File-Based Queries

```python
# Custom queries for SQLite file-based databases
sqlite_file_queries = EntrypointQuerySet(
    identity_query="SELECT datetime('now', 'localtime') as local_time",
    schema_query="SELECT name as table_name, type FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE 'android_%'",
    database_info_query="SELECT sqlite_version() || ' - ' || datetime('now', 'localtime') as db_info"
)

manager.add_custom_query_set("SQLite File Queries", sqlite_file_queries)
```

## Conclusion

The Entrypoint Query System provides a powerful and flexible way to manage database schema discovery while maintaining backward compatibility and providing extensive customization options. This system enhances the database browser's ability to work with different database types while allowing users to tailor the behavior to their specific needs.