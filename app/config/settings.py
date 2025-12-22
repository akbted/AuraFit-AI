from pydantic_settings import BaseSettings
from typing import List, Optional
from pathlib import Path

class Settings(BaseSettings):
    
    # Model Path
    MODEL_PATH: Path = Path("app/models/yolo11l-pose.pt")

    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    CORS_ORIGINS: list = ["http://localhost:3000", "http://localhost:5173"]
    
    class Config:
        env_file = ".env"
    


# Instance
setting = Settings()