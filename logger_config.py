# logger_config.py
import logging
from logging.handlers import RotatingFileHandler

def setup_logging():
    """Initializes a rotating logger layer to monitor portfolio evolution events."""
    handler = RotatingFileHandler(
        'portfolio_builder.log', maxBytes=5000000, backupCount=5
    )
    logging.basicConfig(
        handlers=[handler, logging.StreamHandler()],
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s'
    )