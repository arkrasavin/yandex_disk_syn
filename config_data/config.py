import os

from dotenv import load_dotenv, find_dotenv
from loguru import logger

if not find_dotenv():
    exit("Файл .env не найден, переменные окружения не загружены")
else:
    load_dotenv()

API_KEY = os.getenv("API_KEY")
PATH_TO_LOCAL_DIR = os.getenv("PATH_TO_LOCAL_DIR")
PATH_TO_DIR_DISK = os.getenv("PATH_TO_DIR_DISK")
CHECK_INTERVAL = int(os.getenv("CHECK_INTERVAL"))

path_to_log_file = os.getenv("PATH_TO_LOG_FILE")
current_dir = os.path.abspath(os.path.dirname(__file__))
dir_logger = os.path.join(current_dir, os.path.join("..", "logs"))
os.makedirs(dir_logger, exist_ok=True)
logger_dir = os.path.join(dir_logger, path_to_log_file)

logger.add(
    logger_dir,
    format="{time} {level} - {message}",
    level="INFO",
    enqueue=True,
    rotation="10 MB",
    compression="zip",
    retention="10 days",
)
