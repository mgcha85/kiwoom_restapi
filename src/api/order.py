from api.base_client import BaseAPIClient

class OrderAPI(BaseAPIClient):
    def __init__(self):
        super().__init__()
    
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
    
    def stock_sell_order(self, token: str, order_data: dict, cont_yn: str = 'N', next_key: str = '') -> dict:
        """
        매도 주문
        - 기본 api-id는 매도용으로 'kt10001'을 사용하도록 설정했습니다.
          필요 시 환경변수 KIWOOM_API_ID_SELL로 변경하세요.
        - order_data 예시(시장가 매도):
            {
                "dmst_stex_tp": "KRX",
                "stk_cd": "005930",
                "ord_qty": "1",
                "ord_uv": "",          # 시장가면 빈 문자열
                "trde_tp": "3",        # 시장가
                "cond_uv": ""
            }
        """
        endpoint = '/api/dostk/ordr'
        headers = {
            'authorization': f'Bearer {token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': "kt10001",
        }
        response = self.post(endpoint, data=order_data, headers=headers)
        return response.json()