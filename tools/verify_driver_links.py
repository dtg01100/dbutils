#!/usr/bin/env python3
# We'll import the registry & coords from the project
import json
import ssl
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dbutils.gui.jdbc_auto_downloader import JDBC_DRIVER_COORDINATES, get_jdbc_driver_url
from dbutils.gui.jdbc_driver_downloader import JDBCDriverRegistry

# SSL context that ignores certificate verification for the purpose of this simple check
ssl_ctx = ssl.create_default_context()
ssl_ctx.check_hostname = False
ssl_ctx.verify_mode = ssl.CERT_NONE

results = []


def check_url(url, method="HEAD"):
    try:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "dbutils-link-checker/1.0"})
        with urllib.request.urlopen(req, context=ssl_ctx, timeout=15) as resp:
            return resp.status, resp.geturl()
    except urllib.error.HTTPError as e:
        # Try GET fallback for servers that don't support HEAD
        if method == "HEAD":
            try:
                req2 = urllib.request.Request(url, method="GET", headers={"User-Agent": "dbutils-link-checker/1.0"})
                with urllib.request.urlopen(req2, context=ssl_ctx, timeout=15) as r2:
                    return r2.status, r2.geturl()
            except Exception:
                pass
        return e.code, None
    except urllib.error.URLError:
        return None, None
    except Exception:
        return None, None


# Check JDBCDriverRegistry download_url and license urls
for db_type, info in JDBCDriverRegistry.DRIVERS.items():
    entry = {
        "db_type": db_type,
        "download_url": info.download_url,
        "download_url_ok": None,
        "actual_redirect": None,
        "license_url": getattr(info, "license_url", None),
        "license_url_ok": None,
        "maven_metadata_url": None,
        "maven_metadata_ok": None,
        "maven_jar_url": None,
        "maven_jar_ok": None,
    }
    # Check download_url
    if info.download_url:
        status, redirect = check_url(info.download_url, method="HEAD")
        entry["download_url_ok"] = status == 200
        entry["actual_redirect"] = redirect
    # Check license URL
    if getattr(info, "license_url", None):
        status, redirect = check_url(info.license_url, method="HEAD")
        entry["license_url_ok"] = status == 200
    # Check maven metadata if any
    coords = JDBC_DRIVER_COORDINATES.get(db_type)
    if coords:
        entry["maven_metadata_url"] = coords.get("metadata_url")
        if coords.get("metadata_url"):
            status, redirect = check_url(coords.get("metadata_url"), method="GET")
            entry["maven_metadata_ok"] = status == 200
        # Check constructed jar URL for 'latest' and recommended_version
        # Use recommended version if available, else 'latest'
        recommended = getattr(info, "recommended_version", "latest")
        jar_url = get_jdbc_driver_url(db_type, version=recommended or "latest")
        entry["maven_jar_url"] = jar_url
        if jar_url:
            status, redirect = check_url(jar_url, method="HEAD")
            if status != 200:
                # Some servers may not respond to HEAD for jar files; try GET as fallback
                status, redirect = check_url(jar_url, method="GET")
            entry["maven_jar_ok"] = status == 200
    results.append(entry)

# Print summary
ok_count = sum(1 for r in results if r["download_url_ok"])
print(f"Checked {len(results)} drivers. {ok_count} primary URLs returned HTTP 200.")
for r in results:
    print("\n" + "=" * 80)
    print(f"DB Type: {r['db_type']}")
    print(f"  Download URL: {r['download_url']} -> OK: {r['download_url_ok']} (redirect {r['actual_redirect']})")
    if r["license_url"]:
        print(f"  License URL: {r['license_url']} -> OK: {r['license_url_ok']}")
    if r["maven_metadata_url"]:
        print(f"  Maven metadata URL: {r['maven_metadata_url']} -> OK: {r['maven_metadata_ok']}")
    if r["maven_jar_url"]:
        print(f"  Maven jar URL: {r['maven_jar_url']} -> OK: {r['maven_jar_ok']}")

# Save results to file
with open(ROOT / "tools" / "verify_links_results.json", "w") as fh:
    json.dump(results, fh, indent=2)

# Exit non-zero if any critical link is broken (download_url not ok and maven_jar not ok)
critical_failures = [r for r in results if not (r["download_url_ok"] or r["maven_jar_ok"])]
if critical_failures:
    print("\nCritical failures detected:")
    for r in critical_failures:
        print(f"  {r['db_type']}: {r['download_url']} maven jar {r['maven_jar_url']}")
    sys.exit(2)

print("\nAll checks completed.")
sys.exit(0)
