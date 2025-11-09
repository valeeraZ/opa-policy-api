# Token Generator Examples

This document provides practical examples for using the token generator with the OPA Policy Manager API.

## Quick Test Examples

### 1. Generate and Test with curl (One-liner)

```bash
# Test permission endpoint
curl -X POST "http://localhost:8000/permission" \
  -H "Authorization: Bearer $(make token 2>/dev/null)" \
  -H "Content-Type: application/json"

# Test applications endpoint  
curl -X GET "http://localhost:8000/applications" \
  -H "Authorization: Bearer $(make token 2>/dev/null)"
```

### 2. Store Token in Variable

```bash
# Generate and store token
TOKEN=$(make token 2>/dev/null)

# Use the token in multiple requests
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/permission
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/applications
curl -H "Authorization: Bearer $TOKEN" http://localhost:8000/role-mappings
```

### 3. Test Admin vs Regular User

```bash
# Admin user token
ADMIN_TOKEN=$(make token 2>/dev/null)

# Regular user token
USER_TOKEN=$(make token-user 2>/dev/null)

# Try to create an application (admin only)
curl -X POST "http://localhost:8000/applications" \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "test-app",
    "name": "Test Application",
    "environment": "dev"
  }'

# This should fail with 403
curl -X POST "http://localhost:8000/applications" \
  -H "Authorization: Bearer $USER_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "app_id": "test-app-2",
    "name": "Test Application 2",
    "environment": "dev"
  }'
```

### 4. Test Different AD Groups

```bash
# User with specific AD groups
TOKEN=$(python scripts/generate_token.py \
  --employee-id E11111 \
  --ad-groups "team-alpha,team-beta,infodir-app-user" \
  --email alpha@example.com \
  --name "Alpha User" \
  2>/dev/null)

curl -X POST "http://localhost:8000/permission" \
  -H "Authorization: Bearer $TOKEN"
```

### 5. Test Token Expiration

```bash
# Short-lived token (1 hour)
TOKEN=$(python scripts/generate_token.py --expires-in 1 2>/dev/null)

# Long-lived token (24 hours)
TOKEN=$(python scripts/generate_token.py --expires-in 24 2>/dev/null)

# Token without expiration (for long-running tests)
TOKEN=$(python scripts/generate_token.py --no-expiration 2>/dev/null)
```

## Integration Testing Examples

### Using with pytest

```python
import pytest
from scripts.generate_token import generate_token

@pytest.fixture
def admin_token():
    """Generate an admin token for testing."""
    return generate_token(
        employee_id="E99999",
        ad_groups=["infodir-app-admin", "infodir-app-user"],
        email="admin@test.com",
        name="Test Admin"
    )

@pytest.fixture
def user_token():
    """Generate a regular user token for testing."""
    return generate_token(
        employee_id="E12345",
        ad_groups=["infodir-app-user"],
        email="user@test.com",
        name="Test User"
    )

def test_admin_endpoint(client, admin_token):
    """Test that admin can access protected endpoint."""
    response = client.post(
        "/applications",
        headers={"Authorization": f"Bearer {admin_token}"},
        json={"app_id": "test", "name": "Test", "environment": "dev"}
    )
    assert response.status_code == 201

def test_user_cannot_access_admin_endpoint(client, user_token):
    """Test that regular user cannot access admin endpoint."""
    response = client.post(
        "/applications",
        headers={"Authorization": f"Bearer {user_token}"},
        json={"app_id": "test", "name": "Test", "environment": "dev"}
    )
    assert response.status_code == 403
```

### Using with httpx (async)

```python
import httpx
from scripts.generate_token import generate_token

async def test_api_with_token():
    token = generate_token()
    
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/permission",
            headers={"Authorization": f"Bearer {token}"}
        )
        
        print(f"Status: {response.status_code}")
        print(f"Permissions: {response.json()}")
```

## Production-like Testing

### Test with Different Environments

```bash
# Development environment token
DEV_TOKEN=$(python scripts/generate_token.py \
  --employee-id E10001 \
  --ad-groups "infodir-app-user,dev-team" \
  2>/dev/null)

# Production environment token (longer expiration)
PROD_TOKEN=$(python scripts/generate_token.py \
  --employee-id E10002 \
  --ad-groups "infodir-app-user,prod-team" \
  --expires-in 1 \
  2>/dev/null)

# Test against different environments
curl -H "Authorization: Bearer $DEV_TOKEN" http://localhost:8000/permission
curl -H "Authorization: Bearer $PROD_TOKEN" http://prod-server:8000/permission
```

### Load Testing with Multiple Users

```bash
# Generate tokens for multiple test users
for i in {1..10}; do
  TOKEN=$(python scripts/generate_token.py \
    --employee-id E$(printf "%05d" $i) \
    --email "user$i@example.com" \
    --name "User $i" \
    2>/dev/null)
  
  echo "Testing with user $i..."
  curl -s -H "Authorization: Bearer $TOKEN" http://localhost:8000/permission > /dev/null &
done

wait
echo "All tests completed"
```

## Debugging Examples

### Inspect Token Payload

```bash
# View token payload in JSON format
python scripts/generate_token.py --output json

# Decode an existing token
TOKEN="eyJhbGciOiJIUzI1..."
python -c "
from jose import jwt
import json
payload = jwt.decode('$TOKEN', '', options={'verify_signature': False})
print(json.dumps(payload, indent=2))
"
```

### Test Invalid Tokens

```bash
# Test with malformed token
curl -H "Authorization: Bearer invalid.token.here" http://localhost:8000/permission

# Test with expired token (generate one that expired 1 hour ago)
# Note: This requires modifying the script to support past expiration

# Test without Authorization header
curl http://localhost:8000/permission
```

## Postman/Insomnia Collection

You can also use the generated tokens in API clients:

1. Generate a token:

   ```bash
   make token
   ```

2. Copy the token (without the "# Token details" comments)

3. In Postman/Insomnia:
   - Go to Headers
   - Add header: `Authorization`
   - Value: `Bearer <paste-token-here>`

## GitHub Actions / CI/CD

Example GitHub Actions workflow:

```yaml
- name: Test API with token
  run: |
    TOKEN=$(python scripts/generate_token.py 2>/dev/null)
    curl -f -H "Authorization: Bearer $TOKEN" http://localhost:8000/health
```

## Tips and Best Practices

1. **Redirect stderr** when using tokens in scripts to avoid comments:

   ```bash
   TOKEN=$(make token 2>/dev/null)
   ```

2. **Use appropriate expiration** for your use case:
   - Quick tests: 1 hour (`--expires-in 1`)
   - Development: 8 hours (default)
   - Long-running tests: 24 hours or `--no-expiration`

3. **Match AD groups** to your test scenario:
   - Admin operations: Include `infodir-app-admin`
   - Regular users: Only `infodir-app-user`
   - Custom scenarios: Add relevant team groups

4. **Store tokens securely** in CI/CD:
   - Don't commit generated tokens to git
   - Generate fresh tokens for each test run
   - Use environment variables for token storage
