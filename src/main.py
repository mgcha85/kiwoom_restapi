import os
import sys
import logging
import pause
from decimal import Decimal
from time import sleep
from datetime import datetime

# sys path 설정
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
src_path = os.path.join(project_root, 'src')
sys.path.append(src_path)

# 서비스 모듈 import
from src.api.oauth import OAuthClient
from src.api.market import MarketAPI
from src.api.account_service import AccountService
from src.api.order import OrderAPI
from src.db.hold_sqlite import get_hold_list
from src.db.db import create_order, init_db
from utils.calculate_utils import calculate_tick_price
from src.helpers import *

# 로깅 설정
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

HOLD_INTERVAL = 0.5
ACCOUNT_ID = os.getenv("KIWOOM_ACCOUNT_ID", "ACC1")

def open_yaml(file_path: str):
    import yaml
    """
    YAML 파일을 안전하게 열어서 Python 딕셔너리 형태로 반환합니다.
    """
    with open(file_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    return data


# 현재가 조회
def get_current_price(token: str, stock_code: str) -> int:
    market = MarketAPI()
    info = market.get_stock_info(token=token, stock_code=stock_code)
    return int(info.get("last", 0))

# 매도 주문
def place_sell_order(token: str, code: str, qty: int, price: int):
    order_api = OrderAPI()
    order_data = {
        "dmst_stex_tp": "KRX",
        "stk_cd": code,
        "ord_qty": str(qty),
        "ord_uv": str(price),
        "trde_tp": "0",  # 보통
        "cond_uv": ""
    }
    resp = order_api.stock_sell_order(token, order_data)
    logging.info(f"[SELL] {code}, qty={qty}, price={price}, resp={resp}")
    if resp.get("return_code") == 0:
        create_order(
            order_no=str(resp["ord_no"]),
            account_id=ACCOUNT_ID,
            ticker=code,
            side="SELL",
            qty=Decimal(qty),
            price=Decimal(price),
            status="PLACED",
            placed_at=datetime.now()
        )

# 매수 주문
def place_buy_order(token: str, code: str, qty: int, price: int):
    order_api = OrderAPI()
    order_data = {
        "dmst_stex_tp": "KRX",
        "stk_cd": code,
        "ord_qty": str(qty),
        "ord_uv": str(price),
        "trde_tp": "0",
        "cond_uv": ""
    }
    resp = order_api.stock_buy_order(token, order_data)
    logging.info(f"[BUY] {code}, qty={qty}, price={price}, resp={resp}")
    if resp.get("return_code") == 0:
        create_order(
            order_no=str(resp["ord_no"]),
            account_id=ACCOUNT_ID,
            ticker=code,
            side="BUY",
            qty=Decimal(qty),
            price=Decimal(price),
            status="PLACED",
            placed_at=datetime.now()
        )

# 잔고 계산
def cal_account_balance(seed: float) -> float:
    # 실제 잔고는 get_asset 으로 가져올 수 있지만, seed 값 그대로 사용
    return seed

# 09:00 매도 주문
def opening_orders(token: str, config: dict):
    hold_list = get_hold_list()
    for code, row in hold_list.iterrows():
        sleep(HOLD_INTERVAL)
        avg_price = row["avg_price"]
        qty = row["qty"]
        current_price = get_current_price(token, code)
        if current_price == 0:
            logging.warning(f"[{code}] 현재가 조회 실패")
            continue

        sell_price = int(avg_price * config['sell_price_adjustment'])
        sell_price = calculate_tick_price(sell_price)

        if current_price * 1.2 > sell_price:
            place_sell_order(token, code, qty, sell_price)
        else:
            logging.info(f"[{code}] 상한가 초과, 매도 스킵")

# 15:20 매수 주문
def closing_buy_orders(token: str, config: dict):
    hold_list = get_hold_list()
    max_hold = config['max_hold_stocks']
    if hold_list.shape[0] >= max_hold:
        logging.info(f"보유 종목이 {max_hold}개 이상입니다.")
        return

    balance = cal_account_balance(config['seeds'])
    if balance == 0:
        logging.info("매수 가능 잔고가 없습니다.")
        return

    # 조건 검색식 기반 종목 코드 조회
    from src.trading.condition_ws import fetch_condition_codes
    import asyncio
    codes = asyncio.run(fetch_condition_codes(token, seq="2", stex_tp="K"))[:max_hold]

    for code in codes:
        sleep(HOLD_INTERVAL)
        price = get_current_price(token, code)
        if price == 0:
            continue
        qty = int(balance // (price * len(codes)))
        buy_price = calculate_tick_price(price)
        place_buy_order(token, code, qty, buy_price)

# 메인 함수
def main():
    config = open_yaml("config.yaml")
    token = get_access_token()
    init_db()

    now = datetime.now()
    open_time = now.replace(**config['time_settings']['open_time'])
    close_time = now.replace(**config['time_settings']['close_time'])
    download_time = now.replace(**config['time_settings']['download_time'])

    if now < open_time:
        logging.info(f"Open time까지 대기: {open_time}")
        pause.until(open_time)
        opening_orders(token, config['trade'])

    now = datetime.now()
    if now < close_time:
        logging.info(f"Close time까지 대기: {close_time}")
        pause.until(close_time)
        closing_buy_orders(token, config['trade'])

    now = datetime.now()
    if now < download_time:
        logging.info(f"Download time까지 대기: {download_time}")
        pause.until(download_time)

    revoke_access_token()
    

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logging.info("중지되었습니다.")
        sys.exit(0)
