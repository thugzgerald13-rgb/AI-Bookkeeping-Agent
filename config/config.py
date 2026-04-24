import os
from dotenv import load_dotenv

load_dotenv()

class APIConfig:
    def __init__(self):
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY", "")
        self.model = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-20250514")

class DatabaseConfig:
    def __init__(self):
        self.db_path = os.getenv("DB_PATH", "data/bookkeeping.db")

class LoggingConfig:
    def __init__(self):
        self.log_level = os.getenv("LOG_LEVEL", "INFO")

class AppConfig:
    def __init__(self):
        self.app_name = os.getenv("APP_NAME", "AI Bookkeeping Agent")
        self.version = os.getenv("APP_VERSION", "2.0.0")
        self.company_name = os.getenv("COMPANY_NAME", "My Business")
        self.currency = os.getenv("CURRENCY", "PHP")

class ConfigManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance.api = APIConfig()
            cls._instance.database = DatabaseConfig()
            cls._instance.logging = LoggingConfig()
            cls._instance.app = AppConfig()
        return cls._instance

    def to_dict(self):
        return {
            "app": self.app.__dict__,
            "database": self.database.__dict__,
            "logging": self.logging.__dict__,
        }

config = ConfigManager()
