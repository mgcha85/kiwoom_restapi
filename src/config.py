# src/config.py

import os
import yaml
from pydantic import BaseModel, ValidationError
from dotenv import load_dotenv

# 1. .env 파일 로드 (민감 정보)
load_dotenv()

# 2. 설정 파일에 대한 pydantic 모델 정의
class AppConfig(BaseModel):
    domain: str
    mock_domain: str
    token_expiry: int

class DBConfig(BaseModel):
    host: str
    port: int
    database: str
    user: str
    password: str

class LogConfig(BaseModel):
    level: str
    file: str

class Config(BaseModel):
    app: AppConfig
    db: DBConfig
    log: LogConfig

def load_config(config_file: str = "config.yaml") -> Config:
    """
    config.yaml 파일을 읽어 pydantic 모델로 검증 후 Config 객체를 반환합니다.
    """
    with open(config_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    try:
        config = Config(**data)
    except ValidationError as e:
        print("Configuration validation error:", e)
        raise e
    return config

# 3. 전역 설정 객체 생성
config = load_config()

# 4. 환경 변수에서 추가 정보를 읽어옵니다.
APP_KEY = os.getenv("APP_KEY")
SECRET_KEY = os.getenv("SECRET_KEY")
LOG_FILE = os.getenv("LOG_FILE", config.log.file)
