# Database Seeding Script

This script populates the database with sample data for testing purposes.

## What it creates:

- **Users**: 8 users (1 admin, 7 staff) with different creation dates
- **Clients**: 15 sample clients with addresses, GST numbers, etc.
- **Manufacturers**: 10 sample manufacturers
- **Attributes**: Diamond and gemstone attributes (clarity, color, cut, types, shapes)
- **Jobs**: 50 jobs with different statuses, priorities, and dates spread over 90 days
- **Certificates**: 30 certificates with different dates spread over 60 days

## How to run:

**Make sure you're in the virtual environment and in the `diamond-erp-back-end` directory:**

```bash
cd diamond-erp-back-end
source venv/bin/activate  # or activate your venv
python scripts/seed_data.py
```

Or run as a module:

```bash
cd diamond-erp-back-end
source venv/bin/activate
python -m scripts.seed_data
```

**Note**: Make sure all dependencies are installed (`pip install -r requirements.txt`)

## Test Credentials:

After running the script, you can login with:

- **Admin**: `admin@test.com` / `admin123`
- **Staff**: `staff1@test.com` / `staff123` (or staff2@test.com, etc.)

## Notes:

- The script will **clear existing test data** (users with @test.com emails, all clients, manufacturers, jobs, certificates, and attributes)
- It uses a placeholder image path for all certificate photos and logos
- Job numbers and certificate numbers are auto-generated
- Dates are spread over the last 30-90 days for realistic testing
- All data includes proper relationships (jobs linked to clients, certificates linked to clients, etc.)

