# src/api/oauth.py

from src.api.base_client import BaseAPIClient
from src.models.oauth_model import OAuthRequest, OAuthResponse
from src.config import APP_KEY, SECRET_KEY

class OAuthClient(BaseAPIClient):
    def __init__(self, use_mock: bool = False):
        super().__init__(use_mock=use_mock)
    
    def get_access_token(self) -> OAuthResponse:
        endpoint = '/oauth2/token'
        payload = OAuthRequest(
            grant_type="client_credentials",
            appkey=APP_KEY,
            secretkey=SECRET_KEY
        ).dict()
        response = self.post(endpoint, data=payload)
        response_json = response.json()
        return OAuthResponse(**response_json)
    
    def revoke_token(self, token: str) -> dict:
        endpoint = '/oauth2/revoke'
        payload = {
            "appkey": APP_KEY,
            "secretkey": SECRET_KEY,
            "token": token
        }
        response = self.post(endpoint, data=payload)
        return response.json()
