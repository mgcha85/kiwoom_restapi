# src/models/account_model.py
from typing import Optional, List, Any
from pydantic import BaseModel, validator


# 요청하신 모델 1: 간단 자산 응답 ----------------------------------------
class AssetResponse(BaseModel):
    prsm_dpst_aset_amt: int  # 예: "00000530218" -> 530218
    return_code: int
    return_msg: str


# 요청하신 모델 2: 상세 계좌 응답(필드 많음) ------------------------------
class AccountDetailResponse(BaseModel):
    entr: Optional[int] = None  # 예: '000000003253351' -> 3253351
    profa_ch: Optional[int] = None
    bncr_profa_ch: Optional[int] = None
    nxdy_bncr_sell_exct: Optional[int] = None
    fc_stk_krw_repl_set_amt: Optional[int] = None
    crd_grnta_ch: Optional[int] = None
    crd_grnt_ch: Optional[int] = None
    add_grnt_ch: Optional[int] = None
    etc_profa: Optional[int] = None
    uncl_stk_amt: Optional[int] = None
    shrts_prica: Optional[int] = None
    crd_set_grnta: Optional[int] = None
    chck_ina_amt: Optional[int] = None
    etc_chck_ina_amt: Optional[int] = None
    crd_grnt_ruse: Optional[int] = None
    knx_asset_evltv: Optional[int] = None
    elwdpst_evlta: Optional[int] = None
    crd_ls_rght_frcs_amt: Optional[int] = None
    lvlh_join_amt: Optional[int] = None
    lvlh_trns_alowa: Optional[int] = None
    repl_amt: Optional[int] = None
    remn_repl_evlta: Optional[int] = None
    trst_remn_repl_evlta: Optional[int] = None
    bncr_remn_repl_evlta: Optional[int] = None
    profa_repl: Optional[int] = None
    crd_grnta_repl: Optional[int] = None
    crd_grnt_repl: Optional[int] = None
    add_grnt_repl: Optional[int] = None
    rght_repl_amt: Optional[int] = None
    pymn_alow_amt: Optional[int] = None
    wrap_pymn_alow_amt: Optional[int] = None
    ord_alow_amt: Optional[int] = None
    bncr_buy_alowa: Optional[int] = None
    twenty_stk_ord_alow_amt: Optional[int] = None
    thirty_stk_ord_alow_amt: Optional[int] = None
    forty_stk_ord_alow_amt: Optional[int] = None
    hundred_stk_ord_alow_amt: Optional[int] = None
    fifty_stk_ord_alow_amt: Optional[int] = None
    sixty_stk_ord_alow_amt: Optional[int] = None
    stk_entr_prst: Optional[List[str]] = None  # 필요 시 구조에 맞게 별도 모델로 확장 가능

    return_code: int
    return_msg: str


# (확장) kt00004: 계좌평가현황요청 응답 모델 -------------------------------

class StkAccountEvalItem(BaseModel):
    """stk_acnt_evlt_prst 리스트의 각 아이템(종목별 평가 현황)"""
    stk_cd: Optional[str] = None    # 'A005930' 등
    stk_nm: Optional[str] = None
    rmnd_qty: Optional[int] = None  # 보유수량
    avg_prc: Optional[int] = None   # 평균단가
    cur_prc: Optional[int] = None   # 현재가
    evlt_amt: Optional[int] = None  # 평가금액
    pl_amt: Optional[int] = None    # 손익금액 (음수 가능)
    pl_rt: Optional[float] = None   # 손익율 (예: '-43.8977')
    loan_dt: Optional[str] = None
    pur_amt: Optional[int] = None   # 매입금액
    setl_remn: Optional[int] = None # 결제잔고
    pred_buyq: Optional[int] = None
    pred_sellq: Optional[int] = None
    tdy_buyq: Optional[int] = None
    tdy_sellq: Optional[int] = None


class AccountEvalResponse(BaseModel):
    """
    kt00004 응답 전체를 표현:
      - 상단 요약 필드들(예수금, 평가액 등)
      - 종목별 계좌평가현황 리스트(stk_acnt_evlt_prst)
      - return_code / return_msg
    """
    acnt_nm: Optional[str] = None
    brch_nm: Optional[str] = None

    entr: Optional[int] = None                 # 예수금
    d2_entra: Optional[int] = None            # D+2 추정예수금
    tot_est_amt: Optional[int] = None         # 유가잔고평가액
    aset_evlt_amt: Optional[int] = None       # 예탁자산평가액
    tot_pur_amt: Optional[int] = None         # 총매입금액
    prsm_dpst_aset_amt: Optional[int] = None  # 추정예탁자산
    tot_grnt_sella: Optional[int] = None
    tdy_lspft_amt: Optional[int] = None
    invt_bsamt: Optional[int] = None
    lspft_amt: Optional[int] = None
    tdy_lspft: Optional[int] = None
    lspft2: Optional[int] = None
    lspft: Optional[int] = None
    tdy_lspft_rt: Optional[float] = None
    lspft_ratio: Optional[float] = None
    lspft_rt: Optional[float] = None

    stk_acnt_evlt_prst: Optional[List[StkAccountEvalItem]] = None

    return_code: int
    return_msg: str
