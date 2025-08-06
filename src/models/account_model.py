from pydantic import BaseModel
from typing import Optional, List


class AssetResponse(BaseModel):
    prsm_dpst_aset_amt: int  # 예시: "00000530218"
    return_code: int
    return_msg: str


class AccountDetailResponse(BaseModel):
    entr: Optional[int] = None  # 예시: '000000003253351' -> 3253351
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
    stk_entr_prst: Optional[List[str]] = None  # 주식 진입 내역이 있을 경우 리스트로

    return_code: int
    return_msg: str