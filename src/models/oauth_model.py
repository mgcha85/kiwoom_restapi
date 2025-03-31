# src/models/oauth_model.py

from pydantic import BaseModel

class OAuthRequest(BaseModel):
    grant_type: str
    appkey: str
    secretkey: str

class OAuthResponse(BaseModel):
    expires_dt: str
    token_type: str
    token: str
    return_code: int
    return_msg: str
