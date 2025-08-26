import os
from src.trading.condition_ws import fetch_condition_codes, fetch_condition_list
import asyncio


project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
with open(os.path.join(project_root, "access_token.txt"), "r", encoding="utf-8") as f:
    token = f.read().strip()

# 예: seq=2, KRX
conds = asyncio.run(fetch_condition_list(token))
print("조건검색식 목록:", conds)

codes = asyncio.run(fetch_condition_codes(token, seq="2", stex_tp="K"))
print("코드 개수:", len(codes))
print("예시 20개:", codes[:20])
