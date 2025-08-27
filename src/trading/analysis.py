import logging
import pandas as pd
import sqlite3
# import torch
from src.trading.indicators import compute_indicators
from db.hold_sqlite import get_hold_list
from utils.calculate_utils import calculate_tick_price
from typing import List


def get_last_day_fundamental(con):
    cursor = con.cursor()
    
    # 데이터베이스에서 모든 테이블 이름을 조회
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name DESC")
    
    # 첫 번째 테이블 이름을 가져옴
    first_table_name = cursor.fetchone()
    
    if first_table_name:
        return first_table_name[0]
    else:
        return None

def inference_with_model(X):
    from catboost import CatBoostClassifier
    # Load the model
    loaded_model = CatBoostClassifier()
    loaded_model.load_model('inference/catboost_model.cbm')
    
    # Now you can use the loaded model to make predictions
    y_pred_loaded = loaded_model.predict(X)
    return y_pred_loaded[0] == 0

def filter1(df):
    print(f"cor: {df['COR'].iloc[-1]:0.2f}, vrate: {df['vrate'].iloc[-1]:0.2f}")
    return df['COR'].iloc[-1] > 0.03 and df['vrate'].iloc[-1] > 8

def filter2(df, market):
    # amount = df['volume'] * df['close']
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

def filter3(df, config):
    X = df[config['features']].iloc[-1:, :].values
    return inference_with_model(X)

def filtering(df, config, market='KS'):
    return filter1(df) and filter2(df, market) # and filter3(df, config)

def analyze_stocks(data: dict, config: dict) -> dict:
    """
    머신러닝 모델 등을 이용하여 매수/매도 시그널을 생성.
    - data: 종목별 일봉 데이터 (또는 분봉)
    - return: 분석 결과. 예) { '000660': ('BUY', 57000), '005930': ('SELL', 60000), ... }
    """
    logging.info("Analyzing stocks using ML models...")

    if len(data) == 0:
        logging.warning("No data for analysis.")
        return {}

    con = sqlite3.connect('sqlite3/fundamental.db')
    tname = get_last_day_fundamental(con)
    df_funda = pd.read_sql(f"SELECT * FROM '{tname}'", con, index_col='티커')
    con.close()

    con = sqlite3.connect('sqlite3/candle_data.db')

    # 아래는 단순 예시(다 BUY)
    signals = {}
    for code_, df in data.items():
        code, market = code_.split('.')
        if code not in df_funda.index:
            continue
        
        df_old = pd.read_sql(f"SELECT 시가총액, 거래대금 FROM (SELECT * FROM '{code_}' ORDER BY Date DESC LIMIT 1)", con)
        for key, value in pd.concat([df_funda.loc[code], df_old.loc[0]]).items():
            df[key] = value

        df = df.astype(float)
        df['date'] = pd.to_datetime(df['date'].astype(int), format='%Y%m%d')
        df = compute_indicators(df.set_index('date'))
        
        print("====== ", code, " ======")
        if filtering(df, config, market):
            signals[code] = ("BUY", df['close'].iloc[-1])

    con.close()
    logging.info(f"Analysis signals: {signals}")
    return signals

def fill_orders(balance, signals, trade_config) -> List:
    df_hold = get_hold_list()

    n_balance = balance / trade_config['n_split'] / trade_config['max_hold_stocks']
    print("n_balance: ", n_balance)

    orders = []
    for code, (action, price) in signals.items():
        if code in df_hold.index:
            n_buy = df_hold.loc[code, 'num_buy']
            if n_buy >= 4:
                continue
        
        buy_price = int(price * 1.01)
        buy_price = calculate_tick_price(buy_price)

        qty = f'{int(n_balance / buy_price)}'
        orders.append([code, action, qty, int(buy_price)])
    return orders
