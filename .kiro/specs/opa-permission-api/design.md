# Design Document

## Overview

This document describes the design for a FastAPI-based backend server that integrates with Open Policy Agent (OPA) to provide dynamic, centralized permission management for multiple applications. The system enables token-based permission evaluation, dynamic role mapping management, and extensible custom policy evaluation.

### Key Design Principles

- **Separation of Concerns**: Policy logic resides in OPA, while the API handles data management and orchestration
- **Dynamic Updates**: All policy and data changes take effect immediately without requiring OPA image rebuilds
- **Extensibility**: Support for custom Rego policies beyond standard application permissions
- **Reliability**: Robust error handling, retry logic, and comprehensive logging
- **Performance**: Efficient caching strategies and optimized database queries

## Architecture

### High-Level Architecture

```mermaid
graph TB
    Client[API Clients]
    API[FastAPI Backend]
    OPA[OPA Server]
    DB[(PostgreSQL)]
    S3[S3 Storage]
    Auth[Token Decoder]
    
    Client -->|HTTP Requests| API
    API -->|Decode Token| Auth
    API -->|Query/Update Data| DB
    API -->|Store/Retrieve Policies| S3
    API -->|Policy Evaluation| OPA
    API -->|Push Policy Data| OPA
    API -->|Upload Policies| OPA
```

### Component Interaction Flow

**Permission Evaluation Flow:**

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant TokenDecoder
    participant DB
    participant OPA
    
    Client->>API: POST /permission (token)
    API->>TokenDecoder: decode_token(token)
    TokenDecoder-->>API: user_info (ad_groups, employee_id)
    API->>DB: get_all_applications()
    DB-->>API: applications[]
    API->>DB: get_role_mappings()
    DB-->>API: role_mappings[]
    API->>OPA: evaluate_policy(user_info, apps, mappings)
    OPA-->>API: permissions_result
    API-->>Client: {app_id: permission_level}
```

**Role Mapping Update Flow:**

```mermaid
sequenceDiagram
    participant Admin
    participant API
    participant DB
    participant OPA
    
    Admin->>API: POST /role-mappings (mapping_data)
    API->>DB: insert_role_mapping(mapping_data)
    DB-->>API: success
    API->>DB: get_all_role_mappings()
    DB-->>API: updated_mappings[]
    API->>OPA: PUT /v1/data/role_mappings (updated_mappings)
    OPA-->>API: success
    API-->>Admin: 201 Created
```

## Components and Interfaces

### 1. FastAPI Application Layer

**Main Application (`app/main.py`)**

- FastAPI application initialization
- Middleware configuration (CORS, logging, error handling)
- Router registration
- Lifespan events for startup/shutdown

**Routers:**

- `app/routers/permissions.py`: Permission evaluation endpoints
- `app/routers/applications.py`: Application management endpoints
- `app/routers/role_mappings.py`: Role mapping CRUD endpoints
- `app/routers/custom_policies.py`: Custom policy management and evaluation
- `app/routers/health.py`: Health check endpoints

### 2. Service Layer

**OPA Service (`app/services/opa_service.py`)**

```python
class OPAService:
    async def evaluate_permissions(
        self, 
        user_info: UserInfo, 
        applications: List[Application],
        role_mappings: List[RoleMapping]
    ) -> Dict[str, str]
    
    async def push_policy_data(
        self, 
        data_path: str, 
        data: Dict
    ) -> bool
    
    async def upload_policy(
        self, 
        policy_id: str, 
        policy_content: str
    ) -> bool
    
    async def evaluate_custom_policy(
        self, 
        policy_id: str, 
        input_data: Dict
    ) -> Dict
    
    async def health_check(self) -> bool
```

**Application Service (`app/services/application_service.py`)**

```python
class ApplicationService:
    async def create_application(
        self, 
        app_data: ApplicationCreate
    ) -> Application
    
    async def get_application(
        self, 
        app_id: str
    ) -> Optional[Application]
    
    async def list_applications(self) -> List[Application]
    
    async def update_application(
        self, 
        app_id: str, 
        app_data: ApplicationUpdate
    ) -> Application
    
    async def delete_application(
        self, 
        app_id: str
    ) -> bool
```

**Role Mapping Service (`app/services/role_mapping_service.py`)**

```python
class RoleMappingService:
    async def create_role_mapping(
        self, 
        mapping: RoleMappingCreate
    ) -> RoleMapping
    
    async def get_role_mappings(
        self, 
        app_id: Optional[str] = None
    ) -> List[RoleMapping]
    
    async def update_role_mapping(
        self, 
        mapping_id: int, 
        mapping: RoleMappingUpdate
    ) -> RoleMapping
    
    async def delete_role_mapping(
        self, 
        mapping_id: int
    ) -> bool
    
    async def sync_to_opa(self) -> bool
```

**Custom Policy Service (`app/services/custom_policy_service.py`)**

```python
class CustomPolicyService:
    async def upload_policy(
        self, 
        policy: CustomPolicyCreate, 
        user_id: str
    ) -> CustomPolicy
    
    async def get_policy(
        self, 
        policy_id: str
    ) -> Optional[CustomPolicy]
    
    async def list_policies(self) -> List[CustomPolicy]
    
    async def validate_rego(
        self, 
        rego_content: str
    ) -> Tuple[bool, Optional[str]]
    
    async def evaluate_policy(
        self, 
        policy_id: str, 
        input_data: Dict
    ) -> Dict
```

**S3 Service (`app/services/s3_service.py`)**

```python
class S3Service:
    async def upload_policy_file(
        self, 
        policy_id: str, 
        content: str, 
        version: str
    ) -> str
    
    async def download_policy_file(
        self, 
        policy_id: str, 
        version: Optional[str] = None
    ) -> str
    
    async def list_policy_versions(
        self, 
        policy_id: str
    ) -> List[str]
```

### 3. Data Access Layer

**Database Models (`app/models/`)**

```python
# app/models/application.py
class Application(Base):
    __tablename__ = "applications"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    role_mappings = relationship("RoleMapping", back_populates="application")

# app/models/role_mapping.py
class RoleMapping(Base):
    __tablename__ = "role_mappings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(String, ForeignKey("applications.id"))
    environment = Column(String, nullable=False)
    ad_group = Column(String, nullable=False)
    role = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
    
    application = relationship("Application", back_populates="role_mappings")
    
    __table_args__ = (
        UniqueConstraint('application_id', 'environment', 'ad_group', 
                        name='uq_app_env_adgroup'),
    )

# app/models/custom_policy.py
class CustomPolicy(Base):
    __tablename__ = "custom_policies"
    
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    description = Column(String)
    s3_key = Column(String, nullable=False)
    version = Column(String, nullable=False)
    creator_id = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, onupdate=datetime.utcnow)
```

**Repository Pattern (`app/repositories/`)**

```python
# app/repositories/application_repository.py
class ApplicationRepository:
    def __init__(self, db: Session):
        self.db = db
    
    async def create(self, app: Application) -> Application
    async def get_by_id(self, app_id: str) -> Optional[Application]
    async def get_all(self) -> List[Application]
    async def update(self, app: Application) -> Application
    async def delete(self, app_id: str) -> bool
```

### 4. Authentication and Authorization

**Token Decoder (`app/auth/token_decoder.py`)**

```python
class TokenDecoder:
    def decode_token(self, token: str) -> UserInfo:
        """Leverages existing token decoding functionality"""
        pass

@dataclass
class UserInfo:
    employee_id: str
    ad_groups: List[str]
    email: str
    name: str
```

**Dependency Injection (`app/dependencies.py`)**

```python
async def get_current_user(
    token: str = Depends(oauth2_scheme)
) -> UserInfo:
    """Extract and validate user from token"""
    
async def require_admin(
    user: UserInfo = Depends(get_current_user)
) -> UserInfo:
    """Verify user has admin privileges"""
```

### 5. Configuration Management

**Configuration (`app/config.py`)**

```python
class Settings(BaseSettings):
    # Database
    database_url: str
    
    # OPA
    opa_url: str
    opa_timeout: int = 5
    
    # S3
    s3_bucket: str
    s3_region: str
    aws_access_key_id: str
    aws_secret_access_key: str
    
    # API
    api_title: str = "OPA Permission API"
    api_version: str = "1.0.0"
    
    # Logging
    log_level: str = "INFO"
    
    class Config:
        env_file = ".env"
```

## Data Models

### API Request/Response Models

**Permission Models (`app/schemas/permission.py`)**

```python
class PermissionRequest(BaseModel):
    token: str

class PermissionResponse(BaseModel):
    permissions: Dict[str, str]  # {app_id: role}

class AppPermissionResponse(BaseModel):
    application_id: str
    role: str
```

**Application Models (`app/schemas/application.py`)**

```python
class ApplicationBase(BaseModel):
    name: str
    description: Optional[str] = None

class ApplicationCreate(ApplicationBase):
    id: str

class ApplicationUpdate(ApplicationBase):
    pass

class ApplicationResponse(ApplicationBase):
    id: str
    created_at: datetime
    updated_at: Optional[datetime]
    role_mappings: List[RoleMappingResponse]
```

**Role Mapping Models (`app/schemas/role_mapping.py`)**

```python
class RoleMappingBase(BaseModel):
    application_id: str
    environment: str
    ad_group: str
    role: str

class RoleMappingCreate(RoleMappingBase):
    pass

class RoleMappingUpdate(BaseModel):
    environment: Optional[str]
    ad_group: Optional[str]
    role: Optional[str]

class RoleMappingResponse(RoleMappingBase):
    id: int
    created_at: datetime
    updated_at: Optional[datetime]
```

**Custom Policy Models (`app/schemas/custom_policy.py`)**

```python
class CustomPolicyCreate(BaseModel):
    id: str
    name: str
    description: Optional[str]
    rego_content: str

class CustomPolicyEvaluate(BaseModel):
    policy_id: str
    input_data: Dict[str, Any]

class CustomPolicyResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    version: str
    creator_id: str
    created_at: datetime
```

### OPA Policy Data Structure

**Role Mappings Data (pushed to OPA)**

```json
{
  "role_mappings": {
    "app-a": {
      "DEV": {
        "infodir-application-a-user": "user",
        "infodir-application-a-admin": "admin"
      },
      "PROD": {
        "infodir-application-a-admin": "admin"
      }
    },
    "app-b": {
      "DEV": {
        "infodir-application-b-user": "user"
      }
    }
  }
}
```

### OPA Policy Structure

**Base Permission Policy (`policies/permissions.rego`)**

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

## Error Handling

### Error Response Model

```python
class ErrorResponse(BaseModel):
    error: str
    detail: Optional[str]
    timestamp: datetime
    path: str
```

### Exception Hierarchy

```python
class OPAPermissionAPIException(Exception):
    """Base exception"""

class OPAConnectionError(OPAPermissionAPIException):
    """OPA server unreachable"""

class DatabaseError(OPAPermissionAPIException):
    """Database operation failed"""

class S3Error(OPAPermissionAPIException):
    """S3 operation failed"""

class ValidationError(OPAPermissionAPIException):
    """Input validation failed"""

class AuthenticationError(OPAPermissionAPIException):
    """Authentication failed"""

class AuthorizationError(OPAPermissionAPIException):
    """Authorization failed"""
```

### Global Exception Handler

```python
@app.exception_handler(OPAConnectionError)
async def opa_connection_error_handler(request, exc):
    return JSONResponse(
        status_code=503,
        content=ErrorResponse(
            error="Service Unavailable",
            detail="OPA server is unreachable",
            timestamp=datetime.now(),
            path=request.url.path
        ).dict()
    )
```

## Testing Strategy

### Unit Tests

**Test Coverage Areas:**

- Service layer logic (OPA service, application service, role mapping service)
- Repository operations (CRUD operations)
- Token decoding and authentication
- Input validation and schema validation
- Error handling and exception scenarios

**Testing Tools:**

- pytest for test framework
- pytest-asyncio for async test support
- pytest-mock for mocking
- httpx for API client testing

**Example Test Structure:**

```python
# tests/services/test_opa_service.py
@pytest.mark.asyncio
async def test_evaluate_permissions_success(mock_opa_client):
    # Arrange
    service = OPAService(opa_client=mock_opa_client)
    user_info = UserInfo(...)
    applications = [...]
    
    # Act
    result = await service.evaluate_permissions(user_info, applications, [])
    
    # Assert
    assert result["app-a"] == "admin"
```

### Integration Tests

**Test Scenarios:**

- End-to-end permission evaluation flow
- Role mapping creation and OPA synchronization
- Custom policy upload and evaluation
- Database transaction handling
- S3 file operations

**Test Environment:**

- Docker Compose for OPA, PostgreSQL, LocalStack (S3)
- Test database with migrations
- Isolated test data

### API Tests

**Test Coverage:**

- All endpoint responses (success and error cases)
- Authentication and authorization
- Request validation
- Response format validation

**Example:**

```python
# tests/api/test_permissions.py
async def test_get_permissions_endpoint(client, auth_token):
    response = await client.post(
        "/permission",
        json={"token": auth_token}
    )
    assert response.status_code == 200
    assert "permissions" in response.json()
```

### OPA Policy Tests

**Rego Policy Testing:**

- Use OPA's built-in testing framework
- Test policy logic with various input scenarios
- Validate permission evaluation correctness

**Example:**

```rego
# policies/permissions_test.rego
test_admin_access if {
    permissions["app-a"] == "admin" with input as {
        "user": {"ad_groups": ["infodir-application-a-admin"]},
        "applications": ["app-a"]
    } with data.role_mappings as {
        "app-a": {"DEV": {"infodir-application-a-admin": "admin"}}
    }
}
```

## Deployment Considerations

### Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/opa_permissions

# OPA
OPA_URL=http://localhost:8181
OPA_TIMEOUT=5

# S3
S3_BUCKET=opa-policies
S3_REGION=us-east-1
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...

# API
API_TITLE=OPA Permission API
LOG_LEVEL=INFO
```

### Docker Compose Setup

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql://postgres:postgres@db:5432/opa_permissions
      - OPA_URL=http://opa:8181
    depends_on:
      - db
      - opa
  
  opa:
    image: openpolicyagent/opa:latest
    ports:
      - "8181:8181"
    command:
      - "run"
      - "--server"
      - "--log-level=debug"
  
  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=opa_permissions
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=postgres
    volumes:
      - postgres_data:/var/lib/postgresql/data

volumes:
  postgres_data:
```

### Initialization Process

1. Database migrations (Alembic)
2. Load base OPA policy from S3 or local file
3. Sync existing role mappings to OPA
4. Health check for OPA connectivity
5. Start accepting requests

### Monitoring and Observability

**Metrics to Track:**

- Request latency (p50, p95, p99)
- OPA evaluation time
- Database query performance
- Error rates by endpoint
- OPA server health status

**Logging Strategy:**

- Structured JSON logging
- Request ID tracking across services
- Audit logs for administrative operations
- Performance logs for slow queries

**Health Endpoints:**

- `/health`: Overall system health
- `/health/opa`: OPA server connectivity
- `/health/db`: Database connectivity
- `/health/s3`: S3 accessibility

## Security Considerations

1. **Token Security**: Tokens should be validated and not logged
2. **Admin Authorization**: Administrative endpoints require elevated privileges
3. **Input Validation**: All inputs validated against schemas
4. **SQL Injection Prevention**: Use parameterized queries via SQLAlchemy
5. **S3 Access Control**: Use IAM roles with least privilege
6. **OPA Policy Isolation**: Custom policies isolated by namespace
7. **Audit Logging**: All administrative actions logged with user identity
8. **Rate Limiting**: Consider implementing rate limiting for public endpoints

## Performance Optimization

1. **Caching**: Cache role mappings in memory with TTL
2. **Batch Operations**: Batch OPA data updates when possible
3. **Connection Pooling**: Database connection pooling via SQLAlchemy
4. **Async Operations**: Use async/await throughout for I/O operations
5. **OPA Bundle API**: Consider using OPA bundles for large policy sets
6. **Database Indexing**: Index on application_id, ad_group, environment
