from pydantic import BaseModel, Field, SecretStr
from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os
from typing import Optional

from dotenv import load_dotenv
import os

# .env 파일 로드
load_dotenv()

# 환경 변수에서 값 읽기
APP_DOMAIN = os.getenv("APP_DOMAIN")
APP_MOCK_DOMAIN = os.getenv("APP_MOCK_DOMAIN")
APP_TOKEN_EXPIRY = int(os.getenv("APP_TOKEN_EXPIRY"))

DB_ENGINE = os.getenv("DB_ENGINE")
DB_HOST = os.getenv("DB_HOST")
DB_PORT = int(os.getenv("DB_PORT", 5432))  # 기본값 설정
DB_DATABASE = os.getenv("DB_DATABASE")
DB_USER = os.getenv("DB_USER")
DB_PASSWORD = os.getenv("DB_PASSWORD")

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")  # 기본값 설정
LOG_FILE = os.getenv("LOG_FILE", "kiwoom_auto_trader.log")

APP_KEY = os.getenv("APP_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")

USE_MOCK = bool(os.getenv("USE_MOCK"))

class AppConfig:
    def __init__(self):
        self.domain = APP_DOMAIN
        self.mock_domain = APP_MOCK_DOMAIN
        self.token_expiry = APP_TOKEN_EXPIRY
        self.ws_url = os.getenv('WS_URL_MOCK') if USE_MOCK else os.getenv('WS_URL')

class DBConfig:
    def __init__(self):
        self.engine = DB_ENGINE
        self.host = DB_HOST
        self.port = DB_PORT
        self.database = DB_DATABASE
        self.user = DB_USER
        self.password = DB_PASSWORD

class LogConfig:
    def __init__(self):
        self.level = LOG_LEVEL
        self.file = LOG_FILE

class Config:
    def __init__(self):
        self.app = AppConfig()
        self.db = DBConfig()
        self.log = LogConfig()

# 설정 객체 생성
config = Config()

# # 출력 확인
# print("APP_DOMAIN:", APP_DOMAIN)
# print("DB_ENGINE:", DB_ENGINE)
# print("LOG_FILE:", LOG_FILE)

# # 확인
# print("App Config:", config.app.__dict__)
# print("DB Config:", config.db.__dict__)
# print("Log Config:", config.log.__dict__)
