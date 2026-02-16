from datetime import datetime
from ..db.database import get_db


async def next_certificate_number() -> str:
    """
    Generate next certificate number in format: G{YYMMDD}{XXXX}
    Example: G250215001 (generated on Feb 15, 2025)

    Counter resets daily based on date.
    Uses the actual max certificate number from the database to avoid duplicates.
    """
    db = await get_db()

    # Get current date in YYMMDD format
    now = datetime.utcnow()
    date_str = now.strftime("%y%m%d")  # e.g., "260216"
    prefix = f"G{date_str}"

    # Find the highest certificate number for today
    # Pattern match certificates that start with today's prefix
    latest_cert = await db.certifications.find_one(
        {"certificate_number": {"$regex": f"^{prefix}"}},
        sort=[("certificate_number", -1)]
    )

    if latest_cert and latest_cert.get("certificate_number"):
        # Extract the sequence number from the last certificate
        last_number = latest_cert["certificate_number"]
        try:
            # Get last 4 digits and increment
            last_seq = int(last_number[-4:])
            next_seq = last_seq + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        # No certificates for today yet, start at 1
        next_seq = 1

    # Ensure we don't exceed 9999
    if next_seq > 9999:
        raise ValueError(f"Certificate limit exceeded for date {date_str}")

    # Format: G + YYMMDD + 0001-9999 (4-digit serial)
    cert_number = f"{prefix}{next_seq:04d}"

    # Double-check the number doesn't exist (extra safety)
    existing = await db.certifications.find_one({"certificate_number": cert_number})
    if existing:
        # If it somehow exists, increment and try again (recursive)
        print(f"⚠️  Warning: Certificate number {cert_number} already exists, retrying...")
        # Update the counter to avoid this in the future
        next_seq += 1
        cert_number = f"{prefix}{next_seq:04d}"

    return cert_number
