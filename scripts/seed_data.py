"""
Script to populate database with sample data for testing
Run with: python -m scripts.seed_data
Or: python scripts/seed_data.py (from diamond-erp-back-end directory)
"""
import asyncio
import random
import sys
import os
from datetime import datetime, timedelta
from bson import ObjectId
import uuid

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db, init_db
from app.core.security import hash_password
from app.utils.job_number import next_job_number
from app.utils.qr_generator import save_qr_code_to_minio
from app.core.config import settings

# Sample data
SAMPLE_NAMES = [
    "John Smith", "Sarah Johnson", "Michael Brown", "Emily Davis", "David Wilson",
    "Jessica Martinez", "Christopher Anderson", "Amanda Taylor", "Matthew Thomas",
    "Ashley Jackson", "Daniel White", "Melissa Harris", "James Martin", "Michelle Thompson",
    "Robert Garcia", "Laura Martinez", "William Rodriguez", "Jennifer Lee", "Joseph Walker",
    "Nicole Hall", "Charles Allen", "Stephanie Young", "Thomas King", "Angela Wright"
]

COMPANY_NAMES = [
    "Diamond World", "Precious Gems Co", "Sparkle Jewelers", "Royal Diamonds", "Elite Gemstones",
    "Crystal Palace", "Gemstone Masters", "Diamond Elite", "Precious Stones Inc", "Jewelry House",
    "Diamond Experts", "Gem Collection", "Luxury Gems", "Fine Jewelry Co", "Premium Diamonds"
]

CITIES = ["Mumbai", "Delhi", "Bangalore", "Hyderabad", "Chennai", "Kolkata", "Pune", "Ahmedabad"]

STATUSES = ["pending", "qc", "rfd", "photography", "certification", "completed"]
PRIORITIES = ["low", "medium", "high", "urgent"]
ITEM_TYPES = ["diamond", "jewelry", "gemstone", "loose_diamond"]

CERTIFICATE_TYPES = ["diamond", "gemstone"]

# Sample image URL (placeholder - you can use any image)
SAMPLE_IMAGE_URL = "certificates/sample_image.jpg"


async def create_sample_image_in_minio():
    """Create a placeholder image entry in MinIO (or use existing)"""
    # For simplicity, we'll just use a placeholder path
    # In production, you'd upload an actual image
    return SAMPLE_IMAGE_URL


async def seed_users(db):
    """Create sample users"""
    print("Creating sample users...")
    
    users = [
        {
            "email": "admin@test.com",
            "password": hash_password("admin123"),
            "name": "Admin User",
            "role": "admin",
            "is_active": True,
            "created_at": datetime.utcnow() - timedelta(days=30),
            "updated_at": datetime.utcnow() - timedelta(days=30),
        },
        {
            "email": "staff1@test.com",
            "password": hash_password("staff123"),
            "name": "Staff User 1",
            "role": "staff",
            "is_active": True,
            "created_at": datetime.utcnow() - timedelta(days=25),
            "updated_at": datetime.utcnow() - timedelta(days=25),
        },
        {
            "email": "staff2@test.com",
            "password": hash_password("staff123"),
            "name": "Staff User 2",
            "role": "staff",
            "is_active": True,
            "created_at": datetime.utcnow() - timedelta(days=20),
            "updated_at": datetime.utcnow() - timedelta(days=20),
        },
    ]
    
    # Add more staff users
    for i in range(3, 8):
        users.append({
            "email": f"staff{i}@test.com",
            "password": hash_password("staff123"),
            "name": f"Staff User {i}",
            "role": "staff",
            "is_active": True,
            "created_at": datetime.utcnow() - timedelta(days=15 - i),
            "updated_at": datetime.utcnow() - timedelta(days=15 - i),
        })
    
    inserted = await db.users.insert_many(users)
    print(f"Created {len(inserted.inserted_ids)} users")
    return [str(uid) for uid in inserted.inserted_ids]


async def seed_clients(db, user_ids):
    """Create sample clients"""
    print("Creating sample clients...")
    
    clients = []
    for i in range(15):
        name = random.choice(COMPANY_NAMES) + f" {i+1}"
        city = random.choice(CITIES)
        clients.append({
            "uuid": str(uuid.uuid4()),
            "name": name,
            "email": f"client{i+1}@example.com",
            "phone": f"+91{random.randint(9000000000, 9999999999)}",
            "address": f"{random.randint(1, 999)} Main Street, {city}",
            "gst_number": f"27AABCU{random.randint(1000, 9999)}D1Z{random.randint(1, 9)}" if random.random() > 0.3 else None,
            "notes": f"Sample client {i+1}",
            "is_deleted": False,
            "created_by": {
                "user_id": ObjectId(random.choice(user_ids)),
                "name": "Admin User",
                "email": "admin@test.com",
            },
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 60)),
            "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 60)),
        })
    
    inserted = await db.clients.insert_many(clients)
    print(f"Created {len(inserted.inserted_ids)} clients")
    return [c["uuid"] for c in clients]


async def seed_manufacturers(db, user_ids):
    """Create sample manufacturers"""
    print("Creating sample manufacturers...")
    
    manufacturers = []
    for i in range(10):
        name = f"Manufacturer {i+1}"
        manufacturers.append({
            "uuid": str(uuid.uuid4()),
            "name": name,
            "contact_person": random.choice(SAMPLE_NAMES),
            "email": f"manufacturer{i+1}@example.com",
            "phone": f"+91{random.randint(9000000000, 9999999999)}",
            "address": f"{random.randint(1, 999)} Industrial Area, {random.choice(CITIES)}",
            "gst_number": f"27AABCU{random.randint(1000, 9999)}D1Z{random.randint(1, 9)}" if random.random() > 0.3 else None,
            "notes": f"Sample manufacturer {i+1}",
            "is_deleted": False,
            "created_by": {
                "user_id": ObjectId(random.choice(user_ids)),
                "name": "Admin User",
                "email": "admin@test.com",
            },
            "created_at": datetime.utcnow() - timedelta(days=random.randint(1, 50)),
            "updated_at": datetime.utcnow() - timedelta(days=random.randint(1, 50)),
        })
    
    inserted = await db.manufacturers.insert_many(manufacturers)
    print(f"Created {len(inserted.inserted_ids)} manufacturers")
    return [m["uuid"] for m in manufacturers]


async def seed_jobs(db, client_ids, manufacturer_ids, user_ids):
    """Create sample jobs with different statuses and dates"""
    print("Creating sample jobs...")
    
    jobs = []
    for i in range(50):
        status = random.choice(STATUSES)
        item_type = random.choice(ITEM_TYPES)
        priority = random.choice(PRIORITIES)
        
        # Create dates spread over last 90 days
        created_date = datetime.utcnow() - timedelta(days=random.randint(1, 90))
        received_date = created_date - timedelta(days=random.randint(0, 5))
        expected_delivery = created_date + timedelta(days=random.randint(7, 30))
        
        # Work progress based on status (matching actual job structure)
        work_progress = {
            "qa": {
                "status": "done" if status in ["rfd", "photography", "certification", "completed"] else "in_progress" if status == "qc" else "pending",
                "started_at": received_date if status in ["qc", "rfd", "photography", "certification", "completed"] else None,
                "done_at": received_date + timedelta(days=1) if status in ["rfd", "photography", "certification", "completed"] else None,
                "done_by": None
            },
            "rfd": {
                "status": "done" if status in ["photography", "certification", "completed"] else "in_progress" if status == "rfd" else "pending",
                "started_at": received_date + timedelta(days=1) if status in ["rfd", "photography", "certification", "completed"] else None,
                "done_at": received_date + timedelta(days=2) if status in ["photography", "certification", "completed"] else None,
                "done_by": None
            },
            "photography": {
                "status": "done" if status in ["certification", "completed"] else "in_progress" if status == "photography" else "pending",
                "started_at": received_date + timedelta(days=2) if status in ["photography", "certification", "completed"] else None,
                "done_at": received_date + timedelta(days=3) if status in ["certification", "completed"] else None,
                "done_by": None
            },
        }
        
        job_data = {
            "uuid": str(uuid.uuid4()),
            "job_number": await next_job_number(),
            "client_id": random.choice(client_ids),
            "manufacturer_id": random.choice(manufacturer_ids) if random.random() > 0.4 else None,
            "item_type": item_type,
            "item_description": f"Sample {item_type.replace('_', ' ').title()} item {i+1}",
            "status": status,
            "priority": priority,
            "work_progress": work_progress,
            "received_datetime": received_date,
            "expected_delivery_date": expected_delivery,
            "notes": f"Sample job notes {i+1}" if random.random() > 0.5 else None,
            "is_deleted": False,
            "created_by": {
                "user_id": ObjectId(random.choice(user_ids)),
                "name": random.choice(SAMPLE_NAMES),
                "email": f"user{random.randint(1, 5)}@test.com",
            },
            "created_at": created_date,
            "updated_at": created_date + timedelta(days=random.randint(0, 10)),
        }
        
        # Add item-specific fields
        if item_type == "loose_diamond":
            job_data["item_weight"] = round(random.uniform(0.5, 5.0), 2)
            job_data["item_size"] = f"{random.randint(3, 8)}mm x {random.randint(3, 8)}mm"
        else:
            job_data["item_quantity"] = random.randint(1, 10)
        
        jobs.append(job_data)
    
    inserted = await db.jobs.insert_many(jobs)
    print(f"Created {len(inserted.inserted_ids)} jobs")
    return jobs


async def seed_certificates(db, client_ids):
    """Create sample certificates with different dates"""
    print("Creating sample certificates...")
    
    # First, create a sample image reference
    sample_image_path = await create_sample_image_in_minio()
    
    certificates = []
    for i in range(30):
        cert_type = random.choice(CERTIFICATE_TYPES)
        
        # Create dates spread over last 60 days
        created_date = datetime.utcnow() - timedelta(days=random.randint(1, 60))
        
        # Generate certificate UUID first
        cert_uuid = str(uuid.uuid4())
        
        # Generate certificate number manually (for seeding, we'll use the created_date)
        # Format: G + YYMMDD + 5-digit sequence
        date_str = created_date.strftime("%y%m%d")
        # Use a counter per date for this seeding session
        if not hasattr(seed_certificates, '_date_counters'):
            seed_certificates._date_counters = {}
        if date_str not in seed_certificates._date_counters:
            seed_certificates._date_counters[date_str] = 0
        seed_certificates._date_counters[date_str] += 1
        seq_num = seed_certificates._date_counters[date_str]
        cert_number = f"G{date_str}{seq_num:05d}"
        
        # Generate QR code
        frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:5173')
        qr_code_url = f"{frontend_url}/certificate/{cert_uuid}"
        try:
            qr_code_url_path = save_qr_code_to_minio(cert_uuid, qr_code_url, size=200)
        except Exception as e:
            print(f"Warning: Could not generate QR code for certificate {i+1}: {e}")
            qr_code_url_path = None
        
        # Fields based on certificate type
        fields = {
            "certificate_no": cert_number,
            "certificate_number": cert_number,
            "category": random.choice(["Ring", "Necklace", "Earring", "Bracelet", "Pendant"]),
            "metal_type": random.choice(["Gold", "Platinum", "Silver", "Rose Gold"]),
            "cut": random.choice(["Round", "Princess", "Emerald", "Cushion", "Oval"]),
            "clarity": random.choice(["FL", "IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2"]),
            "color": random.choice(["D", "E", "F", "G", "H", "I", "J", "K"]),
            "conclusion": random.choice(["Natural Diamond", "Lab Grown Diamond"]),
            "gross_weight": f"{random.uniform(1.0, 10.0):.2f}",
            "diamond_weight": f"{random.uniform(0.5, 3.0):.2f}",
            "comments": f"Sample certificate {i+1}" if random.random() > 0.4 else "",
        }
        
        if cert_type == "diamond":
            fields["diamond_piece"] = str(random.randint(1, 5))
        
        cert_data = {
            "uuid": cert_uuid,
            "type": cert_type,
            "client_id": random.choice(client_ids),
            "fields": fields,
            "photo_url": sample_image_path,
            "brand_logo_url": sample_image_path if random.random() > 0.5 else None,
            "qr_code_url": qr_code_url_path,
            "photo_edit_completed": random.random() > 0.3,
            "is_deleted": False,
            "created_at": created_date,
            "updated_at": created_date + timedelta(days=random.randint(0, 5)),
        }
        
        certificates.append(cert_data)
    
    inserted = await db.certifications.insert_many(certificates)
    print(f"Created {len(inserted.inserted_ids)} certificates")
    return certificates


async def seed_attributes(db, user_ids):
    """Create sample attributes for diamond and gemstone"""
    print("Creating sample attributes...")
    
    # Diamond attributes
    diamond_clarity = ["FL", "IF", "VVS1", "VVS2", "VS1", "VS2", "SI1", "SI2", "I1", "I2", "I3"]
    diamond_color = ["D", "E", "F", "G", "H", "I", "J", "K", "L", "M", "N"]
    diamond_cut = ["Round", "Princess", "Emerald", "Cushion", "Oval", "Pear", "Marquise", "Heart", "Asscher", "Radiant"]
    
    # Gemstone attributes
    gemstone_types = ["Ruby", "Sapphire", "Emerald", "Amethyst", "Topaz", "Garnet", "Peridot", "Aquamarine"]
    gemstone_shapes = ["Round", "Oval", "Cushion", "Princess", "Emerald", "Pear", "Marquise"]
    
    attributes = []
    
    # Diamond clarity
    for clarity in diamond_clarity:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "clarity",
            "name": clarity,
            "is_deleted": False,
            "created_by": {
                "user_id": ObjectId(random.choice(user_ids)),
                "name": "Admin User",
                "email": "admin@test.com",
            },
            "created_at": datetime.utcnow() - timedelta(days=30),
            "updated_at": datetime.utcnow() - timedelta(days=30),
        })
    
    # Diamond color
    for color in diamond_color:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "color",
            "name": color,
            "is_deleted": False,
            "created_by": {
                "user_id": ObjectId(random.choice(user_ids)),
                "name": "Admin User",
                "email": "admin@test.com",
            },
            "created_at": datetime.utcnow() - timedelta(days=30),
            "updated_at": datetime.utcnow() - timedelta(days=30),
        })
    
    # Diamond cut
    for cut in diamond_cut:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "diamond",
            "type": "cut",
            "name": cut,
            "is_deleted": False,
            "created_by": {
                "user_id": ObjectId(random.choice(user_ids)),
                "name": "Admin User",
                "email": "admin@test.com",
            },
            "created_at": datetime.utcnow() - timedelta(days=30),
            "updated_at": datetime.utcnow() - timedelta(days=30),
        })
    
    # Gemstone types
    for gem_type in gemstone_types:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "gemstone",
            "type": "type",
            "name": gem_type,
            "is_deleted": False,
            "created_by": {
                "user_id": ObjectId(random.choice(user_ids)),
                "name": "Admin User",
                "email": "admin@test.com",
            },
            "created_at": datetime.utcnow() - timedelta(days=30),
            "updated_at": datetime.utcnow() - timedelta(days=30),
        })
    
    # Gemstone shapes
    for shape in gemstone_shapes:
        attributes.append({
            "uuid": str(uuid.uuid4()),
            "group": "gemstone",
            "type": "shape",
            "name": shape,
            "is_deleted": False,
            "created_by": {
                "user_id": ObjectId(random.choice(user_ids)),
                "name": "Admin User",
                "email": "admin@test.com",
            },
            "created_at": datetime.utcnow() - timedelta(days=30),
            "updated_at": datetime.utcnow() - timedelta(days=30),
        })
    
    if attributes:
        inserted = await db.attributes.insert_many(attributes)
        print(f"Created {len(inserted.inserted_ids)} attributes")
    
    return attributes


async def main():
    """Main seeding function"""
    print("Starting database seeding...")
    
    # Initialize database
    db = await init_db()
    
    # Clear existing data (optional - comment out if you want to keep existing data)
    print("\nClearing existing data...")
    await db.users.delete_many({"email": {"$regex": "@test.com"}})
    await db.clients.delete_many({})
    await db.manufacturers.delete_many({})
    await db.jobs.delete_many({})
    await db.certifications.delete_many({})
    await db.attributes.delete_many({})
    await db.counters.delete_many({"_id": {"$regex": "^certificate_number_"}})
    print("Existing test data cleared\n")
    
    # Seed data
    user_ids = await seed_users(db)
    client_ids = await seed_clients(db, user_ids)
    manufacturer_ids = await seed_manufacturers(db, user_ids)
    await seed_attributes(db, user_ids)
    await seed_jobs(db, client_ids, manufacturer_ids, user_ids)
    await seed_certificates(db, client_ids)
    
    print("\n✅ Database seeding completed!")
    print(f"\nSummary:")
    print(f"- Users: {len(user_ids)}")
    print(f"- Clients: {len(client_ids)}")
    print(f"- Manufacturers: {len(manufacturer_ids)}")
    print(f"- Jobs: 50")
    print(f"- Certificates: 30")
    print(f"\nYou can now login with:")
    print(f"- Admin: admin@test.com / admin123")
    print(f"- Staff: staff1@test.com / staff123")


if __name__ == "__main__":
    asyncio.run(main())

