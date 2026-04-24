import os
import json
import logging
import hashlib
import datetime
from functools import wraps
from typing import Any, Callable, Union, List, Dict

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


class UtilityFunctions:
    @staticmethod
    def log(message: str) -> None:
        logging.info(message)

    @staticmethod
    def validate_type(variable: Any, expected_type: type) -> bool:
        return isinstance(variable, expected_type)

    @staticmethod
    def format_date(date: datetime.date) -> str:
        return date.strftime('%Y-%m-%d')

    @staticmethod
    def hash_string(string: str) -> str:
        return hashlib.sha256(string.encode()).hexdigest()

    @staticmethod
    def json_to_dict(json_string: str) -> Dict:
        return json.loads(json_string)

    @staticmethod
    def dict_to_json(dictionary: Dict) -> str:
        return json.dumps(dictionary, indent=4)

    @staticmethod
    def current_datetime() -> str:
        return datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S')

    @staticmethod
    def read_file(file_path: str) -> str:
        with open(file_path, 'r') as file:
            return file.read()

    @staticmethod
    def write_file(file_path: str, content: str) -> None:
        with open(file_path, 'w') as file:
            file.write(content)

    @staticmethod
    def retry(times: int) -> Callable:
        def decorator(function: Callable) -> Callable:
            @wraps(function)
            def wrapper(*args, **kwargs) -> Any:
                for attempt in range(times):
                    try:
                        return function(*args, **kwargs)
                    except Exception as e:
                        logging.warning(f'Attempt {attempt + 1} failed: {e}')
                return None
            return wrapper
        return decorator

    @staticmethod
    def safe_divide(a: Union[int, float], b: Union[int, float]) -> Union[int, float, str]:
        return a / b if b != 0 else 0.0

    @staticmethod
    def get_env_variable(var_name: str, default: str = '') -> str:
        return os.getenv(var_name, default)

    @staticmethod
    def handle_exception(e: Exception) -> None:
        logging.error(f'Error occurred: {e}')

    @staticmethod
    def format_currency(amount: float, currency: str = "PHP") -> str:
        symbol = {"PHP": "₱", "USD": "$", "EUR": "€"}.get(currency, currency)
        return f"{symbol}{amount:,.2f}"
