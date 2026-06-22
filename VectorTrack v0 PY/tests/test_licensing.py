"""
Tests for the licensing module.
"""

import pytest
import os
from datetime import datetime, timedelta
from unittest.mock import patch, Mock
from vectortrack.licensing import LicenseManager

@pytest.fixture
def license_manager(tmp_path):
    """Create a license manager with temporary files."""
    license_file = tmp_path / "license.json"
    with patch.object(LicenseManager, '_get_hardware_id', return_value="test_hw_id"):
        manager = LicenseManager(str(license_file))
    return manager

def test_license_manager_initialization(tmp_path):
    """Test LicenseManager initialization."""
    license_file = tmp_path / "license.json"
    
    with patch.object(LicenseManager, '_get_hardware_id', return_value="test_hw_id"):
        manager = LicenseManager(str(license_file))
        
    assert os.path.exists(license_file)
    assert manager.trial_duration == timedelta(days=30)
    assert manager.license_data['hardware_id'] == "test_hw_id"
    assert manager.license_data['license_key'] is None

def test_encryption_key_management(tmp_path):
    """Test encryption key generation and storage."""
    key_file = tmp_path / "key.dat"
    
    with patch('os.path.exists', return_value=False), \
         patch('builtins.open', create=True), \
         patch.object(LicenseManager, '_get_hardware_id', return_value="test_hw_id"):
        
        manager = LicenseManager()
        key1 = manager._encryption_key
        
        # Second initialization should use the same key
        manager2 = LicenseManager()
        key2 = manager2._encryption_key
        
        assert key1 == key2

@patch('wmi.WMI')
def test_hardware_id_generation(mock_wmi):
    """Test hardware ID generation."""
    # Mock WMI data
    mock_system = Mock()
    mock_system.UUID = "test-uuid"
    mock_bios = Mock()
    mock_bios.SerialNumber = "test-serial"
    mock_cpu = Mock()
    mock_cpu.ProcessorId = "test-cpu"
    
    mock_wmi.return_value.Win32_ComputerSystemProduct.return_value = [mock_system]
    mock_wmi.return_value.Win32_BIOS.return_value = [mock_bios]
    mock_wmi.return_value.Win32_Processor.return_value = [mock_cpu]
    
    manager = LicenseManager()
    hw_id = manager._get_hardware_id()
    
    assert isinstance(hw_id, str)
    assert len(hw_id) == 64  # SHA-256 hash length

def test_license_key_validation(license_manager):
    """Test license key validation."""
    # Test invalid key format
    assert not license_manager._validate_license_key("invalid-key")
    
    # Generate and test valid key
    valid_key = license_manager.generate_license_key()
    assert license_manager._validate_license_key(valid_key)
    
    # Test key with invalid checksum
    invalid_key = valid_key[:-4] + "0000"
    assert not license_manager._validate_license_key(invalid_key)

def test_license_key_generation(license_manager):
    """Test license key generation."""
    key = license_manager.generate_license_key()
    
    # Check format (XXXX-XXXX-XXXX-XXXX-XXXX-XXXX)
    assert len(key) == 29
    assert key.count('-') == 5
    assert all(c.isalnum() or c == '-' for c in key)
    
    # Verify checksum
    assert license_manager._validate_license_key(key)

def test_license_activation(license_manager):
    """Test license activation."""
    # Generate valid key
    key = license_manager.generate_license_key()
    
    # Test activation
    success, message = license_manager.activate_license(key)
    assert success
    assert "successfully" in message.lower()
    assert license_manager.license_data['license_key'] == key
    assert license_manager.license_data['activation_date'] is not None
    
    # Test invalid key
    success, message = license_manager.activate_license("invalid-key")
    assert not success
    assert "invalid" in message.lower()

def test_license_status_check(license_manager):
    """Test license status checking."""
    # Test trial period
    is_valid, status = license_manager.check_license_status()
    assert is_valid
    assert "trial period" in status.lower()
    
    # Test expired trial
    license_manager.license_data['trial_start'] = (
        datetime.now() - timedelta(days=31)
    ).isoformat()
    is_valid, status = license_manager.check_license_status()
    assert not is_valid
    assert "expired" in status.lower()
    
    # Test valid license
    key = license_manager.generate_license_key()
    license_manager.activate_license(key)
    is_valid, status = license_manager.check_license_status()
    assert is_valid
    assert "licensed" in status.lower()
    
    # Test hardware mismatch
    license_manager.license_data['hardware_id'] = "different_hw_id"
    is_valid, status = license_manager.check_license_status()
    assert not is_valid
    assert "hardware mismatch" in status.lower()

def test_trial_days_remaining(license_manager):
    """Test trial days remaining calculation."""
    # New installation
    days = license_manager.get_trial_days_remaining()
    assert 29 <= days <= 30
    
    # Mid-trial
    license_manager.license_data['trial_start'] = (
        datetime.now() - timedelta(days=15)
    ).isoformat()
    days = license_manager.get_trial_days_remaining()
    assert 14 <= days <= 15
    
    # Expired trial
    license_manager.license_data['trial_start'] = (
        datetime.now() - timedelta(days=31)
    ).isoformat()
    assert license_manager.get_trial_days_remaining() == 0
    
    # Licensed (should return 0)
    key = license_manager.generate_license_key()
    license_manager.activate_license(key)
    assert license_manager.get_trial_days_remaining() == 0 