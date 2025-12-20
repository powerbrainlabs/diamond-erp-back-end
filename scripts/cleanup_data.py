"""
Script to clean up database - removes all data except users
Run with: python -m scripts.cleanup_data
Or: python scripts/cleanup_data.py (from diamond-erp-back-end directory)
"""
import asyncio
import sys
import os

# Add parent directory to path to allow imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.db.database import get_db, init_db


async def cleanup_database():
    """Remove all data except users"""
    print("Starting database cleanup...")
    
    # Initialize database
    db = await init_db()
    
    # Remove all data except users
    print("\nCleaning up data...")
    
    # Remove jobs
    jobs_deleted = await db.jobs.delete_many({})
    print(f"✓ Deleted {jobs_deleted.deleted_count} jobs")
    
    # Remove certificates
    certs_deleted = await db.certifications.delete_many({})
    print(f"✓ Deleted {certs_deleted.deleted_count} certificates")
    
    # Remove clients
    clients_deleted = await db.clients.delete_many({})
    print(f"✓ Deleted {clients_deleted.deleted_count} clients")
    
    # Remove manufacturers
    manufacturers_deleted = await db.manufacturers.delete_many({})
    print(f"✓ Deleted {manufacturers_deleted.deleted_count} manufacturers")
    
    # Remove QC reports
    qc_reports_deleted = await db.qc_reports.delete_many({})
    print(f"✓ Deleted {qc_reports_deleted.deleted_count} QC reports")
    
    # Remove attributes
    attributes_deleted = await db.attributes.delete_many({})
    print(f"✓ Deleted {attributes_deleted.deleted_count} attributes")
    
    # Remove action history
    action_history_deleted = await db.action_history.delete_many({})
    print(f"✓ Deleted {action_history_deleted.deleted_count} action history records")
    
    # Remove counters (job numbers, certificate numbers, etc.)
    counters_deleted = await db.counters.delete_many({})
    print(f"✓ Deleted {counters_deleted.deleted_count} counters")
    
    # Keep users - don't delete them
    user_count = await db.users.count_documents({})
    print(f"\n✓ Kept {user_count} users (not deleted)")
    
    print("\n✅ Database cleanup completed!")
    print("\nYou can now run the seed script to populate fresh data:")
    print("  python -m scripts.seed_data")
    print("  or")
    print("  python scripts/seed_data.py")


async def main():
    """Main cleanup function"""
    try:
        await cleanup_database()
    except Exception as e:
        print(f"\n❌ Error during cleanup: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())

