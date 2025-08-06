from src.api.base_client import BaseAPIClient

class MarketAPI(BaseAPIClient):
    def __init__(self, use_mock: bool = False):
        super().__init__(use_mock=use_mock)
    
    def get_stock_info(self, token: str, stock_code: str, cont_yn: str = 'N', next_key: str = '') -> dict:
        endpoint = '/api/dostk/stkinfo'
        headers = {
            'authorization': f'Bearer {token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': 'ka10001'
        }
        payload = {
            'stk_cd': stock_code
        }
        response = self.post(endpoint, data=payload, headers=headers)
        return response.json()
