from pydantic import BaseModel
from typing import Optional, Literal
from datetime import datetime

# websockets 수신 JSON을 구조화 (키움 이벤트 필드명에 맞춰 수정)
class ExecutionEvent(BaseModel):
    event_type: Literal["execution"]
    account_id: str
    ticker: str
    market: str
    order_no: str
    exec_id: str
    side: Literal["BUY", "SELL"]
    qty: float
    price: float
    commission: float = 0
    tax: float = 0
    exec_time: Optional[datetime] = None

class OrderEvent(BaseModel):
    event_type: Literal["order"]
    order_no: str
    status: str
    account_id: str
    ticker: str
    side: Literal["BUY", "SELL"]
    qty: float
    price: float
    placed_at: Optional[datetime] = None
