"""
Qt dialog for configuring JDBC providers.
"""

from __future__ import annotations

# ruff: noqa
# type: ignore

import PySide6.QtWidgets as _QtWidgets
import PySide6.QtCore as _QtCore

QT_AVAILABLE = True

from dbutils.jdbc_provider import ProviderRegistry, JDBCProvider

if QT_AVAILABLE:

    class ProviderConfigDialog(_QtWidgets.QDialog):
        def __init__(self, parent=None):
            super().__init__(parent)
            self.setWindowTitle("JDBC Providers")
            self.resize(700, 400)
            self.registry = ProviderRegistry()

            layout = _QtWidgets.QVBoxLayout(self)

            # Providers list
            self.list = _QtWidgets.QListWidget()
            layout.addWidget(self.list)

            # Form fields
            form = _QtWidgets.QFormLayout()
            self.name_edit = _QtWidgets.QLineEdit()
            self.driver_edit = _QtWidgets.QLineEdit()
            self.jar_edit = _QtWidgets.QLineEdit()
            # Add a browse button to select JARs (defaults to project jars folder)
            jar_row_widget = _QtWidgets.QWidget()
            jar_row_layout = _QtWidgets.QHBoxLayout(jar_row_widget)
            jar_row_layout.setContentsMargins(0, 0, 0, 0)
            jar_row_layout.setSpacing(6)
            jar_row_layout.addWidget(self.jar_edit)
            browse_btn = _QtWidgets.QPushButton("Browse…")
            jar_row_layout.addWidget(browse_btn)
            self.url_edit = _QtWidgets.QLineEdit()
            self.user_edit = _QtWidgets.QLineEdit()
            self.pass_edit = _QtWidgets.QLineEdit()
            self.pass_edit.setEchoMode(_QtWidgets.QLineEdit.EchoMode.Password)

            form.addRow("Name", self.name_edit)
            form.addRow("Driver Class", self.driver_edit)
            form.addRow("JAR Path", jar_row_widget)
            form.addRow("URL Template", self.url_edit)
            form.addRow("Default User", self.user_edit)
            form.addRow("Default Password", self.pass_edit)
            layout.addLayout(form)

            # Buttons
            btn_row = _QtWidgets.QHBoxLayout()
            add_btn = _QtWidgets.QPushButton("Add/Update")
            del_btn = _QtWidgets.QPushButton("Remove")
            close_btn = _QtWidgets.QPushButton("Close")
            btn_row.addWidget(add_btn)
            btn_row.addWidget(del_btn)
            btn_row.addStretch()
            btn_row.addWidget(close_btn)
            layout.addLayout(btn_row)

            # Wiring
            add_btn.clicked.connect(self._on_add_update)
            del_btn.clicked.connect(self._on_remove)
            close_btn.clicked.connect(self.accept)
            self.list.currentItemChanged.connect(self._on_select)
            browse_btn.clicked.connect(self._on_browse_jar)

            self._refresh_list()

        def _refresh_list(self):
            self.list.clear()
            for name in self.registry.list_names():
                self.list.addItem(name)

        def _on_select(self, cur, _prev):
            name = cur.text() if cur else None
            if not name:
                return
            p = self.registry.get(name)
            if not p:
                return
            self.name_edit.setText(p.name)
            self.driver_edit.setText(p.driver_class)
            self.jar_edit.setText(p.jar_path)
            self.url_edit.setText(p.url_template)
            self.user_edit.setText(p.default_user or "")
            self.pass_edit.setText(p.default_password or "")

        def _on_add_update(self):
            name = self.name_edit.text().strip() or "Unnamed"
            provider = JDBCProvider(
                name=name,
                driver_class=self.driver_edit.text().strip(),
                jar_path=self.jar_edit.text().strip(),
                url_template=self.url_edit.text().strip(),
                default_user=self.user_edit.text().strip() or None,
                default_password=self.pass_edit.text() or None,
                extra_properties={},
            )
            self.registry.add_or_update(provider)
            self._refresh_list()
            # Select the updated item
            matches = self.list.findItems(name, _QtCore.Qt.MatchFlag.MatchExactly)
            if matches:
                self.list.setCurrentItem(matches[0])

        def _on_browse_jar(self):
            """Open a file dialog to select a JDBC driver JAR file.

            Defaults to the workspace 'jars' folder if present; otherwise uses
            the user's home directory. Filters to .jar by default but allows all files.
            """
            try:
                import os

                # Try to locate a project jars folder
                start_dir = os.path.join(os.getcwd(), "jars")
                if not os.path.isdir(start_dir):
                    # Fallback to home
                    start_dir = os.path.expanduser("~")
                fname, _ = _QtWidgets.QFileDialog.getOpenFileName(
                    self,
                    "Select JDBC Driver JAR",
                    start_dir,
                    "JAR Files (*.jar);;All Files (*)",
                )
                if fname:
                    self.jar_edit.setText(fname)
            except Exception:
                # Silent failure to keep dialog usable even in limited environments
                pass

        def _on_remove(self):
            cur = self.list.currentItem()
            if not cur:
                return
            name = cur.text()
            self.registry.remove(name)
            self._refresh_list()
else:

    class ProviderConfigDialog(object):
        def __init__(self, *args, **kwargs):
            raise RuntimeError("Qt bindings not available")
