import asyncio
import websockets
import json
from src.config import APP_KEY  # 실제 환경에서는 OAuth를 통해 획득한 Access Token 사용

# 기본 WebSocket 접속 URL (실전)
SOCKET_URL = "wss://api.kiwoom.com:10000/api/dostk/websocket"
# ACCESS_TOKEN은 실제로 OAuthClient를 통해 획득한 토큰으로 대체합니다.
ACCESS_TOKEN = "your_access_token_here"  

class WebSocketClient:
    def __init__(self, uri: str = SOCKET_URL):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.keep_running = True

    async def connect(self):
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print("WebSocket 연결에 성공하였습니다.")
            # 로그인 패킷 전송
            login_packet = {
                'trnm': 'LOGIN',
                'token': ACCESS_TOKEN
            }
            await self.send_message(login_packet)
        except Exception as e:
            print(f"WebSocket 연결 오류: {e}")
            self.connected = False

    async def send_message(self, message):
        if not self.connected:
            await self.connect()
        if self.connected:
            if not isinstance(message, str):
                message = json.dumps(message)
            await self.websocket.send(message)
            print(f"전송한 메시지: {message}")

    async def receive_messages(self):
        while self.keep_running:
            try:
                message = await self.websocket.recv()
                data = json.loads(message)
                # LOGIN 메시지 처리
                if data.get('trnm') == 'LOGIN':
                    if data.get('return_code') != 0:
                        print("로그인 실패:", data.get('return_msg'))
                        await self.disconnect()
                    else:
                        print("로그인 성공")
                # PING 메시지 처리
                elif data.get('trnm') == 'PING':
                    await self.send_message(data)
                else:
                    print("수신한 메시지:", data)
            except websockets.ConnectionClosed:
                print("서버에 의해 연결이 종료되었습니다.")
                self.connected = False
                break

    async def run(self):
        await self.connect()
        await self.receive_messages()

    async def disconnect(self):
        self.keep_running = False
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
            print("WebSocket 연결 종료")

# 예시 실행 코드
async def main():
    ws_client = WebSocketClient()
    await ws_client.connect()
    # 실시간 항목 등록 예시
    register_packet = {
        'trnm': 'REG',
        'grp_no': '1',
        'refresh': '1',
        'data': [{
            'item': ['005930'],  # 예시 종목코드
            'type': ['00']       # 예시: 주문체결 TR
        }]
    }
    await ws_client.send_message(register_packet)
    await ws_client.receive_messages()

if __name__ == '__main__':
    asyncio.run(main())
