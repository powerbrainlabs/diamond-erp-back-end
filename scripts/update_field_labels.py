"""
Update field labels in existing category schemas to match abbreviated versions
"""
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db


async def update_labels():
    """Update field labels in all category schemas"""
    db = await get_db()

    label_mappings = {
        "Microscopic Observation": "Microscopic Obs",
        "Specific Gravity (SG)": "SG",
        "Refractive Index (RI)": "RI"
    }

    print("🔄 Updating field labels in category schemas...")

    # Get all category schemas
    schemas = await db.category_schemas.find({}).to_list(None)

    updated_count = 0
    for schema in schemas:
        updated = False
        fields = schema.get("fields", [])

        for field in fields:
            old_label = field.get("label")
            if old_label in label_mappings:
                new_label = label_mappings[old_label]
                field["label"] = new_label
                print(f"   ✅ Updated '{old_label}' → '{new_label}' in schema '{schema['name']}'")
                updated = True

        if updated:
            # Update the schema in database
            await db.category_schemas.update_one(
                {"_id": schema["_id"]},
                {"$set": {"fields": fields}}
            )
            updated_count += 1

    print(f"\n✅ Updated {updated_count} schemas")


if __name__ == "__main__":
    asyncio.run(update_labels())
