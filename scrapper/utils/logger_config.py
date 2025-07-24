import logging
import logging.handlers
import os
from pathlib import Path

def setup_logging(
    log_level: str = "ERROR",
    log_dir: str = "logs",
    app_name: str = "market-miner"
) -> None:
    """
    Configure logging for the application with both file and console handlers.
    
    Args:
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_dir (str): Directory to store log files
        app_name (str): Application name for log file naming
    """
    # Create logs directory if it doesn't exist
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Convert string log level to logging constant
    numeric_level = getattr(logging, log_level.upper(), logging.ERROR)
    
    # Define log formatters
    detailed_formatter = logging.Formatter(
        '%(asctime)s | %(name)-12s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    console_formatter = logging.Formatter('%(name)-12s %(levelname)-8s | %(message)s')

    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear any existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Console Handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(console_formatter)
    console_handler.setLevel(numeric_level)
    root_logger.addHandler(console_handler)

    # File Handler - Rotating file handler with max size of 10MB and 5 backup files
    log_file = log_path / f"{app_name}.log"
    file_handler = logging.handlers.RotatingFileHandler(
        log_file,
        maxBytes=10_000_000,  # 10MB
        backupCount=5,
        encoding='utf-8'
    )
    file_handler.setFormatter(detailed_formatter)
    file_handler.setLevel(numeric_level)
    root_logger.addHandler(file_handler)

    # Suppress noisy loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("sentry_sdk").setLevel(logging.ERROR)

    # Log the configuration only if we're above ERROR level
    root_logger.info(f"Logging configured with level: {log_level}")
    root_logger.info(f"Log file location: {log_file}")