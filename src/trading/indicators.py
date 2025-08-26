import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta
from datetime import datetime
# -------------------- Helper Functions -------------------- #

def compute_indicators(df: pd.DataFrame):
    """
    df에는 최소한 'open', 'high', 'low', 'close', 'volume' 컬럼이 있다고 가정.
    원하는 인디케이터를 df에 컬럼으로 추가한 뒤 df를 return
    """

    # SMI (Stochastic Momentum Index) 예시
    # pandas_ta의 smi 함수(이름이 stoch는 여러가지 옵션이 있음)를 사용할 수 있습니다.
    # pandas_ta.stoch() => slow_k, slow_d 가 리턴됨. smi는 별도 구현이나 stoch() 변형 사용 가능.
    # 여기서는 'stoch'를 사용한 근사 예시
    # stoch_df = ta.stoch(df['high'], df['low'], df['close'], k=10, d=3, smooth_k=3)
    stoch_df = ta.smi(df['close'], fast=3, slow=14, signal=3) * 100
    # stoch_df.columns => ['STOCHk_14_3_3', 'STOCHd_14_3_3']
    # 예시로 그냥 k값을 SMI로 가정 (실제 공식과 다를 수 있습니다)
    df['SMI'] = stoch_df.iloc[:, 0]

    df['avg_volume'] = df['volume'].rolling(window=90).mean()
    df['vrate'] = df['volume'] / df['avg_volume']

    # Stoch RSI
    # pandas_ta에 stochrsi() 함수가 있습니다
    stochrsi_df = ta.stochrsi(df['close'], length=14, rsi_length=14, k=3, d=3)
    # stochrsi_df.columns => 
    # ['STOCHRSIk_14_14_3_3', 'STOCHRSId_14_14_3_3']
    # 편의상 k 값을 그대로 사용
    df['Stoch_RSI'] = stochrsi_df.iloc[:, 0]

    boll = df.ta.bbands(length=20, std=2)
    df['BB_lower_pct'] = (boll[f'BBL_20_2.0'] - df['close']) / df['close']
    df['BB_mid'] = boll[f'BBM_20_2.0']
    df['BB_upper_pct'] = (boll[f'BBU_20_2.0'] - df['close']) / df['close']
    df['BB_length'] = (boll[f'BBU_20_2.0'] - boll[f'BBL_20_2.0']) / boll[f'BBL_20_2.0']

    # BB(볼린저 밴드), SQZMOM(스퀴즈 모멘텀) 등은
    # df.ta.bbands(), df.ta.squeeze() 등을 사용하시면 됩니다.
    # 예: boll = df.ta.bbands(length=20, std=2)
    #     sqz = df.ta.squeeze(lazybear=True)
    # df['SQZ_ON']  = sqz_df['SQZ_ON']
    # df['SQZ_OFF'] = sqz_df['SQZ_OFF']
    # df['SQZ_NO']  = sqz_df['SQZ_NO']

    sqz_df = df.ta.squeeze(lazybear=True, detailed=True)
    df['SQZ_VAL'] = sqz_df['SQZ_20_2.0_20_1.5_LB']
    df['SQZ_ON'] = sqz_df['SQZ_ON']
    # df['OBV'] = MinMaxScaler().fit_transform(ta.obv(df['close'], df['volume']).values.reshape(-1, 1))
    df['OBV'] = ta.obv(df['close'], df['volume'])

    for i in [5, 20, 60, 200]:
        df[f'mapct_{i}'] = (df['close'].rolling(i).mean() - df['close']) / df['close']

    # (A) RSI(상대강도지수) - length=14가 기본
    df['RSI'] = ta.rsi(df['close'], length=14)

    # (B) MACD - 기본 파라미터 fast=12, slow=26, signal=9
    macd_df = df.ta.macd(fast=12, slow=26, signal=9)
    # macd_df.columns => ['MACD_12_26_9', 'MACDh_12_26_9', 'MACDs_12_26_9']
    df['MACD']  = macd_df['MACD_12_26_9']
    df['MACDh'] = macd_df['MACDh_12_26_9']  # 히스토그램
    df['MACDs'] = macd_df['MACDs_12_26_9']  # 시그널

    # (C) CCI(Commodity Channel Index) - 기본 length=20
    df['CCI'] = df.ta.cci(length=20)

    df['COR'] = (df['high'] - df['open']) / df['open']
    df['LOR'] = (df['low'] - df['open']) / df['open']
    df['HOR'] = (df['high'] - df['open']) / df['open']
    df['LCR'] = (df['low'] - df['close']) / df['close']
    df['HCR'] = (df['high'] - df['close']) / df['close']
    df['HLR'] = (df['high'] - df['low']) / df['low']

    # 혹시 다른 지표 예시로 ADX, ATR, CMF, etc.도 가능
    df['ADX'] = df.ta.adx(length=14)['ADX_14']
    df['ATR'] = df.ta.atr(length=14)

    df['recover_days'] = (df.index[-1] - df['low'].idxmin()).days
    df['correct_days'] = (df.index[-1] - df['high'].idxmax()).days
    df['minmaxgap'] = (df['high'].max() - df['low'].min()) / df['low'].min()
    df['close_std'] = df['close'].std()
    df['profit_600'] = (df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]
    
    today = datetime.today().strftime('%Y-%m-%d')
    df['days_since_max_high'] = days_since_max_high(df, today, window_days=600)

    df = zlema(df, length=70)
    df['baseline'] = moving_average(df['close'], 60, ma_type="HMA")
    return df

def days_since_max_high(prices: pd.DataFrame, current_date: str, window_days: int = 600) -> int:
    """
    prices: 인덱스가 날짜 문자열('YYYY-MM-DD')인 DataFrame, 'High' 컬럼 보유
    current_date: 기준일 ('YYYY-MM-DD')
    window_days: 몇 거래일(window) 기준으로 볼지
    """
    # 기준일까지의 데이터 중 최근 window_days개
    window = prices.loc[:current_date].tail(window_days)
    if window.empty:
        return None
    # 최고가 발생일
    max_date = window['high'].idxmax()
    # 날짜 차이(일수)
    return (pd.to_datetime(current_date) - pd.to_datetime(max_date)).days

def zlema(df, length=70):
    lag = (length - 1) // 2
    df['zlema'] = df['close'] + (df['close'] - df['close'].shift(lag))
    df['zlema'] = df['zlema'].ewm(span=length, adjust=False).mean()
    return df

def pivot_high(df, length):
    """
    Calculate pivot highs.

    Parameters:
    - df (pd.DataFrame): DataFrame with 'high' column.
    - length (int): Number of bars to the left and right to consider.

    Returns:
    - pd.Series: Series with pivot highs.
    """
    return df['high'][(df['high'] == df['high'].rolling(window=length * 2 + 1, center=True).max())]

def pivot_low(df, length):
    """
    Calculate pivot lows.

    Parameters:
    - df (pd.DataFrame): DataFrame with 'low' column.
    - length (int): Number of bars to the left and right to consider.

    Returns:
    - pd.Series: Series with pivot lows.
    """
    return df['low'][(df['low'] == df['low'].rolling(window=length * 2 + 1, center=True).min())]

def normalize(series):
    """
    Normalize a pandas Series between 0 and 100.

    Parameters:
    - series (pd.Series): Series to normalize.

    Returns:
    - pd.Series: Normalized series.
    """
    return (series - series.min()) / (series.max() - series.min()) * 100

def find_swings(series, is_high=True):
    """
    Find swing points in a series.

    Parameters:
    - series (pd.Series): Series to find swings in.
    - is_high (bool): If True, find swing highs; else, swing lows.

    Returns:
    - pd.Series: Series with swing points.
    """
    roll = series.rolling(window=3, center=True)
    if is_high:
        return series[(series == roll.max()) & (series.shift(1) < series) & (series.shift(-1) < series)]
    else:
        return series[(series == roll.min()) & (series.shift(1) > series) & (series.shift(-1) > series)]

def calculate_fibonacci_levels(high, low):
    """
    Calculate Fibonacci retracement levels.

    Parameters:
    - high (float): Highest pivot.
    - low (float): Lowest pivot.

    Returns:
    - dict: Fibonacci levels.
    """
    diff = high - low
    levels = {
        "0.0": high,
        "0.236": high - 0.236 * diff,
        "0.382": high - 0.382 * diff,
        "0.5": high - 0.5 * diff,
        "0.618": high - 0.618 * diff,
        "0.786": high - 0.786 * diff,
        "1.0": low,
    }
    return levels

def calculate_atr(df, length=14):
    """
    Calculate Average True Range (ATR).

    Parameters:
    - df (pd.DataFrame): DataFrame with 'high', 'low', 'close' columns.
    - length (int): ATR period.

    Returns:
    - pd.Series: ATR values.
    """
    high_low = df['high'] - df['low']
    high_close = (df['high'] - df['close'].shift(1)).abs()
    low_close = (df['low'] - df['close'].shift(1)).abs()
    tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
    atr = tr.rolling(window=length).mean()
    return atr

def moving_average(series, length, ma_type="SMA"):
    """
    Calculate moving average.

    Parameters:
    - series (pd.Series): Series to calculate MA on.
    - length (int): Window length.
    - ma_type (str): Type of MA ('SMA', 'EMA', 'WMA', 'HMA').

    Returns:
    - pd.Series: Moving average series.
    """
    if ma_type == "SMA":
        return series.rolling(window=length).mean()
    elif ma_type == "EMA":
        return series.ewm(span=length, adjust=False).mean()
    elif ma_type == "WMA":
        weights = np.arange(1, length + 1)
        return series.rolling(window=length).apply(lambda x: np.dot(x, weights) / weights.sum(), raw=True)
    elif ma_type == "HMA":
        half_length = int(length / 2)
        sqrt_length = int(np.sqrt(length))
        wma1 = moving_average(series, half_length, "WMA")
        wma2 = moving_average(series, length, "WMA")
        diff = 2 * wma1 - wma2
        return moving_average(diff, sqrt_length, "WMA")
    else:
        raise ValueError(f"Unknown moving average type: {ma_type}")

# -------------------- Indicator Functions -------------------- #

def plot_fibonacci(fig, df, levels, subplot=(1,1)):
    """
    Plot Fibonacci levels on the given subplot.

    Parameters:
    - fig (go.Figure): Plotly figure.
    - df (pd.DataFrame): DataFrame with 'time', 'open', 'high', 'low', 'close' columns.
    - levels (dict): Fibonacci levels to plot.
    - subplot (tuple): Subplot location (row, col).
    """
    for level, value in levels.items():
        fig.add_trace(go.Scatter(
            x=[df.index[0], df.index[-1]],
            y=[value, value],
            mode='lines',
            line=dict(dash='dash', color='yellow'),
            name=f'Fib {level}',
            showlegend=False
        ), row=subplot[0], col=subplot[1])

def plot_ssl_hybrid(fig, df, subplot=(1,1)):
    """
    Plot SSL Hybrid Indicator on the given subplot.

    Parameters:
    - fig (go.Figure): Plotly figure.
    - df (pd.DataFrame): DataFrame with necessary columns.
    - subplot (tuple): Subplot location (row, col).
    """
    # Parameters
    baseline_length = 60

    # Calculate indicators
    df['baseline'] = moving_average(df['close'], baseline_length, ma_type="HMA")

    # Add indicators to the plot
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['baseline'],
        mode='lines',
        name='Baseline',
        line=dict(color='blue'),
        showlegend=False
    ), row=subplot[0], col=subplot[1])

def plot_zero_lag_ema(fig, df, length=70, subplot=(1,1)):
    """
    Plot Zero Lag EMA and Trend Signals on the given subplot.

    Parameters:
    - fig (go.Figure): Plotly figure.
    - df (pd.DataFrame): DataFrame with necessary columns.
    - length (int): Length for ZLEMA calculation.
    - subplot (tuple): Subplot location (row, col).
    """

    # Add Zero Lag EMA
    fig.add_trace(go.Scatter(
        x=df.index,
        y=df['zlema'],
        mode='lines',
        name='Zero Lag EMA',
        line=dict(color='cyan', width=2),
        showlegend=False
    ), row=subplot[0], col=subplot[1])

def plot_all_indicators(fig, df, length=20, filter_threshold=20, 
                        fibonacci=True, ssl_hybrid_flag=True, 
                        zero_lag_ema_flag=True, levels_params={}, 
                        ssl_params={}, zlema_params={}, subplot=(1,1)):
    """
    Plot all indicators on the given subplot.

    Parameters:
    - fig (go.Figure): Plotly figure.
    - df (pd.DataFrame): DataFrame with necessary columns.
    - length (int): Length parameter for levels.
    - filter_threshold (float): Volatility filter threshold.
    - fibonacci (bool): Whether to plot Fibonacci levels.
    - ssl_hybrid_flag (bool): Whether to plot SSL Hybrid.
    - zero_lag_ema_flag (bool): Whether to plot Zero Lag EMA.
    - levels_params (dict): Additional parameters for levels.
    - ssl_params (dict): Additional parameters for SSL Hybrid.
    - zlema_params (dict): Additional parameters for Zero Lag EMA.
    - subplot (tuple): Subplot location (row, col).
    """
    if fibonacci:
        # Find swing points
        df['high_swings'] = find_swings(df['high'], is_high=True)
        df['low_swings'] = find_swings(df['low'], is_high=False)

        # Fibonacci Calculations
        highest_swing = df['high_swings'].max()
        lowest_swing = df['low_swings'].min()

        if not np.isnan(highest_swing) and not np.isnan(lowest_swing):
            fibonacci_levels = calculate_fibonacci_levels(highest_swing, lowest_swing)
            plot_fibonacci(fig, df, fibonacci_levels, subplot=subplot)

    if ssl_hybrid_flag:
        plot_ssl_hybrid(fig, df, subplot=subplot)

    if zero_lag_ema_flag:
        plot_zero_lag_ema(fig, df, length=zlema_params.get('length', 70), subplot=subplot)

def plot_liquidity_profile(fig, df, subplot=(1,2)):
    """
    Plot Liquidity Profile on the specified subplot.

    Parameters:
    - fig (go.Figure): Plotly figure.
    - df (pd.DataFrame): DataFrame with 'low', 'high', 'volume', 'time' columns.
    - subplot (tuple): Subplot location (row, col).
    """
    liquidity_profile = calculate_liquidity_profile(df)
    
    # Calculate bin centers
    bin_centers = (liquidity_profile['bins'][:-1] + liquidity_profile['bins'][1:]) / 2
    
    # Add Liquidity Profile as a horizontal bar chart
    fig.add_trace(go.Bar(
        x=liquidity_profile['volume'],
        y=bin_centers,
        orientation='h',
        name='Liquidity Profile',
        marker=dict(color='rgba(50, 150, 255, 0.6)'),
        showlegend=False
    ), row=subplot[0], col=subplot[1])

def calculate_liquidity_profile(df, bins=50):
    """
    Calculate the liquidity profile using histogram bins.

    Parameters:
    - df (pd.DataFrame): DataFrame with 'low', 'high', and 'volume' columns.
    - bins (int): Number of bins for the histogram.

    Returns:
    - dict: Dictionary with 'bins' and 'volume'.
    """
    # Generate price bins
    price_bins = np.linspace(df['low'].min(), df['high'].max(), bins)
    
    # Calculate bin indices
    bin_indices = np.digitize((df['low'] + df['high']) / 2, price_bins) - 1
    
    # Ensure bin indices are within valid range
    bin_indices = np.clip(bin_indices, 0, len(price_bins) - 2)
    
    # Initialize liquidity volume array
    liquidity_volume = np.zeros(len(price_bins) - 1)
    
    # Accumulate volume into bins
    np.add.at(liquidity_volume, bin_indices, df['volume'])
    
    return {'bins': price_bins, 'volume': liquidity_volume}

# -------------------- Main Plotting Function -------------------- #
def plot_comprehensive_chart(df, length=20, filter_threshold=20, 
                            fibonacci=True, ssl_hybrid_flag=True, 
                            zero_lag_ema_flag=True, 
                            subplot_left=(1,1), subplot_right=(1,2),
                            save_path="output.png"):
    """
    Plot all indicators on a single figure with subplots.

    Parameters:
    - df (pd.DataFrame): DataFrame with OHLCV data.
    - length (int): Period for pivot detection.
    - filter_threshold (float): Volatility filter threshold.
    - fibonacci (bool): Whether to plot Fibonacci levels.
    - ssl_hybrid_flag (bool): Whether to plot SSL Hybrid Indicator.
    - zero_lag_ema_flag (bool): Whether to plot Zero Lag EMA.
    - subplot_left (tuple): Subplot location for candlestick and indicators.
    - subplot_right (tuple): Subplot location for liquidity profile.
    """
    # Initialize the figure with subplots (8:2 ratio)
    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.8, 0.2],
        shared_yaxes=True,
        specs=[[{"secondary_y": True}, {"secondary_y": False}]]  # 수정: 첫 번째 subplot에 secondary_y=True 추가
    )

    # Add candlestick chart to the left subplot
    fig.add_trace(go.Candlestick(
        x=df.index,
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Candlestick'
    ), row=subplot_left[0], col=subplot_left[1], secondary_y=False)

    # Add volume bar chart
    fig.add_trace(go.Bar(
        x=df.index,
        y=df['volume'],
        name='Volume',
        marker=dict(color='rgba(128, 128, 255, 0.5)')  # Semi-transparent
    ), row=subplot_left[0], col=subplot_left[1], secondary_y=True)

    # Plot Liquidity Profile on the right subplot
    plot_liquidity_profile(fig, df, subplot=subplot_right)

    fig.update_layout(
        template='plotly_dark',
        xaxis_rangeslider_visible=False,
        width=1800,
        height=900,
        yaxis=dict(title='Price'),
        yaxis2=dict(
            title='Volume',
            overlaying='y',  # Overlay on the same y-axis
            side='right',
            range=[0, df['volume'].max() * 4]  # 1/4 of candlestick height
        )
    )

    # Remove axis titles and hide tick labels for both subplots
    fig.update_xaxes(title_text="", showticklabels=False, row=1, col=1)
    fig.update_yaxes(title_text="", showticklabels=False, row=1, col=1)
    fig.update_xaxes(title_text="", showticklabels=False, row=1, col=2)
    fig.update_yaxes(title_text="", showticklabels=False, row=1, col=2)

    # Save the figure
    fig.write_image(save_path)
