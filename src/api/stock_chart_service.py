from src.api.base_client import BaseAPIClient
import pandas as pd
import requests
import json

class StockChartService(BaseAPIClient):
    def __init__(self, token: str):
        super().__init__()
        self.token = token
        self.endpoint = '/api/dostk/chart'

    def _get_headers(self, cont_yn='N', next_key=''):
        """기본 header 데이터 설정"""
        return {
            'Content-Type': 'application/json;charset=UTF-8',
            'authorization': f'Bearer {self.token}',
            'cont-yn': cont_yn,
            'next-key': next_key,
            'api-id': ''  # TR명은 나중에 메서드에서 지정
        }

    def get_daily_chart(self, stk_cd: str, base_dt: str, upd_stkpc_tp: str = '1', cont_yn='N', next_key=''):
        """일봉 차트 조회"""
        headers = self._get_headers(cont_yn=cont_yn, next_key=next_key)
        headers['api-id'] = 'ka10081'  # TR명: 주식일봉차트조회요청

        data = {
            'stk_cd': stk_cd,
            'base_dt': base_dt,  # 기준일자 (YYYYMMDD)
            'upd_stkpc_tp': upd_stkpc_tp,  # 수정주가구분
        }

        # 요청
        response = self.post(self.endpoint, data=data, headers=headers)

        # 응답 처리
        if response.status_code == 200:
            chart_data = response.json()
            # DataFrame으로 변환하여 반환
            return self._convert_to_dataframe(chart_data['stk_dt_pole_chart_qry'], is_intraday=False)
        else:
            print(f"Error: {response.status_code}")
            return None

    def get_intraday_chart(self, stk_cd: str, tic_scope: str = '1', upd_stkpc_tp: str = '1', cont_yn='N', next_key=''):
        """분봉 차트 조회"""
        headers = self._get_headers(cont_yn=cont_yn, next_key=next_key)
        headers['api-id'] = 'ka10080'  # TR명: 주식분봉차트조회요청

        data = {
            'stk_cd': stk_cd,
            'tic_scope': tic_scope,  # 틱범위 (1:1분, 3:3분, 5:5분 등)
            'upd_stkpc_tp': upd_stkpc_tp,  # 수정주가구분
        }

        # 요청
        response = self.post(self.endpoint, data=data, headers=headers)

        # 응답 처리
        if response.status_code == 200:
            chart_data = response.json()
            # DataFrame으로 변환하여 반환
            return self._convert_to_dataframe(chart_data['stk_min_pole_chart_qry'], is_intraday=True)
        else:
            print(f"Error: {response.status_code}")
            return None

    def _convert_to_dataframe(self, chart_data: list, is_intraday: bool = False):
        """차트 데이터를 Pandas DataFrame으로 변환"""

        if chart_data:
            # 일봉 데이터의 경우 필드명에 맞춰 컬럼을 설정
            if not is_intraday:  # 일봉 차트
                columns = ['cur_prc', 'trde_qty', 'trde_prica', 'dt', 'open_pric', 'high_pric', 'low_pric']
            else:  # 분봉 차트
                columns = ['cur_prc', 'trde_qty', 'cntr_tm', 'open_pric', 'high_pric', 'low_pric']
            
            # DataFrame으로 변환
            df = pd.DataFrame(chart_data, columns=columns)

            # 'cur_prc', 'open_pric', 'high_pric', 'low_pric'을 숫자로 변환 (가격 관련 컬럼)
            for col in ['cur_prc', 'open_pric', 'high_pric', 'low_pric']:
                if col in df.columns:
                    df[col] = df[col].apply(lambda x: int(x.replace('+', '').replace('-', '')) if isinstance(x, str) else x)

            # 거래량 컬럼 변환 (trde_qty, trde_prica)
            if 'trde_qty' in df.columns:
                df['trde_qty'] = pd.to_numeric(df['trde_qty'], errors='coerce')
            if 'trde_prica' in df.columns:
                df['trde_prica'] = pd.to_numeric(df['trde_prica'], errors='coerce')

            # 일자 또는 시간 컬럼 변환 (dt 또는 cntr_tm)
            if 'dt' in df.columns:
                df['dt'] = pd.to_datetime(df['dt'], format='%Y%m%d')  # 일봉 차트의 dt는 'YYYYMMDD'
                df.set_index('dt', inplace=True)
            elif 'cntr_tm' in df.columns:
                df['cntr_tm'] = pd.to_datetime(df['cntr_tm'], format='%Y%m%d%H%M%S')  # 분봉 차트의 cntr_tm은 'YYYYMMDDHHMMSS'
                df.set_index('cntr_tm', inplace=True)
            # 컬럼 이름 변경

            df = df.rename(columns={
                'cur_prc': 'close', 
                'trde_qty': 'volume', 
                'open_pric': 'open', 
                'high_pric': 'high', 
                'low_pric': 'low'
            })
            return df.astype(int).sort_index()  # 일봉 차트 기준으로 dt를 index로 설정
        else:
            print("No data found in the response.")
            return None
