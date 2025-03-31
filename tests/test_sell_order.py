import unittest
from src.api.order import OrderAPI

class TestSellOrder(unittest.TestCase):
    def test_sell_order(self):
        token = 'dummy_token'
        order_api = OrderAPI(use_mock=True)
        # 매도 주문 예시 (실제 매도 API가 별도로 있으면 해당 함수를 사용)
        order_data = {
            'dmst_stex_tp': 'KRX',
            'stk_cd': '005930',
            'ord_qty': '1',
            'ord_uv': '110000',  # 지정가 매도 주문
            'trde_tp': '0',      # 테스트용 동일 함수 사용
            'cond_uv': ''
        }
        response = order_api.stock_buy_order(token, order_data)
        self.assertIn('return_code', response)

if __name__ == '__main__':
    unittest.main()