# src/trading/daily_candle_downloader.py
import os
import sys
import sqlite3
from datetime import datetime
from typing import Optional
from time import sleep
import pandas as pd

# 프로젝트 루트 경로 추가
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
src_path = os.path.join(project_root, 'src')
if src_path not in sys.path:
    sys.path.append(src_path)

from src.api.stock_chart_service import StockChartService  # 제공하신 서비스 사용

# -----------------------------
# 설정
# -----------------------------
DB_DIR = os.path.join(project_root, "sqlite3")
DB_PATH = os.path.join(DB_DIR, "candle_data.sqlite3")
EXCEL_PATH = os.path.join(project_root, "stocklist.xlsx")  # '주식코드' 컬럼
BASE_DT = datetime.now().strftime("%Y%m%d")  # 당일 기준으로 요청

# -----------------------------
# 유틸
# -----------------------------
def _ensure_db_dir():
    if not os.path.exists(DB_DIR):
        os.makedirs(DB_DIR, exist_ok=True)

def _clean_price(x: Optional[str]) -> Optional[float]:
    """'+12345', '-12345' 등 문자열을 float로 변환"""
    if x is None:
        return None
    s = str(x).strip().replace(",", "")
    # 허용 문자만 남기기
    buf = []
    for ch in s:
        if ch.isdigit() or ch in ['+', '-', '.']:
            buf.append(ch)
    s2 = "".join(buf)
    if s2 in ("", "+", "-"):
        return None
    try:
        return float(s2)
    except Exception:
        return None

def _normalize_daily_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    StockChartService.get_daily_chart 응답 DataFrame을
    표준 컬럼(tohlcv)으로 통일: ['date','open','high','low','close','volume']
    - date: YYYYMMDD → YYYY-MM-DD 문자열 (또는 그대로 YYYYMMDD로 저장해도 됨)
    """
    # 예상되는 원본 컬럼: dt, open_pric, high_pric, low_pric, cur_prc, trde_qty
    colmap = {
        "dt": "date",
        "open_pric": "open",
        "high_pric": "high",
        "low_pric": "low",
        "cur_prc": "close",
        "trde_qty": "volume",
        # 혹시 다른 이름으로 올 수 있는 대비
        "trde_prica": "value",  # 사용하지 않지만 예시 보존
    }

    # 컬럼 이름 표준화(있는 것만)
    df = df.rename(columns={k: v for k, v in colmap.items() if k in df.columns})

    # 필요한 컬럼만 추출
    need_cols = ["date", "open", "high", "low", "close", "volume"]
    for c in need_cols:
        if c not in df.columns:
            df[c] = None

    # 값 정리
    df["open"] = df["open"].apply(_clean_price)
    df["high"] = df["high"].apply(_clean_price)
    df["low"]  = df["low"].apply(_clean_price)
    df["close"]= df["close"].apply(_clean_price)

    # 거래량은 정수로
    def _clean_int(x):
        if x is None:
            return None
        s = str(x).strip().replace(",", "")
        s2 = "".join([ch for ch in s if ch.isdigit()])
        if s2 == "":
            return None
        try:
            return int(s2)
        except Exception:
            return None

    df["volume"] = df["volume"].apply(_clean_int)

    # 날짜 문자열 정리: YYYYMMDD → YYYY-MM-DD (또는 그대로 저장 원하면 아래 라인 변경)
    def _fmt_date(s):
        s = str(s).strip()
        if len(s) == 8 and s.isdigit():
            return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"
        return s

    df["date"] = df["date"].apply(_fmt_date)

    # 정렬 & 중복 제거
    df = df[need_cols].dropna(subset=["date"]).drop_duplicates(subset=["date"]).sort_values("date")
    df.reset_index(drop=True, inplace=True)
    return df

def _table_exists(con: sqlite3.Connection, table_name: str) -> bool:
    cur = con.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?;",
        (table_name,)
    )
    row = cur.fetchone()
    return row is not None

def _get_max_date(con: sqlite3.Connection, table_name: str) -> Optional[str]:
    """
    테이블에서 가장 최근 날짜(YYYY-MM-DD 문자열)를 반환. 없으면 None
    """
    try:
        cur = con.execute(f"SELECT MAX(date) FROM '{table_name}';")
        row = cur.fetchone()
        return row[0] if row and row[0] else None
    except Exception:
        return None

def _create_table_if_not_exists(con: sqlite3.Connection, table_name: str):
    """
    종목코드명(예: '005930')으로 테이블 생성. 표준 TOHLCV 스키마.
    """
    sql = f"""
    CREATE TABLE IF NOT EXISTS '{table_name}' (
        date   TEXT PRIMARY KEY,
        open   REAL,
        high   REAL,
        low    REAL,
        close  REAL,
        volume INTEGER
    );
    """
    con.execute(sql)
    con.commit()

def upsert_daily_candles(code: str, df_daily: pd.DataFrame):
    """
    - 테이블이 없으면 생성 후 전체 저장
    - 테이블이 있으면 MAX(date) 이후 데이터만 append
    """
    _ensure_db_dir()
    with sqlite3.connect(DB_PATH) as con:
        table = code  # 테이블명을 종목코드로
        _create_table_if_not_exists(con, table)

        # 현재 테이블의 마지막 날짜 확인
        last_date = _get_max_date(con, table)

        # 표준화
        df_norm = _normalize_daily_df(df_daily)

        if last_date:
            # last_date 이후만 저장
            df_new = df_norm[df_norm["date"] > last_date].copy()
        else:
            df_new = df_norm.copy()

        if df_new.empty:
            print(f"[{code}] 신규 데이터 없음 (last_date={last_date})")
            return

        # append
        df_new.to_sql(table, con, if_exists="append", index=False)
        print(f"[{code}] 신규 {len(df_new)}건 저장 완료 (마지막: {df_new['date'].max()})")

# -----------------------------
# 메인 로직
# -----------------------------
def main():
    # 토큰
    with open(os.path.join(project_root, "access_token.txt"), "r", encoding="utf-8") as f:
        token = f.read().strip()

    # 종목 리스트 로드
    if not os.path.exists(EXCEL_PATH):
        raise FileNotFoundError(f"엑셀 파일을 찾을 수 없습니다: {EXCEL_PATH}")

    stock_df = pd.read_excel(EXCEL_PATH)
    if "주식코드" not in stock_df.columns:
        raise ValueError("엑셀에 '주식코드' 컬럼이 필요합니다.")

    codes = (
        stock_df["주식코드"]
        .astype(str)
        .str.replace(r"\D", "", regex=True)
        .str.zfill(6)
        .dropna()
        .unique()
        .tolist()
    )

    svc = StockChartService(token)

    # 루프: 각 종목 일봉 다운로드 → DB 저장
    for code in codes:
        sleep(0.25)
        try:
            df_daily = svc.get_daily_chart(code, BASE_DT)  # DataFrame 반환 가정
            if df_daily is None or df_daily.empty:
                print(f"[{code}] 일봉 데이터 없음")
                continue
            upsert_daily_candles(code, df_daily)
        except Exception as e:
            print(f"[{code}] 에러: {e}")


if __name__ == "__main__":
    main()
