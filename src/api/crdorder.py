# src/api/crdorder.py

from src.api.base_client import BaseAPIClient

class CreditOrderAPI(BaseAPIClient):
    def __init__(self, use_mock: bool = False):
        super().__init__(use_mock=use_mock)
    
    def credit_buy_order(self, token: str, order_data: dict, cont_yn: str = 'N', next_key: str = '') -> dict:
        endpoint = '/api/dostk/crdordr'
        headers = {
            'authorization': f'Bearer {token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': 'kt10006'
        }
        response = self.post(endpoint, data=order_data, headers=headers)
        return response.json()
