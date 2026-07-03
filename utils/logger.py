import logging
import sys
import os

def setup_logger(name="AutonomousAgent"):
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
        
    logger.setLevel(logging.INFO)
    
    # Console Handler
    c_handler = logging.StreamHandler(sys.stdout)
    c_handler.setLevel(logging.INFO)
    
    # Formatter
    formatter = logging.Formatter(
        '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    c_handler.setFormatter(formatter)
    
    logger.addHandler(c_handler)
    
    # Ensure logs directory exists if logging to file
    os.makedirs("storage/logs", exist_ok=True)
    f_handler = logging.FileHandler("storage/logs/agent.log", encoding="utf-8")
    f_handler.setLevel(logging.INFO)
    f_handler.setFormatter(formatter)
    logger.addHandler(f_handler)
    
    return logger

logger = setup_logger()
