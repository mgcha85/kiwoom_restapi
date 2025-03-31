import unittest
from src.api.order import OrderAPI

class TestBuyOrder(unittest.TestCase):
    def test_buy_order(self):
        token = 'dummy_token'
        order_api = OrderAPI(use_mock=True)
        # 지정가 주문 예시
        order_data = {
            'dmst_stex_tp': 'KRX',
            'stk_cd': '005930',
            'ord_qty': '1',
            'ord_uv': '100000',  # 지정가 주문
            'trde_tp': '0',      # 예: 0은 지정가 주문
            'cond_uv': ''
        }
        response = order_api.stock_buy_order(token, order_data)
        self.assertIn('return_code', response)

if __name__ == '__main__':
    unittest.main()