import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

from src.api.oauth import OAuthClient


def get_access_token():
    oauth_client = OAuthClient()
    oauth_response = oauth_client.get_access_token()
    return oauth_response.token

token = get_access_token()
print("Access Token:", token)

# 토큰을 파일에 저장
with open("access_token.txt", "w") as f:
    f.write(token)


# oauth_client = OAuthClient()
# oauth_client.revoke_token(token)