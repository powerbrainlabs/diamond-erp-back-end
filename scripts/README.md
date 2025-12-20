# Database Scripts

## Cleanup Script (`cleanup_data.py`)

This script removes all data from the database **except users**. Use this before seeding fresh data.

### How to run cleanup:

```bash
cd diamond-erp-back-end
source venv/bin/activate  # or activate your venv
python scripts/cleanup_data.py
```

Or run as a module:

```bash
cd diamond-erp-back-end
source venv/bin/activate
python -m scripts.cleanup_data
```

**What it removes:**
- All jobs
- All certificates
- All clients
- All manufacturers
- All QC reports
- All attributes
- All action history
- All counters (job numbers, certificate numbers, etc.)

**What it keeps:**
- All users (so you don't lose your login credentials)

---

## Seeding Script (`seed_data.py`)

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

- **Recommended workflow**: Run `cleanup_data.py` first, then run `seed_data.py` to get fresh data
- The seed script will create test users if they don't exist (admin@test.com, staff1@test.com, etc.)
- It uses a placeholder image path for all certificate photos and logos
- Job numbers and certificate numbers are auto-generated
- Dates are spread over the last 30-90 days for realistic testing
- All data includes proper relationships (jobs linked to clients, certificates linked to clients, etc.)
- Jobs are created with the new structure: `qc_job` and `certification_job` types with appropriate work_progress stages

