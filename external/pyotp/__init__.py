# -*- coding: utf-8 -*-
"""
Stub for pyotp module to allow user_router to import without requiring the actual package.
This provides basic TOTP functionality for testing purposes.
"""

import base64
import hashlib
import hmac
import time


class TOTP:
    """Time-based One-Time Password implementation"""

    def __init__(self, secret: str, digits: int = 6, interval: int = 30):
        """
        Initialize TOTP

        Args:
            secret: The secret key
            digits: Number of digits in the OTP (default 6)
            interval: Time interval in seconds (default 30)
        """
        self.secret = secret
        self.digits = digits
        self.interval = interval

    def now(self) -> str:
        """Generate current TOTP"""
        # Simple implementation for compatibility
        timestamp = int(time.time() // self.interval)
        return self._generate_totp(timestamp)

    def verify(self, otp: str, valid_window: int = 1) -> bool:
        """
        Verify OTP against current time

        Args:
            otp: The OTP to verify
            valid_window: Number of intervals to check (default 1)

        Returns:
            True if OTP is valid, False otherwise
        """
        timestamp = int(time.time() // self.interval)

        for i in range(-valid_window, valid_window + 1):
            if self._generate_totp(timestamp + i) == otp:
                return True

        return False

    def _generate_totp(self, timestamp: int) -> str:
        """Generate TOTP for given timestamp"""
        # Simple HMAC-based implementation
        key = base64.b32decode(self.secret.upper())
        counter = timestamp.to_bytes(8, byteorder="big")

        hmac_hash = hmac.new(key, counter, hashlib.sha1).digest()
        offset = hmac_hash[-1] & 0x0F
        code = (
            (hmac_hash[offset] & 0x7F) << 24
            | (hmac_hash[offset + 1] & 0xFF) << 16
            | (hmac_hash[offset + 2] & 0xFF) << 8
            | (hmac_hash[offset + 3] & 0xFF)
        )

        code = code % (10**self.digits)
        return str(code).zfill(self.digits)


def random_base32(length: int = 16) -> str:
    """Generate a random base32 string"""
    import random
    import string

    chars = string.ascii_uppercase + "234567"
    return "".join(random.choice(chars) for _ in range(length))


__all__ = ["TOTP", "random_base32"]
