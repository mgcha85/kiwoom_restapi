from src.api.base_client import BaseAPIClient
from src.models.oauth_model import OAuthRequest, OAuthResponse
from src.config import APP_KEY, SECRET_KEY


class OAuthClient(BaseAPIClient):
    def __init__(self):
        super().__init__()
    
    def get_access_token(self) -> OAuthResponse:
        endpoint = '/oauth2/token'
        payload = OAuthRequest(
            grant_type="client_credentials",
            appkey=APP_KEY,
            secretkey=SECRET_KEY
        ).model_dump()
        
        response = self.post(endpoint, data=payload)
        response_json = response.json()

        # 응답 내용 출력 (디버깅용)
        print("OAuth 응답:", response_json)

        if response_json.get('return_code') == 3:
            raise Exception(f"인증 오류: {response_json.get('return_msg')}")
        
        oauth_response = OAuthResponse(**response_json)
        return oauth_response
    
    def revoke_token(self, token: str) -> dict:
        endpoint = '/oauth2/revoke'
        payload = {
            "appkey": APP_KEY,
            "secretkey": SECRET_KEY,
            "token": token
        }
        response = self.post(endpoint, data=payload)
        return response.json()
