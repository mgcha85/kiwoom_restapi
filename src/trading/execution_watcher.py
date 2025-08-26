import os
import json
import asyncio
import websockets
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import re

from src.db import (
    init_db,
    update_order_status,
    get_order_by_no,
    record_execution,         # SELL이면 내부 FIFO 매칭으로 trades 생성
)
from src.config import config

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
with open(os.path.join(project_root, "access_token.txt"), "r", encoding="utf-8") as f:
    token = f.read().strip()

# -----------------------------
# 환경 변수
# -----------------------------
ACCOUNT_ID = os.getenv("KIWOOM_ACCOUNT_ID", "ACC1")

# 기본 수수료/세금(실계좌 정책 반영 필요 시 교체)
DEFAULT_BUY_COMMISSION = Decimal(os.getenv("DEFAULT_BUY_COMMISSION", "0.00"))
DEFAULT_SELL_COMMISSION = Decimal(os.getenv("DEFAULT_SELL_COMMISSION", "0.00"))
DEFAULT_SELL_TAX = Decimal(os.getenv("DEFAULT_SELL_TAX", "0.00"))

# -----------------------------
# 유틸
# -----------------------------

def _normalize_ticker(t: Optional[str]) -> str:
    """A005930, 005930 등 → 숫자만 남기기"""
    if not t:
        return ""
    return re.sub(r"\D", "", t)

def _to_decimal(s: Optional[str]) -> Decimal:
    if s is None:
        return Decimal("0")
    s = s.strip()
    if not s:
        return Decimal("0")
    # '+60700' 형태 대응: 숫자/부호/점만 남김
    buf = []
    for ch in s:
        if ch.isdigit() or ch in ['+', '-', '.']:
            buf.append(ch)
    try:
        return Decimal("".join(buf))
    except Exception:
        return Decimal("0")

def _parse_side(text: str) -> str:
    """'+매수' → BUY, '+매도' → SELL"""
    if not text:
        return "BUY"
    return "SELL" if "매도" in text else "BUY"

def _parse_exec_time(hhmmss: str) -> datetime:
    """FID 908 (예: '094022') → 오늘 날짜의 KST 시각 (tz-aware)"""
    now_kst = datetime.now()
    try:
        hh = int(hhmmss[0:2]); mm = int(hhmmss[2:4]); ss = int(hhmmss[4:6])
        return datetime(now_kst.year, now_kst.month, now_kst.day, hh, mm, ss, tzinfo=now_kst.tzinfo)
    except Exception:
        return now_kst

def _safe_get(d: Dict[str, Any], key: str, default: str = "") -> str:
    v = d.get(key)
    return v if v is not None else default

# -----------------------------
# REAL: 주문체결(type '00') 처리
# -----------------------------
def handle_order_execution_real(values: Dict[str, Any]) -> None:
    order_no = _safe_get(values, "9203") or _safe_get(values, "9205")

    # 1) orders 테이블에서 정규 정보 우선 가져오기
    db_order = get_order_by_no(order_no) if order_no else None
    db_account_id = getattr(db_order, "account_id", None)
    db_ticker     = getattr(db_order, "ticker", None)

    # 2) 실시간 패킷 값 (fallback)
    raw_ticker = _safe_get(values, "9001")
    market   = _safe_get(values, "2135") or "KRX"
    order_qty = _safe_get(values, "900")
    remaining_qty = _safe_get(values, "902")
    exec_qty = _safe_get(values, "911")
    side_txt = _safe_get(values, "905")
    status   = _safe_get(values, "913")
    qty_all  = _safe_get(values, "907")
    last_tm  = _safe_get(values, "908")
    px27     = _safe_get(values, "910")
    px10     = _safe_get(values, "10")
    comm     = _safe_get(values, "938")
    tax      = _safe_get(values, "939")
    # order_price = _safe_get(values, "901")
    # exec_qty = order_qty - remaining_qty

    print(
        f"raw_ticker={raw_ticker}, "
        f"market={market}, "
        f"side_txt={side_txt}, "
        f"status={status}, "
        f"qty_all={qty_all}, "
        f"last_tm={last_tm}, "
        f"px27={px27}, "
        f"px10={px10}, "
        f"comm={comm}, "
        f"tax={tax}, "
        f"exec_qty_candidate={exec_qty}"
    )

    # 3) 파싱/정규화
    side = _parse_side(side_txt)
    price = _to_decimal(px27) if _to_decimal(px27) > 0 else _to_decimal(px10)
    order_qty = _to_decimal(qty_all)
    commission = _to_decimal(comm)
    sell_tax = _to_decimal(tax)
    exec_time = _parse_exec_time(last_tm)

    # **핵심**: ticker/account_id는 DB 값을 최우선, 없으면 스트림값을 정규화해서 사용
    ticker = db_ticker or _normalize_ticker(raw_ticker)
    account_id = db_account_id or ACCOUNT_ID

    st = (status or "").strip()

    if st == "접수":
        if order_no:
            update_order_status(order_no=order_no, status="ACCEPTED")
        return
    if st == "취소":
        if order_no:
            update_order_status(order_no=order_no, status="CANCELLED")
        return
    if st == "정정":
        if order_no:
            update_order_status(order_no=order_no, status="AMENDED")
        return

    # === 체결 ===
    if "체결" in st:
        exec_qty = _to_decimal(exec_qty)
        remaining_qty = _to_decimal(remaining_qty)

        if exec_qty <= 0:
            exec_qty = order_qty if order_qty > 0 else Decimal("1")

        exec_id = f"{side}-EXEC-{order_no}-{exec_time.strftime('%H%M%S')}"

        use_commission = commission if commission > 0 else (
            DEFAULT_BUY_COMMISSION if side == "BUY" else DEFAULT_SELL_COMMISSION
        )
        use_tax = sell_tax if side == "SELL" else Decimal("0.00")

        if remaining_qty == 0:
            # SELL이면 db.record_execution 내부에서 FIFO 매칭 → trades 생성
            rec_id = record_execution(
                exec_id=str(exec_id),
                order_no=str(order_no) if order_no else "UNKNOWN",
                account_id=account_id,
                ticker=ticker,
                market=str(market),
                side=side,
                qty=float(exec_qty),
                price=float(price),
                commission=float(use_commission),
                tax=float(use_tax),
                exec_time=exec_time
            )
        print(f"[EXEC] saved exec_id={rec_id}, side={side}, order_no={order_no}, ticker={ticker}, qty={exec_qty}, price={price}")
        return

# -----------------------------
# WebSocket 러너
# -----------------------------
class ExecutionWatcher:
    def __init__(self, socket_url: str, access_token: str):
        self.socket_url = socket_url
        self.access_token = access_token
        self.websocket = None
        self.connected = False
        self.keep_running = True

    async def connect(self):
        self.websocket = await websockets.connect(self.socket_url)
        self.connected = True
        print("[WS] connecting...")

        # 로그인
        login = {'trnm': 'LOGIN', 'token': self.access_token}
        await self.send(login)
        print("[WS] login sent")

    async def send(self, payload: dict):
        if not self.connected:
            await self.connect()
        await self.websocket.send(json.dumps(payload))

    async def receive_forever(self):
        while self.keep_running:
            try:
                msg = await self.websocket.recv()
                data = json.loads(msg)

                trnm = data.get('trnm')
                if trnm == 'LOGIN':
                    if data.get('return_code') == 0:
                        print("[WS] login ok")
                    else:
                        print(f"[WS] login failed: {data.get('return_msg')}")
                        await self.close()
                        break

                elif trnm == 'PING':
                    await self.send(data)  # echo

                elif trnm == 'REAL':
                    items = data.get('data') or []
                    for it in items:
                        rtype = it.get('type')
                        rname = it.get('name')
                        values = it.get('values', {})
                        if rtype == '00' and rname == '주문체결':
                            try:
                                handle_order_execution_real(values)
                            except Exception as e:
                                print(f"[ERR] handle_order_execution_real: {e}, values={values}")

                # 디버깅 로그 (원하면 주석)
                if trnm != 'PING':
                    print("[WS] recv:", data)

            except websockets.ConnectionClosed:
                print("[WS] closed by server")
                self.connected = False
                try:
                    await self.websocket.close()
                except Exception:
                    pass
                break
            except Exception as e:
                print(f"[WS] error: {e}")
                break

    async def register_streams(self):
        """
        주문체결(00) 실시간 등록
        """
        payload = {
            'trnm': 'REG',
            'grp_no': '1',
            'refresh': '1',
            'data': [{
                'item': [''],    # 전체
                'type': ['00'],  # 주문체결
            }]
        }
        await self.send(payload)
        print("[WS] REG sent for type=00")

    async def run(self, reconnect: bool = True, backoff_start: float = 1.0, backoff_max: float = 30.0):
        """
        실행/재접속 루프
        """
        if not self.access_token:
            raise RuntimeError("KIWOOM_ACCESS_TOKEN env is required")

        init_db()

        backoff = backoff_start
        while self.keep_running:
            try:
                await self.connect()
                await self.register_streams()
                await self.receive_forever()
            except Exception as e:
                print(f"[WS] run error: {e}")
            finally:
                if self.websocket:
                    try:
                        await self.websocket.close()
                    except Exception:
                        pass
                self.connected = False

            if not reconnect:
                break

            # 지수 백오프
            print(f"[WS] reconnecting in {backoff:.1f}s...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, backoff_max)

    async def close(self):
        self.keep_running = False
        if self.websocket:
            try:
                await self.websocket.close()
            except Exception:
                pass
        self.connected = False
        print("[WS] closed")

# 진입점
async def main():
    watcher = ExecutionWatcher(config.app.ws_url, token)
    await watcher.run()

if __name__ == "__main__":
    asyncio.run(main())
