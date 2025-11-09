# Design Document

## Overview

The demo frontend will be a single-page application (SPA) served at the root path ('/') of the FastAPI application. It will be implemented as a self-contained HTML file with embedded CSS and JavaScript, requiring no external dependencies or build process. The frontend will provide a comprehensive interface for interacting with all API endpoints, including authentication token management, CRUD operations for applications and role mappings, permission evaluation, custom policy management, and health checks.

## Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Browser Client                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │           HTML/CSS/JavaScript Frontend            │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │  Token Management (Session Storage)         │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │  API Client (Fetch API)                     │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  │  ┌─────────────────────────────────────────────┐ │  │
│  │  │  UI Components (Forms, Buttons, Display)    │ │  │
│  │  └─────────────────────────────────────────────┘ │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
                          │
                          │ HTTP/HTTPS
                          ▼
┌─────────────────────────────────────────────────────────┐
│                  FastAPI Backend                         │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Static File Endpoint (GET /)                     │  │
│  └───────────────────────────────────────────────────┘  │
│  ┌───────────────────────────────────────────────────┐  │
│  │  API Routers (Applications, Permissions, etc.)   │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Component Structure

1. **Backend Component**: Modified FastAPI root endpoint to serve HTML content
2. **Frontend Component**: Single HTML file with embedded CSS and JavaScript
3. **API Client**: JavaScript module for making HTTP requests to backend APIs
4. **UI Sections**: Organized interface sections for each API category

## Components and Interfaces

### 1. Backend: Static HTML Serving

**File**: `app/main.py`

**Modification**: Update the root endpoint to serve HTML content instead of JSON

```python
@app.get("/", tags=["root"])
async def root():
    """Serve demo frontend HTML page."""
    return HTMLResponse(content=DEMO_HTML_CONTENT)
```

**HTML Content Storage**: The HTML content will be stored as a constant string in a separate module or directly in the main.py file.

### 2. Frontend: HTML Structure

**Sections**:
- Header with title and token input
- Applications Management
- Role Mappings Management
- Permissions Evaluation
- Custom Policies Management
- Health Checks
- Response Display Area

**HTML Structure**:
```html
<!DOCTYPE html>
<html>
<head>
    <title>OPA Permission API - Demo</title>
    <style>/* Embedded CSS */</style>
</head>
<body>
    <div class="container">
        <header>
            <h1>OPA Permission API Demo</h1>
            <div class="token-section">
                <input type="text" id="token" placeholder="Enter JWT Token">
            </div>
        </header>
        
        <section class="api-section" id="applications">
            <!-- Application management forms and buttons -->
        </section>
        
        <section class="api-section" id="role-mappings">
            <!-- Role mapping management forms and buttons -->
        </section>
        
        <section class="api-section" id="permissions">
            <!-- Permission evaluation forms and buttons -->
        </section>
        
        <section class="api-section" id="custom-policies">
            <!-- Custom policy management forms and buttons -->
        </section>
        
        <section class="api-section" id="health">
            <!-- Health check buttons -->
        </section>
        
        <section class="response-section">
            <h2>Response</h2>
            <pre id="response-display"></pre>
        </section>
    </div>
    
    <script>/* Embedded JavaScript */</script>
</body>
</html>
```

### 3. Frontend: JavaScript API Client

**Core Functions**:

```javascript
// Token management
function getToken() { return sessionStorage.getItem('authToken'); }
function setToken(token) { sessionStorage.setItem('authToken', token); }
function clearToken() { sessionStorage.removeItem('authToken'); }

// API request wrapper
async function apiRequest(method, endpoint, body = null) {
    const token = getToken();
    const headers = {
        'Content-Type': 'application/json'
    };
    
    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }
    
    const options = {
        method,
        headers
    };
    
    if (body) {
        options.body = JSON.stringify(body);
    }
    
    const response = await fetch(endpoint, options);
    return response;
}

// Display response
function displayResponse(data, isError = false) {
    const display = document.getElementById('response-display');
    display.textContent = JSON.stringify(data, null, 2);
    display.className = isError ? 'error' : 'success';
}
```

**API-Specific Functions**:
- `listApplications()`, `getApplication(appId)`, `createApplication(data)`, etc.
- `listRoleMappings(appId)`, `createRoleMapping(data)`, etc.
- `evaluateAllPermissions()`, `evaluateAppPermission(appId)`
- `listCustomPolicies()`, `uploadCustomPolicy(data)`, `evaluateCustomPolicy(policyId, input)`
- `checkHealth()`, `checkOpaHealth()`, `checkDbHealth()`, `checkS3Health()`

### 4. Frontend: CSS Styling

**Design Principles**:
- Clean, modern interface with good contrast
- Responsive layout that works on different screen sizes
- Clear visual hierarchy with sections and headings
- Form inputs with proper spacing and labels
- Color-coded responses (green for success, red for errors)
- Loading states for async operations

**Key Styles**:
```css
body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    background: white;
    padding: 20px;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.api-section {
    margin: 20px 0;
    padding: 20px;
    border: 1px solid #ddd;
    border-radius: 4px;
}

button {
    background-color: #007bff;
    color: white;
    border: none;
    padding: 10px 20px;
    border-radius: 4px;
    cursor: pointer;
}

button:hover {
    background-color: #0056b3;
}

.response-section pre {
    background-color: #f8f9fa;
    padding: 15px;
    border-radius: 4px;
    overflow-x: auto;
}

.response-section pre.success {
    border-left: 4px solid #28a745;
}

.response-section pre.error {
    border-left: 4px solid #dc3545;
}
```

## Data Models

### Frontend Data Structures

**Application**:
```javascript
{
    id: string,
    name: string,
    description: string
}
```

**Role Mapping**:
```javascript
{
    id: number,
    application_id: string,
    environment: string,
    ad_group: string,
    role: string
}
```

**Custom Policy**:
```javascript
{
    id: string,
    name: string,
    description: string,
    rego_content: string,
    created_by: string,
    created_at: string
}
```

**Permission Response**:
```javascript
{
    permissions: {
        [app_id: string]: string  // role level
    }
}
```

**Health Status**:
```javascript
{
    status: string,
    components: {
        [component: string]: {
            status: string,
            message: string
        }
    }
}
```

## Error Handling

### Frontend Error Handling

1. **Network Errors**: Catch fetch errors and display user-friendly messages
2. **HTTP Errors**: Parse error responses from API and display status code and detail
3. **Validation Errors**: Display validation errors from API responses
4. **Authentication Errors**: Prompt user to enter valid token when 401 is received
5. **Authorization Errors**: Display clear message when 403 is received

**Error Display Pattern**:
```javascript
try {
    const response = await apiRequest('GET', '/applications');
    if (!response.ok) {
        const error = await response.json();
        displayResponse({
            status: response.status,
            error: error.error || 'Request failed',
            detail: error.detail || error.message
        }, true);
        return;
    }
    const data = await response.json();
    displayResponse(data);
} catch (error) {
    displayResponse({
        error: 'Network Error',
        detail: error.message
    }, true);
}
```

### Loading States

Display loading indicators during API requests:
```javascript
function showLoading() {
    document.getElementById('response-display').textContent = 'Loading...';
}

function hideLoading() {
    // Response will replace loading text
}
```

## Testing Strategy

### Manual Testing Checklist

1. **Token Management**:
   - Verify token is saved to session storage
   - Verify token is loaded on page refresh
   - Verify token is included in API requests
   - Verify clearing token removes it from storage

2. **Applications Management**:
   - Test listing all applications
   - Test getting a specific application
   - Test creating an application (with admin token)
   - Test updating an application (with admin token)
   - Test deleting an application (with admin token)
   - Test error handling for invalid inputs

3. **Role Mappings Management**:
   - Test listing all role mappings
   - Test filtering role mappings by application ID
   - Test creating a role mapping (with admin token)
   - Test updating a role mapping (with admin token)
   - Test deleting a role mapping (with admin token)
   - Test error handling for conflicts

4. **Permissions Evaluation**:
   - Test evaluating all permissions (with valid token)
   - Test evaluating specific app permission (with valid token)
   - Test error handling for missing token
   - Test error handling for invalid token

5. **Custom Policies Management**:
   - Test listing all custom policies
   - Test getting a specific custom policy
   - Test uploading a custom policy (with admin token and valid Rego)
   - Test evaluating a custom policy with input data
   - Test error handling for invalid Rego syntax

6. **Health Checks**:
   - Test overall health check
   - Test OPA health check
   - Test database health check
   - Test S3 health check
   - Verify color coding for healthy/unhealthy status

7. **UI/UX**:
   - Test responsive design on different screen sizes
   - Verify all buttons provide visual feedback
   - Verify all forms have clear labels
   - Verify response display is readable and formatted
   - Test navigation between sections

### Browser Compatibility

Test on:
- Chrome/Chromium (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)

## Implementation Notes

1. **No External Dependencies**: The frontend should be completely self-contained with no CDN dependencies or external resources
2. **Session Storage**: Use sessionStorage (not localStorage) for token to clear on browser close
3. **CORS**: The existing CORS middleware in FastAPI should allow the frontend to make requests
4. **Content Type**: Use `HTMLResponse` from `fastapi.responses` to serve HTML content
5. **Code Organization**: Consider storing the HTML content in a separate file (e.g., `app/static/demo.html`) and reading it, or embed it as a constant string
6. **Security**: This is a demo interface - in production, additional security measures would be needed
7. **API Base URL**: Use relative URLs for API requests (e.g., `/applications`) so the frontend works regardless of deployment URL

## Future Enhancements (Out of Scope)

- File upload for custom policies
- Syntax highlighting for Rego code
- Request history
- Export/import functionality
- Dark mode toggle
- Advanced filtering and search
- Real-time updates with WebSockets
