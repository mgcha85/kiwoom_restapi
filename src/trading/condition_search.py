import asyncio
import websockets
import json
from typing import List, Dict

SOCKET_URL = 'wss://api.kiwoom.com:10000/api/dostk/websocket'  # 운영 도메인

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
