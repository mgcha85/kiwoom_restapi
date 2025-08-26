from src.api.base_client import BaseAPIClient
from src.models.account_model import AssetResponse, AccountDetailResponse, AccountEvalResponse
import json

class AccountService(BaseAPIClient):
    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self.endpoint = '/api/dostk/acnt'

    def _get_headers(self, cont_yn='N', next_key=''):
        """기본 header 데이터 설정"""
        return {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': ''  # TR명은 나중에 메서드에서 지정
        }

    def get_asset(self, data={"qry_tp": "0"}, cont_yn='N', next_key=''):
        """추정자산 조회 요청"""
        headers = self._get_headers(cont_yn=cont_yn, next_key=next_key)
        headers['api-id'] = 'kt00003'  # 추정자산 조회 TR명

        response = self.post(self.endpoint, data=data, headers=headers)
        if response.status_code == 200:
            return AssetResponse(**response.json())  # AssetResponse 모델로 반환
        else:
            print(f"Error: {response.status_code}")
            return None
        
    def get_status(self, data={"qry_tp": "0"}, cont_yn='N', next_key=''):
        """계좌평가현황요청"""
        headers = self._get_headers(cont_yn=cont_yn, next_key=next_key)
        headers['api-id'] = 'kt00004'  # 추정자산 조회 TR명

        response = self.post(self.endpoint, data=data, headers=headers)
        if response.status_code == 200:
            return AccountEvalResponse(**response.json())  # AssetResponse 모델로 반환
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_account_details(self, data={'qry_tp': '3'}, cont_yn='N', next_key=''):
        """예수금 상세 현황 조회 요청"""
        headers = self._get_headers(cont_yn=cont_yn, next_key=next_key)
        headers['api-id'] = 'kt00001'  # 예수금 조회 TR명

        response = self.post(self.endpoint, data=data, headers=headers)

        if response.status_code == 200:
            return AccountDetailResponse(**response.json())  # AccountDetailResponse 모델로 반환
        else:
            print(f"Error: {response.status_code}")
            return None
