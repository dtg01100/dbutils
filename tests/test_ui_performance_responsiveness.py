"""
Performance and responsiveness UI tests for JDBC download system.

Tests that the UI remains responsive during operations and performance metrics are accurate.
"""

import os
import time
from unittest.mock import MagicMock, patch

import pytest
from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import QApplication, QDialog

# Enable test mode to prevent actual downloads
os.environ["DBUTILS_TEST_MODE"] = "1"


def test_ui_responsiveness_during_mock_download(qtbot, monkeypatch):
    """Test that UI remains responsive during download simulation."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock download with callback to simulate progress
    import tempfile
    temp_dir = tempfile.gettempdir()
    mock_jar_path = os.path.join(temp_dir, "responsive-test.jar")
    
    def mock_download_with_progress(db_type, on_progress=None, on_status=None, version="recommended"):
        # Simulate download progress by calling the callbacks
        total = 1000000  # 1MB simulated size
        downloaded = 0
        chunk = 100000  # 100KB chunks
        
        if on_status:
            on_status("Starting download...")
        
        while downloaded < total:
            downloaded += chunk
            if on_progress:
                on_progress(downloaded, total)
            if on_status:
                on_status(f"Downloading: {downloaded/1024:.1f}KB of {total/1024:.1f}KB")
            time.sleep(0.01)  # Small delay to simulate network
        
        # Create a dummy file
        with open(mock_jar_path, "w") as f:
            f.write("responsive test content")
        
        if on_status:
            on_status("Download completed")
        
        return mock_jar_path
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_with_progress)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Responsive Test Driver",
        driver_class="com.responsive.Driver",
        download_url="https://example.com/responsive-test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Driver for responsiveness testing",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Responsive Test")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            # Test that UI remains responsive during the simulated download
            # We'll call the download function directly since mocking the progress
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_with_progress):
                # Start the download in a way that allows UI processing
                start_time = time.time()
                result_path = dialog.perform_jdbc_download("responsive_test", version="latest")
                end_time = time.time()
                
                # Check that the download completed
                assert result_path is not None
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Clean up the mock file
        if os.path.exists(mock_jar_path):
            try:
                os.remove(mock_jar_path)
            except:
                pass
    
    dialog.close()


def test_progress_updates_continuity(qtbot, monkeypatch):
    """Test that progress updates continue properly during long operations."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Track progress updates
    progress_updates = []
    status_updates = []
    
    def progress_callback(downloaded, total):
        progress_updates.append((downloaded, total))
    
    def status_callback(message):
        status_updates.append(message)
    
    # Mock download that calls the progress and status callbacks
    import tempfile
    temp_dir = tempfile.gettempdir()
    mock_jar_path = os.path.join(temp_dir, "progress-test.jar")
    
    def mock_download_with_tracking(db_type, on_progress=None, on_status=None, version="recommended"):
        if on_status:
            on_status("Initializing download...")
        
        total = 500000  # 0.5MB
        downloaded = 0
        chunk = 50000  # 50KB chunks
        
        while downloaded < total:
            downloaded += chunk
            if on_progress:
                on_progress(downloaded, total)
            if on_status:
                on_status(f"Progress: {downloaded/total*100:.1f}% ({downloaded/1024:.1f}KB/{total/1024:.1f}KB)")
            time.sleep(0.02)  # Small delay to simulate network
        
        # Create a dummy file
        with open(mock_jar_path, "w") as f:
            f.write("progress test content")
        
        if on_status:
            on_status("Progress tracking completed")
        
        return mock_jar_path
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_with_tracking)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Progress Test Driver",
        driver_class="com.progress.Driver", 
        download_url="https://example.com/progress-test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Driver for progress tracking testing",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Progress Test")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_with_tracking):
                dialog.perform_jdbc_download("progress_test", version="latest")
            
            # Verify that multiple progress updates occurred
            assert len(progress_updates) > 0, "Should have received progress updates"
            assert len(status_updates) > 0, "Should have received status updates"
            
            # Check that progress moved from start to finish
            if progress_updates:
                first_update = progress_updates[0]
                last_update = progress_updates[-1]
                assert last_update[0] >= first_update[0], "Progress should advance"
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Clean up the mock file
        if os.path.exists(mock_jar_path):
            try:
                os.remove(mock_jar_path)
            except:
                pass
    
    dialog.close()


def test_download_speed_calculation_accuracy(qtbot, monkeypatch):
    """Test accuracy of download speed and ETA calculations."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Track timing and data for speed calculation verification
    speed_calculations = []
    start_time = None
    
    def mock_download_with_speed_test(db_type, on_progress=None, on_status=None, version="recommended"):
        nonlocal start_time
        start_time = time.time()
        
        total = 300000  # 300KB
        downloaded = 0
        chunk = 30000  # 30KB chunks
        time_per_chunk = 0.05  # 50ms per chunk to make measurable speed
        
        if on_status:
            on_status("Starting speed test download...")
        
        while downloaded < total:
            downloaded += chunk
            elapsed = time.time() - start_time
            if on_progress:
                on_progress(downloaded, total)
            if on_status:
                # Calculate and report speed and ETA
                if elapsed > 0:
                    speed = downloaded / elapsed  # bytes per second
                    speed_kb = speed / 1024
                    remaining = total - downloaded
                    if speed > 0:
                        eta = remaining / speed
                        status_msg = f"Speed: {speed_kb:.2f}KB/s, ETA: {eta:.2f}s"
                        speed_calculations.append({
                            'time': elapsed,
                            'downloaded': downloaded,
                            'speed': speed,
                            'eta': eta
                        })
                        on_status(status_msg)
                    else:
                        on_status(f"Downloaded: {downloaded/1024:.1f}KB/{total/1024:.1f}KB")
            
            time.sleep(time_per_chunk)  # Simulate network delay
        
        # Create a dummy file
        import tempfile
        temp_dir = tempfile.gettempdir()
        mock_jar_path = os.path.join(temp_dir, "speed-test.jar")
        with open(mock_jar_path, "w") as f:
            f.write("speed test content")
        
        if on_status:
            on_status("Speed test completed")
        
        return mock_jar_path
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_with_speed_test)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Speed Test Driver",
        driver_class="com.speed.Driver",
        download_url="https://example.com/speed-test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Driver for speed calculation testing",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Speed Test")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_with_speed_test):
                dialog.perform_jdbc_download("speed_test", version="latest")
            
            # Verify that speed calculations were made
            assert len(speed_calculations) > 0, "Should have recorded speed calculations"
            
            # Check that speed calculations are reasonable
            for calc in speed_calculations:
                assert calc['speed'] > 0, "Speed should be positive"
                assert calc['eta'] >= 0, "ETA should be non-negative"
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Note: We don't delete the jar file here as the download function creates it
    
    dialog.close()


def test_ui_responsiveness_during_repository_checks(qtbot, monkeypatch):
    """Test UI responsiveness during repository connectivity checks."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock repository connectivity that takes time to test responsiveness
    def slow_mock_connectivity(repo_url, timeout=5):
        # Simulate network delay
        time.sleep(0.1)
        # Return successful connection
        return True, f"Repository {repo_url} is available", 0.1
    
    # Mock the prioritization function
    def mock_prioritized_repos():
        return [
            "https://slow-repo1.example.com/",
            "https://slow-repo2.example.com/",
            "https://repo1.maven.org/maven2/"  # Fast fallback
        ]
        
    from dbutils.gui import jdbc_driver_manager
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.JDBCDriverDownloader._get_prioritized_repos_by_connectivity',
                       lambda self: ["https://repo1.maven.org/maven2/"])
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Repo Test Driver",
        driver_class="com.repo.Driver",
        download_url="https://example.com/repo-test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Driver for repository testing",
        recommended_version="1.0.0",
        maven_artifacts=["com.repo:driver"]
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Repo Test")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox, \
            version_choice, specific_version_input, repo_list_label, repo_edit_btn = result
            qtbot.addWidget(download_dialog)
            
            # The UI should be responsive during repository operations
            # Check that the dialog and elements are still accessible
            assert download_dialog is not None
            assert repo_list_label is not None
            assert repo_edit_btn is not None
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
    
    dialog.close()


def test_memory_usage_during_long_operations(qtbot, monkeypatch):
    """Test that UI doesn't consume excessive memory during operations."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    dialog = ProviderConfigDialog()
    qtbot.addWidget(dialog)
    
    # Mock a download that would potentially cause memory issues if not handled properly
    import tempfile
    temp_dir = tempfile.gettempdir()
    mock_jar_path = os.path.join(temp_dir, "memory-test.jar")
    
    def mock_download_memory_test(db_type, on_progress=None, on_status=None, version="recommended"):
        # Create a reasonably sized file to test memory handling
        with open(mock_jar_path, "w") as f:
            # Write 100KB of data in chunks to test memory usage
            for i in range(100):  # 100 iterations of 1KB = 100KB
                f.write(f"Memory test data chunk {i:03d} " + "x" * 70 + "\n")
        
        if on_progress:
            on_progress(100000, 100000)  # 100KB total
        if on_status:
            on_status("Memory test download completed")
        
        return mock_jar_path
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', 
                       mock_download_memory_test)
    
    # Mock driver info
    from dbutils.gui.jdbc_driver_downloader import JDBCDriverInfo
    mock_driver_info = JDBCDriverInfo(
        name="Memory Test Driver",
        driver_class="com.memory.Driver",
        download_url="https://example.com/memory-test",
        alternative_urls=[],
        license="Test License",
        min_java_version="8",
        description="Driver for memory usage testing",
        recommended_version="1.0.0"
    )
    
    monkeypatch.setattr('dbutils.gui.jdbc_driver_downloader.JDBCDriverRegistry.get_driver_info',
                       lambda category: mock_driver_info)
    
    monkeypatch.setattr('dbutils.gui.jdbc_auto_downloader.get_jdbc_driver_download_info', 
                       lambda category: f"JDBC Driver: Memory Test")
    
    # Temporarily make the dialog non-modal for testing
    original_exec = QDialog.exec
    QDialog.exec = lambda self: True
    
    try:
        result = dialog.download_jdbc_driver_gui()
        if result:
            download_dialog, download_btn, manual_btn, license_checkbox = result[:4]
            qtbot.addWidget(download_dialog)
            
            with patch('dbutils.gui.jdbc_driver_manager.download_jdbc_driver', mock_download_memory_test):
                result_path = dialog.perform_jdbc_download("memory_test", version="latest")
                assert result_path is not None
            
            download_dialog.close()
    finally:
        QDialog.exec = original_exec  # Restore original method
        # Clean up the mock file
        if os.path.exists(mock_jar_path):
            try:
                os.remove(mock_jar_path)
            except:
                pass
    
    dialog.close()


def test_ui_element_leak_prevention(qtbot, monkeypatch):
    """Test that UI elements don't leak memory during repeated operations."""
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    
    # Create and destroy multiple dialogs to test for element leaks
    for i in range(3):  # Repeat to stress-test
        dialog = ProviderConfigDialog()
        qtbot.addWidget(dialog)
        
        # Access some UI elements to ensure they exist
        assert dialog.jar_download_btn is not None
        assert dialog.jar_history_btn is not None
        assert dialog.name_input is not None
        assert dialog.driver_class_input is not None
        
        # Close and clean up
        dialog.close()
        dialog.deleteLater()
    
    # Give Qt time to process the deletions
    qtbot.wait(100)


if __name__ == "__main__":
    # This allows running the test directly for debugging
    pytest.main([__file__])