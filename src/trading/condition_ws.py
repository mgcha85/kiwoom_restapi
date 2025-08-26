import asyncio
import json
import re
from typing import Any, Dict, List, Optional
import websockets

WS_URL = 'wss://mockapi.kiwoom.com:10000/api/dostk/websocket'  # 모의
# WS_URL = 'wss://api.kiwoom.com:10000/api/dostk/websocket'    # 실전

def norm_code(raw: Optional[str]) -> Optional[str]:
    if not raw:
        return None
    s = re.sub(r'^[A-Za-z]', '', str(raw))
    return s if re.fullmatch(r'\d{6}', s) else None

async def login(ws, token: str) -> None:
    await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
    # 로그인 응답만 대기 (PING은 즉시 되돌려보내기)
    while True:
        msg = json.loads(await ws.recv())
        t = msg.get("trnm")
        if t == "PING":
            await ws.send(json.dumps(msg))
            continue
        if t == "LOGIN":
            if msg.get("return_code") != 0:
                raise RuntimeError(f"로그인 실패: {msg.get('return_msg')}")
            return

async def reader(ws, queue: asyncio.Queue):
    """유일한 수신자. 모든 메시지를 큐로 전달. PING은 즉시 응답."""
    try:
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            t = msg.get("trnm")
            if t == "PING":
                await ws.send(json.dumps(msg))
                continue
            await queue.put(msg)
    except websockets.ConnectionClosed:
        await queue.put({"trnm": "__CLOSED__"})

async def recv_until(queue: asyncio.Queue, want_trnm: str, timeout: float = 5.0) -> Dict[str, Any]:
    """큐에서 특정 trnm이 나올 때까지 대기 (타임아웃 포함)."""
    while True:
        msg = await asyncio.wait_for(queue.get(), timeout=timeout)
        if msg.get("trnm") == "__CLOSED__":
            raise RuntimeError("WebSocket closed")
        # 필요하다면 여기서 디버그 로그로 모든 수신 메시지를 찍어보세요.
        # print("DBG recv:", msg)
        if msg.get("trnm") == want_trnm:
            return msg

async def request_condition_list(ws, queue: asyncio.Queue) -> List[List[str]]:
    """CNSRLST: 조건목록"""
    await ws.send(json.dumps({"trnm": "CNSRLST"}))
    resp = await recv_until(queue, "CNSRLST", timeout=10.0)
    if resp.get("return_code") != 0:
        raise RuntimeError(f"CNSRLST 실패: {resp.get('return_msg')}")
    return resp.get("data", [])

async def request_cnsrreq_once(ws, queue: asyncio.Queue, *, seq: str, search_type="0", stex_tp="K", cont_yn="N", next_key="") -> Dict[str, Any]:
    """CNSRREQ 1회 호출"""
    payload = {
        "trnm": "CNSRREQ",
        "seq": str(seq).strip(),
        "search_type": str(search_type),
        "stex_tp": str(stex_tp),
        "cont_yn": str(cont_yn),
        "next_key": str(next_key),
    }
    await ws.send(json.dumps(payload))
    resp = await recv_until(queue, "CNSRREQ", timeout=10.0)
    if resp.get("return_code") not in (None, 0):
        raise RuntimeError(f"CNSRREQ 실패: {resp.get('return_msg')}")
    return resp

def extract_codes_from_cnsrreq(data: Any) -> List[str]:
    out: List[str] = []
    if isinstance(data, list):
        for itm in data:
            if isinstance(itm, dict):
                code = norm_code(itm.get("9001") or itm.get("code") or itm.get("stk_cd"))
                if code:
                    out.append(code)
    # 중복 제거(순서 유지)
    return list(dict.fromkeys(out))

async def fetch_condition_codes(token: str, seq: str, stex_tp: str = "K") -> List[str]:
    """CNSRLST로 seq 검증 → CNSRREQ(연속조회 자동) → 종목코드 수집"""
    async with websockets.connect(WS_URL) as ws:
        await login(ws, token)
        queue: asyncio.Queue = asyncio.Queue()
        # 단일 수신자 태스크 가동
        reader_task = asyncio.create_task(reader(ws, queue))

        # (선택) seq 유효성 검증: 목록에서 존재 확인
        conds = await request_condition_list(ws, queue)
        has = any(c and c[0].strip() == str(seq).strip() for c in conds if isinstance(c, list) and len(c) >= 1)
        if not has:
            # 존재하지 않는 seq면 서버가 응답 안 줄 수 있음 → 여기서 빠르게 실패
            raise ValueError(f"조건식 seq={seq} 가 목록에 없습니다. 목록: {conds}")

        # CNSRREQ 연속조회
        all_codes: List[str] = []
        cont_yn, next_key = "N", ""
        while True:
            resp = await request_cnsrreq_once(ws, queue,
                                              seq=str(seq).strip(),
                                              search_type="0",
                                              stex_tp=stex_tp,
                                              cont_yn=cont_yn,
                                              next_key=next_key)
            batch = extract_codes_from_cnsrreq(resp.get("data", []))
            all_codes.extend(batch)

            cont = (resp.get("cont_yn") or resp.get("cont-yn") or "N").strip().upper()
            nk = (resp.get("next_key") or resp.get("next-key") or "").strip()
            if cont == "Y" and nk:
                cont_yn, next_key = "Y", nk
                continue
            break

        reader_task.cancel()
        # 정리
        try:
            await reader_task
        except asyncio.CancelledError:
            pass

        # 최종 중복 제거
        return list(dict.fromkeys(all_codes))


async def _login_only(ws, token: str) -> None:
    await ws.send(json.dumps({"trnm": "LOGIN", "token": token}))
    while True:
        msg = json.loads(await ws.recv())
        t = msg.get("trnm")
        if t == "PING":
            await ws.send(json.dumps(msg))  # pong
            continue
        if t == "LOGIN":
            if msg.get("return_code") != 0:
                raise RuntimeError(f"로그인 실패: {msg.get('return_msg')}")
            return

async def _recv_until_trnm(ws, want: str) -> dict:
    while True:
        msg = json.loads(await ws.recv())
        t = msg.get("trnm")
        if t == "PING":
            await ws.send(json.dumps(msg))
            continue
        if t == want:
            return msg

async def fetch_condition_list(token: str) -> List[List[str]]:
    """
    CNSRLST: 조건검색식 목록 조회
    반환 예시: [['0','배당주'], ['1','코스닥대상'], ...]
    """
    async with websockets.connect(WS_URL) as ws:
        await _login_only(ws, token)
        await ws.send(json.dumps({"trnm": "CNSRLST"}))
        resp = await _recv_until_trnm(ws, "CNSRLST")
        if resp.get("return_code") != 0:
            raise RuntimeError(f"CNSRLST 실패: {resp.get('return_msg')}")
        return resp.get("data", [])
    
if __name__ == "__main__":
    import os
    
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    with open(os.path.join(project_root, "access_token.txt"), "r", encoding="utf-8") as f:
        token = f.read().strip()

    # 예: seq=2, KRX
    codes = asyncio.run(fetch_condition_codes(token, seq="0", stex_tp="K"))
    print("코드 개수:", len(codes))
    print("예시 20개:", codes[:20])
