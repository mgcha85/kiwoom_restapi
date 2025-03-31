import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import logging
from datetime import datetime
from dotenv import load_dotenv

# .env 파일의 환경변수 로드 (DB 관련 보안정보 포함)
load_dotenv()

class PostgresClient:
    """
    PostgreSQL 연결 및 CRUD 작업을 위한 클라이언트 클래스.
    DB 연결 정보는 config.yaml에서 가져올 수 있으며, 민감 정보는 .env 파일로 관리합니다.
    """
    def __init__(self, host: str, port: int, database: str, user: str, password: str):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

    def connect(self):
        """PostgreSQL 데이터베이스에 연결합니다."""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                dbname=self.database,
                user=self.user,
                password=self.password
            )
            logging.info("Postgres DB에 성공적으로 연결되었습니다.")
        except Exception as e:
            logging.error(f"Postgres DB 연결 오류: {e}")
            raise e

    def disconnect(self):
        """DB 연결을 종료합니다."""
        if self.connection:
            self.connection.close()
            logging.info("Postgres DB 연결이 종료되었습니다.")

    @contextmanager
    def get_cursor(self):
        """
        커서를 context manager 형태로 제공하여,
        작업 완료 후 commit 또는 rollback 후 커서를 자동으로 닫습니다.
        """
        if self.connection is None:
            self.connect()
        cursor = self.connection.cursor(cursor_factory=RealDictCursor)
        try:
            yield cursor
            self.connection.commit()
        except Exception as e:
            self.connection.rollback()
            logging.error(f"쿼리 실행 중 오류 발생: {e}")
            raise e
        finally:
            cursor.close()

    def execute_query(self, query: str, params: tuple = None):
        """일반적인 SELECT 또는 DML 쿼리를 실행합니다."""
        with self.get_cursor() as cursor:
            cursor.execute(query, params)
            try:
                result = cursor.fetchall()
                return result
            except psycopg2.ProgrammingError:
                # SELECT 쿼리가 아니거나 결과가 없는 경우
                return None

    # --- hold_list 테이블 관련 함수 ---
    def upsert_hold_list(self, code: str, qty: int, avg_price: int, remain_qty: int = 0, order_id: str = None,
                           num_buy: int = 1, buy_time: datetime = None, due_date: datetime = None,
                           stop_price: int = 0, fee: float = 0.0, tax: float = 0.0):
        """
        hold_list 테이블에 데이터를 삽입하거나, 기존 데이터가 있을 경우 업데이트합니다.
        """
        query = """
        INSERT INTO hold_list (code, qty, avg_price, remain_qty, order_id, num_buy, buy_time, due_date, stop_price, fee, tax)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (code) DO UPDATE
        SET qty = EXCLUDED.qty,
            avg_price = EXCLUDED.avg_price,
            remain_qty = EXCLUDED.remain_qty,
            order_id = EXCLUDED.order_id,
            num_buy = EXCLUDED.num_buy,
            buy_time = EXCLUDED.buy_time,
            due_date = EXCLUDED.due_date,
            stop_price = EXCLUDED.stop_price,
            fee = EXCLUDED.fee,
            tax = EXCLUDED.tax;
        """
        params = (code, qty, avg_price, remain_qty, order_id, num_buy, buy_time, due_date, stop_price, fee, tax)
        self.execute_query(query, params)

    # --- order_list 테이블 관련 함수 ---
    def upsert_order_list(self, order_id: str, code: str, order_type: str, qty: int, remain_qty: int,
                          cum_price: int, name: str = None, fee: float = 0.0, tax: float = 0.0,
                          order_time: datetime = None, status: str = None):
        """
        order_list 테이블에 데이터를 삽입하거나, 기존 데이터가 있을 경우 업데이트합니다.
        """
        query = """
        INSERT INTO order_list (order_id, code, name, order_type, qty, remain_qty, cum_price, fee, tax, order_time, status)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (order_id) DO UPDATE
        SET code = EXCLUDED.code,
            name = EXCLUDED.name,
            order_type = EXCLUDED.order_type,
            qty = EXCLUDED.qty,
            remain_qty = EXCLUDED.remain_qty,
            cum_price = EXCLUDED.cum_price,
            fee = EXCLUDED.fee,
            tax = EXCLUDED.tax,
            order_time = EXCLUDED.order_time,
            status = EXCLUDED.status;
        """
        params = (order_id, code, name, order_type, qty, remain_qty, cum_price, fee, tax, order_time, status)
        self.execute_query(query, params)

    # --- trade_history 테이블 관련 함수 ---
    def insert_trade_history(self, code: str, 회사명: str, avg_price: int, qty: int, sell_price: int,
                             buy_price: int, num_buy: int = 1, stop_price: int = 0, profit: int = 0,
                             fee: float = 0.0, tax: float = 0.0, buy_time: datetime = None,
                             due_date: datetime = None, sell_time: datetime = None, order_id: str = None):
        """
        trade_history 테이블에 거래 기록을 삽입합니다.
        """
        query = """
        INSERT INTO trade_history (code, 회사명, avg_price, qty, sell_price, stop_price, num_buy, buy_price, profit, fee, tax, buy_time, due_date, sell_time, order_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s);
        """
        params = (code, 회사명, avg_price, qty, sell_price, stop_price, num_buy, buy_price, profit, fee, tax, buy_time, due_date, sell_time, order_id)
        self.execute_query(query, params)

    # --- 기타 함수 ---
    def fetch_all_stock_codes(self):
        """
        allStockCode 테이블의 모든 데이터를 조회합니다.
        이 테이블은 trade_history의 종목명 조회를 위해 사용됩니다.
        """
        query = "SELECT * FROM allStockCode;"
        return self.execute_query(query)
