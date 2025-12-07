# Custom JDBC Provider Support

This document describes the custom JDBC provider feature that allows users to define their own JDBC providers for databases not covered by the existing templates.

## Overview

The custom JDBC provider feature enables users to configure JDBC connections for any database system, even those not included in the predefined templates. This is useful for:

- Proprietary or niche database systems
- Custom JDBC drivers
- Experimental or beta database connections
- Specialized connection configurations

## Features

### 1. Custom Provider Category

A new "Custom" category has been added to the JDBC provider system:

- **Category Name**: "Custom"
- **Driver Class**: Empty (user must specify)
- **URL Template**: `jdbc:{custom}://{host}:{port}/{database}` (user can customize)
- **Default Port**: 0 (user must specify)

### 2. Configuration Files Updated

The following configuration files have been updated to support custom providers:

#### `src/dbutils/config/jdbc_templates.json`

Added a new template entry:

```json
"Custom": {
  "driver_class": "",
  "url_template": "jdbc:{custom}://{host}:{port}/{database}",
  "default_port": 0,
  "description": "Custom JDBC provider - configure all parameters manually"
}
```

#### `src/dbutils/enhanced_jdbc_provider.py`

- Added "Custom" to `STANDARD_CATEGORIES`
- Added Custom template to fallback templates in `PredefinedProviderTemplates._load_templates()`

#### `src/dbutils/config_manager.py`

- Added Custom template to fallback templates in `ConfigurationLoader._get_default_provider_templates()`

### 3. GUI Integration

The provider configuration dialog has been enhanced with:

- **Custom Category Selection**: "Custom" appears in the category dropdown
- **Add Custom Provider Button**: Dedicated button for quick custom provider creation
- **Template Support**: Custom providers can be created from the "Custom" template

## Usage

### Creating a Custom Provider via GUI

1. **Open Provider Configuration**: Launch the JDBC Provider Configuration dialog
2. **Add Custom Provider**: Click the "Add Custom Provider" button
3. **Configure Parameters**:
   - **Name**: Give your provider a descriptive name
   - **Driver Class**: Specify the full JDBC driver class name
   - **JAR Path**: Provide the path to the JDBC driver JAR file
   - **URL Template**: Define the JDBC URL format (can use placeholders like `{host}`, `{port}`, `{database}`)
   - **Connection Details**: Set host, port, database name, username, password
   - **Advanced Properties**: Add any additional JDBC properties as needed

### Creating a Custom Provider Programmatically

```python
from dbutils.enhanced_jdbc_provider import JDBCProvider

custom_provider = JDBCProvider(
    name="My Custom Database",
    category="Custom",
    driver_class="com.example.CustomDriver",
    jar_path="/path/to/custom-driver.jar",
    url_template="jdbc:custom://{host}:{port}/{database}",
    default_host="custom-server",
    default_port=1234,
    default_database="customdb",
    extra_properties={"customProperty": "customValue"}
)
```

### Using Custom Provider Templates

```python
from dbutils.enhanced_jdbc_provider import PredefinedProviderTemplates

templates = PredefinedProviderTemplates()
custom_provider = templates.create_provider_from_template(
    category="Custom",
    name="My Custom Connection",
    host="localhost",
    database="mydb"
)

# Then configure the provider properties as needed
custom_provider.driver_class = "com.example.CustomDriver"
custom_provider.jar_path = "/path/to/driver.jar"
custom_provider.url_template = "jdbc:custom://{host}:{port}/{database}"
```

## Configuration Examples

### Example 1: Custom NoSQL Database

```json
{
  "name": "Custom NoSQL DB",
  "category": "Custom",
  "driver_class": "com.nosql.CustomNoSQLDriver",
  "jar_path": "/opt/nosql/nosql-jdbc.jar",
  "url_template": "jdbc:nosql://{host}:{port}/{keyspace}",
  "default_host": "nosql-server",
  "default_port": 9042,
  "default_database": "main_keyspace",
  "extra_properties": {
    "consistencyLevel": "QUORUM",
    "fetchSize": "1000"
  }
}
```

### Example 2: Legacy Database System

```json
{
  "name": "Legacy DB Connection",
  "category": "Custom",
  "driver_class": "com.legacy.LegacyDriver",
  "jar_path": "/legacy/legacy-jdbc.jar",
  "url_template": "jdbc:legacy://{host}:{port};database={database};schema={schema}",
  "default_host": "legacy-server",
  "default_port": 5000,
  "default_database": "legacy_db",
  "extra_properties": {
    "legacyMode": "true",
    "encoding": "ISO-8859-1"
  }
}
```

## Technical Details

### Template Resolution

The custom provider system follows this resolution order:

1. **User Configuration**: Custom providers defined in `~/.config/dbutils/jdbc_providers.json`
2. **Configuration Files**: Templates from `jdbc_templates.json`
3. **Fallback Templates**: Hardcoded defaults in `enhanced_jdbc_provider.py` and `config_manager.py`

### URL Template Variables

Custom providers support the same URL template variables as standard providers:

- `{host}`: Database host name or IP
- `{port}`: Database port number
- `{database}`: Database name or SID
- `{custom}`: Custom placeholder that can be replaced with any value

### Environment Variable Support

Custom providers support environment variable expansion:

```bash
export DBUTILS_CUSTOM_DRIVER_CLASS="com.example.CustomDriver"
export DBUTILS_CUSTOM_URL_TEMPLATE="jdbc:custom://{host}:{port}/{database}"
```

## Troubleshooting

### Common Issues

1. **Driver Class Not Found**: Ensure the JDBC driver JAR is in the classpath
2. **Connection Failed**: Verify the URL template format matches the driver's expectations
3. **Missing Properties**: Check if the driver requires additional JDBC properties

### Debugging Tips

- Enable debug logging: `export DBUTILS_LOG_LEVEL=DEBUG`
- Check JAR file permissions and paths
- Verify the driver class name is correct
- Test the connection URL format independently

## Best Practices

1. **Descriptive Names**: Use clear, descriptive names for custom providers
2. **Documentation**: Add comments or documentation for custom configurations
3. **Testing**: Test custom providers thoroughly before production use
4. **Backup**: Backup custom provider configurations regularly
5. **Version Control**: Consider version-controlling custom provider definitions

## Future Enhancements

Potential future improvements to the custom provider system:

- **Provider Validation**: Automatic validation of custom provider configurations
- **Template Sharing**: Export/import functionality for custom templates
- **Driver Auto-Detection**: Enhanced driver detection for custom providers
- **Connection Testing**: Built-in connection testing for custom providers
- **GUI Wizards**: Step-by-step wizards for creating complex custom providers

## Support

For issues with custom JDBC providers:

1. Check the application logs for detailed error messages
2. Verify the JDBC driver documentation for correct configuration
3. Consult the database vendor's JDBC documentation
4. Review the custom provider configuration for typos or errors