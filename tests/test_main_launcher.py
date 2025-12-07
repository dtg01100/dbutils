import sys

import pytest

from dbutils import main_launcher


def test_check_gui_availability(monkeypatch):
    # Force find_spec to return truthy

    monkeypatch.setattr('importlib.util.find_spec', lambda name: True)
    assert main_launcher.check_gui_availability()

    monkeypatch.setattr('importlib.util.find_spec', lambda name: None)
    assert not main_launcher.check_gui_availability()


def test_main_install_deps_prints(monkeypatch, capsys):
    monkeypatch.setattr('sys.argv', ['prog', '--install-deps'])
    # Running main should print install instructions and not crash
    main_launcher.main()
    captured = capsys.readouterr()
    assert 'Qt DB Browser Dependencies' in captured.out


def test_launch_qt_interface_import_error(monkeypatch):
    # Ensure that if the module is not present, launch_qt_interface exits gracefully
    sys.modules.pop('dbutils.gui.qt_app', None)

    class Args:
        schema = None

    # Running launch_qt_interface should call qt_main; simulate missing module by removing it
    # We capture stdout and return code
    with pytest.raises(SystemExit):
        main_launcher.launch_qt_interface(Args())


def test_launch_qt_interface_calls_main(monkeypatch):
    # Provide a fake module
    class Dummy:
        called = False

        def main(self):
            Dummy.called = True

    dummy_mod = Dummy()
    monkeypatch.setitem(sys.modules, 'dbutils.gui.qt_app', dummy_mod)

    class Args:
        schema = None

    # Should not raise
    main_launcher.launch_qt_interface(Args())
    assert Dummy.called
