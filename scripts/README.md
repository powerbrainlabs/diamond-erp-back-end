# Certificate Seeding Script

## Prerequisites

1. **MongoDB must be running**
   ```bash
   # Option 1: Start with brew services
   brew services start mongodb-community

   # Option 2: Start backend (which connects to MongoDB)
   cd diamond-erp-back-end
   ../venv/bin/uvicorn app.main:app --reload
   ```

2. **Certificate types and schemas must be seeded**
   - Make sure the backend has been started at least once to seed the certificate types

## Usage

### Generate Sample Certificates

```bash
cd diamond-erp-back-end
../venv/bin/python scripts/seed_sample_certificates.py
```

This will create 3-4 sample certificates for each certificate type:
- Single Diamond (4 certificates)
- Loose Diamond (3 certificates)
- Loose Stone (3 certificates)
- Single Mounded (3 certificates)
- Double Mounded (2 certificates)
- Navaratna (2 certificates)

### Clear and Re-seed

To clear existing certificates and re-seed:

```bash
../venv/bin/python scripts/seed_sample_certificates.py --clear
```

## What Gets Created

For each certificate type, the script creates realistic sample data:
- **Clients**: Sample clients with names like "Rajesh Jewelers", "Diamond Palace", etc.
- **Certificate Numbers**: Sequential numbers in format G{YYMMDD}{XXXX}
- **Fields**: Realistic field values (weights, colors, clarity, etc.)
- **No Images**: Photo/logo URLs are set to None (can be added later)

## Verification

After running the script, you can verify:

1. **Check MongoDB**:
   ```bash
   mongosh
   use diamond_erp
   db.certifications.countDocuments()  # Should show ~17 certificates
   db.clients.countDocuments()  # Should show sample clients
   ```

2. **Check Frontend**:
   - Navigate to Certificates page
   - You should see all generated certificates
   - Each type should have 2-4 samples

## Troubleshooting

**Error: Connection refused**
- MongoDB is not running. Start it with `brew services start mongodb-community`

**Error: No certificate types found**
- Start the backend at least once to seed certificate types
- Or manually seed certificate types using the schema seeding script

**Error: No schema found**
- Certificate types exist but schemas are missing
- Check `category_schemas` collection in MongoDB
