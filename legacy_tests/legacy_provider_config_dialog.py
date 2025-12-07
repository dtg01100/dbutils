#!/usr/bin/env python3
"""
Legacy copy of tests that were at the project root - moved to avoid pytest collection conflicts.
"""
from pathlib import Path
import pytest

from dbutils.gui.provider_config_dialog import ProviderConfigDialog

def test_moved():
    # Minimal smoke test to ensure module still loads when run manually
    assert ProviderConfigDialog is not None
