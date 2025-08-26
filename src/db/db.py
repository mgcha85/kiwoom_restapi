# db.py
import os
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Tuple

from sqlalchemy import create_engine, select, update
from sqlalchemy.orm import sessionmaker

# 내부적으로만 엔티티를 참조하고, 외부 모듈에는 노출하지 않음
from src.models.trade_entities import Base, Order, Execution, Trade

# ---------------------------------------------------------------------
# 기본 세팅
# ---------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./trade_test.db")

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True
)

def init_db() -> None:
    """테이블 생성"""
    Base.metadata.create_all(bind=engine)

@contextmanager
def get_session():
    """세션 컨텍스트 매니저"""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

# ---------------------------------------------------------------------
# 유틸
# ---------------------------------------------------------------------
def _now_tz():
    from datetime import datetime, timezone
    return datetime.now()

def _D(x) -> Decimal:
    from decimal import Decimal
    if isinstance(x, Decimal):
        return x
    return Decimal(str(x))


def _q_round(x: Decimal, q: str = "0.01") -> Decimal:
    """금액류 반올림(소수점 2자리 기본)"""
    return x.quantize(Decimal(q), rounding=ROUND_HALF_UP)

# ---------------------------------------------------------------------
# ORDERS: 생성/조회/상태갱신
# ---------------------------------------------------------------------
def create_order(
    *,
    order_no: str,
    account_id: str,
    ticker: str,
    side: str,           # "BUY" / "SELL"
    qty: float,
    price: float,
    status: str = "PLACED",
    placed_at: Optional[datetime] = None
) -> int:
    """주문 생성 후 PK(id) 반환"""
    if placed_at is None:
        placed_at = _now_tz()

    with get_session() as s:
        o = Order(
            order_no=order_no,
            account_id=account_id,
            ticker=ticker,
            side=side,
            qty=_D(qty),
            price=_D(price),
            status=status,
            placed_at=placed_at,
            updated_at=placed_at
        )
        s.add(o)
        s.flush()
        return o.id

def update_order_status(
    *,
    order_no: str,
    status: str
) -> None:
    """주문 상태 갱신"""
    with get_session() as s:
        s.execute(
            update(Order)
            .where(Order.order_no == order_no)
            .values(status=status, updated_at=_now_tz())
        )

def get_order_by_no(order_no: str) -> Optional[Order]:
    """주문 단건 조회 (읽기 전용 용도)"""
    with get_session() as s:
        stmt = select(Order).where(Order.order_no == order_no)
        return s.execute(stmt).scalars().first()

def list_orders_by_status(status: str) -> List[Order]:
    with get_session() as s:
        stmt = select(Order).where(Order.status == status)
        return list(s.execute(stmt).scalars().all())

# ---------------------------------------------------------------------
# FIFO 매칭 & Trade 생성
# ---------------------------------------------------------------------

def _fetch_open_buy_executions(session, account_id: str, ticker: str) -> List[Execution]:
    stmt = (
        select(Execution)
        .where(
            Execution.account_id == account_id,
            Execution.ticker == ticker,
            Execution.side == "BUY",
            Execution.remaining_qty > 0
        )
        .order_by(Execution.exec_time.asc(), Execution.id.asc())
    )
    return list(session.execute(stmt).scalars().all())

def _fifo_match_and_create_trades(session, sell_exec: Execution) -> List[int]:
    """SELL 체결을 기존 BUY 체결들과 FIFO 매칭하여 Trade 생성. 생성된 trade_id 목록 반환."""
    created_trade_ids: List[int] = []
    sell_qty_to_match = _D(sell_exec.qty)
    sell_price = _D(sell_exec.price)

    if sell_qty_to_match <= 0:
        return created_trade_ids

    open_buys = _fetch_open_buy_executions(session, sell_exec.account_id, sell_exec.ticker)
    if not open_buys:
        return created_trade_ids

    from decimal import ROUND_HALF_UP
    def q2(x: Decimal) -> Decimal:
        return x.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    for buy_ex in open_buys:
        if sell_qty_to_match <= 0:
            break

        available = _D(buy_ex.remaining_qty)
        if available <= 0:
            continue

        use_qty = sell_qty_to_match if sell_qty_to_match <= available else available

        buy_price = _D(buy_ex.price)
        # 비례 분배
        buy_commission_part = (_D(buy_ex.commission) * (use_qty / _D(buy_ex.qty))) if _D(buy_ex.qty) > 0 else _D(0)
        sell_commission_part = (_D(sell_exec.commission) * (use_qty / _D(sell_exec.qty))) if _D(sell_exec.qty) > 0 else _D(0)
        sell_tax_part = (_D(sell_exec.tax) * (use_qty / _D(sell_exec.qty))) if _D(sell_exec.qty) > 0 else _D(0)

        buy_value = _D(use_qty) * buy_price
        sell_value = _D(use_qty) * sell_price

        pnl_gross = sell_value - buy_value
        pnl_net = pnl_gross - (buy_commission_part + sell_commission_part + sell_tax_part)
        pnl_net_pct = (pnl_net / buy_value) if buy_value > 0 else _D(0)

        opened_at = buy_ex.exec_time
        closed_at = sell_exec.exec_time

        print(opened_at)
        print(closed_at)
        
        holding_seconds = int((closed_at - opened_at).total_seconds()) if opened_at and closed_at else 0

        trade = Trade(
            account_id=sell_exec.account_id,
            ticker=sell_exec.ticker,
            market=sell_exec.market,
            broker_code="KIWOOM",
            qty=_D(use_qty),
            buy_avg_price=_D(buy_price),
            sell_avg_price=_D(sell_price),
            buy_value=q2(buy_value),
            sell_value=q2(sell_value),
            buy_commission=q2(buy_commission_part),
            sell_commission=q2(sell_commission_part),
            sell_tax=q2(sell_tax_part),
            pnl_gross=q2(pnl_gross),
            pnl_net=q2(pnl_net),
            pnl_net_pct=pnl_net_pct.quantize(Decimal("0.000001"), rounding=ROUND_HALF_UP),
            buy_exec_ids=str(buy_ex.exec_id),
            sell_exec_ids=str(sell_exec.exec_id),
            opened_at=opened_at,
            closed_at=closed_at,
            holding_seconds=holding_seconds
        )
        session.add(trade)
        session.flush()              # trade_id 확보
        created_trade_ids.append(trade.trade_id)

        # BUY 남은 수량 차감
        buy_ex.remaining_qty = _D(available) - _D(use_qty)
        session.add(buy_ex)

        sell_qty_to_match -= _D(use_qty)

    return created_trade_ids

def record_buy_execution(
    *,
    exec_id: str,
    order_no: str,
    account_id: str,
    ticker: str,
    market: str,
    qty: float,
    price: float,
    commission: float = 0.0,
    exec_time: Optional[datetime] = None
) -> int:
    """매수 체결 기록: executions에 남기고 remaining_qty 설정. orders.status=FILLED 갱신."""
    if exec_time is None:
        exec_time = _now_tz()

    with get_session() as s:
        e = Execution(
            exec_id=exec_id,
            order_no=order_no,
            account_id=account_id,
            ticker=ticker,
            market=market,
            side="BUY",
            qty=_D(qty),
            price=_D(price),
            commission=_D(commission),
            tax=_D(0),
            exec_time=exec_time,
            remaining_qty=_D(qty)
        )
        s.add(e)
        s.flush()

        # 주문 상태 FILLED
        s.execute(
            update(Order)
            .where(Order.order_no == order_no)
            .values(status="FILLED", updated_at=_now_tz())
        )
        return e.id


def record_sell_execution(
    *,
    exec_id: str,
    order_no: str,
    account_id: str,
    ticker: str,
    market: str,
    qty: float,
    price: float,
    commission: float = 0.0,
    tax: float = 0.0,
    exec_time: Optional[datetime] = None
) -> Tuple[int, List[int]]:
    """
    매도 체결 기록: executions에 남기고 → FIFO 매칭으로 trades 생성.
    반환: (execution_id, created_trade_ids)
    """
    if exec_time is None:
        exec_time = _now_tz()

    with get_session() as s:
        e = Execution(
            exec_id=exec_id,
            order_no=order_no,
            account_id=account_id,
            ticker=ticker,
            market=market,
            side="SELL",
            qty=_D(qty),
            price=_D(price),
            commission=_D(commission),
            tax=_D(tax),
            exec_time=exec_time,
            remaining_qty=_D(0)
        )
        s.add(e)
        s.flush()
        exec_pk = e.id

        # 주문 상태 FILLED
        s.execute(
            update(Order)
            .where(Order.order_no == order_no)
            .values(status="FILLED", updated_at=_now_tz())
        )

        # FIFO 매칭 → trades 생성
        trade_ids = _fifo_match_and_create_trades(s, sell_exec=e)
        return exec_pk, trade_ids


def record_execution(
    *,
    exec_id: str,
    order_no: str,
    account_id: str,
    ticker: str,
    market: str,
    side: str,           # "BUY" or "SELL"
    qty: float,
    price: float,
    commission: float = 0.0,
    tax: float = 0.0,
    exec_time: Optional[datetime] = None
):
    """
    공용 엔트리: side에 따라 매수/매도 경로 분기.
    - BUY  → executions (remaining_qty 설정)
    - SELL → executions → trades (FIFO)
    """
    side_u = (side or "").upper()
    if side_u == "BUY":
        return record_buy_execution(
            exec_id=exec_id,
            order_no=order_no,
            account_id=account_id,
            ticker=ticker,
            market=market,
            qty=qty,
            price=price,
            commission=commission,
            exec_time=exec_time
        )
    elif side_u == "SELL":
        return record_sell_execution(
            exec_id=exec_id,
            order_no=order_no,
            account_id=account_id,
            ticker=ticker,
            market=market,
            qty=qty,
            price=price,
            commission=commission,
            tax=tax,
            exec_time=exec_time
        )
    else:
        raise ValueError(f"Unsupported side: {side}")

# ---------------------------------------------------------------------
# 포지션/체결 헬퍼
# ---------------------------------------------------------------------
def get_open_position_qty(account_id: str, ticker: str) -> Decimal:
    """
    현재 보유 수량(= BUY 체결의 remaining_qty 합) 반환.
    """
    with get_session() as s:
        buys = _fetch_open_buy_executions(s, account_id, ticker)
        total = sum((_D(b.remaining_qty) for b in buys), _D("0"))
        return total

def list_executions(
    *,
    account_id: Optional[str] = None,
    ticker: Optional[str] = None,
    side: Optional[str] = None
) -> List[Execution]:
    with get_session() as s:
        stmt = select(Execution)
        if account_id:
            stmt = stmt.where(Execution.account_id == account_id)
        if ticker:
            stmt = stmt.where(Execution.ticker == ticker)
        if side:
            stmt = stmt.where(Execution.side == side)
        return list(s.execute(stmt).scalars().all())

def list_trades(
    *,
    account_id: Optional[str] = None,
    ticker: Optional[str] = None,
    start: Optional[datetime] = None,
    end: Optional[datetime] = None
) -> List[Trade]:
    with get_session() as s:
        stmt = select(Trade)
        if account_id:
            stmt = stmt.where(Trade.account_id == account_id)
        if ticker:
            stmt = stmt.where(Trade.ticker == ticker)
        if start:
            stmt = stmt.where(Trade.closed_at >= start)
        if end:
            stmt = stmt.where(Trade.closed_at < end)
        return list(s.execute(stmt).scalars().all())

# ---------------------------------------------------------------------
# 샘플 워크플로우 헬퍼 (테스트 편의)
# ---------------------------------------------------------------------
def upsert_order_and_fill_buy_execution(
    *,
    order_no: str,
    account_id: str,
    ticker: str,
    price: float,
    qty: float,
    market: str = "KRX",
    commission: float = 0.0,
    exec_id: Optional[str] = None,
    placed_at: Optional[datetime] = None,
    exec_time: Optional[datetime] = None
) -> Tuple[int, int]:
    """
    단건 매수 주문 → 체결 까지 한번에 넣는 편의 함수.
    반환: (order_id, execution_id)
    """
    if exec_id is None:
        exec_id = order_no

    order_id = create_order(
        order_no=order_no,
        account_id=account_id,
        ticker=ticker,
        side="BUY",
        qty=qty,
        price=price,
        status="PLACED",
        placed_at=placed_at
    )
    exec_pk = record_execution(
        exec_id=exec_id,
        order_no=order_no,
        account_id=account_id,
        ticker=ticker,
        market=market,
        side="BUY",
        qty=qty,
        price=price,
        commission=commission,
        tax=0.0,
        exec_time=exec_time
    )
    return order_id, exec_pk

def upsert_order_and_fill_sell_execution(
    *,
    order_no: str,
    account_id: str,
    ticker: str,
    price: float,
    qty: float,
    market: str = "KRX",
    commission: float = 0.0,
    tax: float = 0.0,
    exec_id: Optional[str] = None,
    placed_at: Optional[datetime] = None,
    exec_time: Optional[datetime] = None
) -> Tuple[int, int]:
    """
    단건 매도 주문 → 체결 까지 한번에 넣는 편의 함수.
    (SELL 체결 시 내부에서 FIFO 매칭되어 Trade 생성됨)
    반환: (order_id, execution_id)
    """
    if exec_id is None:
        exec_id = f"SELL-{order_no}"

    order_id = create_order(
        order_no=order_no,
        account_id=account_id,
        ticker=ticker,
        side="SELL",
        qty=qty,
        price=price,
        status="PLACED",
        placed_at=placed_at
    )
    exec_pk = record_execution(
        exec_id=exec_id,
        order_no=order_no,
        account_id=account_id,
        ticker=ticker,
        market=market,
        side="SELL",
        qty=qty,
        price=price,
        commission=commission,
        tax=tax,
        exec_time=exec_time
    )
    return order_id, exec_pk
