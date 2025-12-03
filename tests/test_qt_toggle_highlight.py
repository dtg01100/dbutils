import types

from dbutils.gui import qt_app


class DummyTable:
    def __init__(self):
        self.last_delegate = None

    def setItemDelegate(self, delegate):
        # store the delegate for inspection
        self.last_delegate = delegate

    def viewport(self):
        return self

    def update(self):
        # noop - just allow call
        self.updated = True


class DummyProxy:
    def __init__(self):
        self.invalidated = False

    def invalidate(self):
        self.invalidated = True


def test_on_highlight_toggled_installs_and_removes_delegate():
    dummy = types.SimpleNamespace()
    dummy.inline_highlight_enabled = False
    dummy.search_query = "findme"
    dummy.tables_table = DummyTable()
    dummy.columns_table = DummyTable()
    dummy.tables_proxy = DummyProxy()

    # Enable highlighting
    qt_app.QtDBBrowser.on_highlight_toggled(dummy, True)

    assert dummy.inline_highlight_enabled is True
    # Delegate should be installed (stub or real depending on environment)
    assert dummy.tables_table.last_delegate is not None
    assert dummy.columns_table.last_delegate is not None
    # Proxy should be invalidated
    assert dummy.tables_proxy.invalidated

    # Now disable highlighting - should remove delegates
    dummy.tables_table.last_delegate = object()
    dummy.columns_table.last_delegate = object()
    dummy.tables_proxy.invalidated = False

    qt_app.QtDBBrowser.on_highlight_toggled(dummy, False)

    assert dummy.inline_highlight_enabled is False
    assert dummy.tables_table.last_delegate is None
    assert dummy.columns_table.last_delegate is None
    # Invalidate should still be triggered
    assert dummy.tables_proxy.invalidated
