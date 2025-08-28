import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

from api.oauth import OAuthClient
import logging


def get_access_token():
    oauth_client = OAuthClient()
    oauth_response = oauth_client.get_access_token()

    token = oauth_response.token
    print("Access Token:", token)

    # 토큰을 파일에 저장
    with open("access_token.txt", "w") as f:
        f.write(token)

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