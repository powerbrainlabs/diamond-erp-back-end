from datetime import datetime
from ..db.database import get_db


async def next_certificate_number() -> str:
    """
    Generate next certificate number in format: G{YYMMDD}{XXXX}
    Example: G250215001 (generated on Feb 15, 2025)

    Counter resets daily based on date.
    """
    db = await get_db()

    # Get current date in YYMMDD format
    now = datetime.utcnow()
    date_str = now.strftime("%y%m%d")  # e.g., "250215"
    counter_id = f"cert_{date_str}"

    # Atomically increment counter for this date
    doc = await db.certificate_counters.find_one_and_update(
        {"_id": counter_id},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,  # Return updated document (after increment)
    )

    seq = doc.get("seq", 1)

    # Format: G + YYMMDD + 0001-9999 (4-digit serial)
    cert_number = f"G{date_str}{seq:04d}"

    return cert_number
