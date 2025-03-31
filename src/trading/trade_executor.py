# src/trading/trade_executor.py

from src.api.order import OrderAPI
from src.utils.logger import get_logger

logger = get_logger(__name__)

class TradeExecutor:
    def __init__(self, token: str):
        self.token = token
        self.order_api = OrderAPI()

    def execute_trades(self):
        """
        보유 주식 정보를 바탕으로 매수/매도 주문을 진행합니다.
        (매수는 평균가의 -10%, 매도는 평균가의 +10% 가격으로 주문 설정 예시)
        """
        # 가상의 보유 주식 데이터 예시
        holdings = [
            {"stk_cd": "005930", "avg_price": 100000, "qty": 10}
        ]
        for holding in holdings:
            buy_price = int(holding["avg_price"] * 0.9)
            sell_price = int(holding["avg_price"] * 1.1)
            # 주문 데이터 예시 (실제 API 요구사항에 맞게 구성)
            order_data_buy = {
                "dmst_stex_tp": "KRX",
                "stk_cd": holding["stk_cd"],
                "ord_qty": "1",
                "ord_uv": str(buy_price),
                "trde_tp": "0",
                "cond_uv": ""
            }
            order_data_sell = {
                "dmst_stex_tp": "KRX",
                "stk_cd": holding["stk_cd"],
                "ord_qty": "1",
                "ord_uv": str(sell_price),
                "trde_tp": "0",
                "cond_uv": ""
            }
            buy_response = self.order_api.stock_buy_order(token=self.token, order_data=order_data_buy)
            sell_response = self.order_api.stock_buy_order(token=self.token, order_data=order_data_sell)
            logger.info(f"매수 주문 결과: {buy_response}")
            logger.info(f"매도 주문 결과: {sell_response}")

if __name__ == '__main__':
    token = "your_access_token"
    executor = TradeExecutor(token)
    executor.execute_trades()
