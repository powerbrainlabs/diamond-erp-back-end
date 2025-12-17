"""
Utility for generating certificate numbers in format: G + YYMMDD + sequential_number
Example: G25090116388
"""
from datetime import datetime
from ..db.database import get_db

START_AT = 1  # Start sequence from 1

async def next_certificate_number() -> str:
    """
    Generate next certificate number in format: G + YYMMDD + sequential_number
    Example: G25090116388
    - G = prefix
    - 250901 = YYMMDD (date)
    - 16388 = sequential number (5 digits, zero-padded)
    """
    db = await get_db()
    
    # Get current date in YYMMDD format
    now = datetime.utcnow()
    date_str = now.strftime("%y%m%d")  # YYMMDD format
    
    # Get or increment sequence number for today
    counter_key = f"certificate_number_{date_str}"
    
    doc = await db.counters.find_one_and_update(
        {"_id": counter_key},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=True,
    )
    
    seq = doc.get("seq")
    if seq is None:
        # First certificate of the day - start from START_AT
        await db.counters.update_one(
            {"_id": counter_key},
            {"$set": {"seq": START_AT}},
            upsert=True
        )
        seq = START_AT
    
    # Format: G + YYMMDD + 5-digit sequence number (zero-padded)
    cert_no = f"G{date_str}{seq:05d}"
    
    return cert_no

