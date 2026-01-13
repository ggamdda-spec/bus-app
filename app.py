import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# 1. 파일 및 시트 설정
EXCEL_FILE = "버스시간검색(24.01.01).xlsx"
SHEET_SCHEDULE = "Sheet1"    # 첫 번째 시트 이름
SHEET_STATION = "정류장"     # 두 번째 시트 이름

st.set_page_config(page_title="강진 스마트 버스 시간표", layout="wide")

# -------------------------
# [로직 함수] 시간 및 거리 계산
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

# -------------------------
# [데이터 로드] 시트 이름 명시적 지정
# -------------------------
@st.cache_data
def load_data():
    if not os.path.exists(EXCEL_FILE):
        st.error(f"파일을 찾을 수 없습니다: {EXCEL_FILE}")
        return None, None
    try:
        # 시트 이름을 명시적으로 입력하여 로드
        df_times = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_SCHEDULE)
        df_gps = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_STATION)
        
        # 열 이름의 앞뒤 공백 제거 (에러 방지 핵심)
        df_times.columns = df_times.columns.str.strip()
        df_gps.columns = df_gps.columns.str.strip()
        
        return df_times, df_gps
    except Exception as e:
        st.error(f"엑셀 로딩 오류: 시트 이름 '{SHEET_SCHEDULE}' 또는 '{SHEET_STATION}'을 확인하세요. ({e})")
        return None, None

df_times, df_gps = load_data()

# -------------------------
# [메인 UI 컨텐츠]
# -------------------------
st.title("🚌 강진군 버스 시간 검색")

# 세션 상태로 자동 입력값 관리
if 'auto_station' not in st.session_state:
    st.session_state.auto_station = ""

st.subheader("📍 내 주변 정류장")

# 버튼 레이아웃
if st.button("🌐 현재 위치로 정류장 자동 찾기"):
    # 위치 정보 획득 시도
    loc = get_geolocation()
    
    if loc and 'coords' in loc:
        curr_lat = loc['coords']['latitude']
        curr_lon = loc['coords']['longitude']
        
        if df_gps is not None:
            try:
                # 거리 계산
                df_gps['dist'] = df_gps.apply(
                    lambda r: haversine(curr_lat, curr_lon, float(r['위도']), float(r['경도'])), 
                    axis=1
                )
                # 가장 가까운 정류장 추출
                nearest_name = df_gps.sort_values('dist').iloc[0]['정류장명']
                st.session_state.auto_station = nearest_name
                st.success(f"가장 가까운 **[{nearest_name}]** 정류장을 찾았습니다!")
                st.rerun() # 결과 즉시 반영
            except Exception as e:
                st.error("엑셀 데이터 형식이 맞지 않습니다. '위도', '경도', '정류장명' 열이 있는지 확인하세요.")
    else:
        st.info("브라우저 상단의 위치 권한을 '허용'한 뒤 잠시만 기다려 주세요.")

st.divider()

# 검색창 (위치 확인 시 자동으로 이름이 채워짐)
station_query = st.text_input("정류장 이름을 입력하세요 (예: 강진터미널):", value=st.session_state.auto_station)

if station_query:
    up_results = []
    down_results = []

    if df_times is not None:
        for _, row in df_times.iterrows():
            # 상행 데이터 필터링
            up_vals = row.iloc[0:5].tolist()
            if has_all_values(up_vals) and station_query in str(row.iloc[0]):
                up_results.append({
                    "sort": time_to_minutes(row.iloc[1]), "정류장": row.iloc[0],
                    "강진출발": format_time(row.iloc[1]), "도착예정": format_time(row.iloc[2]),
                    "노선": row.iloc[3], "코스": row.iloc[4]
                })
            # 하행 데이터 필터링
            down_vals = row.iloc[5:10].tolist()
            if has_all_values(down_vals) and station_query in str(row.iloc[5]):
                down_results.append({
                    "sort": time_to_minutes(row.iloc[6]), "정류장": row.iloc[5],
                    "강진출발": format_time(row.iloc[6]), "도착예정": format_time(row.iloc[7]),
                    "노선": row.iloc[8], "코스": row.iloc[9]
                })

    # 결과 표 출력
    st.warning("⚠ 실제 도로 상황에 따라 도착 시간이 다를 수 있습니다.")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔼 상행")
        if up_results:
            st.dataframe(pd.DataFrame(up_results).sort_values("sort").drop(columns=["sort"]), use_container_width=True, hide_index=True)
        else: st.write("정보 없음")
        
    with col2:
        st.subheader("🔽 하행")
        if down_results:
            st.dataframe(pd.DataFrame(down_results).sort_values("sort").drop(columns=["sort"]), use_container_width=True, hide_index=True)
        else: st.write("정보 없음")