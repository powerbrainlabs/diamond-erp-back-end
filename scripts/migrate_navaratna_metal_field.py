"""
Add Metal Type field to existing Navaratna schema and update description_template.
"""
import asyncio
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db


async def migrate():
    db = await get_db()

    schema = await db.category_schemas.find_one({"group": "navaratna"})
    if not schema:
        print("❌ Navaratna schema not found.")
        return

    fields = schema.get("fields", [])

    # Check if metal field already exists
    if any(f.get("field_name") == "metal" for f in fields):
        print("[SKIP] Metal Type field already exists in Navaratna schema.")
    else:
        metal_field = {
            "field_id": str(uuid.uuid4()),
            "label": "Metal Type",
            "field_name": "metal",
            "field_type": "creatable_select",
            "is_required": False,
            "options": [],
            "display_order": 1,
        }

        # Shift display_order of all fields with order >= 1
        for f in fields:
            if f.get("display_order", 0) >= 1:
                f["display_order"] += 1

        fields.append(metal_field)
        fields.sort(key=lambda f: f.get("display_order", 99))

        print("[OK] Added Metal Type field to Navaratna schema")

    new_template = "One {metal} {category} studded with {diamond_piece} Natural Diamond and Colour Stones."

    await db.category_schemas.update_one(
        {"_id": schema["_id"]},
        {"$set": {
            "fields": fields,
            "description_template": new_template,
        }}
    )

    print(f"[OK] Updated description_template -> \"{new_template}\"")
    print("[DONE] Navaratna schema migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
