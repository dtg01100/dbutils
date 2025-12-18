import os
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFileDialog


def test_add_custom_provider_and_save(qapp, tmp_path):
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    from dbutils.enhanced_jdbc_provider import EnhancedProviderRegistry

    dlg = ProviderConfigDialog()
    qapp.processEvents()

    # Click Add Custom Provider
    QTest.mouseClick(dlg.custom_provider_btn, Qt.LeftButton)
    qapp.processEvents()

    # Set provider name and driver class
    dlg.name_input.setText("MyTestProvider")
    dlg.driver_class_input.setText("org.postgresql.Driver")
    qapp.processEvents()

    # Accept the dialog (simulate OK)
    dlg.accept()

    # Registry should contain the new provider
    reg = EnhancedProviderRegistry()
    assert any(p.name == "MyTestProvider" for p in reg.list_providers())

    # Cleanup to avoid polluting global state
    try:
        reg.remove_provider("MyTestProvider")
    except Exception:
        pass


def test_add_and_remove_property(qapp):
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog

    dlg = ProviderConfigDialog()
    qapp.processEvents()

    # Add a new provider to populate the form
    QTest.mouseClick(dlg.add_btn, Qt.LeftButton)
    qapp.processEvents()

    # Add a property
    row_count_before = dlg.properties_table.rowCount()
    # Programmatically add a property row (mouse click may not trigger in headless tests)
    dlg.add_property_row()
    qapp.processEvents()
    assert dlg.properties_table.rowCount() == row_count_before + 1

    # Select the last row and remove it programmatically
    last_row = dlg.properties_table.rowCount() - 1
    dlg.properties_table.selectRow(last_row)
    dlg.remove_property_row()
    qapp.processEvents()
    assert dlg.properties_table.rowCount() == row_count_before

    dlg.close()
    dlg.deleteLater()


def test_browse_jar_and_open_download_dialog(qapp, monkeypatch):
    from dbutils.gui.provider_config_dialog import ProviderConfigDialog
    from PySide6.QtWidgets import QFileDialog

    dlg = ProviderConfigDialog()
    qapp.processEvents()

    # Monkeypatch file dialog to return a fake jar path
    monkeypatch.setattr(QFileDialog, "getOpenFileName", lambda *args, **kwargs: ("/tmp/fake.jar", ""))

    # Click Add, then browse for jar
    QTest.mouseClick(dlg.add_btn, Qt.LeftButton)
    qapp.processEvents()

    # Directly invoke browse function (click may not trigger in headless tests)
    dlg.browse_jar_file()
    qapp.processEvents()

    assert dlg.jar_path_input.text() == "/tmp/fake.jar"

    # Set a category and driver class to exercise detection
    dlg.category_input.setCurrentText("PostgreSQL")
    dlg.driver_class_input.setText("org.postgresql.Driver")
    qapp.processEvents()

    # Call download_jdbc_driver_gui in test mode - it should return a dialog and widgets
    res = dlg.download_jdbc_driver_gui()
    assert res is not None
    dialog, download_btn, manual_btn, license_checkbox = res[:4]

    # Simulate clicking download button
    QTest.mouseClick(download_btn, Qt.LeftButton)
    qapp.processEvents()

    # Ensure pending download options were recorded
    assert hasattr(dlg, "_pending_download_options")

    dialog.deleteLater()
    dlg.close()
    dlg.deleteLater()
