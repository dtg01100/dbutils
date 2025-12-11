"""
JDBC Driver Registry - Database-specific driver information and download links.

This module provides information about various JDBC drivers for different databases,
including their download locations, recommended versions, and installation instructions.
"""

import os
from typing import Dict, List, NamedTuple, Optional


class JDBCDriverInfo(NamedTuple):
    """Information about a specific JDBC driver."""

    name: str  # Human-readable name
    driver_class: str  # Fully qualified driver class name
    download_url: str  # Primary download location
    alternative_urls: List[str]  # Alternative download locations
    license: str  # License type (e.g., "Commercial", "Apache 2.0", "BSD")
    min_java_version: str  # Minimum required Java version
    description: str  # Brief description
    recommended_version: str  # Recommended version for stability
    maven_artifacts: Optional[List[str]] = None  # Optional maven artifact coordinates like 'group:artifact'
    requires_license: bool = False
    license_url: Optional[str] = None
    license_text: Optional[str] = None


class JDBCDriverRegistry:
    """Registry of JDBC drivers with download information."""

    DRIVERS: Dict[str, JDBCDriverInfo] = {
        # PostgreSQL drivers
        "postgresql": JDBCDriverInfo(
            name="PostgreSQL JDBC Driver",
            driver_class="org.postgresql.Driver",
            download_url="https://github.com/pgjdbc/pgjdbc/releases",
            alternative_urls=[
                "https://repo1.maven.org/maven2/org/postgresql/postgresql/",
                "https://jdbc.postgresql.org/download.html",
            ],
            license="BSD-2-Clause",
            min_java_version="8",
            description="Official PostgreSQL JDBC driver",
            recommended_version="42.6.0",
            maven_artifacts=["org.postgresql:postgresql"],
        ),
        # MySQL drivers
        "mysql": JDBCDriverInfo(
            name="MySQL Connector/J",
            driver_class="com.mysql.cj.jdbc.Driver",
            download_url="https://dev.mysql.com/downloads/connector/j/",
            alternative_urls=[
                "https://repo1.maven.org/maven2/mysql/mysql-connector-java/",
                "https://github.com/mysql/mysql-connector-j/releases",
            ],
            license="GPL-2.0 or Commercial",
            min_java_version="8",
            description="MySQL JDBC Type 4 driver",
            recommended_version="8.0.33",
            maven_artifacts=["mysql:mysql-connector-java"],
        ),
        # MariaDB drivers
        "mariadb": JDBCDriverInfo(
            name="MariaDB Connector/J",
            driver_class="org.mariadb.jdbc.Driver",
            download_url="https://mariadb.com/downloads/connectors/connectors-data-access/jdbc/",
            alternative_urls=[
                "https://repo1.maven.org/maven2/org/mariadb/jdbc/mariadb-java-client/",
                "https://github.com/mariadb-corporation/mariadb-connector-j/releases",
            ],
            license="LGPL-2.1",
            min_java_version="8",
            description="MariaDB JDBC driver",
            recommended_version="3.1.4",
            maven_artifacts=["org.mariadb.jdbc:mariadb-java-client"],
        ),
        # Oracle drivers
        "oracle": JDBCDriverInfo(
            name="Oracle JDBC Driver",
            driver_class="oracle.jdbc.OracleDriver",
            download_url="https://www.oracle.com/database/technologies/appdev/jdbc-downloads.html",
            alternative_urls=[
                "https://repo1.maven.org/maven2/com/oracle/database/jdbc/",
                "https://www.oracle.com/technical-resources/articles/java/index-099297.html",
            ],
            license="Commercial (with free distribution rights)",
            min_java_version="8",
            description="Oracle JDBC driver (ojdbc)",
            recommended_version="21.13.0.0",
            requires_license=True,
            license_url="https://www.oracle.com/database/technologies/appdev/jdbc-downloads.html",
            license_text=(
                "Oracle JDBC drivers are distributed under Oracle terms. "
                "You must accept Oracle's license before downloading and using their drivers."
            ),
        ),
        # Microsoft SQL Server drivers
        "sqlserver": JDBCDriverInfo(
            name="Microsoft JDBC Driver for SQL Server",
            driver_class="com.microsoft.sqlserver.jdbc.SQLServerDriver",
            download_url="https://docs.microsoft.com/en-us/sql/connect/jdbc/download-microsoft-jdbc-driver-for-sql-server",
            alternative_urls=[
                "https://repo1.maven.org/maven2/com/microsoft/sqlserver/mssql-jdbc/",
                "https://github.com/microsoft/mssql-jdbc/releases",
            ],
            license="MIT",
            min_java_version="8",
            description="Microsoft JDBC driver for SQL Server",
            recommended_version="12.4.2.jre11",
            maven_artifacts=["com.microsoft.sqlserver:mssql-jdbc"],
            requires_license=False,
        ),
        # IBM DB2 drivers
        "db2": JDBCDriverInfo(
            name="IBM DB2 JDBC Driver",
            driver_class="com.ibm.db2.jcc.DB2Driver",
            download_url="https://www.ibm.com/support/pages/db2-jdbc-driver-versions-and-downloads",
            alternative_urls=["https://repo1.maven.org/maven2/com/ibm/db2/jcc/", "https://www.ibm.com/products/db2"],
            license="Commercial (with redistribution rights for clients)",
            min_java_version="8",
            description="IBM DB2 JDBC driver",
            recommended_version="11.5.8.0",
            requires_license=True,
            license_url="https://github.com/IBM/JTOpen/releases",
            license_text=(
                "JT400 (JTOpen) releases are provided under the IBM Public License. "
                "Please ensure you accept the license terms where required."
            ),
        ),
        # IBM AS400 / iSeries / IBM i drivers (JT400)
        "jt400": JDBCDriverInfo(
            name="IBM Toolbox for Java (JT400) - AS400/IBM i",
            driver_class="com.ibm.as400.access.AS400JDBCDriver",
            download_url="https://github.com/IBM/JTOpen/releases",
            alternative_urls=[
                "https://repo1.maven.org/maven2/com/ibm/jtopen/jtopen/",
                "https://sourceforge.net/projects/jt400/",
                "https://www.ibm.com/support/pages/node/1524689",
            ],
            license="IBM Public License",
            min_java_version="8",
            description="JDBC driver for IBM i (AS400) systems",
            recommended_version="10.5",
            maven_artifacts=["com.ibm:jtopen"],
        ),
        # SQLite drivers
        "sqlite": JDBCDriverInfo(
            name="SQLite JDBC Driver",
            driver_class="org.sqlite.JDBC",
            download_url="https://github.com/xerial/sqlite-jdbc/releases",
            alternative_urls=[
                "https://repo1.maven.org/maven2/org/xerial/sqlite-jdbc/",
                "https://www.sqlite.org/download.html",
            ],
            license="Apache 2.0 / GNU LGPL",
            min_java_version="8",
            description="SQLite JDBC driver",
            recommended_version="3.42.0.0",
            maven_artifacts=["org.xerial:sqlite-jdbc"],
        ),
        # H2 Database drivers
        "h2": JDBCDriverInfo(
            name="H2 Database Engine",
            driver_class="org.h2.Driver",
            download_url="https://www.h2database.com/html/download.html",
            alternative_urls=[
                "https://repo1.maven.org/maven2/com/h2database/h2/",
                "https://github.com/h2database/h2database/releases",
            ],
            license="MPL 2.0 / EPL 1.0",
            min_java_version="8",
            description="H2 database JDBC driver",
            recommended_version="2.2.224",
            maven_artifacts=["com.h2database:h2"],
        ),
        # Apache Derby drivers
        "derby": JDBCDriverInfo(
            name="Apache Derby Embedded Driver",
            driver_class="org.apache.derby.jdbc.EmbeddedDriver",
            download_url="https://db.apache.org/derby/derby_downloads.html",
            alternative_urls=[
                "https://repo1.maven.org/maven2/org/apache/derby/derby/",
                "https://archive.apache.org/dist/db-derby/",
            ],
            license="Apache 2.0",
            min_java_version="8",
            description="Apache Derby JDBC driver",
            recommended_version="10.15.2.0",
        ),
        # Generic template
        "generic": JDBCDriverInfo(
            name="Generic JDBC Driver",
            driver_class="com.example.Driver",
            download_url="https://repo1.maven.org/maven2/",
            alternative_urls=[
                "https://search.maven.org/",
                "https://mvnrepository.com/",
            ],
            license="N/A",
            min_java_version="8",
            description="Generic JDBC driver template - search Maven Central Repository",
            recommended_version="x.x.x",
        ),
    }

    @classmethod
    def get_driver_info(cls, database_type: str) -> Optional[JDBCDriverInfo]:
        """Get driver information for a specific database type."""
        # Normalize the input (case-insensitive)
        normalized_type = database_type.lower().strip().replace(" ", "")

        # Handle aliases and variations
        if "postgres" in normalized_type or "pgsql" in normalized_type:
            return cls.DRIVERS.get("postgresql")
        elif "mysql" in normalized_type or "maria" in normalized_type:
            # MariaDB is handled separately but both MySQL and MariaDB are common
            if "maria" in normalized_type:
                return cls.DRIVERS.get("mariadb")
            else:
                return cls.DRIVERS.get("mysql")
        elif "oracle" in normalized_type:
            return cls.DRIVERS.get("oracle")
        elif (
            "sqlserver" in normalized_type
            or "mssql" in normalized_type
            or "sql server" in normalized_type.replace("_", " ")
        ):
            return cls.DRIVERS.get("sqlserver")
        elif (
            # Check for DB2 for i (AS/400) before generic DB2
            "db2fori" in normalized_type
            or "jt400" in normalized_type.lower()
            or "as400" in normalized_type.lower()
            or "ibmi" in normalized_type.lower()
            or "ibm i" in normalized_type.replace("_", " ")
        ):
            return cls.DRIVERS.get("jt400")
        elif "db2" in normalized_type.lower():
            # This handles "DB2 LUW" and "DB2 z/OS"
            return cls.DRIVERS.get("db2")
        elif "sqlite" in normalized_type:
            return cls.DRIVERS.get("sqlite")
        elif "h2" in normalized_type:
            return cls.DRIVERS.get("h2")
        elif "derby" in normalized_type:
            return cls.DRIVERS.get("derby")

        # Direct lookup
        return cls.DRIVERS.get(normalized_type)

    @classmethod
    def get_all_database_types(cls) -> List[str]:
        """Get all supported database types."""
        return list(cls.DRIVERS.keys())

    @classmethod
    def get_quick_download_links(cls) -> Dict[str, str]:
        """Get a mapping of database types to their primary download URLs."""
        return {db_type: info.download_url for db_type, info in cls.DRIVERS.items()}


# Default directory for JDBC drivers
DEFAULT_DRIVER_DIR = os.path.expanduser("~/.config/dbutils/drivers")


def get_driver_directory() -> str:
    """Get the directory where JDBC drivers should be stored."""
    driver_dir = os.environ.get("DBUTILS_DRIVER_DIR", DEFAULT_DRIVER_DIR)
    os.makedirs(driver_dir, exist_ok=True)
    return driver_dir


def suggest_jar_filename(db_type: str, version: str = "latest") -> str:
    """Suggest a filename for a downloaded JAR based on database type."""
    if db_type == "postgresql":
        return f"postgresql-{version}.jar" if version != "latest" else "postgresql-latest.jar"
    elif db_type == "mysql":
        return f"mysql-connector-java-{version}.jar" if version != "latest" else "mysql-connector-java-latest.jar"
    elif db_type == "mariadb":
        return f"mariadb-java-client-{version}.jar" if version != "latest" else "mariadb-java-client-latest.jar"
    elif db_type == "oracle":
        return f"ojdbc{version}.jar" if version != "latest" else "ojdbc-latest.jar"
    elif db_type == "sqlserver":
        return f"mssql-jdbc-{version}.jar" if version != "latest" else "mssql-jdbc-latest.jar"
    elif db_type == "db2":
        return f"db2jcc-{version}.jar" if version != "latest" else "db2jcc-latest.jar"
    elif db_type == "jt400":
        return f"jtopen-{version}.jar" if version != "latest" else "jtopen-latest.jar"
    elif db_type == "sqlite":
        return f"sqlite-jdbc-{version}.jar" if version != "latest" else "sqlite-jdbc-latest.jar"
    elif db_type == "h2":
        return f"h2-{version}.jar" if version != "latest" else "h2-latest.jar"
    else:
        return f"{db_type}-jdbc-driver.jar"
