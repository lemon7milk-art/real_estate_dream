import streamlit as st
import requests
import pandas as pd

# 공공데이터포털 디코딩 인증키
SERVICE_KEY = "c7e345016a204ad9df61c37f7cdf1a888ebc40e31ec9a6c4e6b66e0bc994ca56"
API_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

st.set_page_config(page_title="청약 대시보드 | 경기도 & 남양주 맞춤", layout="wide")

st.title("🏢 경기도 청약 공고 & 맞춤 추천")
st.caption("한국부동산원 청약홈 데이터 기반 | 비규제지역 민영 APT 세대원 1순위 필터링")

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
            house_type = item.get("HOUSE_SECD_NM", "")
            
            if "경기" in area or "경기도" in addr:
                # 비규제지역(남양주 등) 민영주택은 만 19세 이상 세대원도 1순위 청약 가능
                # 국민주택이나 규제지역(강남3구/용산 등)은 세대주 요건 필수
                is_member_eligible = ("민영" in house_type)
                
                cleaned.append({
                    "단지명": item.get("HOUSE_NM"),
                    "구분": house_type,
                    "위치": addr,
                    "접수시작일": item.get("RCEPT_BGNDE"),
                    "접수종료일": item.get("RCEPT_ENDDE"),
                    "당첨자발표": item.get("PRZWLR_ANNC_DE"),
                    "링크": item.get("PBLANC_URL"),
                    "세대원가능여부": is_member_eligible
                })
        return pd.DataFrame(cleaned)
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
        return pd.DataFrame()

df = load_data()

if not df.empty:
    # 탭 구성 (맞춤 추천 탭을 맨 앞에 배치)
    tab_custom, tab_all, tab_table = st.tabs([
        "🎯 나를 위한 맞춤 추천 (남양주 & 세대원 가능)", 
        "📋 경기도 전체 목록", 
        "📊 데이터 표 뷰"
    ])
    
    # 1. 맞춤 추천 탭: 남양주 + 민영 APT(세대원 가능)
    with tab_custom:
        custom_df = df[
            df["위치"].str.contains("남양주", na=False) & 
            df["세대원가능여부"]
        ]
        
        st.info("💡 **남양주시 민영 APT 청약 가이드**: 남양주시는 비규제지역으로, 만 19세 이상 세대원도 청약통장 조건(가입 12개월 이상, 지역별 예치금 충족)만 맞추면 1순위 청약이 가능합니다.")
        st.metric("추천 공고 수", f"{len(custom_df)}건")
        
        if not custom_df.empty:
            for _, row in custom_df.iterrows():
                with st.container(border=True):
                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.subheader(f"[{row['구분']}] {row['단지명']}")
                        st.markdown("**:green[✔ 세대원 청약 가능 (비규제 민영)]**")
                        st.write(f"📍 **위치:** {row['위치']}")
                        st.write(f"📅 **접수기간:** `{row['접수시작일']}` ~ `{row['접수종료일']}`  |  🎉 **발표일:** `{row['당첨자발표']}`")
                    with col2:
                        if row["링크"]:
                            st.link_button("청약홈 상세 보기", row["링크"], use_container_width=True)
        else:
            st.warning("현재 접수 중이거나 예정된 남양주시 세대원 가능 공고가 없습니다. (전체 목록 탭을 확인해보세요!)")

    # 2. 전체 목록 탭
    with tab_all:
        st.sidebar.header("🔍 검색 및 필터")
        search_keyword = st.sidebar.text_input("단지명 또는 지역 검색 (예: 수원, 화성, 평택)")
        types = ["전체"] + list(df["구분"].dropna().unique())
        selected_type = st.sidebar.selectbox("주택 구분", types)
        
        # 세대원 가능 여부 필터 추가
        only_member_allowed = st.sidebar.checkbox("세대원 청약 가능(민영)만 보기", value=False)
        
        filtered_df = df.copy()
        if search_keyword:
            filtered_df = filtered_df[
                filtered_df["단지명"].str.contains(search_keyword, na=False) |
                filtered_df["위치"].str.contains(search_keyword, na=False)
            ]
        if selected_type != "전체":
            filtered_df = filtered_df[filtered_df["구분"] == selected_type]
        if only_member_allowed:
            filtered_df = filtered_df[filtered_df["세대원가능여부"]]
            
        st.metric("총 검색 공고 수", f"{len(filtered_df)}건")
        
        for _, row in filtered_df.iterrows():
            with st.container(border=True):
                col1, col2 = st.columns([4, 1])
                with col1:
                    st.subheader(f"[{row['구분']}] {row['단지명']}")
                    if row["세대원가능여부"]:
                        st.caption("🟢 세대원 청약 가능")
                    else:
                        st.caption("🟡 세대주 확인 필요 (국민/공공)")
                    st.write(f"📍 **위치:** {row['위치']}")
                    st.write(f"📅 **접수기간:** `{row['접수시작일']}` ~ `{row['접수종료일']}`  |  🎉 **발표일:** `{row['당첨자발표']}`")
                with col2:
                    if row["링크"]:
                        st.link_button("청약홈 바로가기", row["링크"], use_container_width=True)
                        
    # 3. 데이터 표 뷰
    with tab_table:
        st.dataframe(df, use_container_width=True)
else:
    st.warning("조회된 청약 데이터가 없습니다.")
