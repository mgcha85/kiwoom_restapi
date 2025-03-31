# src/models/stock_model.py

from pydantic import BaseModel
from typing import Optional

class StockInfo(BaseModel):
    """
    주식 기본 정보에 대한 Pydantic 모델입니다.
    실제 API 응답 필드에 맞게 수정 가능합니다.
    """
    stk_cd: str                   # 종목코드
    stk_nm: Optional[str] = None    # 종목명
    setl_mm: Optional[str] = None   # 결산월
    fav: Optional[str] = None       # 액면가
    cap: Optional[str] = None       # 자본금
    flo_stk: Optional[str] = None   # 상장주식수
    crd_rt: Optional[str] = None    # 신용비율
    oyr_hgst: Optional[str] = None  # 연중최고
    oyr_lwst: Optional[str] = None  # 연중최저
    mac: Optional[str] = None       # 시가총액
    mac_wght: Optional[str] = None  # 시가총액비중
    for_exh_rt: Optional[str] = None# 외인소진률
    repl_pric: Optional[str] = None # 대용가
    per: Optional[str] = None       # PER
    eps: Optional[str] = None       # EPS
    roe: Optional[str] = None       # ROE
    pbr: Optional[str] = None       # PBR
    ev: Optional[str] = None        # EV
    bps: Optional[str] = None       # BPS
    sale_amt: Optional[str] = None  # 매출액
    bus_pro: Optional[str] = None   # 영업이익
    cup_nga: Optional[str] = None   # 당기순이익
    # 필드명이 숫자로 시작할 수 없으므로, 예를 들어 "250hgst"는 "hsthgst"로 변경합니다.
    hsthgst: Optional[str] = None   # 250최고가
    hsthlwst: Optional[str] = None   # 250최저가
    high_pric: Optional[str] = None  # 고가
    open_pric: Optional[str] = None  # 시가
    low_pric: Optional[str] = None   # 저가
    upl_pric: Optional[str] = None   # 상한가
    lst_pric: Optional[str] = None   # 하한가
    base_pric: Optional[str] = None  # 기준가
    exp_cntr_pric: Optional[str] = None  # 예상체결가
    exp_cntr_qty: Optional[str] = None   # 예상체결수량
    hsthgst_pric_dt: Optional[str] = None   # 250최고가일
    hsthgst_pric_pre_rt: Optional[str] = None # 250최고가대비율
    hsthlwst_pric_dt: Optional[str] = None   # 250최저가일
    hsthlwst_pric_pre_rt: Optional[str] = None # 250최저가대비율
    cur_prc: Optional[str] = None    # 현재가
    pre_sig: Optional[str] = None    # 대비기호
    pred_pre: Optional[str] = None   # 전일대비
    flu_rt: Optional[str] = None     # 등락율
    trde_qty: Optional[str] = None   # 거래량
    trde_pre: Optional[str] = None   # 거래대비
    fav_unit: Optional[str] = None   # 액면가단위
    dstr_stk: Optional[str] = None   # 유통주식
    dstr_rt: Optional[str] = None    # 유통비율
