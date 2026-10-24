"""
Certificate-number lookups for QR codes printed by the old Firebase system.

Those QR codes open /certificates/view-certificate/<number>; the certificates
themselves were migrated into `certifications` under the same number.
"""
from typing import Optional

MAX_CERTIFICATE_NUMBER_LENGTH = 64


def certificate_number_key(value: Optional[str]) -> Optional[str]:
    """Certificate number as stored: trimmed and uppercased. None if unusable."""
    if not isinstance(value, str):
        return None
    key = value.strip().upper()
    if not key or len(key) > MAX_CERTIFICATE_NUMBER_LENGTH:
        return None
    return key
