# Nginx Reverse Proxy

This directory contains the nginx reverse proxy configuration for the Diamond ERP application.

## Overview

The nginx container acts as a reverse proxy and static file server for:
- **Frontend UI** (React app - served as static files)
- **Backend API** (FastAPI - proxied requests)
- Optional: MinIO API and Console

## Quick Start

### Prerequisites

1. Ensure the backend services are running:
   ```bash
   cd ../..
   cd diamond-erp-back-end
   docker-compose up -d
   ```

2. Start the frontend service (separate compose):
   ```bash
   cd ../diamond-erp-front-end
   docker-compose up -d
   ```
   
   **Note**: The frontend uses the same network (`erp-backend-network`) so nginx can connect to it.

3. Start nginx:
   ```bash
   cd ../diamond-erp-back-end/nginx
   docker-compose up -d
   ```
   
   **Note**: Nginx will connect to the frontend container via the shared network.

### Access Services

- **Frontend UI**: http://localhost/
- **Backend API**: http://localhost/api/
- **API Docs**: http://localhost/docs
- **Health Check**: http://localhost/health

## Configuration Files

- `nginx.conf`: Main nginx configuration
- `default.conf`: Server block configuration with upstream definitions for frontend and backend
- `Dockerfile`: Nginx container build configuration (nginx only, no frontend build)
- `docker-compose.yml`: Service orchestration (includes separate frontend service)

## How It Works

1. **Frontend Container** (runs separately via `diamond-erp-front-end/docker-compose.yml`): 
   - Builds the React application
   - Serves static files via `serve` (simple HTTP server, port 3000)
   - Handles React Router routing (SPA mode via `serve -s` flag)
   - **No nginx needed** - lightweight HTTP server only
   - Connects to `erp-backend-network` for communication

2. **Nginx Container**: 
   - Proxies frontend requests to the frontend container (port 3000)
   - Proxies API requests from `/api/*` to the backend container
   - Serves API documentation at `/docs` and `/redoc`
   - Handles caching for static assets
   - Single entry point on port 80
   - **Only one nginx instance** - cleaner architecture
   - Connects to `erp-backend-network` to reach frontend and backend

**Benefits for CI/CD**:
- Frontend can be built and deployed independently
- Faster frontend updates (no need to rebuild nginx)
- Better separation of concerns
- Easier to scale services independently
- Simpler architecture (one nginx, one simple HTTP server)
- Frontend and backend can be managed in separate repositories/pipelines

## SSL/TLS Setup (for Production)

To enable HTTPS:

1. **Obtain SSL certificates** (Let's Encrypt, Cloudflare, etc.)

2. **Create SSL directory and mount certificates**:
   ```bash
   mkdir -p ssl
   # Copy your certificates:
   # - ssl/cert.pem (or fullchain.pem)
   # - ssl/key.pem (or privkey.pem)
   ```

3. **Update docker-compose.yml**:
   Uncomment the SSL volume mount:
   ```yaml
   volumes:
     - ./ssl:/etc/nginx/ssl:ro
   ```

4. **Update default.conf**:
   Add an SSL server block:
   ```nginx
   server {
       listen 443 ssl http2;
       server_name your-domain.com;
       
       ssl_certificate /etc/nginx/ssl/cert.pem;
       ssl_certificate_key /etc/nginx/ssl/key.pem;
       
       # SSL configuration
       ssl_protocols TLSv1.2 TLSv1.3;
       ssl_ciphers HIGH:!aNULL:!MD5;
       ssl_prefer_server_ciphers on;
       
       # ... rest of configuration
   }
   
   # Redirect HTTP to HTTPS
   server {
       listen 80;
       server_name your-domain.com;
       return 301 https://$server_name$request_uri;
   }
   ```

## GCP Deployment

### Cloud Run / GKE

For GCP deployment, you may want to:

1. **Use Cloud Load Balancer** instead of nginx for SSL termination
2. **Configure nginx** to work behind the load balancer:
   ```nginx
   # Trust proxy headers from GCP Load Balancer
   real_ip_header X-Forwarded-For;
   set_real_ip_from 0.0.0.0/0;
   ```

3. **Update default.conf** to handle X-Forwarded-* headers properly

### Environment Variables

- `VITE_API_URL`: Frontend API URL (set at build time)
  - Default: `http://localhost/api`
  - Should be relative to the nginx server
  - Set in `.env` file or `docker-compose.yml`

## Exposing MinIO

If you want to expose MinIO through nginx (instead of directly), uncomment the MinIO server blocks in `default.conf` and update the port mappings in `docker-compose.yml`.

## Logs

Logs are stored in the `logs/` directory (mounted as a volume). To view logs:

```bash
# Access logs
tail -f logs/access.log

# Error logs
tail -f logs/error.log

# Or via docker
docker-compose logs -f nginx
```

## Health Checks

The nginx container includes a health check endpoint at `/health`. This can be used by:
- Docker health checks
- GCP Cloud Run health checks
- Kubernetes liveness/readiness probes

## Common Commands

```bash
# Start nginx
docker-compose up -d

# Stop nginx
docker-compose down

# Rebuild nginx
docker-compose build --no-cache
docker-compose up -d

# View logs
docker-compose logs -f

# Test nginx configuration
docker-compose exec nginx nginx -t

# Reload nginx configuration (without restart)
docker-compose exec nginx nginx -s reload
```

## Troubleshooting

### Nginx can't connect to backend or frontend

- Ensure backend services are running: `cd ../.. && cd diamond-erp-back-end && docker-compose ps`
- Ensure frontend service is running: `cd ../diamond-erp-front-end && docker-compose ps`
- Check network connectivity: `docker network inspect erp-backend-network`
- Verify container names match the upstream definitions in `default.conf`:
  - `backend` for API
  - `frontend` for static files
- Verify all services are on the same network: `docker network inspect erp-backend-network | grep -A 5 "Containers"`

### 502 Bad Gateway

- Check if backend is healthy: `docker exec diamond-erp-backend curl http://localhost:8000/`
- Check if frontend is serving files: `docker exec diamond-erp-frontend curl http://localhost:3000/`
- Check nginx error logs: `docker-compose logs nginx`
- Verify network configuration - ensure frontend is on `erp-backend-network`
- Ensure backend, frontend, and nginx services are all running
- Check frontend logs: `cd ../diamond-erp-front-end && docker-compose logs frontend`

### Port conflicts

- Change port mappings in `docker-compose.yml` if ports 80/443 are in use
- Update upstream URLs if backend port changes

## Performance Tuning

For production, consider:

1. **Worker processes**: Already set to `auto` in `nginx.conf`
2. **Connection limits**: Adjust `worker_connections` based on expected load
3. **Caching**: Add proxy cache for static responses
4. **Rate limiting**: Add rate limiting rules to prevent abuse
5. **Compression**: Already enabled (gzip)

## Security

- Security headers are included in `nginx.conf`
- Consider adding rate limiting
- Use SSL/TLS in production
- Restrict access to admin endpoints if needed
- Keep nginx updated

