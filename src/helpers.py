import sys
import os
from typing import Dict, Any, Union, Optional
from decimal import Decimal


# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

from api.oauth import OAuthClient
import logging


def set_access_token():
    oauth_client = OAuthClient()
    oauth_response = oauth_client.get_access_token()

    token = oauth_response.token
    print("Access Token:", token)

    # 토큰을 파일에 저장
    with open("access_token.txt", "w") as f:
        f.write(token)

def get_access_token():
    # 토큰을 파일에 저장
    with open("access_token.txt", "r") as f:
        token = f.read()
    return token

def revoke_access_token():
    token_path = os.path.join(project_root, "access_token.txt")
    if not os.path.exists(token_path):
        logging.warning("access_token.txt not found. Skipping token revoke.")
        return
    
    with open(token_path, "r", encoding="utf-8") as f:
        token = f.read().strip()

    if not token:
        logging.warning("Access token is empty.")
        return
    
    oauth_client = OAuthClient()
    try:
        resp = oauth_client.revoke_token(token)
        if resp.get("return_code") == 0:
            logging.info("Access token successfully revoked.")
            os.remove(token_path)
        else:
            logging.warning(f"Token revoke failed: {resp}")
    except Exception as e:
        logging.error(f"Error while revoking token: {e}")
    

def _to_number(val: Optional[str]) -> Optional[Union[int, float]]:
    """
    문자열 숫자를 int/float로 변환.
    부호(+/-)는 제거하여 양수 값만 반환.
    """
    if val is None:
        return None
    s = str(val).strip()
    if not s:
        return None

    # 숫자와 소수점만 남김 (부호 제거)
    clean = "".join(ch for ch in s if ch.isdigit() or ch == ".")
    if not clean:
        return None
    try:
        if "." in clean:
            return float(clean)
        return int(clean)
    except ValueError:
        return None

def parse_stock_info(info: Dict[str, Any]) -> Dict[str, Any]:
    """
    API에서 받은 info(dict)를 숫자형으로 변환된 dict로 반환
    """
    parsed = {}
    for k, v in info.items():
        if k in ("stk_cd", "stk_nm", "fav_unit", "bus_pro", "return_msg"):
            parsed[k] = v
        else:
            parsed[k] = _to_number(v)
    return parsed