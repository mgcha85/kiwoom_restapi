import sys
import os

# 프로젝트 루트 경로를 sys.path에 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

from api.market import MarketAPI
from utils.logger import get_logger

import asyncio
import websockets
import json
from typing import List, Dict


logger = get_logger(__name__)

SOCKET_URL = 'wss://mockapi.kiwoom.com:10000/api/dostk/websocket'  # 운영 도메인

class ConditionSearch:
    def __init__(self, token: str):
        self.token = token
        self.market_api = MarketAPI()

    def search_conditions(self, conditions: dict) -> list:
        """
        조건 검색을 통해 주식 코드를 수집합니다.
        (실제 조건에 맞춰 API 호출 로직을 구현할 수 있습니다.)
        """
        stock_code = conditions.get("stk_cd", "005930")  # 기본 예시
        result = self.market_api.get_stock_info(token=self.token, stock_code=stock_code)
        logger.info(f"조건 검색 결과: {result}")
        # 예시로 종목코드 반환
        return [result.get("stk_cd", "")]


# 토큰을 파일에서 읽어옵니다.
with open("access_token.txt", "r") as f:
    token = f.read().strip()

async def _fetch_condition_list() -> List[Dict]:
    # 1) WebSocket 연결
    async with websockets.connect(SOCKET_URL) as ws:
        # 2) 로그인
        login_payload = {'trnm': 'LOGIN', 'token': token}
        await ws.send(json.dumps(login_payload))
        # consume login response
        while True:
            msg = json.loads(await ws.recv())
            if msg.get('trnm') == 'LOGIN':
                if msg.get('return_code') != 0:
                    raise RuntimeError(f"로그인 실패: {msg.get('return_msg')}")
                break

        # 3) 조건검색 목록 조회 요청
        req_payload = {'trnm': 'CNSRLST'}
        await ws.send(json.dumps(req_payload))

        # 4) 응답 수신
        while True:
            msg = json.loads(await ws.recv())
            if msg.get('trnm') == 'CNSRLST':
                if msg.get('return_code') != 0:
                    raise RuntimeError(f"CNSRLST 실패: {msg.get('return_msg')}")
                return msg.get('data', [])

def get_condition_list() -> List[Dict]:
    """
    조건검색식 목록을 조회하여 [{'seq': '0','name':'배당주'}, ...] 형태의 리스트로 반환합니다.
    """
    return asyncio.run(_fetch_condition_list())

if __name__ == '__main__':
    conditions = get_condition_list()
    print("조건검색식 목록:", conditions)
