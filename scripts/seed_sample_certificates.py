#!/usr/bin/env python3
"""
Script to generate sample certificates using dynamic attributes from the database.
Generates 3-4 certificates for each certificate type with realistic data from attributes collection.

Usage:
    python scripts/seed_sample_certificates.py

    Or from backend directory:
    ../venv/bin/activate && python scripts/seed_sample_certificates.py
"""

import asyncio
import sys
import os
import random
from pathlib import Path
from datetime import datetime
import uuid as uuid_lib
import base64

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings


def read_test_photo(filename: str) -> str:
    """Read a test photo and return its base64 encoded data URL."""
    test_photo_dir = Path(__file__).parent.parent / "test-photo"
    photo_path = test_photo_dir / filename

    if not photo_path.exists():
        print(f"  ⚠️  Warning: Test photo not found: {photo_path}")
        return None

    with open(photo_path, "rb") as f:
        photo_data = f.read()
        base64_data = base64.b64encode(photo_data).decode('utf-8')

        # Determine mime type
        ext = photo_path.suffix.lower()
        mime_type = "image/png" if ext == ".png" else "image/jpeg"

        return f"data:{mime_type};base64,{base64_data}"


async def get_random_attribute(db, group: str, attr_type: str):
    """Get a random attribute value from the attributes collection."""
    cursor = db.attributes.find({
        "group": group,
        "type": attr_type,
        "is_deleted": False
    })
    attrs = await cursor.to_list(length=100)
    if attrs:
        return random.choice(attrs)["name"]
    return None


async def get_all_attributes(db, group: str, attr_type: str):
    """Get all attribute values for a specific group and type."""
    cursor = db.attributes.find({
        "group": group,
        "type": attr_type,
        "is_deleted": False
    }).sort([("name", 1)])
    attrs = await cursor.to_list(length=100)
    return [attr["name"] for attr in attrs]


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
        "created_by": "system",
        "created_at": datetime.utcnow(),
        "updated_at": datetime.utcnow(),
    })
    return client_uuid


async def generate_single_diamond_certificate(db, client_name: str):
    """Generate a single diamond certificate with dynamic attributes."""
    return {
        "client_name": client_name,
        "fields": {
            "category": await get_random_attribute(db, "diamond", "category") or "Ring",
            "metal": await get_random_attribute(db, "diamond", "metal_type") or "Gold 18K",
            "gross_weight": f"{random.uniform(3.0, 15.0):.2f}",
            "diamond_weight": f"{random.uniform(0.3, 3.0):.2f}",
            "diamond_piece": str(random.randint(1, 50)),
            "cut": await get_random_attribute(db, "diamond", "cut") or "Excellent",
            "clarity": await get_random_attribute(db, "diamond", "clarity") or "VVS1",
            "color": await get_random_attribute(db, "diamond", "color") or "D",
            "conclusion": await get_random_attribute(db, "diamond", "conclusion") or "Natural Diamond",
            "comment": random.choice([
                "Excellent quality with superior characteristics",
                "No visible inclusions under 10x magnification",
                "Minor inclusions visible under magnification",
                "Exceptional clarity and brilliance",
                ""  # Sometimes empty
            ])
        }
    }


async def generate_loose_diamond_certificate(db, client_name: str):
    """Generate a loose diamond certificate with dynamic attributes."""
    return {
        "client_name": client_name,
        "fields": {
            "shape": await get_random_attribute(db, "gemstone", "gemstone_shape") or "Round",
            "weight": f"{random.uniform(0.5, 3.0):.2f}",
            "dimension": f"{random.uniform(5.0, 9.0):.2f}x{random.uniform(5.0, 9.0):.2f}x{random.uniform(3.0, 6.0):.2f}",
            "cut": await get_random_attribute(db, "diamond", "cut") or "Excellent",
            "clarity": await get_random_attribute(db, "diamond", "clarity") or "VVS2",
            "color": await get_random_attribute(db, "diamond", "color") or "E",
            "hardness": "10 (Mohs Scale)",
            "sg": "3.52",
            "microscopic_obs": await get_random_attribute(db, "gemstone", "microscopic_observation") or "Clean",
            "conclusion": await get_random_attribute(db, "diamond", "conclusion") or "Natural Diamond",
            "comment": random.choice([
                "Superior cut and polish",
                "Good symmetry and proportions",
                "Exceptional quality",
                ""
            ])
        }
    }


async def generate_loose_stone_certificate(db, client_name: str):
    """Generate a loose stone (gemstone) certificate with dynamic attributes."""
    gemstone = await get_random_attribute(db, "gemstone", "gemstone") or "Ruby"
    return {
        "client_name": client_name,
        "fields": {
            "gemstone": gemstone,
            "shape": await get_random_attribute(db, "gemstone", "gemstone_shape") or "Oval",
            "weight": f"{random.uniform(1.0, 5.0):.2f}",
            "dimension": f"{random.uniform(7.0, 12.0):.1f}x{random.uniform(6.0, 10.0):.1f}x{random.uniform(4.0, 7.0):.1f}",
            "color": random.choice(["Pigeon Blood Red", "Royal Blue", "Vivid Green", "Deep Purple"]),
            "sg": f"{random.uniform(2.6, 4.1):.2f}",
            "ri": f"{random.uniform(1.5, 1.8):.3f}",
            "hardness": f"{random.randint(7, 9)} (Mohs Scale)",
            "microscopic_obs": await get_random_attribute(db, "gemstone", "microscopic_observation") or "Natural inclusions",
            "conclusion": f"Natural {gemstone}",
            "comment": random.choice([
                "Unheated, excellent origin",
                "Heat treated for color enhancement",
                "Natural with typical inclusions",
                ""
            ])
        }
    }


async def generate_single_mounded_certificate(db, client_name: str):
    """Generate a single mounded (gemstone in setting) certificate."""
    gemstone = await get_random_attribute(db, "gemstone", "gemstone") or "Sapphire"
    return {
        "client_name": client_name,
        "fields": {
            "gemstone": gemstone,
            "category": await get_random_attribute(db, "gemstone", "category") or "Ring",
            "metal": await get_random_attribute(db, "gemstone", "metal_type") or "Gold 18K",
            "gemstone_piece": str(random.randint(1, 5)),
            "gross_weight": f"{random.uniform(4.0, 10.0):.2f}",
            "stone_weight": f"{random.uniform(1.0, 4.0):.2f}",
            "shape": await get_random_attribute(db, "gemstone", "gemstone_shape") or "Oval",
            "sg": f"{random.uniform(2.6, 4.1):.2f}",
            "hardness": f"{random.randint(7, 9)} (Mohs Scale)",
            "ri": f"{random.uniform(1.5, 1.8):.3f}",
            "microscopic_obs": await get_random_attribute(db, "gemstone", "microscopic_observation") or "Inclusions",
            "conclusion": f"Natural {gemstone}",
            "comment": random.choice(["Beautiful color", "Excellent setting", "Premium quality", ""])
        }
    }



async def generate_double_mounded_certificate(db, client_name: str):
    """Generate a double mounded (two gemstones) certificate."""
    primary_gem = await get_random_attribute(db, "gemstone", "gemstone") or "Ruby"
    return {
        "client_name": client_name,
        "fields": {
            "primary_gemstone": primary_gem,
            "secondary_gemstone": "Diamond",
            "metal": await get_random_attribute(db, "gemstone", "metal_type") or "Platinum",
            "gross_weight": f"{random.uniform(5.0, 10.0):.2f}",
            "primary_stone_weight": f"{random.uniform(1.0, 3.0):.2f}",
            "secondary_stone_weight": f"{random.uniform(0.3, 1.0):.2f}",
            "shape": random.choice(["Oval & Round", "Cushion & Princess", "Emerald & Round"]),
            "sg": f"{random.uniform(3.5, 4.0):.2f} & 3.52",
            "ri": f"{random.uniform(1.7, 1.8):.3f} & 2.417",
            "hardness": "9 & 10 (Mohs Scale)",
            "microscopic_obs": f"{primary_gem}: natural inclusions | Diamond: clean",
            "conclusion": f"Natural {primary_gem} & Natural Diamond",
            "comment": ""
        }
    }


async def generate_navaratna_certificate(db, client_name: str):
    """Generate a navaratna (nine gems) certificate."""
    return {
        "client_name": client_name,
        "fields": {
            "metal": await get_random_attribute(db, "navaratna", "metal_type") or "Gold 22K",
            "gross_weight": f"{random.uniform(12.0, 20.0):.2f}",
            "ruby_weight": f"{random.uniform(0.8, 1.5):.2f}",
            "pearl_weight": f"{random.uniform(1.5, 2.5):.2f}",
            "coral_weight": f"{random.uniform(1.2, 2.0):.2f}",
            "emerald_weight": f"{random.uniform(0.8, 1.5):.2f}",
            "yellow_sapphire_weight": f"{random.uniform(1.0, 1.8):.2f}",
            "diamond_weight": f"{random.uniform(0.5, 1.2):.2f}",
            "blue_sapphire_weight": f"{random.uniform(1.0, 1.8):.2f}",
            "hessonite_weight": f"{random.uniform(1.2, 2.0):.2f}",
            "cats_eye_weight": f"{random.uniform(1.3, 2.0):.2f}",
            "cut": "Mixed",
            "color": "Multi-colored",
            "clarity": "Eye Clean",
            "conclusion": "Natural Gemstones",
            "comment": random.choice([
                "Traditional Navaratna setting with 9 auspicious gems",
                "Premium quality Navaratna pendant",
                "Astrological quality gemstones",
                ""
            ])
        }
    }


# Client names for each certificate type
CLIENT_NAMES = {
    "single_diamond": ["Rajesh Jewelers", "Diamond Palace", "Heritage Jewels", "Royal Gems"],
    "loose_diamond": ["Diamond Trading Co.", "Brilliant Diamonds", "Sparkle Gems"],
    "loose_stone": ["Ruby Trading House", "Sapphire Emporium", "Emerald Gallery"],
    "single_mounded": ["Classic Jewelers", "Sapphire House", "Emerald Palace"],
    "double_mounded": ["Twin Gems", "Duo Jewels"],
    "navaratna": ["Navaratna Creations", "Astrological Gems"],
}


CERTIFICATE_GENERATORS = {
    "single_diamond": generate_single_diamond_certificate,
    "loose_diamond": generate_loose_diamond_certificate,
    "loose_stone": generate_loose_stone_certificate,
    "single_mounded": generate_single_mounded_certificate,
    "double_mounded": generate_double_mounded_certificate,
    "navaratna": generate_navaratna_certificate,
}


async def seed_certificates():
    """Generate sample certificates for all certificate types using dynamic attributes."""

    # Connect to MongoDB
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    print("🌱 Starting certificate seeding with dynamic attributes...")
    print(f"📊 Connected to database: {settings.DATABASE_NAME}")

    # Load test photos
    print("📷 Loading test photos...")
    certificate_photo = read_test_photo("certificate-photo-example.png")
    front_logo = read_test_photo("front-logo-example.png")
    back_logo = read_test_photo("back-logo-example.png")

    if certificate_photo:
        print("  ✓ Certificate photo loaded")
    if front_logo:
        print("  ✓ Front logo loaded")
    if back_logo:
        print("  ✓ Back logo loaded")

    # Check if attributes exist
    attr_count = await db.attributes.count_documents({"is_deleted": False})
    if attr_count == 0:
        print("⚠️  Warning: No attributes found in database. Certificates will use fallback values.")
        print("   Run the application first to seed default attributes.")
    else:
        print(f"✅ Found {attr_count} attributes in database")

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

        # Get generator function
        generator = CERTIFICATE_GENERATORS.get(type_slug)
        if not generator:
            print(f"  ⚠️  No generator function for {type_slug}, skipping...")
            continue

        # Get client names for this type
        client_names = CLIENT_NAMES.get(type_slug, [f"Client {i}" for i in range(1, 4)])
        
        print(f"  📋 Creating {len(client_names)} sample certificates...")

        for idx, client_name in enumerate(client_names, 1):
            # Generate certificate data dynamically
            cert_data = await generator(db, client_name)
            
            # Get or create client
            client_uuid = await get_or_create_client(db, cert_data["client_name"])

            # Generate certificate number
            today = datetime.utcnow()
            cert_number = f"G{today.strftime('%y%m%d')}{total_created + 1:04d}"

            # Create certificate document
            cert_doc = {
                "uuid": str(uuid_lib.uuid4()),
                "certificate_number": cert_number,
                "type": type_slug,
                "client_id": client_uuid,
                "category_id": schema["uuid"],
                "fields": cert_data["fields"],
                "photo": certificate_photo,  # Base64 data URL
                "brand_logo": front_logo,  # Base64 data URL
                "rear_brand_logo": back_logo,  # Base64 data URL
                "photo_url": None,  # Signed URL (will be generated by backend)
                "brand_logo_url": None,  # Signed URL (will be generated by backend)
                "rear_brand_logo_url": None,  # Signed URL (will be generated by backend)
                "is_deleted": False,
                "created_at": datetime.utcnow(),
                "updated_at": datetime.utcnow(),
            }

            # Insert certificate
            await db.certifications.insert_one(cert_doc)
            total_created += 1

            print(f"    ✓ Certificate #{idx}: {cert_number} (Client: {cert_data['client_name']})")

    print(f"\n✨ Seeding completed!")
    print(f"📊 Total certificates created: {total_created}")

    # Close connection
    client.close()


async def clear_existing_certificates():
    """Clear existing sample certificates (optional - for re-seeding)"""
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]

    result = await db.certifications.delete_many({})
    print(f"🗑️  Cleared {result.deleted_count} existing certificates")

    client.close()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Seed sample certificates with dynamic attributes")
    parser.add_argument("--clear", action="store_true", help="Clear existing certificates before seeding")
    args = parser.parse_args()

    if args.clear:
        print("⚠️  Clearing existing certificates...")
        asyncio.run(clear_existing_certificates())

    asyncio.run(seed_certificates())
