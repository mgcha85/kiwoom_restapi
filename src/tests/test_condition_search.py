import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

from src.trading.condition_search import ConditionSearch


def get_conditions(token):
    # 조건 검색을 위한 ConditionSearch 객체 생성
    market_api = ConditionSearch(token)
    
    # 조건에 맞는 주식 코드를 검색
    return market_api.fetch_condition_list()
    
def search_conditions(token, conditions):
    # 조건 검색을 위한 ConditionSearch 객체 생성
    market_api = ConditionSearch(token)
    
    # 조건에 맞는 주식 코드를 검색
    stock_codes = market_api.search_conditions(conditions=conditions)
    return stock_codes


# 파일에서 토큰 읽기
with open("access_token.txt", "r") as f:
    token = f.read().strip()

# 검색 조건 설정 (예시: 주식 코드 및 이름을 통한 조건 검색)
# conditions = {
#     "stk_cd": "005930",  # 삼성전자 주식 코드
#     "name": "삼성전자"   # 종목명 예시
# }

# # 조건에 맞는 종목 코드 조회
# stock_codes = search_conditions(token, conditions)
# print("검색된 종목 코드:", stock_codes)

# 다른 조건 예시 (여러 조건을 동시에 사용하는 경우)
conditions_multiple = {
    "stk_cd": "005930",  # 삼성전자 주식 코드
    "name": "삼성전자",   # 종목명 예시
    "market_type": "KRX"  # 예시로 한국거래소 시장 유형
}

# 여러 조건을 바탕으로 종목 코드 조회
conditions = get_conditions(token)
print(conditions)

# stock_codes_multiple = search_conditions(token, conditions_multiple)
# print("검색된 종목 코드 (여러 조건):", stock_codes_multiple)
