import logging
import sys


def setup_logger(name, filename):
    # Logger set up
    FORMAT = f"[{name}] | [%(asctime)s] | %(filename)s/%(funcName)s:%(lineno)d | [%(levelname)s] | %(message)s"
    formatter = logging.Formatter(FORMAT)

    # Create a FileHandler to log messages to a file
    file_handler = logging.FileHandler(f'logs/{filename}.log')
    file_handler.setFormatter(formatter)

    # Create a StreamHandler to log messages to the console
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)

    # Get the logger instance
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)


    return logger