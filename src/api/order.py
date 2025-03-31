# src/api/order.py

from src.api.base_client import BaseAPIClient

class OrderAPI(BaseAPIClient):
    def __init__(self, use_mock: bool = False):
        super().__init__(use_mock=use_mock)
    
    def stock_buy_order(self, token: str, order_data: dict, cont_yn: str = 'N', next_key: str = '') -> dict:
        endpoint = '/api/dostk/ordr'
        headers = {
            'authorization': f'Bearer {token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': 'kt10000'
        }
        response = self.post(endpoint, data=order_data, headers=headers)
        return response.json()
