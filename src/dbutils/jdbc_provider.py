"""
JDBC Provider integration for Python/Qt using JayDeBeApi + JPype.

This module provides a thin abstraction around JDBC connections so the rest of
the app can execute SQL queries generically. It supports a provider registry
that can be configured via GUI and persisted to a JSON file.

Design goals:
- Keep Python + Qt app. Use JDBC drivers (redistributable/licensed) via JVM.
- Avoid tight coupling to any specific DB vendor.
- Provide simple query execution returning list[dict] for GUI models.

Flatpak notes:
- You will need to bundle a Java runtime (e.g., OpenJDK) and the JDBC driver JARs.
- Set JAVA_HOME or ensure the JVM is discoverable. JPype will launch JVM.
- The providers.json can include relative JAR paths bundled with the app.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    import jaydebeapi
    import jpype
except Exception as _exc:
    jpype = None
    jaydebeapi = None
    logger.warning("JDBC bridge libraries not available: %s", _exc)


CONFIG_DIR = os.environ.get("DBUTILS_CONFIG_DIR", os.path.expanduser("~/.config/dbutils"))
PROVIDERS_JSON = os.path.join(CONFIG_DIR, "providers.json")


@dataclass
class JDBCProvider:
    name: str
    driver_class: str
    jar_path: str
    url_template: str  # e.g., "jdbc:db2://{host}:{port}/{database}"
    default_user: Optional[str] = None
    default_password: Optional[str] = None
    extra_properties: Optional[Dict[str, str]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "driver_class": self.driver_class,
            "jar_path": self.jar_path,
            "url_template": self.url_template,
            "default_user": self.default_user,
            "default_password": self.default_password,
            "extra_properties": self.extra_properties or {},
        }

    @staticmethod
    def from_dict(d: Dict[str, Any]) -> "JDBCProvider":
        return JDBCProvider(
            name=d.get("name") or "Unnamed",
            driver_class=d["driver_class"],
            jar_path=d["jar_path"],
            url_template=d["url_template"],
            default_user=d.get("default_user"),
            default_password=d.get("default_password"),
            extra_properties=d.get("extra_properties", {}),
        )


class ProviderRegistry:
    """Manages JDBC providers persisted in a JSON config file."""

    def __init__(self, config_path: str = PROVIDERS_JSON):
        self.config_path = config_path
        self.providers: Dict[str, JDBCProvider] = {}
        self._load()

    def _load(self) -> None:
        try:
            if not os.path.isdir(CONFIG_DIR):
                os.makedirs(CONFIG_DIR, exist_ok=True)
            if not os.path.isfile(self.config_path):
                # Initialize with an example provider stub for DB2/H2
                example = [
                    JDBCProvider(
                        name="H2 (Embedded)",
                        driver_class="org.h2.Driver",
                        jar_path=os.path.join(os.path.dirname(__file__), "..", "..", "jars", "h2.jar"),
                        url_template="jdbc:h2:mem:{database};DB_CLOSE_DELAY=-1",
                        default_user="sa",
                        default_password="",
                    ).to_dict(),
                ]
                with open(self.config_path, "w", encoding="utf-8") as f:
                    json.dump(example, f, indent=2)
            with open(self.config_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
            self.providers = {p["name"]: JDBCProvider.from_dict(p) for p in raw}
        except Exception as e:
            logger.error("Failed to load JDBC providers: %s", e)
            self.providers = {}

    def save(self) -> None:
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump([p.to_dict() for p in self.providers.values()], f, indent=2)
        except Exception as e:
            logger.error("Failed to save JDBC providers: %s", e)

    def add_or_update(self, provider: JDBCProvider) -> None:
        self.providers[provider.name] = provider
        self.save()

    def remove(self, name: str) -> None:
        if name in self.providers:
            self.providers.pop(name)
            self.save()

    def get(self, name: str) -> Optional[JDBCProvider]:
        return self.providers.get(name)

    def list_names(self) -> List[str]:
        return sorted(self.providers.keys())


class JDBCConnection:
    """Wraps a JDBC connection via JayDeBeApi, returning rows as dicts."""

    def __init__(
        self,
        provider: JDBCProvider,
        url_params: Dict[str, Any],
        user: Optional[str] = None,
        password: Optional[str] = None,
    ):
        if jaydebeapi is None or jpype is None:
            raise RuntimeError("JDBC bridge libraries (JayDeBeApi/JPype1) are not installed")
        self.provider = provider
        self.url = provider.url_template.format(**url_params)
        self.user = user if user is not None else provider.default_user
        self.password = password if password is not None else provider.default_password
        self.props = provider.extra_properties or {}
        self._conn = None

    def _ensure_jvm(self):
        if jpype is None:
            raise RuntimeError("JPype not available")
        if not jpype.isJVMStarted():
            # Try to start JVM with explicit JVM path and classpath including the driver jar
            # Use system Java only (no bundled JDK fallback)
            try:
                jvm_path = None
                if os.environ.get("JAVA_HOME"):
                    # Construct libjvm path via JPype helper when JAVA_HOME is set
                    try:
                        jvm_path = jpype.getDefaultJVMPath()
                    except Exception:
                        jvm_path = None

                if not jvm_path:
                    # Last resort: try to find system Java
                    try:
                        jvm_path = jpype.getDefaultJVMPath()
                    except Exception:
                        raise RuntimeError("No Java runtime found. Set JAVA_HOME or ensure Java is in PATH.")

                # Build classpath: include primary driver JAR and allow additional jars via env
                cp_entries = [self.provider.jar_path]
                extra_cp = os.environ.get("DBUTILS_JDBC_CLASSPATH")
                if extra_cp:
                    # Support ':' separated paths (Unix) or ';' (Windows)
                    sep = ";" if ";" in extra_cp and os.name == "nt" else ":"
                    cp_entries.extend([p for p in extra_cp.split(sep) if p])
                classpath = os.pathsep.join(cp_entries)

                jvm_args = [f"-Djava.class.path={classpath}"]
                jpype.startJVM(jvm_path, *jvm_args)
            except Exception as e:
                raise RuntimeError(f"Failed to start JVM: {e}") from e

    def connect(self):
        self._ensure_jvm()
        try:
            self._conn = jaydebeapi.connect(
                self.provider.driver_class,
                self.url,
                [self.user or "", self.password or ""],
                self.provider.jar_path,
            )
        except Exception as e:
            raise RuntimeError(f"JDBC connection failed: {e}") from e
        return self

    def close(self):
        try:
            if self._conn:
                self._conn.close()
        except Exception:
            pass
        finally:
            self._conn = None

    def query(self, sql: str) -> List[Dict[str, Any]]:
        if self._conn is None:
            raise RuntimeError("Connection not established")
        cur = self._conn.cursor()
        try:
            cur.execute(sql)
            # Attempt to fetch column names from cursor description
            cols = [d[0] for d in (cur.description or [])]
            rows_out: List[Dict[str, Any]] = []
            for row in cur.fetchall():
                # Row may be a tuple; zip with columns
                try:
                    rows_out.append(dict(zip(cols, row)))
                except Exception:
                    # Fallback to sequential index mapping
                    rows_out.append({str(i): v for i, v in enumerate(row)})
            return rows_out
        finally:
            try:
                cur.close()
            except Exception:
                pass


# Simple facade for the rest of the app
_registry: Optional[ProviderRegistry] = None


def get_registry() -> ProviderRegistry:
    global _registry
    if _registry is None:
        _registry = ProviderRegistry()
    return _registry


def connect(
    provider_name: str, url_params: Dict[str, Any], user: Optional[str] = None, password: Optional[str] = None
) -> JDBCConnection:
    reg = get_registry()
    provider = reg.get(provider_name)
    if not provider:
        raise KeyError(f"Provider '{provider_name}' not found")
    conn = JDBCConnection(provider, url_params, user=user, password=password)
    return conn.connect()
