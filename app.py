import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# 1. 설정 및 파일 경로
EXCEL_FILE = "버스시간검색(24.01.01).xlsx"

# 페이지 설정
st.set_page_config(page_title="강진군 버스 시간 검색", layout="wide")

# -------------------------
# [로직 함수]
# -------------------------
def has_all_values(values):
    for v in values:
        if pd.isna(v): return False
        if isinstance(v, str) and v.strip() == "": return False
    return True

def format_time(t):
    if pd.isna(t): return ""
    try:
        if isinstance(t, datetime): return t.strftime("%H:%M")
        return str(t)[:5]
    except: return str(t)

def time_to_minutes(t):
    try:
        if isinstance(t, datetime):
            return t.hour * 60 + t.minute
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

# -------------------------
# [데이터 로드]
# -------------------------
@st.cache_data
def load_all_data():
    if not os.path.exists(EXCEL_FILE):
        st.error(f"엑셀 파일을 찾을 수 없습니다: {EXCEL_FILE}")
        return None, None
    try:
        df_times = pd.read_excel(EXCEL_FILE, sheet_name=0)
        df_gps = pd.read_excel(EXCEL_FILE, sheet_name=1)
        return df_times, df_gps
    except Exception as e:
        st.error(f"엑셀 로딩 오류: {e}")
        return None, None

df_times, df_gps = load_all_data()

# -------------------------
# [메인 UI]
# -------------------------
st.title("🚌 스마트 버스 시간 검색 시스템")

# 세션 상태 초기화 (자동 검색어 저장용)
if 'auto_station' not in st.session_state:
    st.session_state.auto_station = ""

# --- 위치 확인 버튼 섹션 ---
st.subheader("📍 내 주변 정류장 찾기")
col_btn, col_txt = st.columns([1, 3])

with col_btn:
    # 버튼을 누르면 get_geolocation()이 작동하도록 유도
    find_me = st.button("🌐 현재 위치 확인")

if find_me:
    with st.spinner('📍 GPS 신호를 수신 중입니다...'):
        loc = get_geolocation()
        
        if loc is None:
            st.error("⚠️ 위치 정보를 가져올 수 없습니다!")
            st.info("""
            **해결 방법:**
            1. 주소창의 **자물쇠 아이콘**을 눌러 '위치 허용'으로 되어있는지 확인하세요.
            2. 카카오톡 안에서 열었다면 **'다른 브라우저로 열기'**를 눌러주세요.
            3. 기기의 **GPS(위치)** 설정이 켜져 있는지 확인하세요.
            """)
        elif 'coords' in loc:
            curr_lat = loc['coords']['latitude']
            curr_lon = loc['coords']['longitude']
            
            if df_gps is not None:
                df_gps['dist'] = df_gps.apply(
                    lambda r: haversine(curr_lat, curr_lon, r['위도'], r['경도']), axis=1
                )
                nearest = df_gps.sort_values('dist').iloc[0]
                st.session_state.auto_station = nearest['정류장명']
                st.success(f"✅ 확인 완료! 가장 가까운 **[{st.session_state.auto_station}]** 정류장입니다.")
                st.rerun()

st.divider()

# --- 검색 및 결과 섹션 ---
# 버튼으로 찾은 정류장명이 있으면 자동으로 입력창에 채워짐
station = st.text_input("정류장 이름을 직접 입력하거나 버튼을 눌러주세요:", value=st.session_state.auto_station)

if station:
    up_results = []
    down_results = []

    if df_times is not None:
        for _, row in df_times.iterrows():
            # 상행 (0~4열)
            up_vals = row.iloc[0:5].tolist()
            if has_all_values(up_vals) and station in str(row.iloc[0]):
                up_results.append({
                    "sort": time_to_minutes(row.iloc[1]), "정류장": row.iloc[0],
                    "강진출발": format_time(row.iloc[1]), "도착시간": format_time(row.iloc[2]),
                    "노선": row.iloc[3], "코스": row.iloc[4]
                })
            
            # 하행 (5~9열)
            down_vals = row.iloc[5:10].tolist()
            if has_all_values(down_vals) and station in str(row.iloc[5]):
                down_results.append({
                    "sort": time_to_minutes(row.iloc[6]), "정류장": row.iloc[5],
                    "강진출발": format_time(row.iloc[6]), "도착시간": format_time(row.iloc[7]),
                    "노선": row.iloc[8], "코스": row.iloc[9]
                })

    st.warning("⚠ 도착시간은 실제 운행 상황에 따라 약 10분 정도 차이가 날 수 있습니다.")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔼 상행")
        if up_results:
            res_df_up = pd.DataFrame(up_results).sort_values("sort").drop(columns=["sort"])
            st.dataframe(res_df_up, use_container_width=True, hide_index=True)
        else:
            st.write("상행 운행 정보가 없습니다.")

    with col2:
        st.subheader("🔽 하행")
        if down_results:
            res_df_down = pd.DataFrame(down_results).sort_values("sort").drop(columns=["sort"])
            st.dataframe(res_df_down, use_container_width=True, hide_index=True)
        else:
            st.write("하행 운행 정보가 없습니다.")