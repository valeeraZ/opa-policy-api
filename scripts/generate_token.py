#!/usr/bin/env python3
"""
Token generator for API testing.

This script generates JWT tokens that can be used to test the OPA Policy Manager API.
The tokens are compatible with the TokenDecoder class in app/auth/token_decoder.py.

Usage:
    # Generate a token with default settings (admin user)
    python scripts/generate_token.py

    # Generate a token for a specific user
    python scripts/generate_token.py --employee-id E12345 --email user@example.com --name "John Doe"

    # Generate a token with specific AD groups
    python scripts/generate_token.py --ad-groups "infodir-app-user,team-dev"

    # Generate a token with custom expiration (in hours)
    python scripts/generate_token.py --expires-in 24

    # Generate a token without signature (for testing)
    python scripts/generate_token.py --no-verify
"""

import argparse
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add parent directory to path to import app modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from jose import jwt
from typing import Optional, Any


def generate_token(
    employee_id: str = "E99999",
    ad_groups: Optional[list[str]] = None,
    email: str = "test.admin@example.com",
    name: str = "Test Admin",
    secret_key: str = "test_secret_key_for_development",
    algorithm: str = "HS256",
    expires_in_hours: int = 8,
    include_expiration: bool = True,
) -> str:
    """
    Generate a JWT token for API testing.

    Args:
        employee_id: Employee ID or subject identifier
        ad_groups: List of Active Directory groups
        email: User email address
        name: User full name
        secret_key: Secret key for signing the token
        algorithm: JWT algorithm to use
        expires_in_hours: Token expiration time in hours
        include_expiration: Whether to include expiration claim

    Returns:
        JWT token string
    """
    if ad_groups is None:
        ad_groups = ["infodir-admin", "infodir-app-user"]

    # Build token payload
    payload: dict[str, Any] = {
        "employee_id": employee_id,
        "ad_groups": ad_groups,
        "email": email,
        "name": name,
        "iat": datetime.now(timezone.utc),
    }

    # Add expiration if requested
    if include_expiration:
        payload["exp"] = datetime.now(timezone.utc) + timedelta(hours=expires_in_hours)

    # Encode the token
    token = jwt.encode(payload, secret_key, algorithm=algorithm)

    return token


def main():
    """Main entry point for the script."""
    parser = argparse.ArgumentParser(
        description="Generate JWT tokens for API testing",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Generate a default admin token
  python scripts/generate_token.py
  
  # Generate a token for a regular user
  python scripts/generate_token.py --employee-id E12345 --ad-groups "infodir-app-user"
  
  # Generate a token for an admin user with custom details
  python scripts/generate_token.py --employee-id E67890 \\
    --email admin@company.com \\
    --name "Jane Smith" \\
    --ad-groups "infodir-admin,infodir-app-user"
  
  # Generate a long-lived token (24 hours)
  python scripts/generate_token.py --expires-in 24
  
  # Generate a token without expiration
  python scripts/generate_token.py --no-expiration
        """,
    )

    parser.add_argument(
        "--employee-id", default="E99999", help="Employee ID (default: E99999)"
    )

    parser.add_argument(
        "--ad-groups",
        default="infodir-admin,infodir-app-user",
        help="Comma-separated list of AD groups (default: infodir-admin,infodir-app-user)",
    )

    parser.add_argument(
        "--email",
        default="test.admin@example.com",
        help="User email address (default: test.admin@example.com)",
    )

    parser.add_argument(
        "--name", default="Test Admin", help="User full name (default: Test Admin)"
    )

    parser.add_argument(
        "--secret-key",
        default="test_secret_key_for_development",
        help="Secret key for signing the token (default: test_secret_key_for_development)",
    )

    parser.add_argument(
        "--algorithm",
        default="HS256",
        choices=["HS256", "HS384", "HS512", "RS256", "RS384", "RS512"],
        help="JWT algorithm (default: HS256)",
    )

    parser.add_argument(
        "--expires-in",
        type=int,
        default=8,
        help="Token expiration time in hours (default: 8)",
    )

    parser.add_argument(
        "--no-expiration",
        action="store_true",
        help="Generate a token without expiration",
    )

    parser.add_argument(
        "--output",
        choices=["token", "curl", "bearer", "json"],
        default="token",
        help="Output format: token (just the token), curl (curl command), bearer (Bearer prefix), json (full payload)",
    )

    parser.add_argument(
        "--url",
        default="http://localhost:8000",
        help="API base URL for curl output (default: http://localhost:8000)",
    )

    args = parser.parse_args()

    # Parse AD groups
    ad_groups = [g.strip() for g in args.ad_groups.split(",") if g.strip()]

    # Generate the token
    token = generate_token(
        employee_id=args.employee_id,
        ad_groups=ad_groups,
        email=args.email,
        name=args.name,
        secret_key=args.secret_key,
        algorithm=args.algorithm,
        expires_in_hours=args.expires_in,
        include_expiration=not args.no_expiration,
    )

    # Output based on format
    if args.output == "token":
        print(token)

    elif args.output == "bearer":
        print(f"Bearer {token}")

    elif args.output == "curl":
        print("# Test the /permission endpoint")
        print(f'curl -X POST "{args.url}/permission" \\')
        print(f'  -H "Authorization: Bearer {token}" \\')
        print('  -H "Content-Type: application/json"')
        print()
        print("# Test the /applications endpoint")
        print(f'curl -X GET "{args.url}/applications" \\')
        print(f'  -H "Authorization: Bearer {token}"')

    elif args.output == "json":
        # Decode and pretty print the payload
        decoded_payload = jwt.decode(token, "", options={"verify_signature": False})
        import json

        print(json.dumps(decoded_payload, indent=2, default=str))
        print()
        print("Token:")
        print(token)

    # Print helpful info to stderr so it doesn't interfere with token output
    if args.output in ["token", "bearer"]:
        print("\n# Token details:", file=sys.stderr)
        print(f"# Employee ID: {args.employee_id}", file=sys.stderr)
        print(f"# AD Groups: {', '.join(ad_groups)}", file=sys.stderr)
        print(f"# Email: {args.email}", file=sys.stderr)
        print(f"# Name: {args.name}", file=sys.stderr)
        if not args.no_expiration:
            print(f"# Expires in: {args.expires_in} hours", file=sys.stderr)
        else:
            print("# Expires: Never", file=sys.stderr)


if __name__ == "__main__":
    main()
