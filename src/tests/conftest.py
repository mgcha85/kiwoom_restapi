# tests/conftest.py
import os
import pathlib
import pytest

from db.db import engine, SessionLocal
from models.trade_entities import Base

# 테스트용 SQLite 파일 경로
TEST_DB_PATH = pathlib.Path(__file__).parent / "trade_test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB_PATH.as_posix()}"

@pytest.fixture(scope="session", autouse=True)
def initialize_database():
    """
    pytest 세션 시작 시 한 번 실행됩니다.
    기존 테스트 DB 파일 삭제 후, 모든 테이블을 생성합니다.
    """
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
    Base.metadata.create_all(bind=engine)
    yield
    # 필요 시 테스트 완료 후 삭제 가능
    # TEST_DB_PATH.unlink(missing_ok=True)

@pytest.fixture(scope="function")
def db_session():
    """
    각 테스트 함수마다 새 세션을 제공합니다.
    필요 시 트랜잭션 관리를 통해 롤백 처리가 가능합니다.
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()
