"""
Restore description_template for single_mounded and double_mounded schemas.
loose_diamond and loose_stone intentionally have no description.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.database import get_db

TEMPLATES = {
    "single_mounded": "One {metal} {category} studded with {gemstone_piece} Natural {gemstone} and Colour Stones.",
    "double_mounded": "One {metal} {category} studded with {primary_gemstone_piece} Natural {primary_gemstone} and {secondary_gemstone} and Colour Stones.",
}


async def migrate():
    db = await get_db()

    for group, template in TEMPLATES.items():
        schema = await db.category_schemas.find_one({"group": group})
        if not schema:
            print(f"[SKIP] Schema not found: {group}")
            continue

        await db.category_schemas.update_one(
            {"_id": schema["_id"]},
            {"$set": {"description_template": template}}
        )
        print(f"[OK] {group} -> \"{template}\"")

    print("[DONE] Description template migration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
