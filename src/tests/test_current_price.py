import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

from src.api.market import MarketAPI

def get_stock_current_price(token, stock_code):
    market_api = MarketAPI()
    stock_info = market_api.get_stock_info(token=token, stock_code=stock_code)
    return stock_info

# 파일에서 토큰 읽기
with open("access_token.txt", "r") as f:
    token = f.read().strip()

stock_code = "005930"  # 예: 삼성전자
stock_info = get_stock_current_price(token, stock_code)
print(f"{stock_code} 현재가:", stock_info)
