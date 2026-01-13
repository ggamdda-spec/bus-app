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

# --- [1단계] 필수 함수 정의 (가장 먼저 정의해야 NameError가 안 납니다) ---
def has_all_values(values):
    for v in values:
        if pd.isna(v) or str(v).strip() == "": return False
    return True

def format_time(t):
    if pd.isna(t): return ""
    try:
        if isinstance(t, datetime): return t.strftime("%H:%M")
        return str(t)[:5]
    except: return str(t)

def time_to_minutes(t):
    try:
        if isinstance(t, datetime): return t.hour * 60 + t.minute
        h, m = str(t)[:5].split(":")
        return int(h) * 60 + int(m)
    except: return 99999

def haversine(lat1, lon1, lat2, lon2):
    R = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlambda/2)**2
    return R * 2 * np.arctan2(np.sqrt(a), np.sqrt(1-a))

# --- [2단계] 데이터 로드 ---
@st.cache_data
def load_data():
    if not os.path.exists(EXCEL_FILE):
        st.error(f"❌ 파일을 찾을 수 없습니다: {EXCEL_FILE}")
        return None, None
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        df_times = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_SCHEDULE)
        df_gps = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_STATION)
        df_times.columns = df_times.columns.str.strip()
        df_gps.columns = df_gps.columns.str.strip()
        return df_times, df_gps
    except Exception as e:
        st.error(f"❌ 데이터 로딩 오류: {e}")
        return None, None

df_times, df_gps = load_data()

# --- [3단계] 메인 UI 및 지도 ---
st.title("🚌 강진군 버스 시간 & 내 위치 확인")

if 'auto_station' not in st.session_state:
    st.session_state.auto_station = ""

st.subheader("📍 현재 내 위치 확인")

# 강진군청 기준 기본 지도 (권한 허용 전 보여줄 용도)
default_lat, default_lon = 34.642, 126.767 
map_data = pd.DataFrame({'lat': [default_lat], 'lon': [default_lon]})

# 위치 확인 버튼
if st.button("🌐 내 위치 찾기 (지도를 내 위치로 이동)"):
    loc = get_geolocation()
    if loc and 'coords' in loc:
        curr_lat = loc['coords']['latitude']
        curr_lon = loc['coords']['longitude']
        map_data = pd.DataFrame({'lat': [curr_lat], 'lon': [curr_lon]})
        
        if df_gps is not None:
            try:
                df_gps['위도'] = pd.to_numeric(df_gps['위도'], errors='coerce')
                df_gps['경도'] = pd.to_numeric(df_gps['경도'], errors='coerce')
                df_gps = df_gps.dropna(subset=['위도', '경도'])
                
                df_gps['dist'] = df_gps.apply(lambda r: haversine(curr_lat, curr_lon, r['위도'], r['경도']), axis=1)
                nearest = df_gps.sort_values('dist').iloc[0]
                st.session_state.auto_station = nearest['정류장명']
                st.success(f"✅ 내 위치 근처 **[{nearest['정류장명']}]** 정류장을 찾았습니다!")
                st.rerun()
            except Exception as e:
                st.error(f"거리 계산 오류: {e}")
    else:
        st.warning("📍 위치 권한을 '허용'으로 바꾼 뒤 2~3초 후에 다시 눌러주세요.")

# 지도 강제 표시
st.map(map_data)

st.divider()

# --- [4단계] 검색 및 결과 ---
station_query = st.text_input("🔍 정류장 검색:", value=st.session_state.auto_station)

if station_query:
    up_res, down_res = [], []
    if df_times is not None:
        for _, row in df_times.iterrows():
            # 상행 (0:5), 하행 (5:10)
            if has_all_values(row.iloc[0:5]) and station_query in str(row.iloc[0]):
                up_res.append({"정류장": row.iloc[0], "강진출발": format_time(row.iloc[1]), "도착": format_time(row.iloc[2]), "노선": row.iloc[3], "sort": time_to_minutes(row.iloc[1])})
            if has_all_values(row.iloc[5:10]) and station_query in str(row.iloc[5]):
                down_res.append({"정류장": row.iloc[5], "강진출발": format_time(row.iloc[6]), "도착": format_time(row.iloc[7]), "노선": row.iloc[8], "sort": time_to_minutes(row.iloc[6])})

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔼 상행")
        if up_res: st.dataframe(pd.DataFrame(up_res).sort_values("sort").drop(columns="sort"), use_container_width=True, hide_index=True)
        else: st.write("검색 결과가 없습니다.")
    with col2:
        st.subheader("🔽 하행")
        if down_res: st.dataframe(pd.DataFrame(down_res).sort_values("sort").drop(columns="sort"), use_container_width=True, hide_index=True)
        else: st.write("검색 결과가 없습니다.")