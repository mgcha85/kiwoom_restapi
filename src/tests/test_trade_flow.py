import os
import time
from datetime import datetime, timezone, timedelta
import pytest

# 프로젝트 경로 추가
import sys, pathlib
project_root = pathlib.Path("C:/Users/woori/Documents/PythonProjects/kiwoom_restapi")
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from api.order import OrderAPI
from db.db import SessionLocal
from sqlalchemy import select, text
from sqlalchemy import inspect as sa_inspect

# ORM 엔티티
from models.trade_entities import Trade
from models.trade_entities import Order as OrderRow
from models.trade_entities import Execution as ExecRow

# (선택) positions 테이블이 ORM에 없다면 간단히 로컬 모델 선언 (조회 전용)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Numeric, TIMESTAMP, Integer

class _Base(DeclarativeBase):
    pass

class PositionRow(_Base):
    __tablename__ = "positions"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(32))
    ticker: Mapped[str] = mapped_column(String(16))
    qty: Mapped[float] = mapped_column(Numeric(18,6))
    avg_price: Mapped[float] = mapped_column(Numeric(18,6))
    updated_at: Mapped[datetime] = mapped_column(TIMESTAMP(timezone=True))

# --------- 환경 변수 (실/모의 구동 시 필수) ----------
RUN_LIVE = os.getenv("RUN_LIVE_KIWOOM_TESTS") == "1"
ACCOUNT_ID = os.getenv("ACC_ID", "")  # 예: "ACC1"
TICKER = os.getenv("KIWOOM_TICKER", "005930")    # 기본 삼성전자
MARKET = os.getenv("KIWOOM_MARKET", "KOSPI")
EXPIRE_SEC = int(os.getenv("KIWOOM_TEST_TIMEOUT", "180"))   # 단계별 타임아웃(초, 약간 여유)

# ---- 주문 페이로드 (REST 문서 kt10000 예제에 맞춤: 시장가 trde_tp=3, ord_uv="")
def make_buy_payload():
    return {
        "dmst_stex_tp": "KRX",
        "stk_cd": TICKER,
        "ord_qty": "1",
        "ord_uv": "",      # 시장가이므로 빈 문자열
        "trde_tp": "3",    # 시장가
        "cond_uv": ""
    }

def make_sell_payload():
    return {
        "dmst_stex_tp": "KRX",
        "stk_cd": TICKER,
        "ord_qty": "1",
        "ord_uv": "",      # 시장가이므로 빈 문자열
        "trde_tp": "3",    # 시장가
        "cond_uv": ""
    }

# --------- 헬퍼 ---------
def _wait_for(cond_fn, timeout_sec=EXPIRE_SEC, interval=1.0, desc="condition"):
    start = time.time()
    while time.time() - start < timeout_sec:
        if cond_fn():
            return True
        time.sleep(interval)
    pytest.fail(f"Timeout waiting for: {desc}")

def _read_token():
    token_path = project_root / "access_token.txt"
    with open(token_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def _extract_order_no(resp):
    """
    REST 문서 응답 예:
    {
      "ord_no": "00024",
      "return_code": 0,
      "return_msg": "정상적으로 처리되었습니다"
    }
    """
    if not resp:
        return None
    if isinstance(resp, dict):
        # 최우선: 문서 기준 키
        if "ord_no" in resp:
            return resp["ord_no"]
        # 혹시 다른 래핑 구조를 대비
        for container in ("output", "result", "data"):
            if container in resp and isinstance(resp[container], dict) and "ord_no" in resp[container]:
                return resp[container]["ord_no"]
        # 과거 키들 방어
        for k in ("order_no", "ord_no", "ODNO", "odno"):
            if k in resp:
                return resp[k]
    return None

def _positions_table_exists(session):
    inspector = sa_inspect(session.bind)
    return "positions" in inspector.get_table_names()

# --------- 테스트 시작 ---------

@pytest.mark.skipif(not RUN_LIVE, reason="LIVE/모의 실환경 통합 테스트는 RUN_LIVE_KIWOOM_TESTS=1 일 때만 실행")
def test_buy_positions_sell_trades_flow():
    """
    시나리오:
    1) BUY 1주 (시장가) 주문 → orders에 저장 확인
    2) BUY 체결되면 positions 반영 확인 (positions 테이블이 있으면)
    3) SELL 1주 (시장가) 주문 → orders에 저장 확인
    4) SELL 체결되면 trades 생성 확인
    * 전제: ws_consumer가 REG(REAL/00) 구독 상태로 실행 중
    """
    assert ACCOUNT_ID, "환경변수 ACC_ID 가 필요합니다."
    order_api = OrderAPI(use_mock=True)

    # ----- 1) BUY 주문 -----
    buy_resp = order_api.stock_buy_order(token=_read_token(), order_data=make_buy_payload())
    buy_order_no = _extract_order_no(buy_resp)
    assert buy_order_no, f"BUY 응답에서 주문번호(ord_no)를 찾지 못했습니다: {buy_resp}"

    with SessionLocal() as s:
        def _order_in_db():
            row = s.execute(select(OrderRow).where(OrderRow.order_no == buy_order_no)).scalar_one_or_none()
            return row is not None
        _wait_for(_order_in_db, desc="orders에 BUY 주문행 존재")

        # ----- 2) BUY 체결 → positions 반영 확인 (positions 테이블 있을 때만) -----
        def _buy_filled_and_positioned():
            # (a) executions에 BUY 체결 존재?
            ex = s.execute(
                select(ExecRow).where(
                    ExecRow.order_no == buy_order_no,
                    ExecRow.side == "BUY"
                )
            ).first()
            if not ex:
                return False

            # (b) positions 테이블 없으면 이 단계는 패스
            if not _positions_table_exists(s):
                return True

            # (c) positions 수량 반영?
            pos = s.execute(
                select(PositionRow).where(
                    PositionRow.account_id == ACCOUNT_ID,
                    PositionRow.ticker == TICKER
                )
            ).scalar_one_or_none()
            if not pos:
                return False
            return float(pos.qty) >= 1.0

        _wait_for(_buy_filled_and_positioned, desc="BUY 체결 및 positions 수량 ≥ 1 (테이블 있으면)")

    # ----- 3) SELL 주문 -----
    sell_resp = order_api.stock_sell_order(token=_read_token(), order_data=make_sell_payload())
    sell_order_no = _extract_order_no(sell_resp)
    assert sell_order_no, f"SELL 응답에서 주문번호(ord_no)를 찾지 못했습니다: {sell_resp}"

    with SessionLocal() as s:
        def _sell_order_in_db():
            row = s.execute(select(OrderRow).where(OrderRow.order_no == sell_order_no)).scalar_one_or_none()
            return row is not None
        _wait_for(_sell_order_in_db, desc="orders에 SELL 주문행 존재")

        # ----- 4) SELL 체결 → trades 생성 확인 -----
        def _trade_created_after_sell():
            tr = s.execute(
                select(Trade).where(
                    Trade.account_id == ACCOUNT_ID,
                    Trade.ticker == TICKER
                ).order_by(Trade.trade_id.desc())
            ).scalar_one_or_none()
            if not tr:
                return False
            if float(tr.qty) < 1.0:
                return False
            if tr.closed_at and (datetime.now() - tr.closed_at) > timedelta(hours=2):
                return False
            return True

        _wait_for(_trade_created_after_sell, desc="SELL 체결 후 trades 생성")

    print("✅ BUY(시장가)/positions(옵션)/SELL(시장가)/trades 플로우 통과")
