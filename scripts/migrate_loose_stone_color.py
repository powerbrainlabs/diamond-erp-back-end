"""
Change Color field in loose_stone schema from text to creatable_select.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db


async def migrate():
    db = await get_db()

    schema = await db.category_schemas.find_one({"group": "loose_stone"})
    if not schema:
        print("[SKIP] loose_stone schema not found.")
        return

    fields = schema.get("fields", [])
    updated = False

    for field in fields:
        if field.get("field_name") == "color":
            field["field_type"] = "creatable_select"
            field.pop("placeholder", None)
            if "options" not in field:
                field["options"] = []
            updated = True
            print("[OK] Color field changed to creatable_select")
            break

    if not updated:
        print("[SKIP] Color field not found in loose_stone schema.")
        return

    await db.category_schemas.update_one(
        {"_id": schema["_id"]},
        {"$set": {"fields": fields}}
    )
    print("[DONE] loose_stone Color field migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
