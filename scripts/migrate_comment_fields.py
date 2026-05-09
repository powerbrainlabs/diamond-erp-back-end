#!/usr/bin/env python3
"""
One-time migration: update 'comment' field in all category schemas
(except double_mounded) from textarea to creatable_select with
min_length=50 validation and predefined options.

Usage:
    python scripts/migrate_comment_fields.py
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

COMMENT_OPTIONS = {
    "single_diamond": [
        "Excellent quality with superior characteristics and exceptional brilliance",
        "No visible inclusions under 10x magnification, outstanding clarity grade",
        "Minor inclusions visible only under magnification, does not affect brilliance",
        "Exceptional clarity and brilliance with superior cut proportions",
        "Good overall quality with well-defined characteristics and natural origin confirmed",
    ],
    "loose_diamond": [
        "Superior cut and polish with excellent light performance and symmetry",
        "Good symmetry and proportions with natural characteristics confirmed",
        "Exceptional quality with well-defined inclusions typical of natural origin",
        "Outstanding brilliance and fire with superior optical performance observed",
        "No fluorescence detected, natural formation confirmed under magnification",
    ],
    "loose_stone": [
        "Unheated, excellent origin with natural inclusions typical of the variety",
        "Heat treated for color enhancement, standard industry practice confirmed",
        "Natural with typical inclusions observed, no clarity enhancement detected",
        "Origin and natural formation confirmed, exceptional color saturation noted",
        "Vivid natural color with no indications of artificial treatment observed",
    ],
    "single_mounded": [
        "Beautiful color with excellent setting craftsmanship and premium quality stones",
        "Excellent setting with natural gemstone origin confirmed under magnification",
        "Premium quality gemstone with well-defined natural characteristics observed",
        "Superior brilliance with natural inclusions typical of the gemstone variety",
        "Outstanding color saturation with no indications of artificial enhancement",
    ],
    "navaratna": [
        "Traditional Navaratna setting with nine auspicious gems of natural origin",
        "Premium quality Navaratna with all nine gemstones confirmed as natural",
        "Astrological quality gemstones with natural characteristics confirmed under magnification",
        "All nine stones are natural and untreated, excellent astrological properties",
        "Superior craftsmanship with natural gemstones, ideal for astrological purposes",
    ],
}


async def migrate():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    for group, options in COMMENT_OPTIONS.items():
        schema = await db.category_schemas.find_one({"group": group, "is_deleted": False})
        if not schema:
            print(f"  [SKIP] Schema not found for group: {group}")
            continue

        fields = schema.get("fields", [])
        updated = False
        for i, field in enumerate(fields):
            if field.get("field_name") == "comment":
                fields[i] = {
                    **field,
                    "field_type": "creatable_select",
                    "placeholder": "Select or type a comment (min 50 characters)",
                    "options": options,
                    "validation": {"min_length": 50},
                }
                updated = True
                break

        if updated:
            await db.category_schemas.update_one(
                {"_id": schema["_id"]},
                {"$set": {"fields": fields}}
            )
            print(f"  [OK] Updated comment field for: {group}")
        else:
            print(f"  [SKIP] No comment field found in schema: {group}")

    client.close()
    print("\nMigration complete.")


if __name__ == "__main__":
    asyncio.run(migrate())
