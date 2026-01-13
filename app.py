import streamlit as st
import pandas as pd
import numpy as np
import os
from datetime import datetime
from streamlit_js_eval import get_geolocation

# 1. 설정 (시트 이름 확인 필수!)
EXCEL_FILE = "버스시간검색(24.01.01).xlsx"
SHEET_SCHEDULE = "Sheet1"    # 시간표 시트
SHEET_STATION = "정류장"     # GPS 정보 시트

st.set_page_config(page_title="강진군 스마트 버스", layout="wide")

# --- 유틸리티 함수 ---
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

# --- 데이터 로드 ---
@st.cache_data
def load_data():
    if not os.path.exists(EXCEL_FILE):
        st.error(f"❌ 엑셀 파일을 찾을 수 없습니다: {EXCEL_FILE}")
        return None, None
    try:
        xl = pd.ExcelFile(EXCEL_FILE)
        # 시트 존재 확인
        if SHEET_SCHEDULE not in xl.sheet_names or SHEET_STATION not in xl.sheet_names:
            st.error(f"❌ 시트 이름을 확인하세요. (현재 엑셀 시트: {xl.sheet_names})")
            return None, None
            
        df_times = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_SCHEDULE)
        df_gps = pd.read_excel(EXCEL_FILE, sheet_name=SHEET_STATION)
        df_times.columns = df_times.columns.str.strip()
        df_gps.columns = df_gps.columns.str.strip()
        return df_times, df_gps
    except Exception as e:
        st.error(f"❌ 데이터 로딩 오류: {e}")
        return None, None

df_times, df_gps = load_data()

# --- 메인 UI ---
st.title("🚌 강진군 버스 시간 & 내 위치 확인")

if 'auto_station' not in st.session_state:
    st.session_state.auto_station = ""

# --- 📍 위치 확인 및 지도 섹션 ---
st.subheader("📍 현재 내 위치 확인")
if st.button("🌐 내 위치 지도로 확인하고 정류장 찾기"):
    loc = get_geolocation()
    
    if loc and 'coords' in loc:
        lat = loc['coords']['latitude']
        lon = loc['coords']['longitude']
        
        # 지도 표시용 데이터
        my_location = pd.DataFrame({'lat': [lat], 'lon': [lon]})
        
        if df_gps is not None:
            try:
                # 거리 계산
                df_gps['dist'] = df_gps.apply(lambda r: haversine(lat, lon, float(r['위도']), float(r['경도'])), axis=1)
                nearest = df_gps.sort_values('dist').iloc[0]
                st.session_state.auto_station = nearest['정류장명']
                
                st.success(f"✅ 확인 완료! 가장 가까운 정류장: **[{nearest['정류장명']}]**")
                
                # 지도 출력
                st.map(my_location)
                st.info("💡 지도에 점이 보인다면 위치 권한이 정상입니다. 안 보인다면 GPS를 켜주세요.")
                st.rerun()
            except Exception as e:
                st.error(f"거리 계산 오류 (엑셀 위도/경도 확인): {e}")
    else:
        st.error("⚠️ 위치 신호를 잡지 못했습니다. 주소창의 '자물쇠'를 눌러 위치 권한을 '허용'으로 바꿔주세요.")

st.divider()

# --- 🔍 검색 및 결과 섹션 ---
station_query = st.text_input("🔍 정류장 검색 (직접 입력도 가능):", value=st.session_state.auto_station)

if station_query:
    up_res, down_res = [], []
    if df_times is not None:
        for _, row in df_times.iterrows():
            # 상행 (0~4열), 하행 (5~9열)
            if has_all_values(row.iloc[0:5]) and station_query in str(row.iloc[0]):
                up_res.append({"정류장": row.iloc[0], "출발": format_time(row.iloc[1]), "도착": format_time(row.iloc[2]), "노선": row.iloc[3], "sort": time_to_minutes(row.iloc[1])})
            if has_all_values(row.iloc[5:10]) and station_query in str(row.iloc[5]):
                down_res.append({"정류장": row.iloc[5], "출발": format_time(row.iloc[6]), "도착": format_time(row.iloc[7]), "노선": row.iloc[8], "sort": time_to_minutes(row.iloc[6])})

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🔼 상행 (시내방향 등)")
        if up_res: st.dataframe(pd.DataFrame(up_res).sort_values("sort").drop(columns="sort"), use_container_width=True, hide_index=True)
        else: st.write("검색 결과가 없습니다.")
    with col2:
        st.subheader("🔽 하행 (읍내방향 등)")
        if down_res: st.dataframe(pd.DataFrame(down_res).sort_values("sort").drop(columns="sort"), use_container_width=True, hide_index=True)
        else: st.write("검색 결과가 없습니다.")