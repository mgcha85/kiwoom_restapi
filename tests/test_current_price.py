import unittest
from src.api.market import MarketAPI

class TestCurrentPrice(unittest.TestCase):
    def test_get_current_price(self):
        token = 'dummy_token'
        market_api = MarketAPI(use_mock=True)
        response = market_api.get_stock_info(token, '005930')
        self.assertIn('cur_prc', response)

if __name__ == '__main__':
    unittest.main()