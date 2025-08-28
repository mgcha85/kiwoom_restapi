import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

from api.stock_chart_service import StockChartService

# 토큰을 파일에서 읽어옵니다.
with open("access_token.txt", "r") as f:
    token = f.read().strip()

stock_chart_service = StockChartService(token)

# 일봉 차트 조회
stk_cd = '005930'  # 삼성전자 종목 코드
base_dt = '20241108'  # 기준일자

daily_chart_df = stock_chart_service.get_daily_chart(stk_cd, base_dt)
if daily_chart_df is not None:
    print("일봉 차트:")
    print(daily_chart_df)

# 분봉 차트 조회
# intraday_chart_df = stock_chart_service.get_intraday_chart(stk_cd, tic_scope='1')  # 1분봉
# if intraday_chart_df is not None:
#     print("분봉 차트:")
#     print(intraday_chart_df)
