# Implementation Plan

- [x] 1. Set up project structure and configuration
  - Create FastAPI project directory structure with app/, tests/, and policies/ folders
  - Create requirements.txt with FastAPI, SQLAlchemy, Alembic, boto3, httpx, pydantic-settings
  - Create .env.example file with all required environment variables
  - Implement configuration management in app/config.py using pydantic-settings
  - _Requirements: 7.1, 10.1_

- [x] 2. Implement database models and migrations
  - [x] 2.1 Create SQLAlchemy database models
    - Implement Application model in app/models/application.py
    - Implement RoleMapping model with foreign key and unique constraint in app/models/role_mapping.py
    - Implement CustomPolicy model in app/models/custom_policy.py
    - Create database base and session management in app/database.py
    - _Requirements: 4.1, 3.1, 6.2, 7.1_
  - [x] 2.2 Set up Alembic migrations
    - Initialize Alembic configuration
    - Create initial migration for all database tables
    - Add database indexes for application_id, ad_group, and environment fields
    - _Requirements: 7.1_

- [x] 3. Implement Pydantic schemas
  - Create UserInfo schema in app/schemas/user.py
  - Create permission request/response schemas in app/schemas/permission.py
  - Create application schemas (Create, Update, Response) in app/schemas/application.py
  - Create role mapping schemas in app/schemas/role_mapping.py
  - Create custom policy schemas in app/schemas/custom_policy.py
  - Create error response schema in app/schemas/error.py
  - _Requirements: 1.1, 2.1, 3.1, 4.1, 6.1_

- [x] 4. Implement custom exceptions
  - Create exception hierarchy in app/exceptions.py with OPAConnectionError, DatabaseError, S3Error, ValidationError, AuthenticationError, AuthorizationError
  - _Requirements: 1.4, 1.5, 9.1, 9.2_

- [x] 5. Implement authentication and token decoding
  - Create TokenDecoder class in app/auth/token_decoder.py that integrates with existing token decoding functionality
  - Implement get_current_user dependency in app/dependencies.py
  - Implement require_admin dependency for authorization checks
  - _Requirements: 1.1, 8.1, 8.2, 8.3, 8.4_

- [x] 6. Implement repository layer
  - [x] 6.1 Create ApplicationRepository
    - Implement CRUD operations in app/repositories/application_repository.py
    - Add error handling for database operations
    - _Requirements: 4.1, 4.4, 4.5_
  - [x] 6.2 Create RoleMappingRepository
    - Implement CRUD operations in app/repositories/role_mapping_repository.py
    - Implement get_all_as_opa_data method to format data for OPA
    - Add unique constraint validation
    - _Requirements: 3.1, 3.2, 3.3, 3.5_
  - [x] 6.3 Create CustomPolicyRepository
    - Implement CRUD operations in app/repositories/custom_policy_repository.py
    - _Requirements: 6.2, 6.6_

- [x] 7. Implement S3 service
  - Create S3Service class in app/services/s3_service.py using boto3
  - Implement upload_policy_file method with versioning
  - Implement download_policy_file method
  - Implement list_policy_versions method
  - Add error handling for S3 operations
  - _Requirements: 5.2, 5.4, 6.2, 7.3_

- [x] 8. Create base OPA policy
  - Create permissions.rego file in policies/ directory
  - Implement user_role rule that matches AD groups to roles
  - Implement permissions rule that evaluates all applications
  - Add default "none" role for applications without matches
  - _Requirements: 1.2, 1.3, 2.1, 2.4_

- [x] 9. Implement OPA service
  - [x] 9.1 Create OPA HTTP client
    - Create OPAService class in app/services/opa_service.py using httpx
    - Implement health_check method
    - Add connection retry logic with exponential backoff
    - _Requirements: 10.1, 10.5_
  - [x] 9.2 Implement policy upload on initialization
    - Implement method to upload base permissions.rego policy to OPA on startup
    - Add error handling for policy upload failures
    - _Requirements: 5.3, 10.4_
  - [x] 9.3 Implement policy evaluation methods
    - Implement evaluate_permissions method that calls OPA REST API
    - Format user info and role mappings as OPA input
    - Parse OPA response and return permission dictionary
    - _Requirements: 1.2, 1.3, 2.1, 2.4, 10.2_
  - [x] 9.4 Implement policy data management
    - Implement push_policy_data method using OPA Data API
    - Implement upload_policy method using OPA Policy API
    - Add error handling for OPA communication failures
    - _Requirements: 3.4, 5.1, 5.3, 5.5, 10.3, 10.4_
  - [x] 9.5 Implement custom policy evaluation
    - Implement evaluate_custom_policy method
    - _Requirements: 6.3, 6.4_

- [x] 10. Implement application service
  - Create ApplicationService class in app/services/application_service.py
  - Implement create_application method with duplicate check
  - Implement get_application, list_applications methods
  - Implement update_application and delete_application methods
  - Add logging for all operations
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 8.5, 9.3_

- [x] 11. Implement role mapping service
  - Create RoleMappingService class in app/services/role_mapping_service.py
  - Implement create_role_mapping with conflict detection
  - Implement get_role_mappings with optional app_id filter
  - Implement update_role_mapping and delete_role_mapping
  - Implement sync_to_opa method that pushes all mappings to OPA after changes
  - Add logging for all operations
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 5.1, 8.5, 9.3_

- [x] 12. Implement custom policy service
  - Create CustomPolicyService class in app/services/custom_policy_service.py
  - Implement validate_rego method using OPA compile API
  - Implement upload_policy method that validates, stores in S3, saves metadata to DB, and uploads to OPA
  - Implement get_policy and list_policies methods
  - Implement evaluate_policy method
  - Add logging for all operations
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 8.5, 9.3_

- [x] 13. Implement permission router
  - [x] 13.1 Create permission evaluation endpoints
    - Create router in app/routers/permissions.py
    - Implement POST /permission endpoint that decodes token, fetches apps and mappings, calls OPA, returns all permissions
    - Implement GET /permission/{app_id} endpoint for single app permission check
    - Add authentication dependency
    - Add error handling for invalid tokens, OPA failures, missing applications
    - _Requirements: 1.1, 1.2, 1.3, 1.4, 1.5, 2.1, 2.2, 2.3, 2.4, 9.2, 9.3, 9.4_

- [x] 14. Implement application router
  - Create router in app/routers/applications.py
  - Implement POST /applications endpoint with admin authorization
  - Implement GET /applications and GET /applications/{app_id} endpoints
  - Implement PUT /applications/{app_id} and DELETE /applications/{app_id} endpoints with admin authorization
  - Add request/response validation
  - Add audit logging for create/update/delete operations
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3_

- [x] 15. Implement role mapping router
  - Create router in app/routers/role_mappings.py
  - Implement POST /role-mappings endpoint with admin authorization and OPA sync
  - Implement GET /role-mappings endpoint with optional app_id query parameter
  - Implement PUT /role-mappings/{mapping_id} endpoint with admin authorization and OPA sync
  - Implement DELETE /role-mappings/{mapping_id} endpoint with admin authorization and OPA sync
  - Add audit logging for all operations
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 8.1, 8.2, 8.3, 8.4, 8.5, 9.1, 9.2, 9.3_

- [x] 16. Implement custom policy router
  - Create router in app/routers/custom_policies.py
  - Implement POST /custom-policies endpoint for uploading policies with validation
  - Implement GET /custom-policies and GET /custom-policies/{policy_id} endpoints
  - Implement POST /custom-policies/{policy_id}/evaluate endpoint for policy evaluation
  - Add authentication and authorization
  - Add audit logging
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 8.1, 8.5, 9.1, 9.3_

- [x] 17. Implement health check router
  - Create router in app/routers/health.py
  - Implement GET /health endpoint that checks overall system health
  - Implement GET /health/opa endpoint for OPA connectivity check
  - Implement GET /health/db endpoint for database connectivity check
  - Implement GET /health/s3 endpoint for S3 accessibility check
  - Return 503 status when services are unhealthy
  - _Requirements: 1.5, 10.5_

- [x] 18. Implement main FastAPI application
  - Create FastAPI app in app/main.py
  - Configure CORS middleware
  - Configure logging middleware with request ID tracking
  - Register all routers (permissions, applications, role_mappings, custom_policies, health)
  - Implement global exception handlers for custom exceptions
  - Implement lifespan event for database connection and OPA initialization
  - Implement startup event to upload base OPA policy and sync existing role mappings to OPA
  - _Requirements: 5.4, 7.4, 7.5, 9.1, 9.2, 9.3, 10.1_

- [x] 19. Create Docker Compose setup
  - Create docker-compose.yml with services for api, opa, postgres
  - Create Dockerfile for FastAPI application
  - Configure environment variables
  - Add volume mounts for postgres data persistence and OPA policy loading
  - _Requirements: 7.1, 10.1_

- [x] 20. Create deployment documentation
  - Create README.md with project overview and setup instructions
  - Document all API endpoints with request/response examples
  - Document environment variables and configuration
  - Add instructions for running with Docker Compose
  - Add instructions for database migrations
  - Document OPA policy structure and how policies are loaded
  - _Requirements: All_
