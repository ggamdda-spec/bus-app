import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# 1. 설정
EXCEL_FILE = "버스시간검색(24.01.01).xlsx"
SHEET_SCHEDULE = "Sheet1"
SHEET_STATION = "정류장"

st.set_page_config(page_title="강진 스마트 버스", layout="wide")

# --- 데이터 로드 부분 (생략 - 기존과 동일) ---
@st.cache_data
def load_data():
    if not os.path.exists(EXCEL_FILE): return None, None
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        df_times = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_SCHEDULE)
        df_gps = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_STATION)
        df_times.columns = df_times.columns.str.strip()
        df_gps.columns = df_gps.columns.str.strip()
        return df_times, df_gps
    except: return None, None

df_times, df_gps = load_data()

st.title("🚌 강진군 버스 안내 (지도 모드)")

# --- 🗺️ 지도 강제 로드 섹션 ---
st.subheader("📍 현재 위치 및 정류장 지도")

# 기본 지도 위치 (강진군청 중심)
default_lat, default_lon = 34.642, 126.767 

# 세션 상태 초기화
if 'map_center' not in st.session_state:
    st.session_state.map_center = pd.DataFrame({'lat': [default_lat], 'lon': [default_lon]})
if 'auto_station' not in st.session_state:
    st.session_state.auto_station = ""

# 1. 지도 먼저 보여주기
st.map(st.session_state.map_center)

# 2. 위치 확인 버튼
if st.button("🌐 내 위치 찾기 (지도를 내 위치로 이동)"):
    loc = get_geolocation()
    if loc and 'coords' in loc:
        curr_lat = loc['coords']['latitude']
        curr_lon = loc['coords']['longitude']
        
        # 지도 위치 업데이트
        st.session_state.map_center = pd.DataFrame({'lat': [curr_lat], 'lon': [curr_lon]})
        
        if df_gps is not None:
            # 거리 계산 로직
            df_gps['위도'] = pd.to_numeric(df_gps['위도'], errors='coerce')
            df_gps['경도'] = pd.to_numeric(df_gps['경도'], errors='coerce')
            df_gps['dist'] = df_gps.apply(lambda r: haversine(curr_lat, curr_lon, r['위도'], r['경도']), axis=1)
            nearest = df_gps.sort_values('dist').iloc[0]
            st.session_state.auto_station = nearest['정류장명']
            st.success(f"✅ 내 위치 근처 **[{nearest['정류장명']}]** 정류장을 찾았습니다!")
            st.rerun()
    else:
        st.error("⚠️ 위치 접근이 차단되었습니다. 주소창의 '자물쇠' 아이콘을 눌러 허용해 주세요.")

st.divider()

# --- 검색창 ---
station_query = st.text_input("🔍 정류장 검색:", value=st.session_state.auto_station)
if station_query:
    up_res, down_res = [], []
    if df_times is not None:
        for _, row in df_times.iterrows():
            # 상행 (0~4열), 하행 (5~9열) 구조
            if has_all_values(row.iloc[0:5]) and station_query in str(row.iloc[0]):
                up_res.append({"정류장": row.iloc[0], "강진출발": format_time(row.iloc[1]), "도착": format_time(row.iloc[2]), "노선": row.iloc[3], "sort": time_to_minutes(row.iloc[1])})
            if has_all_values(row.iloc[5:10]) and station_query in str(row.iloc[5]):
                down_res.append({"정류장": row.iloc[5], "강진출발": format_time(row.iloc[6]), "도착": format_time(row.iloc[7]), "노선": row.iloc[8], "sort": time_to_minutes(row.iloc[6])})

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔼 상행")
        if up_res: st.dataframe(pd.DataFrame(up_res).sort_values("sort").drop(columns="sort"), use_container_width=True, hide_index=True)
        else: st.write("결과 없음")
    with col2:
        st.subheader("🔽 하행")
        if down_res: st.dataframe(pd.DataFrame(down_res).sort_values("sort").drop(columns="sort"), use_container_width=True, hide_index=True)
        else: st.write("결과 없음")