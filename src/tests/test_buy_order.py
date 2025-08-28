import os
import sys
import json
from decimal import Decimal
from datetime import datetime, timezone

# 프로젝트 루트 경로 세팅
import os as _os
project_root = _os.path.abspath(_os.path.join(_os.path.dirname(__file__), '..', '..'))
src_path = _os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from api.order import OrderAPI
from db import (
    init_db,
    create_order,
    upsert_order_and_fill_buy_execution,
    update_order_status,   # 상태만 바꾸고 싶을 때 사용 가능
)

init_db()

# 토큰을 파일에서 읽어옵니다.
with open("access_token.txt", "r") as f:
    token = f.read().strip()

ACCOUNT_ID = os.getenv("KIWOOM_ACCOUNT_ID", "ACC1")
BUY_COMMISSION_RATE = Decimal(os.getenv("BUY_COMMISSION_RATE", "0.00015"))  # 0.015% 예시


def calc_buy_commission(qty: Decimal, price: Decimal) -> Decimal:
    # 간단 수수료: 약정금액 * 수수료율
    notional = qty * price
    fee = notional * BUY_COMMISSION_RATE
    # 소수 2자리 반올림
    return fee.quantize(Decimal("0.01"))

def place_buy_order(token, order_data):
    order_api = OrderAPI()
    response = order_api.stock_buy_order(token=token, order_data=order_data)
    return response


def main():
    # DB 초기화 (최초 1회)
    init_db()

    # 예시 주문 데이터
    order_data = {
        "dmst_stex_tp": "KRX",
        "stk_cd": "005930",   # 삼성전자
        "ord_qty": "4",
        "ord_uv": "71000",    # 지정가 70,000
        "trde_tp": "0",       # 보통
        "cond_uv": ""
    }

    buy_response = place_buy_order(token, order_data)
    print("매수 주문 응답:", buy_response)

    # 응답 검증
    if not isinstance(buy_response, dict):
        raise RuntimeError(f"Unexpected response: {buy_response}")

    rc = buy_response.get("return_code")
    if rc != 0:
        # 실패시 예외
        msg = buy_response.get("return_msg", "Unknown error")
        raise RuntimeError(f"Buy order failed (code={rc}): {msg}")

    # 응답에서 주문번호 등 추출
    order_no = str(buy_response.get("ord_no"))
    ticker   = str(order_data["stk_cd"])

    # 수량/가격은 요청값 기준(문자열→Decimal)
    qty   = Decimal(order_data["ord_qty"])
    price = Decimal(order_data["ord_uv"])

    placed_at = datetime.now()
    order_id = create_order(
        order_no=order_no,
        account_id=ACCOUNT_ID,
        ticker=ticker,
        side="BUY",
        qty=qty,
        price=price,
        status="PLACED",
        placed_at=placed_at
    )
    # 필요시 상태만 별도 갱신하고 싶다면 (기본적으로 record_execution에서 FILLED로 업데이트함)
    # update_order_status(order_no=order_no, status="FILLED")

    print(f"[OK] order saved: id={order_id}, buy_exec_id={order_no}")


if __name__ == "__main__":
    main()