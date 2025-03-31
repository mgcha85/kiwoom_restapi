import unittest
import asyncio
from src.api.websocket_client import WebSocketClient

class TestRealtimeCandle(unittest.TestCase):
    def test_realtime_candle(self):
        async def run_test():
            ws_client = WebSocketClient()
            await ws_client.connect()
            # 실시간 캔들 데이터 요청 예시 (타입은 'min', 'hour', 'day' 등으로 가정)
            register_packet = {
                'trnm': 'REG',
                'grp_no': '1',
                'refresh': '1',
                'data': [{
                    'item': ['005930'],
                    'type': ['min']  # 분봉 테스트 (시봉, 일봉은 type 값을 변경)
                }]
            }
            await ws_client.send_message(register_packet)
            # 짧은 시간 대기 후 연결 종료
            await asyncio.sleep(1)
            await ws_client.disconnect()
        asyncio.run(run_test())
        self.assertTrue(True)

if __name__ == '__main__':
    unittest.main()