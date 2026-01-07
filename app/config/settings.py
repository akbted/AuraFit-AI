from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List, Optional
from pathlib import Path
import os
from dotenv import load_dotenv


class Settings(BaseSettings):
    
    # Model Path
    MODEL_PATH: Path = Path("app/models/yolo11l-pose.pt")

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    hf_token: str = ""  # Add this field

    # Fetch variables
    DB_USER: str 
    DB_PASSWORD: str
    DB_HOST: str
    DB_PORT: int
    DB_NAME: str

    # Keycloak
    KEYCLOAK_URL: str
    KEYCLOAK_ADMIN_USERNAME: str
    KEYCLOAK_ADMIN_PASSWORD: str

    # Database Schema Folder
    DB_SCHEMA: str = "app/database/schema"

    model_config = SettingsConfigDict(
        env_file=".env",           
        env_file_encoding="utf-8",
        extra="ignore"            
    )
    

# Instance
setting = Settings()