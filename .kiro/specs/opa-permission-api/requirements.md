# Requirements Document

## Introduction

This document outlines the requirements for a FastAPI backend server that integrates with Open Policy Agent (OPA) to manage application permissions based on user attributes (AD groups, employee ID, etc.). The system will support dynamic permission evaluation, role mapping management, and extensibility for custom policy evaluation scenarios.

The system manages permissions for multiple applications across different environments (DEV, PROD, etc.), where access is controlled through AD group memberships. Users can have different roles (user, admin) based on their AD group assignments, and the system must support dynamic updates to role mappings without requiring OPA image rebuilds.

The system leverages existing token decoding functionality and uses PostgreSQL for structured data storage and S3 for policy file storage.

## Requirements

### Requirement 1: Token-Based Permission Evaluation

**User Story:** As an API client, I want to send a user token to the /permission endpoint, so that I can retrieve all application permissions for that user.

#### Acceptance Criteria

1. WHEN a client sends a POST request to /permission with a valid token THEN the system SHALL use existing token decoding functionality to extract user information including ad_groups and employee_id
2. WHEN user information is extracted THEN the system SHALL send this information along with application data to the OPA HTTP server for policy evaluation
3. WHEN OPA evaluation completes THEN the system SHALL return a list of all applications with their corresponding permission levels (e.g., user, admin, none) for the authenticated user
4. IF the token is invalid or expired THEN the system SHALL return a 401 Unauthorized error
5. IF the OPA server is unreachable THEN the system SHALL return a 503 Service Unavailable error

### Requirement 2: Application-Specific Permission Evaluation

**User Story:** As an API client, I want to query specific application permissions via /permission/{app-id}, so that I can check access for a single application without retrieving all permissions.

#### Acceptance Criteria

1. WHEN a client sends a GET request to /permission/{app-id} with a valid token THEN the system SHALL evaluate permissions only for the specified application
2. WHEN the application exists THEN the system SHALL return the user's permission level for that specific application
3. IF the application does not exist THEN the system SHALL return a 404 Not Found error
4. WHEN evaluating permissions THEN the system SHALL use the same OPA policy evaluation as the general /permission endpoint

### Requirement 3: AD Group to Role Mapping Management

**User Story:** As a system administrator, I want to create and modify AD group to role mappings for applications, so that I can control which AD groups grant which permission levels.

#### Acceptance Criteria

1. WHEN an administrator creates a new role mapping THEN the system SHALL store the mapping with application_id, environment, ad_group, and role fields
2. WHEN an administrator updates an existing role mapping THEN the system SHALL update the mapping in the database and synchronize with OPA
3. WHEN an administrator deletes a role mapping THEN the system SHALL remove it from the database and update OPA policies accordingly
4. WHEN role mappings are modified THEN the system SHALL make changes available to OPA without requiring an OPA image rebuild
5. IF a role mapping conflicts with existing mappings THEN the system SHALL return a 409 Conflict error with details

### Requirement 4: Application Management

**User Story:** As a system administrator, I want to create and manage applications in the system, so that I can add new applications that require permission management.

#### Acceptance Criteria

1. WHEN an administrator creates a new application THEN the system SHALL store the application with a unique application_id in the PostgreSQL database
2. WHEN a new application is created THEN the system SHALL initialize default role mapping structures for that application
3. WHEN an application is created THEN the system SHALL support immediate role mapping creation without requiring system restarts
4. WHEN an administrator retrieves application details THEN the system SHALL return application metadata and associated role mappings
5. IF an application_id already exists THEN the system SHALL return a 409 Conflict error

### Requirement 5: Dynamic OPA Policy and Data Management

**User Story:** As a system administrator, I want the system to dynamically update OPA policies and data when applications or role mappings change, so that permission changes take effect immediately without rebuilding OPA images.

#### Acceptance Criteria

1. WHEN role mappings are created or updated THEN the system SHALL push updated policy data to OPA via the OPA Data API
2. WHEN new applications are added THEN the system SHALL generate or update OPA policy code if necessary and store it in S3
3. WHEN OPA policies are updated THEN the system SHALL load the updated policies into the OPA server dynamically
4. WHEN policy data is stored THEN the system SHALL maintain versioning for audit and rollback purposes
5. IF OPA policy update fails THEN the system SHALL log the error and return a 500 Internal Server Error with details

### Requirement 6: Custom Policy Evaluation Extension

**User Story:** As a developer, I want to upload custom Rego policies and evaluate them with custom input data, so that I can use the system for permission scenarios beyond application access (e.g., service-specific policies).

#### Acceptance Criteria

1. WHEN a user uploads a custom Rego policy THEN the system SHALL validate the Rego syntax before storing
2. WHEN a custom policy is uploaded THEN the system SHALL store it in S3 with a unique policy identifier
3. WHEN a user requests custom policy evaluation via a dedicated endpoint THEN the system SHALL load the specified policy and evaluate it with provided input data
4. WHEN custom policy evaluation completes THEN the system SHALL return the OPA decision result
5. IF the Rego policy has syntax errors THEN the system SHALL return a 400 Bad Request error with validation details
6. WHEN custom policies are stored THEN the system SHALL associate them with metadata including creator, creation date, and description

### Requirement 7: Data Persistence and Storage

**User Story:** As a system operator, I want application data and role mappings stored reliably, so that the system maintains state across restarts and supports disaster recovery.

#### Acceptance Criteria

1. WHEN the system starts THEN it SHALL connect to a PostgreSQL database for storing application metadata and role mappings
2. WHEN role mapping data exceeds a configurable size threshold THEN the system SHALL store it in S3 with database references
3. WHEN OPA policy files are generated THEN the system SHALL store them in S3 with versioning enabled
4. WHEN the system initializes THEN it SHALL load current policy data from the database and S3 into OPA
5. IF database connection fails THEN the system SHALL retry with exponential backoff and log connection errors

### Requirement 8: API Authentication and Authorization

**User Story:** As a security administrator, I want API endpoints to be properly authenticated and authorized, so that only authorized users can manage applications and role mappings.

#### Acceptance Criteria

1. WHEN a client accesses management endpoints (create/update/delete) THEN the system SHALL require valid authentication tokens
2. WHEN a client attempts administrative operations THEN the system SHALL verify the user has administrative privileges
3. WHEN authentication fails THEN the system SHALL return a 401 Unauthorized error
4. WHEN authorization fails THEN the system SHALL return a 403 Forbidden error
5. WHEN audit events occur (create, update, delete operations) THEN the system SHALL log the operation with user identity and timestamp

### Requirement 9: Error Handling and Logging

**User Story:** As a system operator, I want comprehensive error handling and logging, so that I can troubleshoot issues and monitor system health.

#### Acceptance Criteria

1. WHEN any error occurs THEN the system SHALL log the error with appropriate severity level (ERROR, WARN, INFO)
2. WHEN external service calls fail (OPA, database, S3) THEN the system SHALL log detailed error information including service name and error message
3. WHEN API requests are received THEN the system SHALL log request details including endpoint, method, and user identity
4. WHEN OPA policy evaluation occurs THEN the system SHALL log evaluation time and decision results for audit purposes
5. IF logging fails THEN the system SHALL continue operation and attempt to log the logging failure

### Requirement 10: OPA Server Integration

**User Story:** As a system architect, I want the backend API to integrate seamlessly with an OPA HTTP server, so that policy evaluation is centralized and consistent.

#### Acceptance Criteria

1. WHEN the system initializes THEN it SHALL establish connection to the configured OPA HTTP server
2. WHEN evaluating permissions THEN the system SHALL send policy queries to OPA using the OPA REST API
3. WHEN updating policy data THEN the system SHALL use the OPA Data API to push updates
4. WHEN loading custom policies THEN the system SHALL use the OPA Policy API to upload policy bundles
5. IF OPA server health check fails THEN the system SHALL expose this status via a health endpoint and return 503 for permission requests
