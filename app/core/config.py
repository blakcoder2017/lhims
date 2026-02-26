import os
from pydantic_settings import BaseSettings 
from pydantic import Field

class Settings(BaseSettings):
    # Application Settings
    app_title: str = "LHIMS"
    version: str = "0.1.0"
    debug: bool = True
    
    SQLALCHEMY_DATABASE_URL: str
    
    # Security Settings
    SECRET_KEY: str
    ALGORITHM: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    
    # SMS Settings (SMSOnlineGH)
    SMSONLINEGH_API_KEY: str = ""
    SMSONLINEGH_SENDER: str = "LHIMS"

    # ============================================
    # DHIMS2 Integration Settings
    # ============================================
    # Base URL for DHIMS2/DHIS2 instance
    DHIMS2_BASE_URL: str = Field(
        default="",
        description="Base URL for DHIMS2/DHIS2 API (e.g., https://dhims2.ghana.gov.gh)"
    )
    # DHIMS2 API credentials
    DHIMS2_USERNAME: str = Field(
        default="",
        description="DHIMS2 API username"
    )
    DHIMS2_PASSWORD: str = Field(
        default="",
        description="DHIMS2 API password"
    )
    # API configuration
    DHIMS2_TIMEOUT_SECONDS: int = Field(
        default=30,
        description="Timeout for DHIMS2 API requests in seconds"
    )
    DHIMS2_VERIFY_TLS: bool = Field(
        default=True,
        description="Verify TLS certificates for DHIMS2 API"
    )
    DHIMS2_MAX_RETRIES: int = Field(
        default=5,
        description="Maximum number of retry attempts for failed API calls"
    )
    DHIMS2_BACKOFF_SECONDS: int = Field(
        default=2,
        description="Initial backoff seconds for exponential retry"
    )
    # Instance identification
    DHIMS2_INSTANCE_NAME: str = Field(
        default="production",
        description="DHIMS2 instance name (e.g., 'prod', 'training', 'demo')"
    )
    # Data locking configuration
    DHIMS2_DATA_LOCK_DAYS: int = Field(
        default=60,
        description="Number of days after period end when data becomes locked for editing"
    )
    # Dry run mode - validates but doesn't submit
    DHIMS2_DRY_RUN: bool = Field(
        default=False,
        description="If true, validates and builds payload but does not submit to DHIMS2"
    )

    # Configuration for Pydantic to load the .env file
    # extra='ignore' allows .env to contain other keys (e.g. postgres_*, docker) without validation errors
    model_config = {
        'env_file': '.env',
        'extra': 'ignore',
    }

# Instantiate the settings object once
# When this line runs, Pydantic loads the values from .env
settings = Settings()

