# Docker Setup Guide

This guide explains how to run the OPA Permission API using Docker Compose.

## Prerequisites

- Docker Engine 20.10+
- Docker Compose 2.0+

## Quick Start (Development)

1. **Copy environment variables:**
   ```bash
   cp .env.example .env
   ```

2. **Start all services:**
   ```bash
   docker-compose up -d
   ```

3. **Check service health:**
   ```bash
   docker-compose ps
   ```

4. **View logs:**
   ```bash
   docker-compose logs -f api
   ```

5. **Initialize S3 bucket (LocalStack):**
   ```bash
   docker-compose exec localstack awslocal s3 mb s3://opa-policies
   ```

6. **Access the API:**
   - API: http://localhost:8000
   - API Docs: http://localhost:8000/docs
   - OPA: http://localhost:8181
   - PostgreSQL: localhost:5432

## Services

### API (FastAPI Application)
- **Port:** 8000
- **Health Check:** http://localhost:8000/health
- **Dependencies:** PostgreSQL, OPA, LocalStack

### OPA (Open Policy Agent)
- **Port:** 8181
- **Health Check:** http://localhost:8181/health
- **Policy Directory:** `./policies` (mounted read-only)

### PostgreSQL Database
- **Port:** 5432
- **Database:** opa_permissions
- **User:** postgres
- **Password:** postgres (change in production)
- **Data Persistence:** `postgres_data` volume

### LocalStack (S3 Emulation)
- **Port:** 4566
- **Services:** S3
- **Note:** Only for local development

## Database Migrations

Migrations run automatically on container startup. To run manually:

```bash
docker-compose exec api alembic upgrade head
```

To create a new migration:

```bash
docker-compose exec api alembic revision --autogenerate -m "description"
```

## Production Deployment

1. **Create production environment file:**
   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Update docker-compose.prod.yml with your configuration**

3. **Start with production configuration:**
   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

4. **Use real AWS S3 instead of LocalStack:**
   - Set proper AWS credentials in .env.prod
   - Remove S3_ENDPOINT_URL environment variable
   - LocalStack service will be disabled via profile

## Useful Commands

### Stop all services:
```bash
docker-compose down
```

### Stop and remove volumes (WARNING: deletes data):
```bash
docker-compose down -v
```

### Rebuild API container:
```bash
docker-compose build api
docker-compose up -d api
```

### View API logs:
```bash
docker-compose logs -f api
```

### Execute commands in API container:
```bash
docker-compose exec api bash
```

### Access PostgreSQL:
```bash
docker-compose exec db psql -U postgres -d opa_permissions
```

### Check OPA policies:
```bash
curl http://localhost:8181/v1/policies
```

### Push data to OPA:
```bash
curl -X PUT http://localhost:8181/v1/data/role_mappings \
  -H "Content-Type: application/json" \
  -d @data.json
```

## Troubleshooting

### API container fails to start
- Check logs: `docker-compose logs api`
- Verify database is healthy: `docker-compose ps db`
- Verify OPA is healthy: `docker-compose ps opa`

### Database connection errors
- Ensure PostgreSQL is running: `docker-compose ps db`
- Check DATABASE_URL in .env file
- Verify network connectivity: `docker-compose exec api ping db`

### OPA connection errors
- Ensure OPA is running: `docker-compose ps opa`
- Check OPA_URL in .env file
- Test OPA health: `curl http://localhost:8181/health`

### S3 errors (LocalStack)
- Ensure LocalStack is running: `docker-compose ps localstack`
- Create bucket: `docker-compose exec localstack awslocal s3 mb s3://opa-policies`
- List buckets: `docker-compose exec localstack awslocal s3 ls`

### Port conflicts
If ports 8000, 8181, 5432, or 4566 are already in use, modify the port mappings in docker-compose.yml:
```yaml
ports:
  - "8001:8000"  # Change host port (left side)
```

## Volume Management

### Backup PostgreSQL data:
```bash
docker-compose exec db pg_dump -U postgres opa_permissions > backup.sql
```

### Restore PostgreSQL data:
```bash
docker-compose exec -T db psql -U postgres opa_permissions < backup.sql
```

### Inspect volumes:
```bash
docker volume ls
docker volume inspect opa-permission-api_postgres_data
```

## Development Workflow

1. Make code changes in your local directory
2. Rebuild and restart the API container:
   ```bash
   docker-compose up -d --build api
   ```
3. View logs to verify changes:
   ```bash
   docker-compose logs -f api
   ```

## Environment Variables

See `.env.example` for all available environment variables and their descriptions.

Key variables:
- `DATABASE_URL`: PostgreSQL connection string
- `OPA_URL`: OPA server URL
- `S3_BUCKET`: S3 bucket name for policy storage
- `LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)
- `JWT_SECRET_KEY`: Secret key for JWT token validation

## Security Notes

- Change default passwords in production
- Use secrets management for sensitive values
- Enable SSL/TLS for database connections
- Restrict network access using Docker networks
- Use read-only mounts where possible
- Regularly update base images
