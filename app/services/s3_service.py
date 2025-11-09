"""S3 service for managing policy file storage."""

import logging
from typing import List, Optional
from datetime import datetime

import boto3
from botocore.exceptions import ClientError, BotoCoreError

from app.config import settings
from app.exceptions import S3Error

logger = logging.getLogger(__name__)


class S3Service:
    """Service for managing policy files in S3 with versioning support."""

    def __init__(self):
        """Initialize S3 client with configuration from settings."""
        try:
            # Build client configuration
            client_config = {
                "service_name": "s3",
                "region_name": settings.s3_region,
                "aws_access_key_id": settings.aws_access_key_id,
                "aws_secret_access_key": settings.aws_secret_access_key,
            }

            # Add endpoint URL if configured (for LocalStack or custom S3 endpoints)
            if settings.s3_endpoint_url:
                client_config["endpoint_url"] = settings.s3_endpoint_url
                logger.info(f"Using custom S3 endpoint: {settings.s3_endpoint_url}")

            self.s3_client = boto3.client(**client_config)
            self.bucket = settings.s3_bucket
            logger.info(f"S3Service initialized for bucket: {self.bucket}")
        except Exception as e:
            logger.error(f"Failed to initialize S3 client: {str(e)}")
            raise S3Error(message="Failed to initialize S3 client", detail=str(e))

    async def upload_policy_file(
        self, policy_id: str, content: str, version: str
    ) -> str:
        """
        Upload a policy file to S3 with versioning.

        Args:
            policy_id: Unique identifier for the policy
            content: The policy content (Rego code)
            version: Version identifier for the policy

        Returns:
            S3 key where the file was stored

        Raises:
            S3Error: If upload fails
        """
        try:
            # Construct S3 key with version
            s3_key = f"policies/{policy_id}/{version}.rego"

            # Add metadata
            metadata = {
                "policy_id": policy_id,
                "version": version,
                "uploaded_at": datetime.now().isoformat(),
            }

            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket,
                Key=s3_key,
                Body=content.encode("utf-8"),
                ContentType="text/plain",
                Metadata=metadata,
            )

            logger.info(
                f"Successfully uploaded policy {policy_id} version {version} to S3: {s3_key}"
            )
            return s3_key

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                f"S3 ClientError uploading policy {policy_id}: {error_code} - {error_message}"
            )
            raise S3Error(
                message="Failed to upload policy file to S3",
                detail=f"{error_code}: {error_message}",
            )
        except BotoCoreError as e:
            logger.error(f"BotoCoreError uploading policy {policy_id}: {str(e)}")
            raise S3Error(message="S3 connection error during upload", detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error uploading policy {policy_id}: {str(e)}")
            raise S3Error(
                message="Unexpected error during policy upload", detail=str(e)
            )

    async def download_policy_file(
        self, policy_id: str, version: Optional[str] = None
    ) -> str:
        """
        Download a policy file from S3.

        Args:
            policy_id: Unique identifier for the policy
            version: Optional version identifier. If None, gets the latest version

        Returns:
            Policy content as string

        Raises:
            S3Error: If download fails or file not found
        """
        try:
            # If no version specified, get the latest version
            if version is None:
                versions = await self.list_policy_versions(policy_id)
                if not versions:
                    raise S3Error(
                        message=f"No versions found for policy {policy_id}",
                        detail="Policy does not exist in S3",
                    )
                version = versions[0]  # Assuming versions are sorted, latest first

            # Construct S3 key
            s3_key = f"policies/{policy_id}/{version}.rego"

            # Download from S3
            response = self.s3_client.get_object(Bucket=self.bucket, Key=s3_key)

            content = response["Body"].read().decode("utf-8")
            logger.info(
                f"Successfully downloaded policy {policy_id} version {version} from S3"
            )
            return content

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))

            if error_code == "NoSuchKey":
                logger.warning(
                    f"Policy file not found in S3: {policy_id} version {version}"
                )
                raise S3Error(
                    message="Policy file not found",
                    detail=f"Policy {policy_id} version {version} does not exist in S3",
                )

            logger.error(
                f"S3 ClientError downloading policy {policy_id}: {error_code} - {error_message}"
            )
            raise S3Error(
                message="Failed to download policy file from S3",
                detail=f"{error_code}: {error_message}",
            )
        except BotoCoreError as e:
            logger.error(f"BotoCoreError downloading policy {policy_id}: {str(e)}")
            raise S3Error(message="S3 connection error during download", detail=str(e))
        except Exception as e:
            logger.error(f"Unexpected error downloading policy {policy_id}: {str(e)}")
            raise S3Error(
                message="Unexpected error during policy download", detail=str(e)
            )

    async def list_policy_versions(self, policy_id: str) -> List[str]:
        """
        List all versions of a policy in S3.

        Args:
            policy_id: Unique identifier for the policy

        Returns:
            List of version identifiers, sorted by most recent first

        Raises:
            S3Error: If listing fails
        """
        try:
            prefix = f"policies/{policy_id}/"

            # List objects with the policy prefix
            response = self.s3_client.list_objects_v2(Bucket=self.bucket, Prefix=prefix)

            # Extract versions from keys
            versions = []
            if "Contents" in response:
                for obj in response["Contents"]:
                    key = obj["Key"]
                    # Extract version from key (e.g., "policies/policy-1/v1.0.0.rego" -> "v1.0.0")
                    if key.endswith(".rego"):
                        version = key.split("/")[-1].replace(".rego", "")
                        versions.append(
                            {"version": version, "last_modified": obj["LastModified"]}
                        )

            # Sort by last modified date (most recent first)
            versions.sort(key=lambda x: x["last_modified"], reverse=True)
            version_list = [v["version"] for v in versions]

            logger.info(f"Found {len(version_list)} versions for policy {policy_id}")
            return version_list

        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "Unknown")
            error_message = e.response.get("Error", {}).get("Message", str(e))
            logger.error(
                f"S3 ClientError listing versions for policy {policy_id}: {error_code} - {error_message}"
            )
            raise S3Error(
                message="Failed to list policy versions from S3",
                detail=f"{error_code}: {error_message}",
            )
        except BotoCoreError as e:
            logger.error(
                f"BotoCoreError listing versions for policy {policy_id}: {str(e)}"
            )
            raise S3Error(
                message="S3 connection error during version listing", detail=str(e)
            )
        except Exception as e:
            logger.error(
                f"Unexpected error listing versions for policy {policy_id}: {str(e)}"
            )
            raise S3Error(
                message="Unexpected error during version listing", detail=str(e)
            )
