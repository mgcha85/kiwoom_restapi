import asyncio
import websockets
import json

# WebSocket URL
SOCKET_URL = "wss://api.kiwoom.com:10000/api/dostk/websocket"  # 실시간 WebSocket URL

# 파일에서 토큰 읽기
with open("access_token.txt", "r") as f:
    token = f.read().strip()


class WebSocketClient:
    def __init__(self, uri: str = SOCKET_URL):
        self.uri = uri
        self.websocket = None
        self.connected = False
        self.keep_running = True

    async def connect(self):
        """WebSocket 서버에 연결합니다."""
        try:
            self.websocket = await websockets.connect(self.uri)
            self.connected = True
            print("서버와 연결을 시도 중입니다.")

            # 로그인 패킷 전송
            login_packet = {
                'trnm': 'LOGIN',
                'token': token
            }
            print('실시간 시세 서버로 로그인 패킷을 전송합니다.')
            await self.send_message(message=login_packet)

        except Exception as e:
            print(f'Connection error: {e}')
            self.connected = False

    async def send_message(self, message: dict):
        """서버로 메시지를 보냅니다. 연결이 없으면 자동으로 연결을 시도합니다."""
        if not self.connected:
            await self.connect()
        if self.connected:
            if not isinstance(message, str):
                message = json.dumps(message)

            await self.websocket.send(message)
            print(f'Message sent: {message}')

    async def receive_messages(self):
        """서버에서 수신한 메시지를 처리합니다."""
        while self.keep_running:
            try:
                response = json.loads(await self.websocket.recv())

                # 로그인 처리
                if response.get('trnm') == 'LOGIN':
                    if response.get('return_code') != 0:
                        print('로그인 실패: ', response.get('return_msg'))
                        await self.disconnect()
                    else:
                        print('로그인 성공')

                # PING 메시지 처리
                elif response.get('trnm') == 'PING':
                    await self.send_message(response)

                # 조건검색 목록 조회 응답 처리
                elif response.get('trnm') == 'CNSRLST':
                    if response.get('return_code') == 0:
                        print(f'조건검색 목록 조회 성공: {response.get("data")}')
                    else:
                        print(f'조건검색 목록 조회 실패: {response.get("return_msg")}')

                # 조건검색 요청 응답 처리
                elif response.get('trnm') == 'CNSRREQ':
                    if response.get('return_code') == 0:
                        print(f"조건검색식에 해당하는 주식 코드 조회 성공: {response.get('data')}")
                    else:
                        print(f'조건검색 요청 실패: {response.get("return_msg")}')
                
                else:
                    print(f'응답 수신: {response}')

            except websockets.ConnectionClosed:
                print('서버에 의해 연결이 종료되었습니다.')
                self.connected = False
                break

    async def run(self):
        """WebSocket 연결 및 메시지 수신 작업을 실행합니다."""
        await self.connect()
        await self.receive_messages()

    async def disconnect(self):
        """WebSocket 연결 종료"""
        self.keep_running = False
        if self.connected and self.websocket:
            await self.websocket.close()
            self.connected = False
            print('WebSocket 연결 종료')


class ConditionSearch:
    def __init__(self, token: str):
        self.token = token
        self.websocket_client = WebSocketClient()

    async def fetch_condition_list(self):
        """조건검색 목록 조회"""
        try:
            await self.websocket_client.connect()

            # 조건검색 목록 조회 요청
            condition_list_packet = {
                "trnm": "CNSRLST",  # 조건검색 목록 조회 TR명
                "token": self.token
            }
            await self.websocket_client.send_message(condition_list_packet)

            # 메시지 수신 대기 및 목록 반환
            condition_list = await self.websocket_client.receive_messages()
            return condition_list  # 조회된 조건검색 목록 반환

        except Exception as e:
            print(f"조건검색 목록 조회 중 오류 발생: {e}")
            return []

    async def search_conditions(self, seq: str):
        """조건검색을 통한 주식 코드 조회"""
        try:
            await self.websocket_client.connect()

            # 조건검색 요청
            search_packet = {
                "trnm": "CNSRREQ",  # 조건검색 요청
                "token": self.token,
                "seq": seq,  # 조건식 일련번호
                "search_type": "0",  # 조회타입
                "stex_tp": "K",  # 거래소구분
                "cont_yn": "N",  # 연속조회여부
                "next_key": ""  # 연속조회키
            }
            await self.websocket_client.send_message(search_packet)

            # 메시지 수신 대기 및 결과 반환
            result = await self.websocket_client.receive_messages()
            return result

        except Exception as e:
            print(f"조건검색 요청 중 오류 발생: {e}")

    async def process_all_conditions(self):
        """모든 조건식 목록에 대해 검색을 실행"""
        condition_list = await self.fetch_condition_list()

        # 모든 조건식에 대해 조건검색 실행
        results = []
        for condition in condition_list:
            seq, name = condition  # seq: 조건식 번호, name: 조건식 명
            print(f"조건식: {name} (Seq: {seq}) 검색 시작...")

            # 조건에 맞는 데이터 검색 (주식 코드 리스트를 가져오기)
            result = await self.search_conditions(seq)
            results.append({name: result})  # 조건식 이름과 해당 조건의 주식 코드 리스트 저장
        return results


# 테스트 실행
async def main():
    cs = ConditionSearch(token)

    # 조건검색 목록 조회
    print("조건검색 목록 조회 시작...")
    results = await cs.process_all_conditions()

    print(f"최종 검색 결과: {results}")


if __name__ == "__main__":
    asyncio.run(main())
