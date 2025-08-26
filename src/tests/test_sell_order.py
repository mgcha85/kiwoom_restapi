# src/tests/test_sell_order.py
import os
import sys
from decimal import Decimal
from datetime import datetime, timezone

# 프로젝트 루트 경로 세팅
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from src.api.order import OrderAPI
from src.db import (
    init_db,
    create_order,
)

# ---- 설정값 ----
ACCOUNT_ID = os.getenv("ACC_ID", "ACC1")
DMST_STEX_TP = os.getenv("DMST_STEX_TP", "KRX")     # KRX / NXT / SOR

SELL_TICKER = "005930"
SELL_QTY = "4"
TRADE_TYPE = "3"
SELL_PRICE = "70500"

# 토큰 파일에서 로드
with open("access_token.txt", "r", encoding="utf-8") as f:
    ACCESS_TOKEN = f.read().strip()


def place_sell_order(token: str, order_data: dict) -> dict:
    api = OrderAPI()
    # OrderAPI.stock_sell_order 를 이용 (BaseAPIClient 기반, requests 직접 사용 X)
    return api.stock_sell_order(token=token, order_data=order_data)


def main():
    # DB 초기화
    init_db()

    # 1) 매도 주문 데이터 준비
    order_data = {
        "dmst_stex_tp": DMST_STEX_TP,  # 국내거래소구분
        "stk_cd": SELL_TICKER,         # 종목코드
        "ord_qty": SELL_QTY,           # 주문수량(문자열)
        "ord_uv": SELL_PRICE,          # 시장가면 빈 문자열
        "trde_tp": TRADE_TYPE,         # 3: 시장가, 0: 보통(지정가)
        "cond_uv": "",
    }

    # 2) 매도 주문 발주
    sell_resp = place_sell_order(ACCESS_TOKEN, order_data)
    print("매도 주문 응답:", sell_resp)

    # 3) 응답 검증
    if not isinstance(sell_resp, dict):
        raise RuntimeError(f"Unexpected response: {sell_resp}")

    rc = sell_resp.get("return_code")
    if rc != 0:
        msg = sell_resp.get("return_msg", "Unknown error")
        raise RuntimeError(f"Sell order failed (code={rc}): {msg}")

    # 4) DB orders 테이블에 기록 (SELL/PLACED)
    order_no = str(sell_resp.get("ord_no"))
    ticker = order_data["stk_cd"]
    qty = Decimal(order_data["ord_qty"])

    # 지정가면 SELL_PRICE 사용, 시장가면 0으로 기록(체결가는 execution에서 기록/정산)
    price = Decimal(order_data["ord_uv"] or "0")

    order_id = create_order(
        order_no=order_no,
        account_id=ACCOUNT_ID,
        ticker=ticker,
        side="SELL",
        qty=qty,
        price=price,
        status="PLACED",
        placed_at=datetime.now(),
    )

    print(f"[OK] SELL order saved: id={order_id}, order_no={order_no}")
    print("※ 체결되면 execution_watcher 가 executions/trades를 자동 반영합니다.")


if __name__ == "__main__":
    main()
