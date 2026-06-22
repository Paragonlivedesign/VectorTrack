"""
Licensing module for managing trial periods and license key validation.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Optional, Tuple
from pathlib import Path
import hashlib
import uuid
from cryptography.fernet import Fernet
from loguru import logger

class LicenseManager:
    def __init__(self, license_file: str = "license.json", key_file: Optional[str] = None):
        self.license_file = license_file
        self.key_file = key_file or str(Path(license_file).with_name("key.dat"))
        self.trial_duration = timedelta(days=30)
        self._encryption_key = self._get_or_create_encryption_key()
        self._fernet = Fernet(self._encryption_key)
        self._load_license_data()
        
    def _get_or_create_encryption_key(self) -> bytes:
        """Get or create encryption key stored alongside the license file."""
        if os.path.exists(self.key_file):
            with open(self.key_file, "rb") as f:
                return f.read()

        key = Fernet.generate_key()
        Path(self.key_file).parent.mkdir(parents=True, exist_ok=True)
        with open(self.key_file, "wb") as f:
            f.write(key)

        return key
        
    def _get_hardware_id(self) -> str:
        """Generate a stable hardware ID without optional WMI dependency."""
        hw_info = (
            f"{os.getenv('USERNAME', '')}"
            f"{os.getenv('COMPUTERNAME', '')}"
            f"{os.getenv('PROCESSOR_IDENTIFIER', '')}"
        )
        return hashlib.sha256(hw_info.encode()).hexdigest()
        
    def _load_license_data(self):
        """Load or initialize license data."""
        if os.path.exists(self.license_file):
            try:
                with open(self.license_file, 'r') as f:
                    encrypted_data = f.read()
                    data = json.loads(self._fernet.decrypt(encrypted_data.encode()).decode())
                    self.license_data = data
                    return
            except Exception as e:
                logger.error(f"Error loading license data: {e}")
                
        # Initialize new license data
        self.license_data = {
            'trial_start': datetime.now().isoformat(),
            'license_key': None,
            'activation_date': None,
            'hardware_id': self._get_hardware_id()
        }
        self._save_license_data()
        
    def _save_license_data(self):
        """Save license data securely."""
        encrypted_data = self._fernet.encrypt(json.dumps(self.license_data).encode())
        with open(self.license_file, 'w') as f:
            f.write(encrypted_data.decode())
            
    def _validate_license_key(self, key: str) -> bool:
        """Validate license key format and checksum."""
        if len(key) != 29:  # Format: XXXX-XXXX-XXXX-XXXX-XXXX-XXXX
            return False
            
        # Remove dashes and validate checksum
        key_parts = key.split('-')
        if len(key_parts) != 6:
            return False
            
        try:
            # Last part is checksum
            checksum = key_parts[-1]
            key_data = ''.join(key_parts[:-1])
            calculated_checksum = hashlib.sha256(key_data.encode()).hexdigest()[:4]
            return checksum.upper() == calculated_checksum.upper()
        except Exception:
            return False
            
    def generate_license_key(self) -> str:
        """Generate a new license key (for testing/development)."""
        # Generate random segments
        segments = [str(uuid.uuid4())[:4].upper() for _ in range(5)]
        key_data = ''.join(segments)
        
        # Generate checksum
        checksum = hashlib.sha256(key_data.encode()).hexdigest()[:4].upper()
        
        # Combine segments with checksum
        return '-'.join(segments + [checksum])
        
    def activate_license(self, license_key: str) -> Tuple[bool, str]:
        """Activate the software with a license key."""
        if not self._validate_license_key(license_key):
            return False, "Invalid license key format"
            
        # In a production environment, you might want to validate the key
        # against an online service here
        
        self.license_data['license_key'] = license_key
        self.license_data['activation_date'] = datetime.now().isoformat()
        self._save_license_data()
        
        return True, "License activated successfully"
        
    def check_license_status(self) -> Tuple[bool, str]:
        """Check if the software is licensed or in trial period."""
        if self.license_data.get('license_key'):
            # Verify hardware ID hasn't changed (prevent license transfer)
            if self.license_data['hardware_id'] != self._get_hardware_id():
                return False, "Invalid license: Hardware mismatch"
            return True, "Licensed"
            
        # Check trial period
        trial_start = datetime.fromisoformat(self.license_data['trial_start'])
        time_elapsed = datetime.now() - trial_start
        
        if time_elapsed <= self.trial_duration:
            days_left = (self.trial_duration - time_elapsed).days
            return True, f"Trial period ({days_left} days remaining)"
            
        return False, "Trial period expired"
        
    def get_trial_days_remaining(self) -> int:
        """Get number of trial days remaining."""
        if self.license_data.get('license_key'):
            return 0
            
        trial_start = datetime.fromisoformat(self.license_data['trial_start'])
        time_elapsed = datetime.now() - trial_start
        days_left = (self.trial_duration - time_elapsed).days
        
        return max(0, days_left)

    def get_expiry_date(self) -> Optional[datetime]:
        """Get the expiration date of the current license or trial period."""
        if self.license_data.get('license_key'):
            # Licensed version doesn't expire
            return None
        
        # For trial version, calculate expiry from trial start
        trial_start = datetime.fromisoformat(self.license_data['trial_start'])
        return trial_start + self.trial_duration 