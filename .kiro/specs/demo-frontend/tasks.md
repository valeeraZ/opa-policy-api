# Implementation Plan

- [x] 1. Create HTML template with basic structure and styling
  - Create a new file `app/templates/demo.html` with complete HTML structure
  - Include embedded CSS for styling all UI components
  - Add responsive design styles for different screen sizes
  - Include color-coded response display styles (success/error)
  - _Requirements: 1.1, 1.2, 1.3, 1.4, 9.1, 9.2, 9.3, 9.4, 9.5_

- [x] 2. Implement token management functionality
  - Add token input field in the HTML header section
  - Write JavaScript functions for token storage (getToken, setToken, clearToken)
  - Implement session storage integration for token persistence
  - Add event listeners for token input changes
  - Add token loading on page initialization
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5_

- [x] 3. Implement core API client functions
  - Write apiRequest() function with fetch API integration
  - Add Authorization header handling with Bearer token
  - Implement error handling for network failures
  - Write displayResponse() function for showing API responses
  - Add loading state management functions
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_

- [x] 4. Build applications management interface
  - Add HTML forms and buttons for application operations
  - Implement listApplications() function calling GET /applications
  - Implement getApplication() function calling GET /applications/{app_id}
  - Implement createApplication() function calling POST /applications
  - Implement updateApplication() function calling PUT /applications/{app_id}
  - Implement deleteApplication() function calling DELETE /applications/{app_id}
  - Add event listeners for all application buttons
  - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7_

- [x] 5. Build role mappings management interface
  - Add HTML forms and buttons for role mapping operations
  - Implement listRoleMappings() function calling GET /role-mappings
  - Add application ID filter support for role mappings list
  - Implement createRoleMapping() function calling POST /role-mappings
  - Implement updateRoleMapping() function calling PUT /role-mappings/{mapping_id}
  - Implement deleteRoleMapping() function calling DELETE /role-mappings/{mapping_id}
  - Add event listeners for all role mapping buttons
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 4.7_

- [x] 6. Build permissions evaluation interface
  - Add HTML forms and buttons for permission operations
  - Implement evaluateAllPermissions() function calling POST /permission
  - Implement evaluateAppPermission() function calling GET /permission/{app_id}
  - Add formatted display for permission results
  - Add event listeners for permission evaluation buttons
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 7. Build custom policies management interface
  - Add HTML forms and buttons for custom policy operations
  - Implement listCustomPolicies() function calling GET /custom-policies
  - Implement getCustomPolicy() function calling GET /custom-policies/{policy_id}
  - Implement uploadCustomPolicy() function calling POST /custom-policies
  - Add textarea for Rego content input
  - Implement evaluateCustomPolicy() function calling POST /custom-policies/{policy_id}/evaluate
  - Add JSON input field for policy evaluation data
  - Add event listeners for all custom policy buttons
  - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 8. Build health checks interface
  - Add HTML buttons for health check operations
  - Implement checkHealth() function calling GET /health
  - Implement checkOpaHealth() function calling GET /health/opa
  - Implement checkDbHealth() function calling GET /health/db
  - Implement checkS3Health() function calling GET /health/s3
  - Add color-coded status display for health results
  - Add event listeners for all health check buttons
  - _Requirements: 7.1, 7.2, 7.3, 7.4, 7.5, 7.6_

- [x] 9. Update FastAPI root endpoint to serve HTML
  - Modify the root endpoint in `app/main.py` to return HTMLResponse
  - Read the HTML template file content
  - Import HTMLResponse from fastapi.responses
  - Update the root endpoint to serve the demo HTML content
  - _Requirements: 1.1, 1.2_

- [x] 10. Add comprehensive error handling
  - Implement HTTP error response parsing in API client
  - Add user-friendly error messages for common errors (401, 403, 404, 409, 500, 503)
  - Add network error handling with try-catch blocks
  - Implement validation error display from API responses
  - Add error state styling in response display
  - _Requirements: 8.1, 8.2, 8.3, 8.4, 8.5_
