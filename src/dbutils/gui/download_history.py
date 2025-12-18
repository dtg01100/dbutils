"""
Download History Module - Track and manage JDBC driver download history.

This module provides functionality to track download history, maintain
records of previous downloads, and provide historical statistics.
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Union

from .jdbc_driver_downloader import JDBCDriverRegistry


class DownloadRecord:
    """Represents a single download record."""

    def __init__(
        self,
        database_type: str,
        downloaded_at: Optional[datetime] = None,
        file_path: Optional[str] = None,
        file_size: Optional[int] = None,
        version: Optional[str] = None,
        url: Optional[str] = None,
        success: bool = True,
        error_message: Optional[str] = None,
        download_duration: Optional[float] = None,
    ):
        self.database_type = database_type
        self.downloaded_at = downloaded_at or datetime.now()
        self.file_path = file_path
        self.file_size = file_size
        self.version = version
        self.url = url
        self.success = success
        self.error_message = error_message
        self.download_duration = download_duration

    def to_dict(self) -> Dict:
        """Convert the download record to a dictionary."""
        return {
            "database_type": self.database_type,
            "downloaded_at": self.downloaded_at.isoformat() if self.downloaded_at else None,
            "file_path": self.file_path,
            "file_size": self.file_size,
            "version": self.version,
            "url": self.url,
            "success": self.success,
            "error_message": self.error_message,
            "download_duration": self.download_duration,
        }

    @classmethod
    def from_dict(cls, data: Dict) -> "DownloadRecord":
        """Create a DownloadRecord from a dictionary."""
        downloaded_at = None
        if data.get("downloaded_at"):
            try:
                downloaded_at = datetime.fromisoformat(data["downloaded_at"])
            except ValueError:
                # Fallback for different timestamp formats
                pass

        return cls(
            database_type=data.get("database_type", ""),
            downloaded_at=downloaded_at,
            file_path=data.get("file_path"),
            file_size=data.get("file_size"),
            version=data.get("version"),
            url=data.get("url"),
            success=data.get("success", True),
            error_message=data.get("error_message"),
            download_duration=data.get("download_duration"),
        )


class DownloadHistoryManager:
    """Manages the history of JDBC driver downloads."""

    def __init__(self):
        self.config_dir = os.environ.get("DBUTILS_CONFIG_DIR", os.path.expanduser("~/.config/dbutils"))
        self.history_file = os.path.join(self.config_dir, "download_history.json")
        os.makedirs(self.config_dir, exist_ok=True)
        self.records = self._load_history()

    def _load_history(self) -> List[DownloadRecord]:
        """Load download history from the file."""
        if not os.path.exists(self.history_file):
            return []

        try:
            with open(self.history_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            records = []
            if isinstance(data, list):
                for record_data in data:
                    if isinstance(record_data, dict):
                        records.append(DownloadRecord.from_dict(record_data))
            return records
        except Exception as e:
            print(f"Error loading download history: {e}")
            return []

    def _save_history(self) -> bool:
        """Save download history to the file."""
        try:
            with open(self.history_file, "w", encoding="utf-8") as f:
                json.dump([record.to_dict() for record in self.records], f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving download history: {e}")
            return False

    def add_record(self, record: DownloadRecord) -> bool:
        """Add a new download record to history."""
        self.records.append(record)
        # Keep only the last 100 records to avoid unlimited growth
        if len(self.records) > 100:
            self.records = self.records[-100:]
        return self._save_history()

    def get_recent_downloads(self, limit: int = 10) -> List[DownloadRecord]:
        """Get the most recent download records."""
        return self.records[-limit:] if self.records else []

    def get_successful_downloads(self) -> List[DownloadRecord]:
        """Get all successful download records."""
        return [record for record in self.records if record.success]

    def get_failed_downloads(self) -> List[DownloadRecord]:
        """Get all failed download records."""
        return [record for record in self.records if not record.success]

    def get_downloads_by_type(self, database_type: str) -> List[DownloadRecord]:
        """Get all downloads for a specific database type."""
        return [
            record for record in self.records
            if record.database_type.lower() == database_type.lower()
        ]

    def get_download_stats(self) -> Dict[str, Union[int, float]]:
        """Get statistics about download history."""
        total_downloads = len(self.records)
        successful_downloads = len(self.get_successful_downloads())
        failed_downloads = len(self.get_failed_downloads())

        success_rate = (successful_downloads / total_downloads * 100) if total_downloads > 0 else 0

        # Calculate average download duration for successful downloads
        successful_with_duration = [r for r in self.get_successful_downloads() if r.download_duration is not None]
        avg_duration = None
        if successful_with_duration:
            avg_duration = sum(r.download_duration for r in successful_with_duration) / len(successful_with_duration)

        # Group by database type
        type_counts = {}
        for record in self.records:
            db_type = record.database_type
            if db_type in type_counts:
                type_counts[db_type] += 1
            else:
                type_counts[db_type] = 1

        return {
            "total_downloads": total_downloads,
            "successful_downloads": successful_downloads,
            "failed_downloads": failed_downloads,
            "success_rate_percent": success_rate,
            "average_duration_seconds": avg_duration,
            "downloads_by_type": type_counts,
        }

    def clear_history(self) -> bool:
        """Clear all download history."""
        self.records = []
        return self._save_history()

    def export_history(self, export_path: str) -> bool:
        """Export download history to a JSON file."""
        try:
            with open(export_path, "w", encoding="utf-8") as f:
                json.dump([record.to_dict() for record in self.records], f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting download history: {e}")
            return False

    def get_driver_info_from_history(self, database_type: str) -> Optional[Dict]:
        """Get driver information from history and registry for a specific database type."""
        # Get from registry first
        driver_info = JDBCDriverRegistry.get_driver_info(database_type)
        if not driver_info:
            return None

        # Enhance with history data
        recent_downloads = self.get_downloads_by_type(database_type)
        if recent_downloads:
            latest_download = recent_downloads[-1]  # Most recent
            return {
                "name": driver_info.name,
                "driver_class": driver_info.driver_class,
                "download_url": driver_info.download_url,
                "license": driver_info.license,
                "min_java_version": driver_info.min_java_version,
                "description": driver_info.description,
                "recommended_version": driver_info.recommended_version,
                "latest_downloaded_version": latest_download.version,
                "last_downloaded_at": latest_download.downloaded_at.isoformat() if latest_download.downloaded_at else None,
                "last_download_success": latest_download.success,
                "last_file_path": latest_download.file_path,
                "last_file_size": latest_download.file_size,
            }

        return {
            "name": driver_info.name,
            "driver_class": driver_info.driver_class,
            "download_url": driver_info.download_url,
            "license": driver_info.license,
            "min_java_version": driver_info.min_java_version,
            "description": driver_info.description,
            "recommended_version": driver_info.recommended_version,
            "latest_downloaded_version": None,
            "last_downloaded_at": None,
            "last_download_success": None,
            "last_file_path": None,
            "last_file_size": None,
        }


# Global instance
download_history = DownloadHistoryManager()


def add_download_record(
    database_type: str,
    file_path: Optional[str] = None,
    file_size: Optional[int] = None,
    version: Optional[str] = None,
    url: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    download_duration: Optional[float] = None,
) -> bool:
    """
    Add a download record to the history.
    
    Args:
        database_type: Type of database (e.g., 'postgresql', 'mysql')
        file_path: Path where the JAR file was downloaded
        file_size: Size of the downloaded file in bytes
        version: Version of the driver that was downloaded
        url: URL from which the driver was downloaded
        success: Whether the download was successful
        error_message: Error message if download failed
        download_duration: Time taken to download in seconds
        
    Returns:
        True if record was added successfully, False otherwise
    """
    record = DownloadRecord(
        database_type=database_type,
        file_path=file_path,
        file_size=file_size,
        version=version,
        url=url,
        success=success,
        error_message=error_message,
        download_duration=download_duration,
    )
    return download_history.add_record(record)


def get_recent_downloads(limit: int = 10) -> List[DownloadRecord]:
    """Get the most recent download records."""
    return download_history.get_recent_downloads(limit)


def get_download_stats() -> Dict[str, Union[int, float]]:
    """Get statistics about download history."""
    return download_history.get_download_stats()


def get_driver_download_info(database_type: str) -> Optional[Dict]:
    """Get driver information enhanced with download history."""
    return download_history.get_driver_info_from_history(database_type)


def clear_download_history() -> bool:
    """Clear all download history."""
    return download_history.clear_history()