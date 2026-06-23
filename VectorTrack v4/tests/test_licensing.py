"""
Tests for the licensing module.
"""

import os
from datetime import datetime, timedelta

import pytest

from vectortrack.licensing import LicenseManager


@pytest.fixture
def license_manager(tmp_path, monkeypatch):
    """Create a license manager with temporary files."""
    license_file = tmp_path / "license.json"
    key_file = tmp_path / "key.dat"
    monkeypatch.setattr(LicenseManager, "_get_hardware_id", lambda self: "test_hw_id")
    return LicenseManager(str(license_file), str(key_file))


def test_license_manager_initialization(tmp_path, monkeypatch):
    license_file = tmp_path / "license.json"
    key_file = tmp_path / "key.dat"
    monkeypatch.setattr(LicenseManager, "_get_hardware_id", lambda self: "test_hw_id")
    manager = LicenseManager(str(license_file), str(key_file))

    assert os.path.exists(license_file)
    assert manager.trial_duration == timedelta(days=30)
    assert manager.license_data["hardware_id"] == "test_hw_id"
    assert manager.license_data["license_key"] is None


def test_encryption_key_management(tmp_path, monkeypatch):
    license_file = tmp_path / "license.json"
    key_file = tmp_path / "key.dat"
    monkeypatch.setattr(LicenseManager, "_get_hardware_id", lambda self: "test_hw_id")

    manager = LicenseManager(str(license_file), str(key_file))
    key1 = manager._encryption_key

    manager2 = LicenseManager(str(license_file), str(key_file))
    key2 = manager2._encryption_key

    assert key1 == key2


def test_hardware_id_generation(monkeypatch):
    monkeypatch.setattr(LicenseManager, "_get_hardware_id", lambda self: "test_hw_id")
    manager = LicenseManager()
    hw_id = manager._get_hardware_id()
    assert hw_id == "test_hw_id"


def test_license_key_validation(license_manager):
    assert not license_manager._validate_license_key("invalid-key")
    valid_key = license_manager.generate_license_key()
    assert license_manager._validate_license_key(valid_key)
    invalid_key = valid_key[:-4] + "0000"
    assert not license_manager._validate_license_key(invalid_key)


def test_license_key_generation(license_manager):
    key = license_manager.generate_license_key()
    assert len(key) == 29
    assert key.count("-") == 5
    assert all(c.isalnum() or c == "-" for c in key)
    assert license_manager._validate_license_key(key)


def test_license_activation(license_manager):
    key = license_manager.generate_license_key()
    success, message = license_manager.activate_license(key)
    assert success
    assert "successfully" in message.lower()
    assert license_manager.license_data["license_key"] == key
    assert license_manager.license_data["activation_date"] is not None

    success, message = license_manager.activate_license("invalid-key")
    assert not success
    assert "invalid" in message.lower()


def test_license_status_check(license_manager):
    is_valid, status = license_manager.check_license_status()
    assert is_valid
    assert "trial period" in status.lower()

    license_manager.license_data["trial_start"] = (
        datetime.now() - timedelta(days=31)
    ).isoformat()
    is_valid, status = license_manager.check_license_status()
    assert not is_valid
    assert "expired" in status.lower()

    key = license_manager.generate_license_key()
    license_manager.activate_license(key)
    is_valid, status = license_manager.check_license_status()
    assert is_valid
    assert "licensed" in status.lower()

    license_manager.license_data["hardware_id"] = "different_hw_id"
    is_valid, status = license_manager.check_license_status()
    assert not is_valid
    assert "hardware mismatch" in status.lower()


def test_trial_days_remaining(license_manager):
    days = license_manager.get_trial_days_remaining()
    assert 29 <= days <= 30

    license_manager.license_data["trial_start"] = (
        datetime.now() - timedelta(days=15)
    ).isoformat()
    days = license_manager.get_trial_days_remaining()
    assert 14 <= days <= 15

    license_manager.license_data["trial_start"] = (
        datetime.now() - timedelta(days=31)
    ).isoformat()
    assert license_manager.get_trial_days_remaining() == 0

    key = license_manager.generate_license_key()
    license_manager.activate_license(key)
    assert license_manager.get_trial_days_remaining() == 0
