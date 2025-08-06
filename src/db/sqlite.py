import sqlite3
from contextlib import contextmanager
import logging
from datetime import datetime
from typing import Optional

class SQLiteClient:
    """
    SQLite 연결 및 CRUD 작업을 위한 클라이언트 클래스.
    """
    def __init__(self, database: str):
        self.database = database
        self.connection = None

    def connect(self):
        """SQLite 데이터베이스에 연결합니다."""
        try:
            self.connection = sqlite3.connect(self.database)
            self.connection.row_factory = sqlite3.Row  # 컬럼명을 키로 사용하는 딕셔너리 형태로 반환
            logging.info(f"SQLite DB '{self.database}'에 성공적으로 연결되었습니다.")
        except sqlite3.Error as e:
            logging.error(f"SQLite DB 연결 오류: {e}")
            raise e

    def disconnect(self):
        """DB 연결을 종료합니다."""
        if self.connection:
            self.connection.close()
            logging.info(f"SQLite DB '{self.database}' 연결이 종료되었습니다.")

    @contextmanager
    def get_cursor(self):
        """SQLite 커서를 context manager 형태로 제공합니다."""
        if self.connection is None:
            self.connect()
        cursor = self.connection.cursor()
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
            cursor.execute(query, params or ())
            try:
                result = cursor.fetchall()
                return result
            except sqlite3.ProgrammingError:
                # SELECT 쿼리가 아니거나 결과가 없는 경우
                return None

    # --- hold_list 테이블 관련 함수 ---
    def upsert_hold_list(self, code: str, qty: int, avg_price: int, remain_qty: int = 0, order_id: Optional[str] = None,
                         num_buy: int = 1, buy_time: Optional[datetime] = None, due_date: Optional[datetime] = None,
                         stop_price: int = 0, fee: float = 0.0, tax: float = 0.0):
        """
        hold_list 테이블에 데이터를 삽입하거나, 기존 데이터가 있을 경우 업데이트합니다.
        """
        query = """
        INSERT INTO hold_list (code, qty, avg_price, remain_qty, order_id, num_buy, buy_time, due_date, stop_price, fee, tax)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(code) DO UPDATE
        SET qty = excluded.qty,
            avg_price = excluded.avg_price,
            remain_qty = excluded.remain_qty,
            order_id = excluded.order_id,
            num_buy = excluded.num_buy,
            buy_time = excluded.buy_time,
            due_date = excluded.due_date,
            stop_price = excluded.stop_price,
            fee = excluded.fee,
            tax = excluded.tax;
        """
        params = (code, qty, avg_price, remain_qty, order_id, num_buy, buy_time, due_date, stop_price, fee, tax)
        self.execute_query(query, params)

    # --- order_list 테이블 관련 함수 ---
    def upsert_order_list(self, order_id: str, code: str, order_type: str, qty: int, remain_qty: int,
                          cum_price: int, name: Optional[str] = None, fee: float = 0.0, tax: float = 0.0,
                          order_time: Optional[datetime] = None, status: Optional[str] = None):
        """
        order_list 테이블에 데이터를 삽입하거나, 기존 데이터가 있을 경우 업데이트합니다.
        """
        query = """
        INSERT INTO order_list (order_id, code, name, order_type, qty, remain_qty, cum_price, fee, tax, order_time, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(order_id) DO UPDATE
        SET code = excluded.code,
            name = excluded.name,
            order_type = excluded.order_type,
            qty = excluded.qty,
            remain_qty = excluded.remain_qty,
            cum_price = excluded.cum_price,
            fee = excluded.fee,
            tax = excluded.tax,
            order_time = excluded.order_time,
            status = excluded.status;
        """
        params = (order_id, code, name, order_type, qty, remain_qty, cum_price, fee, tax, order_time, status)
        self.execute_query(query, params)

    # --- trade_history 테이블 관련 함수 ---
    def insert_trade_history(self, code: str, 회사명: str, avg_price: int, qty: int, sell_price: int,
                             buy_price: int, num_buy: int = 1, stop_price: int = 0, profit: int = 0,
                             fee: float = 0.0, tax: float = 0.0, buy_time: Optional[datetime] = None,
                             due_date: Optional[datetime] = None, sell_time: Optional[datetime] = None, order_id: Optional[str] = None):
        """
        trade_history 테이블에 거래 기록을 삽입합니다.
        """
        query = """
        INSERT INTO trade_history (code, 회사명, avg_price, qty, sell_price, stop_price, num_buy, buy_price, profit, fee, tax, buy_time, due_date, sell_time, order_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
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
