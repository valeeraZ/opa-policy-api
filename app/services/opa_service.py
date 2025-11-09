"""OPA Service for policy evaluation and management."""

import httpx
import asyncio
import logging
from typing import Dict, List, Any, Optional
from app.config import settings
from app.exceptions import OPAConnectionError
from app.schemas.user import UserInfo
from app.models.application import Application

logger = logging.getLogger(__name__)


class OPAService:
    """Service for interacting with Open Policy Agent server."""

    def __init__(self, opa_url: Optional[str] = None, timeout: Optional[int] = None):
        """
        Initialize OPA service.

        Args:
            opa_url: OPA server URL (defaults to settings.opa_url)
            timeout: Request timeout in seconds (defaults to settings.opa_timeout)
        """
        self.opa_url = (opa_url or settings.opa_url).rstrip("/")
        self.timeout = timeout or settings.opa_timeout
        self.client = httpx.AsyncClient(timeout=self.timeout)

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def health_check(self) -> bool:
        """
        Check if OPA server is healthy and reachable.

        Returns:
            bool: True if OPA is healthy, False otherwise

        Raises:
            OPAConnectionError: If connection fails after retries
        """
        max_retries = 3
        base_delay = 1  # seconds

        for attempt in range(max_retries):
            try:
                response = await self.client.get(f"{self.opa_url}/health")
                if response.status_code == 200:
                    logger.info("OPA health check successful")
                    return True
                else:
                    logger.warning(
                        f"OPA health check returned status {response.status_code}"
                    )

            except httpx.RequestError as e:
                logger.warning(
                    f"OPA health check attempt {attempt + 1}/{max_retries} failed: {e}"
                )

                if attempt < max_retries - 1:
                    # Exponential backoff
                    delay = base_delay * (2**attempt)
                    logger.info(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    raise OPAConnectionError(
                        "OPA server is unreachable",
                        detail=f"Failed after {max_retries} attempts: {str(e)}",
                    )

        return False

    async def upload_base_policy(
        self, policy_path: str = "policies/permissions.rego"
    ) -> bool:
        """
        Upload base permissions.rego policy to OPA on startup.

        Args:
            policy_path: Path to the base policy file

        Returns:
            bool: True if upload successful

        Raises:
            OPAConnectionError: If policy upload fails
        """
        try:
            # Read the policy file
            with open(policy_path, "r") as f:
                policy_content = f.read()

            # Upload to OPA using Policy API
            # PUT /v1/policies/{id} where id is the policy module name
            policy_id = "permissions"
            url = f"{self.opa_url}/v1/policies/{policy_id}"

            response = await self.client.put(
                url, content=policy_content, headers={"Content-Type": "text/plain"}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Successfully uploaded base policy '{policy_id}' to OPA")
                return True
            else:
                error_detail = response.text
                logger.error(
                    f"Failed to upload base policy: {response.status_code} - {error_detail}"
                )
                raise OPAConnectionError(
                    "Failed to upload base policy to OPA",
                    detail=f"Status {response.status_code}: {error_detail}",
                )

        except FileNotFoundError as e:
            logger.error(f"Base policy file not found: {policy_path}")
            raise OPAConnectionError("Base policy file not found", detail=str(e))
        except httpx.RequestError as e:
            logger.error(f"Network error uploading base policy: {e}")
            raise OPAConnectionError(
                "Failed to connect to OPA for policy upload", detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading base policy: {e}")
            raise OPAConnectionError(
                "Unexpected error during policy upload", detail=str(e)
            )

    async def evaluate_permissions(
        self,
        user_info: UserInfo,
        applications: List[Application],
    ) -> Dict[str, str]:
        """
        Evaluate permissions for all applications for a given user.

        Args:
            user_info: User information including AD groups
            applications: List of all applications
            role_mappings: List of all role mappings

        Returns:
            Dict mapping application IDs to permission levels (user, admin, none)

        Raises:
            OPAConnectionError: If OPA evaluation fails
        """
        try:
            # Format input for OPA
            opa_input = self._format_opa_input(user_info, applications)

            # Call OPA REST API for policy evaluation
            url = f"{self.opa_url}/v1/data/permissions/permissions"

            response = await self.client.post(url, json={"input": opa_input})

            if response.status_code == 200:
                result = response.json()
                permissions = result.get("result", {})

                logger.info(
                    f"Successfully evaluated permissions for user {user_info.employee_id}"
                )
                logger.debug(f"Permissions result: {permissions}")

                return permissions
            else:
                error_detail = response.text
                logger.error(
                    f"OPA evaluation failed: {response.status_code} - {error_detail}"
                )
                raise OPAConnectionError(
                    "Failed to evaluate permissions",
                    detail=f"Status {response.status_code}: {error_detail}",
                )

        except httpx.RequestError as e:
            logger.error(f"Network error during OPA evaluation: {e}")
            raise OPAConnectionError(
                "Failed to connect to OPA for evaluation", detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during permission evaluation: {e}")
            raise OPAConnectionError(
                "Unexpected error during permission evaluation", detail=str(e)
            )

    def _format_opa_input(
        self,
        user_info: UserInfo,
        applications: List[Application],
    ) -> Dict[str, Any]:
        """
        Format user info and applications as OPA input.

        Args:
            user_info: User information
            applications: List of applications
            role_mappings: List of role mappings (not used in input, but available for context)

        Returns:
            Dict formatted for OPA input
        """
        return {
            "user": {
                "employee_id": user_info.employee_id,
                "ad_groups": user_info.ad_groups,
                "email": user_info.email,
                "name": user_info.name,
            },
            "applications": [app.id for app in applications],
        }

    async def push_policy_data(self, data_path: str, data: Dict[str, Any]) -> bool:
        """
        Push policy data to OPA using the Data API.

        Args:
            data_path: Path in OPA data hierarchy (e.g., "role_mappings")
            data: Data to push to OPA

        Returns:
            bool: True if successful

        Raises:
            OPAConnectionError: If data push fails
        """
        try:
            url = f"{self.opa_url}/v1/data/{data_path}"

            response = await self.client.put(url, json=data)

            if response.status_code in [200, 204]:
                logger.info(f"Successfully pushed data to OPA path: {data_path}")
                logger.debug(f"Data pushed: {data}")
                return True
            else:
                error_detail = response.text
                logger.error(
                    f"Failed to push data to OPA: {response.status_code} - {error_detail}"
                )
                raise OPAConnectionError(
                    f"Failed to push data to OPA path '{data_path}'",
                    detail=f"Status {response.status_code}: {error_detail}",
                )

        except httpx.RequestError as e:
            logger.error(f"Network error pushing data to OPA: {e}")
            raise OPAConnectionError(
                "Failed to connect to OPA for data push", detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error pushing data to OPA: {e}")
            raise OPAConnectionError("Unexpected error during data push", detail=str(e))

    async def upload_policy(self, policy_id: str, policy_content: str) -> bool:
        """
        Upload a policy to OPA using the Policy API.

        Args:
            policy_id: Unique identifier for the policy
            policy_content: Rego policy content

        Returns:
            bool: True if successful

        Raises:
            OPAConnectionError: If policy upload fails
        """
        try:
            url = f"{self.opa_url}/v1/policies/{policy_id}"

            response = await self.client.put(
                url, content=policy_content, headers={"Content-Type": "text/plain"}
            )

            if response.status_code in [200, 201]:
                logger.info(f"Successfully uploaded policy '{policy_id}' to OPA")
                return True
            else:
                error_detail = response.text
                logger.error(
                    f"Failed to upload policy: {response.status_code} - {error_detail}"
                )
                raise OPAConnectionError(
                    f"Failed to upload policy '{policy_id}' to OPA",
                    detail=f"Status {response.status_code}: {error_detail}",
                )

        except httpx.RequestError as e:
            logger.error(f"Network error uploading policy to OPA: {e}")
            raise OPAConnectionError(
                "Failed to connect to OPA for policy upload", detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error uploading policy to OPA: {e}")
            raise OPAConnectionError(
                "Unexpected error during policy upload", detail=str(e)
            )

    async def evaluate_custom_policy(
        self, policy_id: str, input_data: Dict[str, Any], query_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Evaluate a custom policy with provided input data.

        Args:
            policy_id: ID of the custom policy to evaluate
            input_data: Input data for policy evaluation
            query_path: Optional specific path to query (e.g., "allow", "permissions")
                       If not provided, queries the entire policy package

        Returns:
            Dict containing the OPA decision result

        Raises:
            OPAConnectionError: If policy evaluation fails
        """
        try:
            # Construct the query URL
            # If query_path is provided, use it; otherwise query the policy package root
            if query_path:
                url = f"{self.opa_url}/v1/data/{policy_id}/{query_path}"
            else:
                url = f"{self.opa_url}/v1/data/{policy_id}"

            response = await self.client.post(url, json={"input": input_data})

            if response.status_code == 200:
                result = response.json()
                decision = result.get("result", {})

                logger.info(f"Successfully evaluated custom policy '{policy_id}'")
                logger.debug(f"Custom policy result: {decision}")

                return decision
            else:
                error_detail = response.text
                logger.error(
                    f"Custom policy evaluation failed: {response.status_code} - {error_detail}"
                )
                raise OPAConnectionError(
                    f"Failed to evaluate custom policy '{policy_id}'",
                    detail=f"Status {response.status_code}: {error_detail}",
                )

        except httpx.RequestError as e:
            logger.error(f"Network error during custom policy evaluation: {e}")
            raise OPAConnectionError(
                "Failed to connect to OPA for custom policy evaluation", detail=str(e)
            )
        except Exception as e:
            logger.error(f"Unexpected error during custom policy evaluation: {e}")
            raise OPAConnectionError(
                "Unexpected error during custom policy evaluation", detail=str(e)
            )
