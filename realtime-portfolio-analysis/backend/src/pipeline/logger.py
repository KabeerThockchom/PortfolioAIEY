import os
from datetime import datetime
from loguru import logger

# Create logs directory if it doesn't exist
logs_dir = os.path.join(os.getcwd(), "logs")
os.makedirs(logs_dir, exist_ok=True)

# Generate log file name
LOG_FILE = f"{datetime.now().strftime('%m_%d_%Y_%H_%M_%S')}.log"
LOG_FILE_PATH = os.path.join(logs_dir, LOG_FILE)

# Configure Loguru
logger.add(
    LOG_FILE_PATH,
    format="[ {time:YYYY-MM-DD HH:mm:ss} ] {line} {name} - {level} - {message}",
    level="DEBUG",
    rotation="10 MB",
    retention="30 days"
)