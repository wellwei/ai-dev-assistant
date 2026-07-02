import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
    OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    MODEL_NAME = os.getenv("MODEL_NAME", "gpt-4o")
    
    # 本地 SQLite 持久化
    CHECKPOINT_DB = os.getenv("CHECKPOINT_DB", "./checkpoints/checkpoints.db")
    
    # 日志
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

settings = Settings()