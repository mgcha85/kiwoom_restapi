# src/db/hold_sqlite.py
import os
import sqlite3
from decimal import Decimal, ROUND_HALF_UP
from datetime import datetime
from typing import Optional, Dict, Any
import pandas as pd

from config import config

DB_PATH = getattr(config.db, "sqlite_path", "./data/trading.sqlite3")

def _get_conn():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_hold_table():
    sql = """
    CREATE TABLE IF NOT EXISTS hold_list (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        account_id TEXT NOT NULL,
        ticker TEXT NOT NULL,
        market TEXT DEFAULT 'KRX',
        name TEXT,
        qty NUMERIC DEFAULT 0,
        remain_qty NUMERIC DEFAULT 0,
        buy_avg_price NUMERIC DEFAULT 0,
        n_trade INTEGER DEFAULT 0,
        buy_time TIMESTAMP,
        last_buy_time TIMESTAMP,
        due_date TIMESTAMP,
        target_price NUMERIC DEFAULT 0,
        stop_price NUMERIC DEFAULT 0,
        fee_accum NUMERIC DEFAULT 0,
        tax_accum NUMERIC DEFAULT 0,
        last_order_id TEXT,
        updated_at TIMESTAMP,
        UNIQUE(account_id, ticker)
    );
    """
    with _get_conn() as conn:
        conn.execute(sql)
        conn.commit()

def _dec(x) -> Decimal:
    if isinstance(x, Decimal):
        return x
    try:
        return Decimal(str(x))
    except Exception:
        return Decimal("0")

def _round_px(x: Decimal, q="0.01") -> Decimal:
    return x.quantize(Decimal(q), rounding=ROUND_HALF_UP)

def get_hold(account_id: str, ticker: str) -> Optional[sqlite3.Row]:
    with _get_conn() as conn:
        cur = conn.execute(
            "SELECT * FROM hold_list WHERE account_id=? AND ticker=?",
            (account_id, ticker)
        )
        return cur.fetchone()

def get_hold_list() -> pd.DataFrame:
    with _get_conn() as conn:
        query = "SELECT * FROM hold_list WHERE order_id IS NOT NULL"
        df = pd.read_sql(query, con=conn)
        if not df.empty and "code" in df.columns:
            df = df.set_index("code")
        return df

def upsert_hold_after_buy(
    *,
    account_id: str,
    ticker: str,
    market: str,
    exec_qty: Decimal,
    exec_price: Decimal,
    commission: Decimal,
    tax: Decimal,
    now_ts: datetime,
    # 정책값: 분할 최대 횟수, 목표/손절 퍼센트
    max_splits: int = 4,
    target_pct: Decimal = Decimal("0.10"),
    stop_pct: Decimal = Decimal("-0.10"),
    last_order_id: Optional[str] = None,
):
    row = get_hold(account_id, ticker)
    with _get_conn() as conn:
        if row is None:
            qty = exec_qty
            avg = exec_price
            n_trade = 1
            target = _round_px(avg * (Decimal("1") + target_pct))
            stop   = _round_px(avg * (Decimal("1") + stop_pct))
            conn.execute(
                """
                INSERT INTO hold_list
                (account_id, ticker, market, qty, remain_qty, buy_avg_price, n_trade,
                 buy_time, last_buy_time, target_price, stop_price,
                 fee_accum, tax_accum, last_order_id, updated_at)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    account_id, ticker, market,
                    str(qty), str(qty), str(avg), n_trade,
                    now_ts, now_ts, str(target), str(stop),
                    str(commission), str(tax), last_order_id, now_ts
                )
            )
        else:
            old_qty = _dec(row["qty"])
            new_qty = old_qty + exec_qty
            if new_qty > 0:
                new_avg = (_dec(row["buy_avg_price"]) * old_qty + exec_price * exec_qty) / new_qty
            else:
                new_avg = Decimal("0")
            new_avg = new_avg.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP)
            new_n   = min(int(row["n_trade"]) + 1, max_splits)
            new_fee = _dec(row["fee_accum"]) + commission
            new_tax = _dec(row["tax_accum"]) + tax
            # 평단 기반 목표/손절 재계산
            target = _round_px(new_avg * (Decimal("1") + target_pct))
            stop   = _round_px(new_avg * (Decimal("1") + stop_pct))

            conn.execute(
                """
                UPDATE hold_list
                SET qty=?, remain_qty=?, buy_avg_price=?, n_trade=?,
                    last_buy_time=?, target_price=?, stop_price=?,
                    fee_accum=?, tax_accum=?, last_order_id=?, updated_at=?
                WHERE account_id=? AND ticker=?
                """,
                (
                    str(new_qty), str(new_qty), str(new_avg), new_n,
                    now_ts, str(target), str(stop),
                    str(new_fee), str(new_tax), last_order_id, now_ts,
                    account_id, ticker
                )
            )
        conn.commit()

def apply_sell_to_hold(
    *,
    account_id: str,
    ticker: str,
    exec_qty: Decimal,
    commission: Decimal,
    tax: Decimal,
    now_ts: datetime,
):
    row = get_hold(account_id, ticker)
    if row is None:
        return
    old_qty = _dec(row["qty"])
    old_rem = _dec(row["remain_qty"])
    new_qty = max(old_qty - exec_qty, Decimal("0"))
    new_rem = max(old_rem - exec_qty, Decimal("0"))
    new_fee = _dec(row["fee_accum"]) + commission
    new_tax = _dec(row["tax_accum"]) + tax

    with _get_conn() as conn:
        conn.execute(
            """
            UPDATE hold_list
            SET qty=?, remain_qty=?, fee_accum=?, tax_accum=?, updated_at=?
            WHERE account_id=? AND ticker=?
            """,
            (str(new_qty), str(new_rem), str(new_fee), str(new_tax), now_ts, account_id, ticker)
        )
        conn.commit()
