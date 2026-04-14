import os

class APIConfig:
    def __init__(self, api_type):
        self.api_type = api_type
        self.api_key = os.getenv(f'{api_type.upper()}_API_KEY')
        
class DatabaseConfig:
    def __init__(self, db_type):
        self.db_type = db_type
        self.connection_string = os.getenv(f'{db_type.upper()}_DB_CONNECTION_STRING')
        
class LoggingConfig:
    def __init__(self, log_level='INFO'):
        self.log_level = log_level
        
class AgentConfig:
    def __init__(self, pattern='ReAct'):
        self.pattern = pattern
        
class AppConfig:
    def __init__(self):
        self.app_name = os.getenv('APP_NAME', 'AI Bookkeeping Agent')
        self.version = os.getenv('APP_VERSION', '1.0')
        
class ConfigManager:
    def __init__(self):
        self.api_config = APIConfig('OpenAI')  # Default to OpenAI
        self.database_config = DatabaseConfig('SQLite')  # Default to SQLite
        self.logging_config = LoggingConfig()
        self.agent_config = AgentConfig()
        self.app_config = AppConfig()  
        
    def get_config(self):
        return {
            'API': self.api_config.__dict__,
            'Database': self.database_config.__dict__,
            'Logging': self.logging_config.__dict__,
            'Agent': self.agent_config.__dict__,
            'Application': self.app_config.__dict__,
        }

# Initialize ConfigManager
config_manager = ConfigManager()
