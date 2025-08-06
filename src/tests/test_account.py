import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

from src.api.account_service import AccountService

# 토큰을 파일에서 읽어옵니다.
with open("access_token.txt", "r") as f:
    token = f.read().strip()

account_service = AccountService(token)

# 추정자산 조회
asset_response = account_service.get_asset(data={"qry_tp": "0"})
if asset_response:
    print("추정자산 조회 결과:", asset_response)

# 예수금 상세 현황 조회
account_details_response = account_service.get_account_details(data={'qry_tp': '3'})
if account_details_response:
    print("예수금 상세 현황 조회 결과:", account_details_response)
