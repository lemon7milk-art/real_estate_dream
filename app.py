import streamlit as st
import requests
import pandas as pd
from datetime import datetime

# 공공데이터포털 디코딩 인증키
SERVICE_KEY = "c7e345016a204ad9df61c37f7cdf1a888ebc40e31ec9a6c4e6b66e0bc994ca56"
API_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

st.set_page_config(page_title="청약 대시보드 | 경기도 & 남양주 맞춤", layout="wide")

st.title("🏢 경기도 청약 공고 & 일정 대시보드")
st.caption("한국부동산원 청약홈 데이터 연동 | 진행·예정 공고 및 지난 공고 분리 조회")

@st.cache_data(ttl=3600)
def load_data():
    params = {"page": 1, "perPage": 100, "serviceKey": SERVICE_KEY}
    try:
        res = requests.get(API_URL, params=params, timeout=10)
        res.raise_for_status()
        raw_items = res.json().get("data", [])
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        cleaned = []
        
        for item in raw_items:
            area = item.get("SUBSCRPT_AREA_CODE_NM", "")
            addr = item.get("HSSPLY_ADRES", "")
            dtl_type = item.get("HOUSE_DTL_SECD_NM", "") or item.get("HOUSE_SECD_NM", "민영")
            
            if "경기" in area or "경기도" in addr:
                is_member_eligible = ("민영" in dtl_type) or ("국민" not in dtl_type and "공공" not in dtl_type)
                
                # 총 공급세대수
                tot_supply = item.get("TOT_SUPLY_HSHLDCO", "")
                tot_supply_str = f"{tot_supply}세대" if tot_supply else "공고문 참조"

                # 특별공급 접수일
                sp_start = item.get("SPSPLY_RCEPT_BGNDE", "")
                sp_end = item.get("SPSPLY_RCEPT_ENDDE", "")
                if sp_start and sp_end:
                    sp_date = sp_start if sp_start == sp_end else f"{sp_start} ~ {sp_end}"
                else:
                    sp_date = sp_start or sp_end or "해당없음"

                # 1순위 접수일
                rnk1_crtr = item.get("GNRL_RNK1_CRTR_RCEPT_PD", "")
                rnk1_etc = item.get("GNRL_RNK1_ETC_GG_RCEPT_PD", "")
                if rnk1_crtr and rnk1_etc and rnk1_crtr != rnk1_etc:
                    rnk1_date = f"{rnk1_crtr}(해당) / {rnk1_etc}(기타경기)"
                else:
                    rnk1_date = rnk1_crtr or rnk1_etc or item.get("RCEPT_BGNDE", "-")

                # 2순위 접수일
                rnk2_crtr = item.get("GNRL_RNK2_CRTR_RCEPT_PD", "")
                rnk2_etc = item.get("GNRL_RNK2_ETC_GG_RCEPT_PD", "")
                rnk2_date = rnk2_crtr or rnk2_etc or "-"

                # 접수 상태 판별
                rcept_bgnde = item.get("RCEPT_BGNDE", "")
                rcept_endde = item.get("RCEPT_ENDDE", "")
                
                if rcept_endde and rcept_endde < today_str:
                    status = "마감"
                elif rcept_bgnde and rcept_bgnde > today_str:
                    status = "접수예정"
                else:
                    status = "접수중"

                # 당첨자 발표일 (청약홈 정확한 필드명: PRZWNER_PRESNATN_DE)
                winner_date = item.get("PRZWNER_PRESNATN_DE") or item.get("PRZWLR_ANNC_DE") or "-"

                cleaned.append({
                    "단지명": item.get("HOUSE_NM"),
                    "구분": dtl_type,
                    "공급세대수": tot_supply_str,
                    "위치": addr,
                    "특별공급": sp_date,
                    "1순위": rnk1_date,
                    "2순위": rnk2_date,
                    "접수시작일": rcept_bgnde,
                    "접수종료일": rcept_endde,
                    "당첨자발표": winner_date,
                    "모집공고일": item.get("RCRIT_PBLANC_DE", "-"),
                    "링크": item.get("PBLANC_URL"),
                    "세대원가능여부": is_member_eligible,
                    "상태": status
                })
        return pd.DataFrame(cleaned)
    except Exception as e:
        st.error(f"데이터 조회 실패: {e}")
        return pd.DataFrame()

df = load_data()

# 공고 카드 렌더링 함수
def render_apt_card(row, is_recommend=False):
    with st.container(border=True):
        col1, col2 = st.columns([4, 1])
        with col1:
            st.subheader(row['단지명'])
            
            # 상태 배지
            if row["상태"] == "접수중":
                status_badge = "**:red[🔥 접수 진행중]**"
            elif row["상태"] == "접수예정":
                status_badge = "**:blue[⏳ 접수 예정]**"
            else:
                status_badge = "**:gray[🔒 접수 마감]**"
            
            # 세대원 자격 배지
            if is_recommend:
                eligibility = "**:green[✔ 세대원 가능]**"
            else:
                eligibility = "**:green[🟢 세대원 가능]**" if row["세대원가능여부"] else "**:orange[🟡 세대주 확인]**"
                
            st.markdown(f"🔢 **공급규모:** **{row['공급세대수']}** &nbsp;|&nbsp; 🏷️ **구분:** `{row['구분']}` &nbsp;|&nbsp; {eligibility} &nbsp;|&nbsp; {status_badge}")
            st.write(f"📍 **위치:** {row['위치']}")
            
            st.divider()
            
            sched_col1, sched_col2, sched_col3, sched_col4 = st.columns(4)
            sched_col1.metric("🎁 특별공급", row["특별공급"])
            sched_col2.metric("🥇 1순위", row["1순위"])
            sched_col3.metric("🥈 2순위", row["2순위"])
            sched_col4.metric("🎉 당첨자 발표", row["당첨자발표"])
            
        with col2:
            st.write("")
            st.caption(f"📢 공고일: {row['모집공고일']}")
            if row["링크"]:
                st.link_button("청약홈 상세 보기", row["링크"], use_container_width=True)

if not df.empty:
    tab_custom, tab_active, tab_closed, tab_table = st.tabs([
        "🎯 맞춤 추천 (남양주 & 세대원)", 
        "🚀 진행 및 예정 공고", 
        "📂 지난 공고 (마감)", 
        "📊 전체 데이터 표"
    ])
    
    # 1. 맞춤 추천 탭
    with tab_custom:
        custom_df = df[
            df["위치"].str.contains("남양주", na=False) & 
            df["세대원가능여부"]
        ]
        
        st.info("💡 **남양주시 민영 APT 청약 안내**: 비규제지역으로, 만 19세 이상 세대원도 청약통장 12개월 이상 및 예치금 충족 시 1순위 청약이 가능합니다.")
        st.metric("남양주 맞춤 공고 수", f"{len(custom_df)}건")
        
        if not custom_df.empty:
            for _, row in custom_df.iterrows():
                render_apt_card(row, is_recommend=True)
        else:
            st.warning("현재 남양주시 세대원 가능 공고가 없습니다. 다른 탭을 확인해보세요!")

    # 사이드바 공통 필터
    st.sidebar.header("🔍 검색 및 필터")
    search_keyword = st.sidebar.text_input("단지명 또는 지역 검색 (예: 화성, 평택, 수원)")
    types = ["전체"] + list(df["구분"].dropna().unique())
    selected_type = st.sidebar.selectbox("주택 구분", types)
    only_member_allowed = st.sidebar.checkbox("세대원 청약 가능(민영)만 보기", value=False)
    
    def apply_filter(target_df):
        res_df = target_df.copy()
        if search_keyword:
            res_df = res_df[
                res_df["단지명"].str.contains(search_keyword, na=False) |
                res_df["위치"].str.contains(search_keyword, na=False)
            ]
        if selected_type != "전체":
            res_df = res_df[res_df["구분"] == selected_type]
        if only_member_allowed:
            res_df = res_df[res_df["세대원가능여부"]]
        return res_df

    # 2. 진행 및 예정 공고 탭
    with tab_active:
        active_df = apply_filter(df[df["상태"].isin(["접수중", "접수예정"])])
        st.metric("진행/예정 공고 수", f"{len(active_df)}건")
        
        if not active_df.empty:
            for _, row in active_df.iterrows():
                render_apt_card(row, is_recommend=False)
        else:
            st.info("현재 진행 중이거나 예정된 청약 공고가 없습니다.")

    # 3. 지난 공고 (마감) 탭
    with tab_closed:
        closed_df = apply_filter(df[df["상태"] == "마감"])
        st.metric("마감된 지난 공고 수", f"{len(closed_df)}건")
        
        if not closed_df.empty:
            for _, row in closed_df.iterrows():
                render_apt_card(row, is_recommend=False)
        else:
            st.info("마감된 공고가 없습니다.")
                        
    # 4. 전체 데이터 표 뷰
    with tab_table:
        st.dataframe(df, use_container_width=True)
else:
    st.warning("조회된 청약 데이터가 없습니다.")
