from src.api.order import OrderAPI

def place_buy_order(token, order_data):
    order_api = OrderAPI()
    response = order_api.stock_buy_order(token=token, order_data=order_data)
    return response

order_data = {
    "dmst_stex_tp": "KRX",
    "stk_cd": "005930",
    "ord_qty": "10",
    "ord_uv": "70000",  # 예: 70,000원
    "trde_tp": "0",     # 보통
    "cond_uv": ""
}
buy_response = place_buy_order(token, order_data)
print("매수 주문 응답:", buy_response)
