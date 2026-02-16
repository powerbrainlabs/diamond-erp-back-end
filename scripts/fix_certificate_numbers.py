"""
Script to check and fix certificate numbering issues
Run this if you encounter duplicate certificate number errors
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db


async def check_duplicates():
    """Check for duplicate certificate numbers"""
    db = await get_db()

    print("🔍 Checking for duplicate certificate numbers...")

    pipeline = [
        {"$group": {
            "_id": "$certificate_number",
            "count": {"$sum": 1},
            "ids": {"$push": "$uuid"}
        }},
        {"$match": {"count": {"$gt": 1}}}
    ]

    duplicates = await db.certifications.aggregate(pipeline).to_list(None)

    if duplicates:
        print(f"\n⚠️  Found {len(duplicates)} duplicate certificate numbers:")
        for dup in duplicates:
            print(f"   - {dup['_id']}: {dup['count']} occurrences (UUIDs: {dup['ids']})")
        return True
    else:
        print("✅ No duplicates found!")
        return False


async def check_counter_sync():
    """Check if the counter is in sync with actual certificates"""
    db = await get_db()
    from datetime import datetime

    print("\n🔍 Checking counter synchronization...")

    now = datetime.utcnow()
    date_str = now.strftime("%y%m%d")
    prefix = f"G{date_str}"

    # Get the counter value
    counter_doc = await db.certificate_counters.find_one({"_id": f"cert_{date_str}"})
    counter_value = counter_doc.get("seq", 0) if counter_doc else 0

    # Get the actual max certificate number
    latest_cert = await db.certifications.find_one(
        {"certificate_number": {"$regex": f"^{prefix}"}},
        sort=[("certificate_number", -1)]
    )

    actual_max = 0
    if latest_cert and latest_cert.get("certificate_number"):
        try:
            actual_max = int(latest_cert["certificate_number"][-4:])
        except (ValueError, IndexError):
            pass

    print(f"   Counter value: {counter_value}")
    print(f"   Actual max certificate: {actual_max}")

    if counter_value != actual_max:
        print(f"   ⚠️  Counter is out of sync! Difference: {counter_value - actual_max}")
        return True
    else:
        print("   ✅ Counter is in sync!")
        return False


async def list_todays_certificates():
    """List all certificates created today"""
    db = await get_db()
    from datetime import datetime

    print("\n📋 Today's certificates:")

    now = datetime.utcnow()
    date_str = now.strftime("%y%m%d")
    prefix = f"G{date_str}"

    certs = await db.certifications.find(
        {"certificate_number": {"$regex": f"^{prefix}"}},
        {"certificate_number": 1, "uuid": 1, "created_at": 1}
    ).sort([("certificate_number", 1)]).to_list(None)

    if certs:
        for cert in certs:
            print(f"   - {cert['certificate_number']} (UUID: {cert['uuid']}, Created: {cert.get('created_at')})")
        print(f"\n   Total: {len(certs)} certificates")
    else:
        print("   No certificates found for today")


async def main():
    print("=" * 60)
    print("Certificate Number Diagnostic Tool")
    print("=" * 60)

    has_duplicates = await check_duplicates()
    is_out_of_sync = await check_counter_sync()
    await list_todays_certificates()

    print("\n" + "=" * 60)
    if has_duplicates or is_out_of_sync:
        print("⚠️  Issues detected!")
        print("\n💡 Solution:")
        print("   The updated cert_numbering.py now checks the actual database")
        print("   instead of relying on the counter, which should prevent future issues.")
        print("\n   If you want to clean up the counter collection:")
        print("   db.certificate_counters.drop()")
    else:
        print("✅ Everything looks good!")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
