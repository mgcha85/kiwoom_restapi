import unittest
from src.api.order import OrderAPI

def place_sell_order(token, order_data):
    order_api = OrderAPI()
    response = order_api.stock_buy_order(token=token, order_data=order_data)
    return response

order_data = {
    "dmst_stex_tp": "KRX",
    "stk_cd": "005930",
    "ord_qty": "10",
    "ord_uv": "75000",  # 예: 75,000원
    "trde_tp": "1",     # 시장가
    "cond_uv": ""
}
sell_response = place_sell_order(token, order_data)
print("매도 주문 응답:", sell_response)
