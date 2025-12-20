# Build frontend
FROM node:20-alpine AS frontend-builder

WORKDIR /app

# Copy frontend package files
# Note: Build context should be set to project root in docker-compose
COPY diamond-erp-front-end/package*.json ./

# Install dependencies
RUN npm ci

# Copy frontend source code
COPY diamond-erp-front-end/ ./

# Set build-time environment variables
ARG VITE_API_URL=http://localhost/api
ENV VITE_API_URL=$VITE_API_URL

# Build the frontend application
RUN npm run build

# Nginx stage
FROM nginx:alpine

# Remove default nginx config
RUN rm /etc/nginx/conf.d/default.conf

# Copy custom nginx configuration
COPY diamond-erp-back-end/nginx/nginx.conf /etc/nginx/nginx.conf
COPY diamond-erp-back-end/nginx/default.conf /etc/nginx/conf.d/default.conf

# Copy built frontend files from builder stage
COPY --from=frontend-builder /app/dist /usr/share/nginx/html

# Create necessary directories
RUN mkdir -p /var/log/nginx /var/cache/nginx

# Expose ports
EXPOSE 80 443

# Start nginx
CMD ["nginx", "-g", "daemon off;"]

