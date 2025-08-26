from typing import Optional
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer, Numeric, TIMESTAMP, Text

# Declarative Base (SQLAlchemy 2.x)
# https://docs.sqlalchemy.org/en/latest/orm/declarative_tables.html
class Base(DeclarativeBase):
    pass

class Order(Base):
    __tablename__ = "orders"
    id: Mapped[int] = mapped_column(primary_key=True)
    order_no: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    account_id: Mapped[str] = mapped_column(String(32))
    ticker: Mapped[str] = mapped_column(String(16))
    side: Mapped[str] = mapped_column(String(5))  # BUY / SELL
    qty: Mapped[float] = mapped_column(Numeric(18,6))
    price: Mapped[float] = mapped_column(Numeric(18,6))
    status: Mapped[str] = mapped_column(String(32))
    placed_at: Mapped[Optional[str]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    updated_at: Mapped[Optional[str]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)

class Execution(Base):
    __tablename__ = "executions"
    id: Mapped[int] = mapped_column(primary_key=True)
    exec_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    order_no: Mapped[str] = mapped_column(String(64), index=True)
    account_id: Mapped[str] = mapped_column(String(32))
    ticker: Mapped[str] = mapped_column(String(16))
    market: Mapped[str] = mapped_column(String(16))
    side: Mapped[str] = mapped_column(String(5))  # BUY / SELL
    qty: Mapped[float] = mapped_column(Numeric(18,6))
    price: Mapped[float] = mapped_column(Numeric(18,6))
    commission: Mapped[float] = mapped_column(Numeric(18,2), default=0)  # (키움 FID 938)
    tax: Mapped[float] = mapped_column(Numeric(18,2), default=0)         # (키움 FID 939, SELL시)
    exec_time: Mapped[Optional[str]] = mapped_column(TIMESTAMP(timezone=True), nullable=True)
    # FIFO 매칭용 남은 수량
    remaining_qty: Mapped[float] = mapped_column(Numeric(18,6))

class Trade(Base):
    __tablename__ = "trades"
    trade_id: Mapped[int] = mapped_column(primary_key=True)

    account_id: Mapped[str] = mapped_column(String(32))
    ticker: Mapped[str] = mapped_column(String(16))
    market: Mapped[str] = mapped_column(String(16))
    broker_code: Mapped[str] = mapped_column(String(16), default="KIWOOM")

    qty: Mapped[float] = mapped_column(Numeric(18,6))
    buy_avg_price: Mapped[float] = mapped_column(Numeric(18,6))
    sell_avg_price: Mapped[float] = mapped_column(Numeric(18,6))
    buy_value: Mapped[float] = mapped_column(Numeric(18,2))
    sell_value: Mapped[float] = mapped_column(Numeric(18,2))

    buy_commission: Mapped[float] = mapped_column(Numeric(18,2), default=0)
    sell_commission: Mapped[float] = mapped_column(Numeric(18,2), default=0)
    sell_tax: Mapped[float] = mapped_column(Numeric(18,2), default=0)

    pnl_gross: Mapped[float] = mapped_column(Numeric(18,2))
    pnl_net: Mapped[float] = mapped_column(Numeric(18,2))
    pnl_net_pct: Mapped[float] = mapped_column(Numeric(18,6))

    # 간단히 CSV 문자열로 저장 (원하면 관계 테이블로 정규화 가능)
    buy_exec_ids: Mapped[str] = mapped_column(Text)
    sell_exec_ids: Mapped[str] = mapped_column(Text)

    opened_at: Mapped[Optional[str]] = mapped_column(TIMESTAMP(timezone=True))
    closed_at: Mapped[Optional[str]] = mapped_column(TIMESTAMP(timezone=True))
    holding_seconds: Mapped[int] = mapped_column(Integer)
