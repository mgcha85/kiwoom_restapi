# -*- coding: utf-8 -*-
"""
AccountService로 예수금/계좌 현황을 조회하고,
보유 종목의 분할 진행도를 DB에서 읽어온 뒤,
bet_allocator 모듈로 다음 1유닛 베팅액을 계산하는 엔드투엔드 테스트.
"""

import os
import sys
import sqlite3
from decimal import Decimal

# 프로젝트 루트 세팅
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from api.account_service import AccountService
from trading.bet_allocator import BetSizingConfig, compute_bet_unit

# ---------------------------------------------------------------------
# 1) 토큰 로드 & AccountService 준비
# ---------------------------------------------------------------------
with open(os.path.join(project_root, "access_token.txt"), "r", encoding="utf-8") as f:
    token = f.read().strip()

account_service = AccountService(token=token)

# ---------------------------------------------------------------------
# 2) 계좌 / 자산 조회
# ---------------------------------------------------------------------
asset = account_service.get_asset(data={"qry_tp": "0"})  # 추정자산(모의투자 예: prsm_dpst_aset_amt)
status = account_service.get_status(data={"qry_tp": "0", "dmst_stex_tp": "KRX"})  # 계좌평가현황
details = account_service.get_account_details(data={"qry_tp": "3"})  # 예수금 상세 현황

print("==== [원시 조회 결과 요약] ====")
print("자산(Asset):", asset)
print("계좌평가현황(Status):", status)
print("예수금상세(Details):", details)

# ---------------------------------------------------------------------
# 3) 가용 현금 계산
#    - 우선순위(권장): details.ord_alow_amt(주문가능금액) → details.pymn_alow_amt(지급가능) → asset.prsm_dpst_aset_amt(추정예탁자산)
# ---------------------------------------------------------------------
def _to_decimal_safe(v) -> Decimal:
    if v is None:
        return Decimal("0")
    if isinstance(v, (int, float, Decimal)):
        return Decimal(str(v))
    s = str(v).strip()
    if s == "":
        return Decimal("0")
    # "000000001234" 같은 문자열도 Decimal로 변환
    try:
        return Decimal(s)
    except Exception:
        return Decimal("0")

available_cash = Decimal("0")

if details and getattr(details, "ord_alow_amt", None) is not None:
    available_cash = _to_decimal_safe(details.ord_alow_amt)
elif details and getattr(details, "pymn_alow_amt", None) is not None:
    available_cash = _to_decimal_safe(details.pymn_alow_amt)
elif asset and getattr(asset, "prsm_dpst_aset_amt", None) is not None:
    available_cash = _to_decimal_safe(asset.prsm_dpst_aset_amt)

print(f"\n가용 현금(우선순위 적용): {available_cash:,} 원")

# ---------------------------------------------------------------------
# 4) DB에서 보유 종목의 현재 분할 진행도(n_trade 등) 읽기
#    - sqlite DB 경로는 프로젝트 환경에 맞게 조정하세요.
#    - 테이블: hold_list (컬럼: code, n_trade 등) 가정
# ---------------------------------------------------------------------
# 예시: src/db/{파일}.sqlite3 를 쓰고 있다면 아래 경로로 바꾸세요.
# 여기서는 프로젝트 루트에 'trading.sqlite3' 가 있다고 가정합니다.
sqlite_path = os.path.join(project_root, "trading.sqlite3")
completed_splits: list[int] = []

if os.path.exists(sqlite_path):
    try:
        con = sqlite3.connect(sqlite_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        # n_trade(분할 진행도)이 없으면 1로 가정
        cur.execute("""
            SELECT code,
                   COALESCE(n_trade, 0) AS n_trade
            FROM hold_list
        """)
        rows = cur.fetchall()
        for r in rows:
            completed_splits.append(int(r["n_trade"]))
        con.close()
        print(f"\nDB 보유 포지션 수: {len(completed_splits)}개")
        if completed_splits:
            print("각 포지션의 현재 분할 진행도(n_trade):", completed_splits)
    except Exception as e:
        print(f"\n[경고] hold_list 조회 실패: {e}")
else:
    print(f"\n[안내] sqlite 파일이 없어 보유분할은 빈 리스트로 진행합니다: {sqlite_path}")

# ---------------------------------------------------------------------
# 5) 베팅 규칙 설정 & 1유닛 베팅액 계산
#    - 예시: 최대 4종목 보유, 각 4분할, 포지션별 1유닛 예약(보수적)
# ---------------------------------------------------------------------
cfg = BetSizingConfig(max_positions=4, max_splits=4, reserve_one_per_position=True)

unit_krw, denom = compute_bet_unit(
    cash_krw=available_cash,
    completed_splits_per_position=completed_splits,
    cfg=cfg,
    quantize_to=Decimal("1"),  # 원 단위 절사
)

print("\n==== [베팅 계산 결과] ====")
print(f"총 유닛 = {cfg.max_positions} x {cfg.max_splits} = {cfg.max_positions * cfg.max_splits}")
print(f"보유 포지션 분할 진행도 = {completed_splits} (합계={sum(completed_splits)})")
print(f"reserve_one_per_position = {cfg.reserve_one_per_position}")
print(f"분모(남은 유닛, 예약 반영) = {denom}")
print(f"다음 1유닛 베팅액 = {unit_krw:,} 원")

# 참고) 종목 현재가로 수량 환산:
# current_price = Decimal("70000")
# qty = int(unit_krw // current_price)
# print("이 종목에 매수 가능한 수량:", qty)
