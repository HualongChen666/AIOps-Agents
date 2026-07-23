# -*- coding: utf-8 -*-
"""
Stub for qrcode module to allow user_router to import without requiring the actual package.
This provides basic QR code functionality for testing purposes.
"""


class QRCode:
    """Simple QR Code implementation stub"""

    def __init__(self, data: str):
        """Initialize QR Code with data"""
        self.data = data
        self.image = None

    def make(self, fill_color: str = "black", back_color: str = "white"):
        """Generate QR code (stub implementation)"""
        # In real implementation, this would generate actual QR code
        self.image = f"QR_CODE_STUB_FOR_{self.data}"
        return self

    def make_image(self, fill_color: str = "black", back_color: str = "white"):
        """Generate QR code image (stub implementation)"""
        return self.make(fill_color, back_color)

    def get_image(self):
        """Get the generated image"""
        return self.image


def make(data: str) -> QRCode:
    """Create a QR code instance"""
    return QRCode(data)


def make_qr(data: str) -> QRCode:
    """Create a QR code instance (alternative function name)"""
    return QRCode(data)


# For compatibility with different qrcode library versions
constants = {
    "ERROR_CORRECT_L": "L",
    "ERROR_CORRECT_M": "M",
    "ERROR_CORRECT_Q": "Q",
    "ERROR_CORRECT_H": "H",
}

ERROR_CORRECT_L = "L"
ERROR_CORRECT_M = "M"
ERROR_CORRECT_Q = "Q"
ERROR_CORRECT_H = "H"
