from pydantic import BaseModel
from typing import Optional

class OAuthRequest(BaseModel):
    grant_type: str
    appkey: str
    secretkey: str

class OAuthResponse(BaseModel):
    expires_dt: Optional[str]  # Optional로 수정
    token_type: Optional[str]  # Optional로 수정
    token: Optional[str]  # Optional로 수정
    return_code: int
    return_msg: str