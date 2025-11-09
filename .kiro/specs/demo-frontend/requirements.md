# Requirements Document

## Introduction

This feature adds a demo frontend web interface to the OPA Permission API that allows users to interact with all available API endpoints through a browser-based UI. The frontend will be served at the root path ('/') and provide an intuitive interface for testing and demonstrating the API's capabilities including application management, role mapping management, permission evaluation, custom policy management, and health checks.

## Requirements

### Requirement 1: Frontend Page Serving

**User Story:** As a developer or API user, I want to access a demo frontend page at the root URL, so that I can interact with the API through a web interface without using command-line tools.

#### Acceptance Criteria

1. WHEN a user navigates to the root path ('/') THEN the system SHALL serve an HTML page with embedded CSS and JavaScript
2. WHEN the page loads THEN the system SHALL display a clean, organized interface with sections for each API endpoint category
3. WHEN the page is served THEN the system SHALL include proper HTML structure with responsive design
4. WHEN the page loads THEN the system SHALL not require any external dependencies or CDN resources for basic functionality

### Requirement 2: Authentication Token Management

**User Story:** As a user of the demo frontend, I want to input and manage my authentication token, so that I can make authenticated API requests.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL display a token input field at the top of the page
2. WHEN a user enters a token THEN the system SHALL store it in browser session storage
3. WHEN a user makes an API request THEN the system SHALL include the token in the Authorization header as a Bearer token
4. WHEN the page loads THEN the system SHALL retrieve any previously stored token from session storage
5. WHEN a user clears the token field THEN the system SHALL remove the token from session storage

### Requirement 3: Application Management Interface

**User Story:** As an admin user, I want to manage applications through the frontend, so that I can create, view, update, and delete applications without using API tools.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL display a section for application management
2. WHEN a user clicks "List Applications" THEN the system SHALL call GET /applications and display the results
3. WHEN a user enters an application ID and clicks "Get Application" THEN the system SHALL call GET /applications/{app_id} and display the result
4. WHEN a user fills the create form and clicks "Create Application" THEN the system SHALL call POST /applications with the form data
5. WHEN a user fills the update form and clicks "Update Application" THEN the system SHALL call PUT /applications/{app_id} with the form data
6. WHEN a user enters an application ID and clicks "Delete Application" THEN the system SHALL call DELETE /applications/{app_id}
7. WHEN any application operation completes THEN the system SHALL display the response or error message

### Requirement 4: Role Mapping Management Interface

**User Story:** As an admin user, I want to manage role mappings through the frontend, so that I can create, view, update, and delete role mappings without using API tools.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL display a section for role mapping management
2. WHEN a user clicks "List Role Mappings" THEN the system SHALL call GET /role-mappings and display the results
3. WHEN a user enters an application ID filter and clicks "List Role Mappings" THEN the system SHALL call GET /role-mappings?app_id={app_id} and display the results
4. WHEN a user fills the create form and clicks "Create Role Mapping" THEN the system SHALL call POST /role-mappings with the form data
5. WHEN a user fills the update form and clicks "Update Role Mapping" THEN the system SHALL call PUT /role-mappings/{mapping_id} with the form data
6. WHEN a user enters a mapping ID and clicks "Delete Role Mapping" THEN the system SHALL call DELETE /role-mappings/{mapping_id}
7. WHEN any role mapping operation completes THEN the system SHALL display the response or error message

### Requirement 5: Permission Evaluation Interface

**User Story:** As an authenticated user, I want to evaluate my permissions through the frontend, so that I can see what access levels I have for applications.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL display a section for permission evaluation
2. WHEN a user clicks "Evaluate All Permissions" THEN the system SHALL call POST /permission and display the permissions for all applications
3. WHEN a user enters an application ID and clicks "Evaluate App Permission" THEN the system SHALL call GET /permission/{app_id} and display the permission level
4. WHEN permission evaluation completes THEN the system SHALL display the results in a readable format
5. WHEN permission evaluation fails THEN the system SHALL display the error message

### Requirement 6: Custom Policy Management Interface

**User Story:** As an admin user, I want to manage custom policies through the frontend, so that I can upload, view, and evaluate custom Rego policies.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL display a section for custom policy management
2. WHEN a user clicks "List Custom Policies" THEN the system SHALL call GET /custom-policies and display the results
3. WHEN a user enters a policy ID and clicks "Get Custom Policy" THEN the system SHALL call GET /custom-policies/{policy_id} and display the result
4. WHEN a user fills the upload form with policy ID, name, description, and Rego content and clicks "Upload Policy" THEN the system SHALL call POST /custom-policies with the form data
5. WHEN a user enters a policy ID and input data and clicks "Evaluate Policy" THEN the system SHALL call POST /custom-policies/{policy_id}/evaluate with the input data
6. WHEN any custom policy operation completes THEN the system SHALL display the response or error message

### Requirement 7: Health Check Interface

**User Story:** As a system administrator, I want to check system health through the frontend, so that I can monitor the status of all components.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL display a section for health checks
2. WHEN a user clicks "Overall Health" THEN the system SHALL call GET /health and display the status of all components
3. WHEN a user clicks "OPA Health" THEN the system SHALL call GET /health/opa and display the OPA server status
4. WHEN a user clicks "Database Health" THEN the system SHALL call GET /health/db and display the database status
5. WHEN a user clicks "S3 Health" THEN the system SHALL call GET /health/s3 and display the S3 bucket status
6. WHEN health check completes THEN the system SHALL display the status with color coding (green for healthy, red for unhealthy)

### Requirement 8: Response Display and Error Handling

**User Story:** As a user of the demo frontend, I want to see clear responses and error messages, so that I can understand the results of my API requests.

#### Acceptance Criteria

1. WHEN an API request succeeds THEN the system SHALL display the response data in a formatted, readable manner
2. WHEN an API request fails THEN the system SHALL display the error message and status code
3. WHEN displaying JSON responses THEN the system SHALL format them with proper indentation
4. WHEN an API request is in progress THEN the system SHALL display a loading indicator
5. WHEN multiple requests are made THEN the system SHALL display each response in the appropriate section

### Requirement 9: User Experience and Design

**User Story:** As a user of the demo frontend, I want an intuitive and visually appealing interface, so that I can easily navigate and use all features.

#### Acceptance Criteria

1. WHEN the page loads THEN the system SHALL display a clear title and description
2. WHEN viewing the interface THEN the system SHALL organize sections with clear headings and visual separation
3. WHEN interacting with forms THEN the system SHALL provide clear labels and placeholders for all input fields
4. WHEN viewing the page on different screen sizes THEN the system SHALL maintain usability and readability
5. WHEN buttons are clicked THEN the system SHALL provide visual feedback
