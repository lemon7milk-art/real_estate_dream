import streamlit as st
import requests
import pandas as pd

# 공공데이터포털에서 발급받은 Decoding 인증키 입력
SERVICE_KEY = "c7e345016a204ad9df61c37f7cdf1a888ebc40e31ec9a6c4e6b66e0bc994ca56"
API_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

st.set_page_config(page_title="경기도 청약 공고 알림판", layout="wide")

st.title("🏢 경기도 APT 청약 공고 대시보드")
st.caption("한국부동산원 청약홈 분양정보 연동")

@st.cache_data(ttl=3600)
def load_data():
    params = {"page": 1, "perPage": 100, "serviceKey": SERVICE_KEY}
    try:
        res = requests.get(API_URL, params=params, timeout=10)
        res.raise_for_status()
        raw_items = res.json().get("data", [])
        
        cleaned = []
        for item in raw_items:
            area = item.get("SUBSCRPT_AREA_CODE_NM", "")
            addr = item.get("HSSPLY_ADRES", "")
            if "경기" in area or "경기도" in addr:
                cleaned.append({
                    "단지명": item.get("HOUSE_NM"),
                    "구분": item.get("HOUSE_SECD_NM"),
                    "위치": addr,
                    "접수시작일": item.get("RCEPT_BGNDE"),
                    "접수종료일": item.get("RCEPT_ENDDE"),
                    "당첨자발표": item.get("PRZWLR_ANNC_DE"),
                    "링크": item.get("PBLANC_URL")
                })
        return pd.DataFrame(cleaned)
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    st.sidebar.header("🔍 검색 및 필터")
    search_keyword = st.sidebar.text_input("단지명 또는 지역 검색 (예: 수원, 화성, 평택)")
    
    types = ["전체"] + list(df["구분"].dropna().unique())
    selected_type = st.sidebar.selectbox("주택 구분", types)
    
    filtered_df = df.copy()
    if search_keyword:
        filtered_df = filtered_df[
            filtered_df["단지명"].str.contains(search_keyword, na=False) |
            filtered_df["위치"].str.contains(search_keyword, na=False)
        ]
    if selected_type != "전체":
        filtered_df = filtered_df[filtered_df["구분"] == selected_type]
        
    st.metric("총 검색 공고 수", f"{len(filtered_df)}건")
    
    tab1, tab2 = st.tabs(["📋 카드 목록 뷰", "📊 데이터 표 뷰"])
    
    with tab1:
        for _, row in filtered_df.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.subheader(f"[{row['구분']}] {row['단지명']}")
                    st.write(f"📍 **위치:** {row['위치']}")
                    st.write(f"📅 **접수기간:** `{row['접수시작일']}` ~ `{row['접수종료일']}`  |  🎉 **발표일:** `{row['당첨자발표']}`")
                with col2:
                    if row["링크"]:
                        st.link_button("청약홈 공고 바로가기", row["링크"], use_container_width=True)
                        
    with tab2:
        st.dataframe(filtered_df, use_container_width=True)
else:
    st.warning("조회된 경기도 청약 데이터가 없습니다.")
