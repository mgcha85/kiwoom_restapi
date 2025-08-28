import os
import json
import asyncio
import websockets
from decimal import Decimal
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
import re

from db import (
    init_db,
    update_order_status,
    get_order_by_no,
    record_execution,         # SELL이면 내부 FIFO 매칭으로 trades 생성
)
from db.hold_sqlite import (
    _get_conn,
    init_hold_table,
    get_hold,
)

from config import config

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
with open(os.path.join(project_root, "access_token.txt"), "r", encoding="utf-8") as f:
    token = f.read().strip()

# -----------------------------
# 환경 변수
# -----------------------------
ACCOUNT_ID = os.getenv("KIWOOM_ACCOUNT_ID", "ACC1")
MAX_SPLITS = int(os.getenv("MAX_SPLITS", "4"))
TARGET_PCT = float(os.getenv("TARGET_PCT", "0.1"))
STOP_PCT = float(os.getenv("STOP_PCT", "-0.1"))

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

    # 1) orders 테이블 등록정보(있으면 우선)
    db_order = get_order_by_no(order_no) if order_no else None
    db_account_id = getattr(db_order, "account_id", None)
    db_ticker     = getattr(db_order, "ticker", None)

    # 2) 실시간 패킷 값
    raw_ticker      = _safe_get(values, "9001")
    market          = _safe_get(values, "2135") or "KRX"
    order_qty_s     = _safe_get(values, "900")   # 주문수량
    remain_qty_s    = _safe_get(values, "902")   # 미체결수량
    exec_qty_s      = _safe_get(values, "911")   # 이번 체결수량
    side_txt        = _safe_get(values, "905")   # +매수/+매도
    status          = _safe_get(values, "913")   # 접수/체결/…
    qty_all_s       = _safe_get(values, "907")   # 매도수/매수수 구분수량(브로커 형식)
    last_tm         = _safe_get(values, "908")   # 체결시각(HHMMSS)
    px_exec_s       = _safe_get(values, "910")   # 체결가(FID 910) ※ 문서 예시 상 여기 체결가
    px_ref_s        = _safe_get(values, "10")    # 현재가(대체)
    comm_s          = _safe_get(values, "938")   # 수수료
    tax_s           = _safe_get(values, "939")   # 세금(보통 SELL)

    # 디버깅: 모든 주요 필드 출력
    print(
        "REAL(00) ▶ "
        f"order_no={order_no}, raw_ticker={raw_ticker}, market={market}, "
        f"side_txt={side_txt}, status={status}, "
        f"order_qty={order_qty_s}, remain_qty={remain_qty_s}, exec_qty={exec_qty_s}, qty_all={qty_all_s}, "
        f"exec_time={last_tm}, px_exec={px_exec_s}, px_ref={px_ref_s}, "
        f"commission={comm_s}, tax={tax_s}"
    )

    # 3) 정규화/파싱
    side        = _parse_side(side_txt)  # BUY / SELL
    price_exec  = _to_decimal(px_exec_s)
    price_ref   = _to_decimal(px_ref_s)
    price       = price_exec if price_exec > 0 else price_ref

    order_qty   = _to_decimal(order_qty_s)
    remain_qty  = _to_decimal(remain_qty_s)
    exec_qty    = _to_decimal(exec_qty_s)
    if exec_qty <= 0:
        # 일부 브로커 패킷에서 누락되면 방어적으로 처리
        exec_qty = order_qty if order_qty > 0 else Decimal("1")

    commission  = _to_decimal(comm_s)
    sell_tax    = _to_decimal(tax_s)
    exec_time   = _parse_exec_time(last_tm)

    ticker      = db_ticker or _normalize_ticker(raw_ticker)
    account_id  = db_account_id or ACCOUNT_ID
    st          = (status or "").strip()

    # 4) 상태별 주문 상태 갱신
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

    # 5) 체결 처리
    if "체결" in st:
        # exec_id (체결번호가 있으면 그걸 쓰고, 없으면 구성)
        exec_no = _safe_get(values, "909")
        if exec_no:
            exec_id = f"{side}-EXEC-{exec_no}"
        else:
            exec_id = f"{side}-EXEC-{order_no}-{exec_time.strftime('%H%M%S')}"

        use_commission = commission if commission > 0 else (
            DEFAULT_BUY_COMMISSION if side == "BUY" else DEFAULT_SELL_COMMISSION
        )
        use_tax = sell_tax if side == "SELL" else Decimal("0.00")

        # (A) executions 항상 기록
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

        # (B) orders 상태 갱신
        if order_no:
            if remain_qty == 0:
                update_order_status(order_no=order_no, status="FILLED")
            else:
                update_order_status(order_no=order_no, status="PARTIALLY_FILLED")

        # (C) hold_list 갱신 (핵심)
        now_ts = datetime.now(timezone.utc).replace(tzinfo=None)
        row = get_hold(account_id, ticker)

        if side == "BUY":
            # 신규/추가 매수 → 평단/수량/수수료/세금 누적 + n_trade 증가(최대 4)
            if row is None:
                new_qty = exec_qty
                new_avg = price
                n_trade = 1
                target  = (new_avg * (Decimal("1")+TARGET_PCT)).quantize(Decimal("0.01"))
                stop    = (new_avg * (Decimal("1")+STOP_PCT)).quantize(Decimal("0.01"))
                _sql = """
                    INSERT INTO hold_list
                    (account_id, ticker, market,
                     qty, remain_qty, buy_avg_price, n_trade,
                     buy_time, last_buy_time, target_price, stop_price,
                     fee_accum, tax_accum, last_order_id, updated_at)
                    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """
                _args = (
                    account_id, ticker, market,
                    str(new_qty), str(new_qty), str(new_avg), n_trade,
                    now_ts, now_ts, str(target), str(stop),
                    str(use_commission), str(use_tax), order_no, now_ts
                )
            else:
                old_qty = Decimal(str(row["qty"]))
                old_avg = Decimal(str(row["buy_avg_price"]))
                old_fee = Decimal(str(row["fee_accum"]))
                old_tax = Decimal(str(row["tax_accum"]))
                old_n   = int(row["n_trade"]) if row["n_trade"] is not None else 0

                new_qty = old_qty + exec_qty
                new_avg = ((old_avg * old_qty) + (price * exec_qty)) / (new_qty if new_qty != 0 else Decimal("1"))
                new_avg = new_avg.quantize(Decimal("0.000001"))
                n_trade = min(old_n + 1, MAX_SPLITS)
                fee_acc = old_fee + use_commission
                tax_acc = old_tax + use_tax
                target  = (new_avg * (Decimal("1")+TARGET_PCT)).quantize(Decimal("0.01"))
                stop    = (new_avg * (Decimal("1")+STOP_PCT)).quantize(Decimal("0.01"))

                _sql = """
                    UPDATE hold_list
                    SET qty=?, remain_qty=?, buy_avg_price=?, n_trade=?,
                        last_buy_time=?, target_price=?, stop_price=?,
                        fee_accum=?, tax_accum=?, last_order_id=?, updated_at=?
                    WHERE account_id=? AND ticker=?
                """
                _args = (
                    str(new_qty), str(new_qty), str(new_avg), n_trade,
                    now_ts, str(target), str(stop),
                    str(fee_acc), str(tax_acc), order_no, now_ts,
                    account_id, ticker
                )

        else:  # SELL
            # 보유 수량 차감, 수수료/세금 누적
            if row is not None:
                old_qty = Decimal(str(row["qty"]))
                old_rem = Decimal(str(row["remain_qty"]))
                old_fee = Decimal(str(row["fee_accum"]))
                old_tax = Decimal(str(row["tax_accum"]))

                new_qty = max(old_qty - exec_qty, Decimal("0"))
                new_rem = max(old_rem - exec_qty, Decimal("0"))
                fee_acc = old_fee + use_commission
                tax_acc = old_tax + use_tax

                _sql = """
                    UPDATE hold_list
                    SET qty=?, remain_qty=?, fee_accum=?, tax_accum=?, updated_at=?
                    WHERE account_id=? AND ticker=?
                """
                _args = (
                    str(new_qty), str(new_rem), str(fee_acc), str(tax_acc), now_ts,
                    account_id, ticker
                )
            else:
                _sql, _args = None, None

        # (D) hold_list에 반영
        if _sql:
            with _get_conn() as _c:
                _c.execute(_sql, _args)
                _c.commit()

        print(
            f"[EXEC] rec_id={rec_id}, side={side}, order_no={order_no}, "
            f"ticker={ticker}, exec_qty={exec_qty}, price={price}, "
            f"remain(order)={remain_qty}, hold.updated"
        )
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
        init_hold_table()

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
