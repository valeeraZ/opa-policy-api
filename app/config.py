from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings loaded from environment variables."""

    # Database Configuration
    database_url: str

    # OPA Configuration
    opa_url: str
    opa_timeout: int = 5

    # S3 Configuration
    s3_bucket: str
    s3_region: str
    s3_endpoint_url: str = ""  # Optional: for LocalStack or custom S3 endpoints
    aws_access_key_id: str
    aws_secret_access_key: str

    # API Configuration
    api_title: str = "OPA Permission API"
    api_version: str = "1.0.0"

    # Logging Configuration
    log_level: str = "INFO"

    # JWT Configuration
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_verify_signature: bool = False  # Set to True in production with proper secret

    # Admin Configuration
    admin_ad_group: str = "infodir-admin"  # AD group that grants admin privileges

    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", case_sensitive=False
    )


# Global settings instance
settings = Settings()
