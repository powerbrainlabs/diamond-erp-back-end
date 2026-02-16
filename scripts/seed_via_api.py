#!/usr/bin/env python3
"""
Seed sample certificates using the backend API.
This approach doesn't require direct MongoDB connection - it uses the running backend.

Usage:
    # Make sure backend is running first:
    # cd diamond-erp-back-end && ../venv/bin/uvicorn app.main:app --reload

    # Then run this script:
    python scripts/seed_via_api.py
"""

import requests
import json
from datetime import datetime

BASE_URL = "http://localhost:8000"

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
}


def get_or_create_client(client_name):
    """Get existing client or create new one"""
    # Search for client
    response = requests.get(f"{BASE_URL}/api/clients", params={"search": client_name})
    if response.status_code == 200:
        data = response.json()
        clients = data.get("clients", [])
        for client in clients:
            if client["name"].lower() == client_name.lower():
                return client["uuid"]

    # Create new client
    client_data = {
        "name": client_name,
        "contact_person": f"Contact {client_name}",
        "email": f"{client_name.lower().replace(' ', '_')}@example.com",
        "phone": f"+91-900000{hash(client_name) % 10000:04d}",
        "address": f"{client_name} Address",
        "notes": f"Sample client for testing",
    }

    response = requests.post(f"{BASE_URL}/api/clients", json=client_data)
    if response.status_code == 201:
        return response.json()["uuid"]
    else:
        print(f"  ❌ Failed to create client {client_name}: {response.text}")
        return None


def get_schema_for_type(type_slug):
    """Get category schema for a certificate type"""
    response = requests.get(f"{BASE_URL}/api/super-admin/categories")
    if response.status_code == 200:
        schemas = response.json()
        for schema in schemas:
            if schema.get("group") == type_slug:
                return schema["uuid"]
    return None


def seed_certificates():
    """Generate sample certificates via API"""
    print("🌱 Starting certificate seeding via API...")
    print(f"📊 Backend URL: {BASE_URL}")

    # Check if backend is accessible
    try:
        response = requests.get(f"{BASE_URL}/api/certificate-types")
        if response.status_code != 200:
            print("❌ Backend is not accessible or endpoint failed")
            print(f"   Response: {response.status_code} - {response.text[:200]}")
            return
    except requests.exceptions.ConnectionError:
        print("❌ Cannot connect to backend. Make sure it's running:")
        print("   cd diamond-erp-back-end && ../venv/bin/uvicorn app.main:app --reload")
        return

    # Get all certificate types
    response = requests.get(f"{BASE_URL}/api/certificate-types")
    cert_types = response.json() if response.status_code == 200 else []

    if not cert_types:
        print("❌ No certificate types found")
        return

    print(f"✅ Found {len(cert_types)} certificate types")

    total_created = 0

    for cert_type in cert_types:
        type_slug = cert_type["slug"]
        type_name = cert_type["name"]

        print(f"\n📝 Processing: {type_name} ({type_slug})")

        # Get schema for this type
        schema_id = get_schema_for_type(type_slug)
        if not schema_id:
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
            client_uuid = get_or_create_client(sample["client_name"])
            if not client_uuid:
                continue

            # Create certificate payload
            cert_payload = {
                "type": type_slug,
                "client_id": client_uuid,
                "category_id": schema_id,
                "fields": sample["fields"],
            }

            # Create certificate
            response = requests.post(f"{BASE_URL}/api/certifications", json=cert_payload)

            if response.status_code == 201:
                cert_data = response.json()
                cert_number = cert_data.get("certificate_number", "N/A")
                total_created += 1
                print(f"    ✓ Certificate #{idx}: {cert_number} (Client: {sample['client_name']})")
            else:
                print(f"    ❌ Failed to create certificate #{idx}: {response.status_code}")
                print(f"       {response.text[:200]}")

    print(f"\n✨ Seeding completed!")
    print(f"📊 Total certificates created: {total_created}")


if __name__ == "__main__":
    seed_certificates()
