# Scripts

This directory contains utility scripts for the OPA Policy Manager project.

## Token Generator (`generate_token.py`)

A utility script to generate JWT tokens for API testing. These tokens are compatible with the TokenDecoder class and can be used to authenticate API requests during development and testing.

### Quick Start

```bash
# Generate a default admin token
python scripts/generate_token.py

# Copy the token to clipboard (macOS)
python scripts/generate_token.py | pbcopy

# Generate a curl command to test the API
python scripts/generate_token.py --output curl
```

### Usage Examples

**Generate a token for a regular user:**

```bash
python scripts/generate_token.py \
  --employee-id E12345 \
  --ad-groups "infodir-app-user" \
  --email user@example.com \
  --name "John Doe"
```

**Generate a token for an admin:**

```bash
python scripts/generate_token.py \
  --employee-id E67890 \
  --ad-groups "infodir-app-admin,infodir-app-user" \
  --email admin@example.com \
  --name "Jane Admin"
```

**Generate a long-lived token (24 hours):**

```bash
python scripts/generate_token.py --expires-in 24
```

**Generate a token without expiration (for long-running tests):**

```bash
python scripts/generate_token.py --no-expiration
```

**View token payload in JSON format:**

```bash
python scripts/generate_token.py --output json
```

**Generate curl commands for API testing:**

```bash
python scripts/generate_token.py --output curl --url http://localhost:8000
```

### Output Formats

- `token` (default): Outputs just the JWT token
- `bearer`: Outputs the token with "Bearer " prefix
- `curl`: Generates example curl commands for testing the API
- `json`: Shows the decoded token payload and the token

### Using with curl

```bash
# Store token in a variable
TOKEN=$(python scripts/generate_token.py)

# Use it in API requests
curl -X POST "http://localhost:8000/permission" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json"

# Test specific application permission
curl -X GET "http://localhost:8000/permission/app-id-123" \
  -H "Authorization: Bearer $TOKEN"
```

### Using with httpie

```bash
TOKEN=$(python scripts/generate_token.py)

http POST http://localhost:8000/permission \
  "Authorization: Bearer $TOKEN"
```

### Using in Python Tests

```python
from scripts.generate_token import generate_token

# Generate a token programmatically
token = generate_token(
    employee_id="E12345",
    ad_groups=["infodir-app-admin"],
    email="test@example.com",
    name="Test User"
)

# Use in test
headers = {"Authorization": f"Bearer {token}"}
response = client.post("/permission", headers=headers)
```

### Common Scenarios

**Testing as an admin user:**

```bash
python scripts/generate_token.py \
  --ad-groups "infodir-app-admin,infodir-app-user"
```

**Testing as a regular user (no admin privileges):**

```bash
python scripts/generate_token.py \
  --ad-groups "infodir-app-user"
```

**Testing with multiple AD groups:**

```bash
python scripts/generate_token.py \
  --ad-groups "infodir-app-user,team-dev,team-qa"
```

### Parameters

- `--employee-id`: Employee ID (default: E99999)
- `--ad-groups`: Comma-separated list of AD groups (default: infodir-app-admin,infodir-app-user)
- `--email`: User email address (default: <test.admin@example.com>)
- `--name`: User full name (default: Test Admin)
- `--secret-key`: Secret key for signing (default: test_secret_key_for_development)
- `--algorithm`: JWT algorithm (default: HS256)
- `--expires-in`: Expiration time in hours (default: 8)
- `--no-expiration`: Generate a token without expiration
- `--output`: Output format (token|bearer|curl|json, default: token)
- `--url`: API base URL for curl output (default: <http://localhost:8000>)

### Notes

- The default secret key is for development/testing only
- Tokens are signed with HS256 by default
- The token decoder in the API can work with or without signature verification
- For production use, always use proper secret keys and signature verification
