import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from datetime import datetime
from math import radians, sin, cos, sqrt, atan2
import json

# =========================
# 기본 설정
# =========================
st.set_page_config(page_title="버스 시간 검색", layout="wide")
EXCEL_FILE = "버스시간검색(24.01.01).xlsx"

# =========================
# 엑셀 로드
# =========================
@st.cache_data
def load_excel():
    df_time = pd.read_excel(EXCEL_FILE, sheet_name=0)
    df_gps = pd.read_excel(EXCEL_FILE, sheet_name=1)
    return df_time, df_gps

df_time, df_gps = load_excel()

# =========================
# 유틸 함수
# =========================
def has_all_values(values):
    return not any(pd.isna(v) or str(v).strip() == "" for v in values)

def format_time(t):
    if isinstance(t, datetime):
        return t.strftime("%H:%M")
    return str(t)[:5]

def time_to_minutes(t):
    try:
        if isinstance(t, datetime):
            return t.hour * 60 + t.minute
        h, m = str(t)[:5].split(":")
        return int(h) * 60 + int(m)
    except:
        return 99999

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)
    a = sin(dlat/2)**2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    return R * c

def search_station(station):
    up, down = [], []
    for _, row in df_time.iterrows():
        if has_all_values(row.iloc[0:5]) and station in str(row.iloc[0]):
            up.append((time_to_minutes(row.iloc[1]), format_time(row.iloc[1]),
                       format_time(row.iloc[2]), row.iloc[3], row.iloc[4]))
        if has_all_values(row.iloc[5:10]) and station in str(row.iloc[5]):
            down.append((time_to_minutes(row.iloc[6]), format_time(row.iloc[6]),
                         format_time(row.iloc[7]), row.iloc[8], row.iloc[9]))
    return sorted(up), sorted(down)

# =========================
# GPS JavaScript
# =========================
st.title("🚌 버스 시간 검색")
st.markdown("<p style='color:red;'>⚠ 도착시간은 실제 운행 상황에 따라 약 10분 차이날 수 있습니다.</p>", unsafe_allow_html=True)

components.html("""
<script>
navigator.geolocation.getCurrentPosition(
    (pos) => {
        const data = {
            lat: pos.coords.latitude,
            lon: pos.coords.longitude
        };
        window.parent.postMessage(data, "*");
    }
);
</script>
""", height=0)

# =========================
# 위치 수신
# =========================
if "lat" not in st.session_state:
    try:
        message = st.session_state["_streamlit_message"]
        if isinstance(message, dict) and "lat" in message:
            st.session_state.lat = message["lat"]
            st.session_state.lon = message["lon"]
    except:
        pass

if "lat" not in st.session_state:
    st.info("📍 위치 정보를 불러오는 중입니다… (모바일이면 잠시만 기다려주세요)")
    st.stop()

curr_lat = st.session_state.lat
curr_lon = st.session_state.lon

# =========================
# 정류장 거리 계산
# =========================
df_gps.columns = ["정류장명", "위도", "경도"]
df_gps["위도"] = pd.to_numeric(df_gps["위도"], errors="coerce")
df_gps["경도"] = pd.to_numeric(df_gps["경도"], errors="coerce")
df_gps = df_gps.dropna()

df_gps["거리"] = df_gps.apply(
    lambda r: haversine(curr_lat, curr_lon, r["위도"], r["경도"]), axis=1
)

nearest_3 = df_gps.sort_values("거리").head(3)

# =========================
# 지도 표시
# =========================
st.subheader("📍 내 위치 & 근처 정류장")
st.map(pd.DataFrame({
    "lat": [curr_lat] + nearest_3["위도"].tolist(),
    "lon": [curr_lon] + nearest_3["경도"].tolist()
}))

# =========================
# 결과 출력
# =========================
for _, r in nearest_3.iterrows():
    st.divider()
    st.subheader(f"🚏 {r['정류장명']} ({r['거리']:.2f} km)")

    up, down = search_station(r["정류장명"])
    c1, c2 = st.columns(2)

    with c1:
        st.write("⬆ 상행")
        for u in up:
            st.write(f"{u[1]} → {u[2]} | {u[3]} | {u[4]}")

    with c2:
        st.write("⬇ 하행")
        for d in down:
            st.write(f"{d[1]} → {d[2]} | {d[3]} | {d[4]}")
