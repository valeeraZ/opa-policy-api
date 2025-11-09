#!/bin/bash
# Initialize LocalStack S3 bucket for local development

set -e

echo "Waiting for LocalStack to be ready..."
until curl -s http://localhost:4566/_localstack/health | grep -q '"s3": "available"'; do
  echo "Waiting for S3 service..."
  sleep 2
done

echo "Creating S3 bucket: opa-policies"
aws --endpoint-url=http://localhost:4566 s3 mb s3://opa-policies 2>/dev/null || echo "Bucket already exists"

echo "Enabling versioning on bucket"
aws --endpoint-url=http://localhost:4566 s3api put-bucket-versioning \
  --bucket opa-policies \
  --versioning-configuration Status=Enabled

echo "LocalStack S3 initialization complete!"
echo "Bucket: opa-policies"
echo "Endpoint: http://localhost:4566"
