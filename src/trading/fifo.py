from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timezone
from typing import List
from models.trade_entities import Execution, Trade

def _csv(ids: List[str]) -> str:
    return ",".join(ids)

def settle_fifo_on_new_sell(session: Session, account_id: str, ticker: str, market: str) -> List[int]:
    """
    SELL execution이 들어왔을 때, 남은 BUY executions(remaining_qty>0)을 FIFO로 매칭.
    매칭된 분량만큼 trades에 라운드트립 행을 생성.
    반환: 생성된 trade_id 리스트
    """
    created: List[int] = []

    buys = list(session.scalars(
        select(Execution)
        .where(Execution.account_id==account_id,
               Execution.ticker==ticker,
               Execution.side=="BUY",
               Execution.remaining_qty>0)
        .order_by(Execution.exec_time.asc(), Execution.id.asc())
    ))

    sells = list(session.scalars(
        select(Execution)
        .where(Execution.account_id==account_id,
               Execution.ticker==ticker,
               Execution.side=="SELL",
               Execution.remaining_qty>0)
        .order_by(Execution.exec_time.asc(), Execution.id.asc())
    ))

    bi = si = 0
    while bi < len(buys) and si < len(sells):
        b = buys[bi]
        s = sells[si]
        match_qty = float(min(b.remaining_qty, s.remaining_qty))
        if match_qty <= 0:
            break

        b.remaining_qty = float(b.remaining_qty) - match_qty
        s.remaining_qty = float(s.remaining_qty) - match_qty

        qty = match_qty
        buy_value  = qty * float(b.price)
        sell_value = qty * float(s.price)

        # 체결 건별로 내려온 수수료/세금(키움 FID 938/939)을 체결 비율대로 안분
        buy_comm = float(b.commission) * (qty/float(b.qty)) if float(b.qty) > 0 else 0.0
        sell_comm = float(s.commission) * (qty/float(s.qty)) if float(s.qty) > 0 else 0.0
        sell_tax  = float(s.tax)        * (qty/float(s.qty)) if float(s.qty) > 0 else 0.0

        pnl_gross = sell_value - buy_value
        pnl_net   = pnl_gross - (buy_comm + sell_comm + sell_tax)
        pnl_pct   = (pnl_net / buy_value) if buy_value else 0.0

        opened_at = b.exec_time
        closed_at = s.exec_time
        holding_seconds = int((closed_at - opened_at).total_seconds()) if (opened_at and closed_at) else 0

        trade = Trade(
            account_id=account_id, ticker=ticker, market=market,
            qty=qty, buy_avg_price=float(b.price), sell_avg_price=float(s.price),
            buy_value=buy_value, sell_value=sell_value,
            buy_commission=buy_comm, sell_commission=sell_comm, sell_tax=sell_tax,
            pnl_gross=pnl_gross, pnl_net=pnl_net, pnl_net_pct=pnl_pct,
            buy_exec_ids=_csv([b.exec_id]), sell_exec_ids=_csv([s.exec_id]),
            opened_at=opened_at, closed_at=closed_at, holding_seconds=holding_seconds,
        )
        session.add(trade)
        session.flush()
        created.append(trade.trade_id)

        if float(b.remaining_qty) <= 5e-7: bi += 1
        if float(s.remaining_qty) <= 5e-7: si += 1

    session.commit()
    return created
