# OPA Permission API

A FastAPI-based backend server that integrates with Open Policy Agent (OPA) to provide dynamic, centralized permission management for multiple applications. The system enables token-based permission evaluation, dynamic role mapping management, and extensible custom policy evaluation.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Architecture](#architecture)
- [Prerequisites](#prerequisites)
- [Quick Start](#quick-start)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Database Migrations](#database-migrations)
- [OPA Policy Structure](#opa-policy-structure)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Troubleshooting](#troubleshooting)

## Overview

The OPA Permission API manages permissions for multiple applications across different environments (DEV, PROD, etc.), where access is controlled through Active Directory (AD) group memberships. Users can have different roles (user, admin) based on their AD group assignments, and the system supports dynamic updates to role mappings without requiring OPA image rebuilds.

### Key Components

- **FastAPI Backend**: RESTful API for permission evaluation and management
- **Open Policy Agent (OPA)**: Policy evaluation engine
- **PostgreSQL**: Structured data storage for applications and role mappings
- **S3 (or LocalStack)**: Policy file storage with versioning
- **JWT Token Authentication**: Secure user authentication

## Features

- ✅ **Token-Based Permission Evaluation**: Decode JWT tokens and evaluate permissions for all applications
- ✅ **Application Management**: CRUD operations for applications with admin authorization
- ✅ **Role Mapping Management**: Dynamic AD group to role mappings with OPA synchronization
- ✅ **Custom Policy Support**: Upload and evaluate custom Rego policies
- ✅ **Health Monitoring**: Comprehensive health checks for all system components
- ✅ **Audit Logging**: Complete audit trail for administrative operations
- ✅ **Dynamic Policy Updates**: Changes take effect immediately without OPA restarts

## Architecture

```
┌─────────────┐
│   Clients   │
└──────┬──────┘
       │
       ▼
┌─────────────────────────────────────┐
│       FastAPI Backend API           │
│  ┌──────────────────────────────┐  │
│  │  Routers (Endpoints)         │  │
│  ├──────────────────────────────┤  │
│  │  Services (Business Logic)   │  │
│  ├──────────────────────────────┤  │
│  │  Repositories (Data Access)  │  │
│  └──────────────────────────────┘  │
└───┬─────────┬─────────┬────────────┘
    │         │         │
    ▼         ▼         ▼
┌────────┐ ┌─────┐ ┌────────┐
│  OPA   │ │ DB  │ │   S3   │
└────────┘ └─────┘ └────────┘
```

## Prerequisites

- **Docker Engine** 20.10+ and **Docker Compose** 2.0+
- **Python** 3.10+ (for local development)
- **PostgreSQL** 15+ (or use Docker)
- **AWS Account** (or LocalStack for local S3 emulation)

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone the repository**

   ```bash
   git clone <repository-url>
   cd opa-permission-api
   ```

2. **Copy environment variables**

   ```bash
   cp .env.example .env
   ```

3. **Start all services**

   ```bash
   docker-compose up -d
   ```

4. **Initialize S3 bucket (LocalStack)**

   ```bash
   docker-compose exec localstack awslocal s3 mb s3://opa-policies
   ```

5. **Access the API**
   - API: <http://localhost:8000>
   - API Documentation: <http://localhost:8000/docs>
   - OPA: <http://localhost:8181>
   - PostgreSQL: localhost:5432

### Local Development

1. **Install dependencies**

   ```bash
   pip install -r requirements.txt
   # or using poetry
   poetry install
   ```

2. **Set up environment variables**

   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run database migrations**

   ```bash
   alembic upgrade head
   ```

4. **Start the API server**

   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## Configuration

### Environment Variables

Create a `.env` file based on `.env.example`:

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://postgres:postgres@localhost:5432/opa_permissions` | Yes |
| `OPA_URL` | OPA server URL | `http://localhost:8181` | Yes |
| `OPA_TIMEOUT` | OPA request timeout (seconds) | `5` | No |
| `S3_BUCKET` | S3 bucket name for policy storage | `opa-policies` | Yes |
| `S3_REGION` | AWS region | `us-east-1` | Yes |
| `S3_ENDPOINT_URL` | S3 endpoint (for LocalStack) | - | No |
| `AWS_ACCESS_KEY_ID` | AWS access key | - | Yes |
| `AWS_SECRET_ACCESS_KEY` | AWS secret key | - | Yes |
| `API_TITLE` | API title | `OPA Permission API` | No |
| `LOG_LEVEL` | Logging level | `INFO` | No |
| `JWT_SECRET_KEY` | JWT secret key for token validation | - | Yes |
| `JWT_ALGORITHM` | JWT algorithm | `HS256` | No |
| `JWT_VERIFY_SIGNATURE` | Verify JWT signature | `false` | No |
| `ADMIN_AD_GROUP` | AD group for admin users | `infodir-admin` | Yes |

### Docker Compose Services

The `docker-compose.yml` file defines the following services:

- **api**: FastAPI application (port 8000)
- **opa**: Open Policy Agent server (port 8181)
- **db**: PostgreSQL database (port 5432)
- **localstack**: S3 emulation for local development (port 4566)

## API Documentation

### Interactive API Documentation

Once the server is running, visit:

- **Swagger UI**: <http://localhost:8000/docs>
- **ReDoc**: <http://localhost:8000/redoc>

### API Endpoints

#### Permission Evaluation

##### POST /permission

Evaluate permissions for all applications for the authenticated user.

**Request:**

```bash
curl -X POST "http://localhost:8000/permission" \
  -H "Authorization: Bearer <token>"
```

**Response:**

```json
{
  "permissions": {
    "app-a": "admin",
    "app-b": "user",
    "app-c": "none"
  }
}
```

##### GET /permission/{app_id}

Check permission for a specific application.

**Request:**

```bash
curl -X GET "http://localhost:8000/permission/app-a" \
  -H "Authorization: Bearer <token>"
```

**Response:**

```json
{
  "application_id": "app-a",
  "role": "admin"
}
```

#### Application Management

##### POST /applications

Create a new application (admin only).

**Request:**

```bash
curl -X POST "http://localhost:8000/applications" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "app-a",
    "name": "Application A",
    "description": "My application"
  }'
```

**Response:**

```json
{
  "id": "app-a",
  "name": "Application A",
  "description": "My application",
  "created_at": "2025-01-09T10:00:00Z",
  "updated_at": null,
  "role_mappings": []
}
```

##### GET /applications

List all applications.

**Request:**

```bash
curl -X GET "http://localhost:8000/applications"
```

**Response:**

```json
[
  {
    "id": "app-a",
    "name": "Application A",
    "description": "My application",
    "created_at": "2025-01-09T10:00:00Z",
    "updated_at": null,
    "role_mappings": []
  }
]
```

##### GET /applications/{app_id}

Get a specific application.

**Request:**

```bash
curl -X GET "http://localhost:8000/applications/app-a"
```

##### PUT /applications/{app_id}

Update an application (admin only).

**Request:**

```bash
curl -X PUT "http://localhost:8000/applications/app-a" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Updated Application A",
    "description": "Updated description"
  }'
```

##### DELETE /applications/{app_id}

Delete an application (admin only).

**Request:**

```bash
curl -X DELETE "http://localhost:8000/applications/app-a" \
  -H "Authorization: Bearer <admin-token>"
```

#### Role Mapping Management

##### POST /role-mappings

Create a new role mapping (admin only).

**Request:**

```bash
curl -X POST "http://localhost:8000/role-mappings" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "application_id": "app-a",
    "environment": "DEV",
    "ad_group": "infodir-app-a-users",
    "role": "user"
  }'
```

**Response:**

```json
{
  "id": 1,
  "application_id": "app-a",
  "environment": "DEV",
  "ad_group": "infodir-app-a-users",
  "role": "user",
  "created_at": "2025-01-09T10:00:00Z",
  "updated_at": null
}
```

##### GET /role-mappings

List all role mappings (optionally filter by application).

**Request:**

```bash
# All role mappings
curl -X GET "http://localhost:8000/role-mappings"

# Filter by application
curl -X GET "http://localhost:8000/role-mappings?app_id=app-a"
```

##### PUT /role-mappings/{mapping_id}

Update a role mapping (admin only).

**Request:**

```bash
curl -X PUT "http://localhost:8000/role-mappings/1" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "role": "admin"
  }'
```

##### DELETE /role-mappings/{mapping_id}

Delete a role mapping (admin only).

**Request:**

```bash
curl -X DELETE "http://localhost:8000/role-mappings/1" \
  -H "Authorization: Bearer <admin-token>"
```

#### Custom Policy Management

##### POST /custom-policies

Upload a custom Rego policy (admin only).

**Request:**

```bash
curl -X POST "http://localhost:8000/custom-policies" \
  -H "Authorization: Bearer <admin-token>" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "my-custom-policy",
    "name": "My Custom Policy",
    "description": "Custom authorization logic",
    "rego_content": "package custom\n\nallow {\n  input.user == \"admin\"\n}"
  }'
```

##### GET /custom-policies

List all custom policies.

**Request:**

```bash
curl -X GET "http://localhost:8000/custom-policies" \
  -H "Authorization: Bearer <token>"
```

##### GET /custom-policies/{policy_id}

Get a specific custom policy.

**Request:**

```bash
curl -X GET "http://localhost:8000/custom-policies/my-custom-policy" \
  -H "Authorization: Bearer <token>"
```

##### POST /custom-policies/{policy_id}/evaluate

Evaluate a custom policy with input data.

**Request:**

```bash
curl -X POST "http://localhost:8000/custom-policies/my-custom-policy/evaluate" \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "input_data": {
      "user": "admin",
      "action": "read"
    }
  }'
```

**Response:**

```json
{
  "policy_id": "my-custom-policy",
  "result": {
    "allow": true
  }
}
```

#### Health Checks

##### GET /health

Check overall system health.

**Request:**

```bash
curl -X GET "http://localhost:8000/health"
```

**Response:**

```json
{
  "status": "healthy",
  "components": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "opa": {
      "status": "healthy",
      "message": "OPA server is reachable"
    },
    "s3": {
      "status": "healthy",
      "message": "S3 bucket is accessible"
    }
  }
}
```

##### GET /health/opa

Check OPA server health.

##### GET /health/db

Check database health.

##### GET /health/s3

Check S3 bucket accessibility.

## Database Migrations

This project uses Alembic for database migrations.

### Running Migrations

**Upgrade to latest version:**

```bash
alembic upgrade head
```

**Downgrade one version:**

```bash
alembic downgrade -1
```

**View migration history:**

```bash
alembic history
```

**View current version:**

```bash
alembic current
```

### Creating New Migrations

**Auto-generate migration from model changes:**

```bash
alembic revision --autogenerate -m "Description of changes"
```

**Create empty migration:**

```bash
alembic revision -m "Description of changes"
```

### Docker Environment

Migrations run automatically when the API container starts. To run manually:

```bash
docker-compose exec api alembic upgrade head
```

## OPA Policy Structure

### Base Permission Policy

The base policy is located at `policies/permissions.rego`:

```rego
package permissions

import future.keywords.if
import future.keywords.in

default allow = false

# Get user's role for a specific application
user_role[app_id] = role if {
    some app_id
    some env
    some group in input.user.ad_groups
    role := data.role_mappings[app_id][env][group]
}

# Evaluate permissions for all applications
permissions[app_id] = role if {
    some app_id in input.applications
    role := user_role[app_id]
}

# Default to "none" if no role found
permissions[app_id] = "none" if {
    some app_id in input.applications
    not user_role[app_id]
}
```

### Policy Data Structure

Role mappings are pushed to OPA in the following format:

```json
{
  "role_mappings": {
    "app-a": {
      "DEV": {
        "infodir-app-a-users": "user",
        "infodir-app-a-admins": "admin"
      },
      "PROD": {
        "infodir-app-a-admins": "admin"
      }
    }
  }
}
```

### Policy Loading

1. **On Startup**: The base `permissions.rego` policy is uploaded to OPA
2. **On Role Mapping Changes**: All role mappings are synchronized to OPA via the Data API
3. **Custom Policies**: Uploaded via the `/custom-policies` endpoint and stored in S3

### Testing Policies

You can test OPA policies directly:

```bash
# Query OPA directly
curl -X POST http://localhost:8181/v1/data/permissions/permissions \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "user": {
        "ad_groups": ["infodir-app-a-users"]
      },
      "applications": ["app-a", "app-b"]
    }
  }'
```

## Development

### Token Generator for API Testing

The project includes a convenient token generator script for creating JWT tokens during development and testing.

**Quick usage:**

```bash
# Generate an admin token
make token

# Generate a regular user token
make token-user

# Generate curl commands with authentication
make token-curl
```

**Manual usage:**

```bash
# Generate a default admin token
python scripts/generate_token.py

# Generate a token for a specific user
python scripts/generate_token.py \
  --employee-id E12345 \
  --ad-groups "infodir-app-user" \
  --email user@example.com \
  --name "Regular User"

# View token payload in JSON format
python scripts/generate_token.py --output json

# Generate curl commands for testing
python scripts/generate_token.py --output curl
```

**Use with API requests:**

```bash
# Store token in variable
TOKEN=$(make token 2>/dev/null)

# Test permission endpoint
curl -X POST "http://localhost:8000/permission" \
  -H "Authorization: Bearer $TOKEN"

# Test applications endpoint
curl -X GET "http://localhost:8000/applications" \
  -H "Authorization: Bearer $TOKEN"
```

For more examples, see `scripts/README.md` and `scripts/EXAMPLES.md`.

### Project Structure

```
.
├── app/
│   ├── auth/              # Authentication and token decoding
│   ├── models/            # SQLAlchemy database models
│   ├── repositories/      # Data access layer
│   ├── routers/           # API endpoints
│   ├── schemas/           # Pydantic request/response models
│   ├── services/          # Business logic
│   ├── config.py          # Configuration management
│   ├── database.py        # Database connection
│   ├── dependencies.py    # FastAPI dependencies
│   ├── exceptions.py      # Custom exceptions
│   └── main.py            # FastAPI application
├── alembic/               # Database migrations
├── policies/              # OPA policy files
├── tests/                 # Test suite
├── docker-compose.yml     # Docker Compose configuration
├── Dockerfile             # API container definition
├── requirements.txt       # Python dependencies
└── README.md              # This file
```

### Running Tests

**Run all tests:**

```bash
pytest
```

**Run with coverage:**

```bash
pytest --cov=app --cov-report=html
```

**Run specific test file:**

```bash
pytest tests/test_permissions_router.py
```

**Run in Docker:**

```bash
docker-compose exec api pytest
```

### Code Quality

**Format code:**

```bash
black app/ tests/
```

**Lint code:**

```bash
flake8 app/ tests/
```

**Type checking:**

```bash
mypy app/
```

## Deployment

### Production Deployment

1. **Create production environment file:**

   ```bash
   cp .env.example .env.prod
   # Edit .env.prod with production values
   ```

2. **Use production Docker Compose:**

   ```bash
   docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
   ```

3. **Configure real AWS S3:**
   - Remove `S3_ENDPOINT_URL` from environment
   - Set proper AWS credentials
   - Ensure S3 bucket exists with versioning enabled

4. **Security Checklist:**
   - [ ] Change all default passwords
   - [ ] Use secrets management (AWS Secrets Manager, HashiCorp Vault)
   - [ ] Enable SSL/TLS for database connections
   - [ ] Configure firewall rules
   - [ ] Enable audit logging
   - [ ] Set up monitoring and alerting
   - [ ] Regular security updates

### Kubernetes Deployment

See `k8s/` directory for Kubernetes manifests (if available).

### Monitoring

Recommended monitoring setup:

- **Prometheus**: Metrics collection
- **Grafana**: Metrics visualization
- **ELK Stack**: Log aggregation and analysis
- **Sentry**: Error tracking

## Troubleshooting

### Common Issues

#### API Container Fails to Start

**Check logs:**

```bash
docker-compose logs api
```

**Verify dependencies:**

```bash
docker-compose ps
```

**Common causes:**

- Database not ready (wait for health check)
- OPA not reachable
- Invalid environment variables

#### Database Connection Errors

**Test connection:**

```bash
docker-compose exec api python -c "from app.database import engine; engine.connect()"
```

**Check DATABASE_URL:**

```bash
docker-compose exec api env | grep DATABASE_URL
```

#### OPA Connection Errors

**Test OPA health:**

```bash
curl http://localhost:8181/health
```

**Check OPA logs:**

```bash
docker-compose logs opa
```

#### S3 Errors (LocalStack)

**Create bucket:**

```bash
docker-compose exec localstack awslocal s3 mb s3://opa-policies
```

**List buckets:**

```bash
docker-compose exec localstack awslocal s3 ls
```

#### Permission Evaluation Returns "none"

**Verify role mappings exist:**

```bash
curl http://localhost:8000/role-mappings
```

**Check OPA data:**

```bash
curl http://localhost:8181/v1/data/role_mappings
```

**Verify user's AD groups match:**

- Decode JWT token to see user's AD groups
- Ensure AD group names match exactly in role mappings

### Logs

**View all logs:**

```bash
docker-compose logs -f
```

**View API logs only:**

```bash
docker-compose logs -f api
```

**View logs with timestamps:**

```bash
docker-compose logs -f --timestamps api
```

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

[Your License Here]

## Support

For issues and questions:

- Create an issue in the repository
- Contact the development team
- Check the documentation at <http://localhost:8000/docs>

---

**Built with ❤️ using FastAPI and Open Policy Agent**
