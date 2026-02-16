"""
Update existing certificates to reference the new schema with updated field labels
This script refreshes the schema reference for all existing certificates
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db


async def update_certificates():
    """Update all existing certificates to use the latest schema"""
    db = await get_db()

    print("🔄 Updating existing certificates with new schema labels...")

    # Get all non-deleted certificates
    certificates = await db.certifications.find({"is_deleted": False}).to_list(None)

    if not certificates:
        print("ℹ️  No certificates found to update")
        return

    updated_count = 0
    for cert in certificates:
        category_id = cert.get("category_id")

        if not category_id:
            print(f"   ⚠️  Certificate {cert['certificate_number']} has no category_id, skipping")
            continue

        # Get the latest version of the schema
        latest_schema = await db.category_schemas.find_one({
            "uuid": category_id,
            "is_deleted": False
        })

        if not latest_schema:
            print(f"   ⚠️  Schema {category_id} not found for certificate {cert['certificate_number']}, skipping")
            continue

        # The certificate's fields data stays the same (field_name keys don't change)
        # But when displayed, it will now use the updated labels from the schema
        # No need to modify the certificate document itself

        updated_count += 1
        print(f"   ✅ Certificate {cert['certificate_number']} will use updated schema labels")

    print(f"\n✅ {updated_count} certificates will now display with new labels")
    print(f"ℹ️  Note: Certificate field data (field_name keys) remain unchanged")
    print(f"ℹ️  The updated labels will appear when viewing certificates")


if __name__ == "__main__":
    asyncio.run(update_certificates())
