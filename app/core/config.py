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

    # Configuration for Pydantic to load the .env file
    # This is a different syntax for Pydantic v2
    # If using Pydantic v1, use 'class Config: env_file = ".env"'
    model_config = {
        'env_file': '.env'
    }

# Instantiate the settings object once
# When this line runs, Pydantic loads the values from .env
settings = Settings()

