import os
import logging
from logging.handlers import TimedRotatingFileHandler

class RagLogger:
    __logger: logging.Logger = None

    @classmethod
    def logger(cls) -> logging.Logger:
        if cls.__logger is None:
             RagLogger.setup(kwargs={})
        return cls.__logger
    
    @classmethod
    def _set_logger(cls, value: logging.Logger):
        if not isinstance(value, logging.Logger):
             raise RuntimeError("RagLogger.logger must be an instance of logging.Logger")
        cls.__logger = value

    @staticmethod
    def setup(kwargs: dict):
        default_log_dir = f"{os.getcwd()}/logs"
        log_dir = kwargs.get("directory", default_log_dir) if kwargs is not None else default_log_dir
        os.makedirs(log_dir, exist_ok=True)
        default_log_level = "INFO"
        log_level = kwargs.get("level", default_log_level).upper() if kwargs is not None else default_log_level

        file_handler = TimedRotatingFileHandler(f'{log_dir}/rag.log', 'midnight', 1)
        file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

        logger = logging.getLogger(__name__)
        logger.setLevel(log_level)
        logger.addHandler(file_handler)
        logger.info("RagLogger is set up with level %s and directory %s", log_level, log_dir)

        RagLogger._set_logger(logger)

