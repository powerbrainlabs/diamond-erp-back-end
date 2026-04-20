# Diamond ERP Backend

FastAPI backend application for the Diamond ERP system. n


## Features

- FastAPI REST API
- MongoDB database
- MinIO object storage
- JWT authentication
- Admin user seeding

## Docker Setup

This project includes a `docker-compose.yml` file that sets up:
- Backend API service
- MongoDB database
- MinIO object storage

### Quick Start with Docker

1. **Set up environment variables** (optional):
   Create a `.env` file:
   ```env
   SECRET_KEY=your-secret-key-change-this-in-production-min-16-chars
   ADMIN_EMAIL=admin@diamonderp.com
   ADMIN_PASSWORD=Admin@123
   ADMIN_NAME=Administrator
   REMOVE_BG_API_KEY=your-remove-bg-api-key
   ```

2. **Start all services**:
   ```bash
   docker-compose up -d
   ```

3. **View logs**:
   ```bash
   docker-compose logs -f
   ```

4. **Access services**:
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - MongoDB: localhost:27017
   - MinIO Console: http://localhost:9001 (minioadmin/minioadmin)

### Docker Commands

```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# Rebuild and restart
docker-compose build
docker-compose up -d

# View logs
docker-compose logs -f

# Execute commands in container
docker-compose exec backend bash

# Run database seeding
docker-compose exec backend python -m scripts.seed_data
```

## Local Development Setup

### Prerequisites

- Python 3.9+
- MongoDB (running locally or via Docker)
- MinIO (running locally or via Docker)

### Installation

1. **Create virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file with required variables (see Docker setup above)

4. **Run the application**:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Documentation

Once the server is running, visit:
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

## Project Structure

```
diamond-erp-back-end/
├── app/
│   ├── api/           # API routes
│   ├── core/          # Core configuration and utilities
│   ├── db/            # Database connection and setup
│   ├── schemas/       # Pydantic schemas
│   └── utils/         # Utility functions
├── scripts/           # Utility scripts (seeding, cleanup)
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```
