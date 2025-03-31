# src/models/order_model.py

from pydantic import BaseModel
from typing import Optional

class StockOrderRequest(BaseModel):
    """
    주식 주문 요청에 대한 Pydantic 모델입니다.
    API 요청에 필요한 필드와 타입을 정의합니다.
    """
    dmst_stex_tp: str  # 국내거래소구분 (예: KRX, NXT, SOR)
    stk_cd: str        # 종목코드
    ord_qty: str       # 주문수량
    ord_uv: Optional[str] = None  # 주문단가 (시장가 주문의 경우 빈 값)
    trde_tp: str       # 매매구분 (예: 0:보통, 3:시장가 등)
    cond_uv: Optional[str] = None # 조건단가

class StockOrderResponse(BaseModel):
    """
    주식 주문 응답에 대한 Pydantic 모델입니다.
    API 응답에 포함된 주문번호와 상태 정보를 포함합니다.
    """
    ord_no: str               # 주문번호
    dmst_stex_tp: Optional[str] = None  # 국내거래소구분
    return_code: int          # 결과 코드 (0: 정상)
    return_msg: str           # 결과 메시지
