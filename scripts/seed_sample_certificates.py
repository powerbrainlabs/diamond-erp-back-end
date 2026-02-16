#!/usr/bin/env python3
"""
Script to generate sample certificates for testing certificate card designs.
Generates 3-4 certificates for each certificate type with realistic data.

Usage:
    python scripts/seed_sample_certificates.py

    Or from backend directory:
    ../venv/bin/python scripts/seed_sample_certificates.py
"""

import asyncio
import sys
import os
from pathlib import Path
from datetime import datetime
import uuid as uuid_lib

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


# Sample data for different certificate types
SAMPLE_DATA = {
    "single_diamond": [
        {
            "client_name": "Rajesh Jewelers",
            "fields": {
                "category": "Ring",
                "metal_type": "Gold 18K",
                "gross_weight": "5.25",
                "diamond_weight": "0.75",
                "diamond_piece": "1",
                "cut": "Excellent",
                "clarity": "VVS1 (Very Very Slightly Included)",
                "color": "D (Colorless)",
                "conclusion": "Natural Diamond",
                "description": "One Gold 18K Ring Studded with 1 Natural Diamond.",
                "comment": "No visible inclusions under 10x magnification"
            }
        },
        {
            "client_name": "Diamond Palace",
            "fields": {
                "category": "Earring",
                "metal_type": "White Gold 18K",
                "gross_weight": "3.80",
                "diamond_weight": "1.25",
                "diamond_piece": "12",
                "cut": "Very Good",
                "clarity": "VS1 (Very Slightly Included)",
                "color": "E (Colorless)",
                "conclusion": "Natural Diamond",
                "description": "One pair of White Gold 18K Earring Studded with 12 Natural Diamonds.",
                "comment": "Minor inclusions visible under 10x"
            }
        },
        {
            "client_name": "Heritage Jewels",
            "fields": {
                "category": "Pendant",
                "metal_type": "Platinum",
                "gross_weight": "4.15",
                "diamond_weight": "0.50",
                "diamond_piece": "1",
                "cut": "Excellent",
                "clarity": "IF (Internally Flawless)",
                "color": "F (Colorless)",
                "conclusion": "Natural Diamond",
                "description": "One Platinum Pendant Studded with 1 Natural Diamond.",
                "comment": "Exceptional clarity and brilliance"
            }
        },
        {
            "client_name": "Royal Gems",
            "fields": {
                "category": "Bracelet",
                "metal_type": "Gold 22K",
                "gross_weight": "12.50",
                "diamond_weight": "2.10",
                "diamond_piece": "24",
                "cut": "Good",
                "clarity": "SI1 (Slightly Included)",
                "color": "G (Near Colorless)",
                "conclusion": "Natural Diamond",
                "description": "One Gold 22K Bracelet Studded with 24 Natural Diamonds.",
                "comment": "Slight inclusions visible under magnification"
            }
        }
    ],
    "loose_diamond": [
        {
            "client_name": "Diamond Trading Co.",
            "fields": {
                "shape": "Round",
                "weight": "1.52",
                "dimension": "7.42x7.45x4.58",
                "cut": "Excellent",
                "clarity": "VVS2 (Very Very Slightly Included)",
                "color": "E (Colorless)",
                "hardness": "10 (Mohs Scale)",
                "sg": "3.52",
                "microscopic_obs": "Pinpoint inclusions",
                "conclusion": "Natural Diamond",
                "comment": "Superior cut and polish"
            }
        },
        {
            "client_name": "Brilliant Diamonds",
            "fields": {
                "shape": "Princess",
                "weight": "0.95",
                "dimension": "5.85x5.80x4.12",
                "cut": "Very Good",
                "clarity": "VS2 (Very Slightly Included)",
                "color": "F (Colorless)",
                "hardness": "10 (Mohs Scale)",
                "sg": "3.52",
                "microscopic_obs": "Feather inclusions",
                "conclusion": "Natural Diamond",
                "comment": "Good symmetry and proportions"
            }
        },
        {
            "client_name": "Sparkle Gems",
            "fields": {
                "shape": "Cushion",
                "weight": "2.03",
                "dimension": "8.12x7.95x5.24",
                "cut": "Excellent",
                "clarity": "IF (Internally Flawless)",
                "color": "D (Colorless)",
                "hardness": "10 (Mohs Scale)",
                "sg": "3.52",
                "microscopic_obs": "No inclusions visible",
                "conclusion": "Natural Diamond",
                "comment": "Exceptional quality, museum grade"
            }
        }
    ],
    "loose_stone": [
        {
            "client_name": "Ruby Trading House",
            "fields": {
                "gemstone_type": "Ruby",
                "shape": "Oval",
                "weight": "3.25",
                "dimension": "9.5x7.8x5.2",
                "color": "Pigeon Blood Red",
                "sg": "3.99-4.00",
                "ri": "1.762-1.770",
                "hardness": "9 (Mohs Scale)",
                "microscopic_obs": "Natural rutile needles",
                "conclusion": "Natural Ruby (Corundum)",
                "comment": "Unheated, Burmese origin"
            }
        },
        {
            "client_name": "Sapphire Emporium",
            "fields": {
                "gemstone_type": "Blue Sapphire",
                "shape": "Cushion",
                "weight": "5.12",
                "dimension": "11.2x9.8x6.5",
                "color": "Royal Blue",
                "sg": "3.99-4.00",
                "ri": "1.762-1.770",
                "hardness": "9 (Mohs Scale)",
                "microscopic_obs": "Zoning pattern visible",
                "conclusion": "Natural Blue Sapphire (Corundum)",
                "comment": "Ceylon origin, heat treated"
            }
        },
        {
            "client_name": "Emerald Gallery",
            "fields": {
                "gemstone_type": "Emerald",
                "shape": "Emerald Cut",
                "weight": "2.85",
                "dimension": "9.1x7.3x5.8",
                "color": "Vivid Green",
                "sg": "2.67-2.78",
                "ri": "1.577-1.583",
                "hardness": "7.5-8 (Mohs Scale)",
                "microscopic_obs": "Three-phase inclusions",
                "conclusion": "Natural Emerald (Beryl)",
                "comment": "Colombian origin, minor oil treatment"
            }
        }
    ],
    "single_mounded": [
        {
            "client_name": "Classic Jewelers",
            "fields": {
                "gemstone_type": "Ruby",
                "metal_type": "Gold 18K",
                "gross_weight": "6.45",
                "gemstone_weight": "2.15",
                "shape": "Oval",
                "sg": "3.99-4.00",
                "hardness": "9 (Mohs Scale)",
                "ri": "1.762-1.770",
                "microscopic_obs": "Silk inclusions",
                "conclusion": "Natural Ruby (Corundum)",
                "comment": "Beautiful pigeon blood color"
            }
        },
        {
            "client_name": "Sapphire House",
            "fields": {
                "gemstone_type": "Blue Sapphire",
                "metal_type": "Platinum",
                "gross_weight": "8.20",
                "gemstone_weight": "3.80",
                "shape": "Cushion",
                "sg": "3.99-4.00",
                "hardness": "9 (Mohs Scale)",
                "ri": "1.762-1.770",
                "microscopic_obs": "Color zoning",
                "conclusion": "Natural Blue Sapphire (Corundum)",
                "comment": "Ceylon origin"
            }
        },
        {
            "client_name": "Emerald Palace",
            "fields": {
                "gemstone_type": "Emerald",
                "metal_type": "Gold 22K",
                "gross_weight": "5.95",
                "gemstone_weight": "1.85",
                "shape": "Emerald Cut",
                "sg": "2.67-2.78",
                "hardness": "7.5-8 (Mohs Scale)",
                "ri": "1.577-1.583",
                "microscopic_obs": "Jardin inclusions",
                "conclusion": "Natural Emerald (Beryl)",
                "comment": "Colombian origin with typical inclusions"
            }
        }
    ],
    "double_mounded": [
        {
            "client_name": "Twin Gems",
            "fields": {
                "primary_gemstone": "Ruby",
                "secondary_gemstone": "Diamond",
                "metal_type": "Gold 18K",
                "gross_weight": "7.80",
                "primary_stone_weight": "1.95",
                "secondary_stone_weight": "0.65",
                "shape": "Oval & Round",
                "sg": "3.99 & 3.52",
                "ri": "1.762-1.770 & 2.417",
                "hardness": "9 & 10 (Mohs Scale)",
                "microscopic_obs": "Ruby: silk inclusions | Diamond: feather",
                "conclusion": "Natural Ruby & Natural Diamond"
            }
        },
        {
            "client_name": "Duo Jewels",
            "fields": {
                "primary_gemstone": "Emerald",
                "secondary_gemstone": "Diamond",
                "metal_type": "Platinum",
                "gross_weight": "6.95",
                "primary_stone_weight": "1.50",
                "secondary_stone_weight": "0.45",
                "shape": "Emerald & Princess",
                "sg": "2.70 & 3.52",
                "ri": "1.577-1.583 & 2.417",
                "hardness": "8 & 10 (Mohs Scale)",
                "microscopic_obs": "Emerald: jardin | Diamond: pinpoint",
                "conclusion": "Natural Emerald & Natural Diamond"
            }
        }
    ],
    "navaratna": [
        {
            "client_name": "Navaratna Creations",
            "fields": {
                "metal_type": "Gold 22K",
                "gross_weight": "18.50",
                "ruby_weight": "1.25",
                "pearl_weight": "2.10",
                "coral_weight": "1.85",
                "emerald_weight": "1.15",
                "yellow_sapphire_weight": "1.35",
                "diamond_weight": "0.95",
                "blue_sapphire_weight": "1.45",
                "hessonite_weight": "1.55",
                "cats_eye_weight": "1.65",
                "cut": "Mixed",
                "color": "Multi-colored",
                "clarity": "Eye Clean",
                "conclusion": "Natural Gemstones",
                "comment": "Traditional Navaratna setting with 9 auspicious gems"
            }
        },
        {
            "client_name": "Astrological Gems",
            "fields": {
                "metal_type": "Gold 18K",
                "gross_weight": "15.75",
                "ruby_weight": "1.05",
                "pearl_weight": "1.85",
                "coral_weight": "1.55",
                "emerald_weight": "0.95",
                "yellow_sapphire_weight": "1.15",
                "diamond_weight": "0.75",
                "blue_sapphire_weight": "1.25",
                "hessonite_weight": "1.35",
                "cats_eye_weight": "1.45",
                "cut": "Mixed",
                "color": "Multi-colored",
                "clarity": "Eye Clean",
                "conclusion": "Natural Gemstones",
                "comment": "Premium quality Navaratna pendant"
            }
        }
    ]
}


async def get_or_create_client(db, client_name: str) -> str:
    """Get existing client or create new one"""
    client = await db.clients.find_one({"name": client_name, "is_deleted": False})
    if client:
        return client["uuid"]

    # Create new client
    client_uuid = str(uuid_lib.uuid4())
    await db.clients.insert_one({
        "uuid": client_uuid,
        "name": client_name,
        "contact_person": f"Contact {client_name}",
        "email": f"{client_name.lower().replace(' ', '_')}@example.com",
        "phone": f"+91-{9000000000 + hash(client_name) % 100000000}",
        "address": f"{client_name} Address",
        "gst_number": None,
        "notes": f"Sample client for {client_name}",
        "is_deleted": False,
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    return client_uuid


async def seed_certificates():
    """Generate sample certificates for all certificate types"""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    print("🌱 Starting certificate seeding...")
    print(f"📊 Connected to database: {settings.DATABASE_NAME}")

    # Get all certificate types
    cert_types = await db.certificate_types.find({
        "is_deleted": False,
        "is_active": True
    }).to_list(length=100)

    if not cert_types:
        print("❌ No certificate types found. Please seed certificate types first.")
        return

    print(f"✅ Found {len(cert_types)} certificate types")

    total_created = 0

    for cert_type in cert_types:
        type_slug = cert_type["slug"]
        type_name = cert_type["name"]

        print(f"\n📝 Processing: {type_name} ({type_slug})")

        # Get schema for this type
        schema = await db.category_schemas.find_one({
            "group": type_slug,
            "is_deleted": False,
            "is_active": True
        })

        if not schema:
            print(f"  ⚠️  No schema found for {type_slug}, skipping...")
            continue

        # Get sample data for this type
        samples = SAMPLE_DATA.get(type_slug, [])
        if not samples:
            print(f"  ⚠️  No sample data defined for {type_slug}, skipping...")
            continue

        print(f"  📋 Creating {len(samples)} sample certificates...")

        for idx, sample in enumerate(samples, 1):
            # Get or create client
            client_uuid = await get_or_create_client(db, sample["client_name"])

            # Generate certificate number (simple sequential for testing)
            # In production, this would use next_certificate_number()
            today = datetime.utcnow()
            cert_number = f"G{today.strftime('%y%m%d')}{total_created + 1:04d}"

            # Create certificate document
            cert_doc = {
                "uuid": str(uuid_lib.uuid4()),
                "certificate_number": cert_number,
                "type": type_slug,
                "client_id": client_uuid,
                "category_id": schema["uuid"],
                "fields": sample["fields"],
                "photo_url": None,  # Could add sample images later
                "brand_logo_url": None,
                "rear_brand_logo_url": None,
                "qr_code_url": None,
                "is_deleted": False,
                "is_rejected": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            # Insert certificate
            await db.certifications.insert_one(cert_doc)
            total_created += 1

            print(f"    ✓ Certificate #{idx}: {cert_number} (Client: {sample['client_name']})")

    print(f"\n✨ Seeding completed!")
    print(f"📊 Total certificates created: {total_created}")

    # Close connection
    client.close()


async def clear_existing_certificates():
    """Clear existing sample certificates (optional - for re-seeding)"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.MONGODB_DB]

    result = await db.certifications.delete_many({})
    print(f"🗑️  Cleared {result.deleted_count} existing certificates")

    client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed sample certificates")
    parser.add_argument("--clear", action="store_true", help="Clear existing certificates before seeding")
    args = parser.parse_args()

    if args.clear:
        print("⚠️  Clearing existing certificates...")
        asyncio.run(clear_existing_certificates())

    asyncio.run(seed_certificates())
