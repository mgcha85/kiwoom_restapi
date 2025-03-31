# src/utils/logger.py

import os
import sys
import logging
from logging.handlers import RotatingFileHandler
from src.config import config, LOG_FILE

def get_logger(name: str = __name__, level: int = None) -> logging.Logger:
    """
    설정 파일(config.yaml)과 .env의 정보를 활용하여 로깅을 초기화하고 Logger 객체를 반환합니다.
    """
    logger = logging.getLogger(name)
    # config의 log.level 값에 따라 로그 레벨 결정
    if level is None:
        level = getattr(logging, config.log.level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # 핸들러가 이미 등록되어 있으면 재설정하지 않음
    if not logger.handlers:
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', "%Y-%m-%d %H:%M:%S"
        )
        # 콘솔 핸들러
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)

        # 파일 핸들러 (LOG_FILE 환경 변수 사용)
        file_handler = RotatingFileHandler(LOG_FILE, maxBytes=5*1024*1024, backupCount=3)
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger
