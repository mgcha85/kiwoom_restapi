from __future__ import annotations
import logging
from typing import Dict, Tuple, List, Optional

import pandas as pd

# 프로젝트 내부 유틸/서비스 경로로 교체
from trading.indicators import compute_indicators           # 기존 services.indicators -> trading.indicators 로 배치 권장
from utils.calculate_utils import calculate_tick_price
from utils.config_utils import open_yaml                    # 유지
from api.order import OrderAPI

# (선택) 보유종목 목록/한도 관리가 있으면 연결, 없으면 pass
try:
    from db.portfolio import get_hold_list  # 사용자가 만들었을 수도 있음
except Exception:
    def get_hold_list():
        # DataFrame-like (index=ticker, columns=['num_buy']) 를 기대하던 코드 호환용 stub
        return pd.DataFrame(columns=["num_buy"]).set_index(pd.Index([], name="ticker"))


# --------------------------
# 옵션: CatBoost 추론 훅
# --------------------------
def inference_with_model(X) -> bool:
    """
    분류 모델이 있으면 True(매수 신호) 반환.
    없으면 항상 True로 취급하거나, 설정에서 끌 수 있음.
    """
    try:
        from catboost import CatBoostClassifier
        model = CatBoostClassifier()
        model.load_model("inference/catboost_model.cbm")
        pred = model.predict(X)
        return pred[0] == 0
    except Exception:
        # 모델이 없거나 로드 실패해도 파이프라인이 돌아가도록 기본 True
        return True


# --------------------------
# 필터 함수 (기존 로직 유지)
# --------------------------
def filter1(df: pd.DataFrame) -> bool:
    print(f"cor: {df['COR'].iloc[-1]:0.2f}, vrate: {df['vrate'].iloc[-1]:0.2f}")
    return df['COR'].iloc[-1] > 0.03 and df['vrate'].iloc[-1] > 8

def filter2(df: pd.DataFrame, market: str) -> bool:
    if market == 'KQ':
        print(f"""
        [{market}] 
        vrate: {df['vrate'].iloc[-1]:0.2f}, 
        LOR: {df['LOR'].iloc[-1]:0.2f}, 
        HOR: {df['HOR'].iloc[-1]:0.2f}, 
        ADX: {df['ADX'].iloc[-1]:0.2f}, 
        HCR: {df['HCR'].iloc[-1]:0.2f}, 
        HLR: {df['HLR'].iloc[-1]:0.2f}, 
        LCR: {df['LCR'].iloc[-1]:0.2f}, 
        mapct_20: {df['mapct_20'].iloc[-1]:0.2f}, 
        mapct_200: {df['mapct_200'].iloc[-1]:0.2f}
        """)
        return 0.15 <= df['vrate'].iloc[-1] < 35 and \
            df['LOR'].iloc[-1] > -0.1 and \
            df['HOR'].iloc[-1] > 0.1 and \
            df['ADX'].iloc[-1] > 15 and \
            df['HCR'].iloc[-1] > 0.033 and \
            df['HLR'].iloc[-1] > 0.2 and \
            -0.3 < df['LCR'].iloc[-1] < -0.04 and \
            df['mapct_20'].iloc[-1] < 1 and \
            0.05 < df['mapct_200'].iloc[-1] < 1.5
    else:
        print(f"""
        [{market}] 
        vrate: {df['vrate'].iloc[-1]:0.2f}, 
        HOR: {df['HOR'].iloc[-1]:0.2f}, 
        HCR: {df['HCR'].iloc[-1]:0.2f}, 
        mapct_20: {df['mapct_20'].iloc[-1]:0.2f}, 
        mapct_60: {df['mapct_60'].iloc[-1]:0.2f}, 
        RSI: {df['RSI'].iloc[-1]:0.2f}, 
        CCI: {df['CCI'].iloc[-1]:0.2f}, 
        SMI: {df['SMI'].iloc[-1]:0.2f}, 
        OBV: {df['OBV'].iloc[-1]:0.2f}, 
        DIV: {df['DIV'].iloc[-1]:0.2f}, 
        DPS: {df['DPS'].iloc[-1]:0.2f}, 
        correct_days: {df['correct_days'].iloc[-1]:0.2f}, 
        recover_days: {df['recover_days'].iloc[-1]:0.2f}
        """)
        return df['vrate'].iloc[-1] < 40 and \
            df['HOR'].iloc[-1] > 0.13 and \
            df['HCR'].iloc[-1] > 0.025 and \
            df['mapct_20'].iloc[-1] < 2 and \
            df['mapct_60'].iloc[-1] > -0.2 and \
            df['RSI'].iloc[-1] < 73 and \
            df['CCI'].iloc[-1] < 600 and \
            df['SMI'].iloc[-1] < 57 and \
            df['OBV'].iloc[-1] < 3E9 and \
            df['DIV'].iloc[-1] < 8 and \
            df['DPS'].iloc[-1] < 600 and \
            df['correct_days'].iloc[-1] > 165 and \
            df['recover_days'].iloc[-1] < 700 and \
            df['days_since_max_high'].iloc[-1] > 100

def filter3(df: pd.DataFrame, config: dict) -> bool:
    X = df[config.get('features', [])].iloc[-1:, :].values if config.get('features') else None
    return True if X is None else inference_with_model(X)

def filtering(df: pd.DataFrame, config: dict, market='KS') -> bool:
    return filter1(df) and filter2(df, market)  # and filter3(df, config)


# --------------------------
# 분석 → 매수 시그널
# --------------------------
def analyze_stocks(
    data: Dict[str, pd.DataFrame],
    config: dict,
    *,
    use_fundamental: bool = False,
    fundamental_df: Optional[pd.DataFrame] = None,
    last_ohlcv_lookup: Optional[Dict[str, Dict[str, float]]] = None,
) -> Dict[str, Tuple[str, float]]:
    """
    data: {'005930.KS': df, '000660.KS': df, ...} 형태 (df는 최소 ['date','close',...])
    return: {'005930': ('BUY', buy_price_basis), ...}
    """
    logging.info("Analyzing stocks...")

    if not data:
        logging.warning("No data for analysis.")
        return {}

    # (옵션) 펀더멘털/최근 거래대금 등 추가 병합
    # - 프로젝트 내 통합 DB가 아직 없다면, 외부 sqlite 의존을 제거하고
    #   호출 측에서 fundamental_df/last_ohlcv_lookup을 주입하는 방식으로 유지
    signals: Dict[str, Tuple[str, float]] = {}

    for code_with_market, df in data.items():
        # code_with_market: "005930.KS" or "005930.KQ"
        try:
            code, market = code_with_market.split('.')
        except ValueError:
            code, market = code_with_market, 'KS'

        # (옵션) 펀더멘털 머지
        if use_fundamental and (fundamental_df is not None) and (code in fundamental_df.index):
            ser = fundamental_df.loc[code]
            for k, v in ser.items():
                df[k] = v

        # (옵션) 마지막 캔들 보조 정보(거래대금 등)
        if last_ohlcv_lookup and code_with_market in last_ohlcv_lookup:
            for k, v in last_ohlcv_lookup[code_with_market].items():
                df[k] = v

        # dtype 정리
        if 'date' in df.columns:
            # 'date'가 20240814 같은 정수/문자라면 datetime으로 변환
            if pd.api.types.is_numeric_dtype(df['date']):
                df['date'] = pd.to_datetime(df['date'].astype(int), format='%Y%m%d')
            else:
                df['date'] = pd.to_datetime(df['date'])
        else:
            # 인덱스가 datetime이라면 그대로 사용
            pass

        # 인디케이터 계산
        df = df.copy()
        if 'date' in df.columns:
            df = compute_indicators(df.set_index('date'))
        else:
            df = compute_indicators(df)

        print("====== ", code, " ======")
        if filtering(df, config, market):
            signals[code] = ("BUY", float(df['close'].iloc[-1]))

    logging.info(f"Analysis signals: {signals}")
    return signals


# --------------------------
# 시그널 → 주문 목록 작성
# --------------------------
def fill_orders(
    balance: float,
    signals: Dict[str, Tuple[str, float]],
    trade_config: dict
) -> List[Tuple[str, str, str, int]]:
    """
    return: [(code, 'BUY', qty_str, price_int), ...]
    - qty는 정수 문자열(키움 REST 스펙), price는 호가단위 반영된 int
    """
    hold_list = get_hold_list()  # index=ticker, columns=['num_buy'] 가정(없으면 빈 DF)

    n_balance = balance / trade_config.get('n_split', 1) / trade_config.get('max_hold_stocks', 1)
    print("n_balance: ", n_balance)

    orders: List[Tuple[str, str, str, int]] = []
    for code, (action, price_basis) in signals.items():
        if code in hold_list.index:
            n_buy = hold_list.loc[code].get('num_buy', 0)
            if n_buy >= trade_config.get('max_buy_per_stock', 4):
                continue

        # 가격 산정: 기본은 현재가의 1.01배 후 호가 반올림 → 지정가 매수용
        target_price = int(price_basis * trade_config.get('buy_price_multiplier', 1.01))
        target_price = calculate_tick_price(target_price)

        qty_int = max(int(n_balance // target_price), 0)
        if qty_int <= 0:
            continue

        orders.append((code, action, str(qty_int), int(target_price)))
    return orders


# --------------------------
# 주문 전송 (REST)
# --------------------------
def send_orders_with_orderapi(
    orders: List[Tuple[str, str, str, int]],
    *,
    token: str,
    market_code: str = "KRX",
    order_type: str = "market"  # "market" or "limit"
) -> List[dict]:
    """
    orders: [(code, 'BUY', qty_str, price_int), ...]
    order_type:
      - "market": trde_tp="3", ord_uv="" (시장가)
      - "limit" : trde_tp="0", ord_uv=가격  (지정가)
    """
    api = OrderAPI()
    results: List[dict] = []

    for code, action, qty, price in orders:
        # REST 스펙에 맞춰 페이로드 구성
        if order_type == "market":
            trde_tp = "3"; ord_uv = ""
        else:
            trde_tp = "0"; ord_uv = str(price)

        payload = {
            "dmst_stex_tp": market_code,  # "KRX"
            "stk_cd": code,               # "005930"
            "ord_qty": qty,               # "1"
            "ord_uv": ord_uv,             # "" or "70000"
            "trde_tp": trde_tp,           # "3" market / "0" limit
            "cond_uv": ""
        }

        if action.upper() == "BUY":
            resp = api.stock_buy_order(token=token, order_data=payload)
        else:
            resp = api.stock_sell_order(token=token, order_data=payload)

        print(f"[ORDER] {action} {code} x{qty} @{ord_uv or 'MKT'} -> {resp}")
        results.append(resp)

    return results


# --------------------------
# 엔드투엔드: 한 번에 실행
# --------------------------
def run_once_for_signals_and_orders(
    data: Dict[str, pd.DataFrame],
    *,
    config_path: str,
    balance: float,
    token: str,
    place_orders: bool = True,
    market_code: str = "KRX",
    order_type: str = "market"
) -> Dict[str, Tuple[str, float]]:
    """
    1) config 로딩 → 2) 분석 → 3) 주문목록 생성 → 4) 주문 전송(옵션)
    return: signals (분석 결과)
    """
    cfg = open_yaml(config_path) if config_path else {}
    trade_config = cfg.get("trade", {"n_split": 1, "max_hold_stocks": 10, "max_buy_per_stock": 4, "buy_price_multiplier": 1.01})

    signals = analyze_stocks(data, cfg.get("features_cfg", {}))
    orders = fill_orders(balance, signals, trade_config)

    if not orders:
        print("[RUN] No orders to place.")
        return signals

    if place_orders:
        send_orders_with_orderapi(
            orders,
            token=token,
            market_code=market_code,
            order_type=order_type
        )
        # 주문/체결/포지션/트레이드 업데이트는 WS가 담당 (ws_consumer.py)
    return signals
