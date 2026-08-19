import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from datetime import datetime
import requests

SERVICE_KEY = os.environ.get("SERVICE_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")
EMAIL_RECEIVER = os.environ.get("EMAIL_RECEIVER")

API_URL = "https://api.odcloud.kr/api/ApplyhomeInfoDetailSvc/v1/getAPTLttotPblancDetail"

def send_notification_email(matched_items):
    today_str = datetime.now().strftime("%Y년 %m월 %d일")
    
    # HTML 이메일 본문 생성
    html_content = f"""
    <html>
    <body style="font-family: 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 8px;">
            <h2 style="color: #2b6cb0; border-bottom: 2px solid #2b6cb0; padding-bottom: 10px;">
                🏢 남양주시 신규 청약 맞춤 알림 ({today_str})
            </h2>
            <p>회원님을 위한 <strong>[남양주 & 세대원 청약 가능(민영)]</strong> 공고가 등록되어 안내해 드립니다.</p>
    """
    
    for item in matched_items:
        html_content += f"""
        <div style="background-color: #f7fafc; border-left: 4px solid #3182ce; padding: 15px; margin-bottom: 15px; border-radius: 4px;">
            <h3 style="margin-top: 0; color: #1a202c;">{item['name']} <span style="font-size: 12px; background: #e2e8f0; padding: 2px 6px; border-radius: 4px;">{item['supply']}</span></h3>
            <p style="margin: 4px 0; font-size: 14px;"><strong>📍 위치:</strong> {item['addr']}</p>
            <p style="margin: 4px 0; font-size: 14px;"><strong>🎁 특별공급:</strong> {item['sp_date']}</p>
            <p style="margin: 4px 0; font-size: 14px;"><strong>🥇 1순위 접수:</strong> {item['rnk1_date']}</p>
            <p style="margin: 4px 0; font-size: 14px;"><strong>🎉 당첨자 발표:</strong> {item['winner_date']}</p>
            <div style="margin-top: 10px;">
                <a href="{item['url']}" style="background-color: #3182ce; color: white; padding: 8px 14px; text-decoration: none; border-radius: 4px; font-size: 13px; display: inline-block;">청약홈 공고 바로가기</a>
            </div>
        </div>
        """
        
    html_content += """
            <p style="font-size: 12px; color: #718096; margin-top: 20px;">
                * 본 메일은 GitHub Actions 자동화 시스템을 통해 청약홈 Open API 데이터를 기반으로 발송되었습니다.
            </p>
        </div>
    </body>
    </html>
    """

    msg = MIMEMultipart("alternative")
    msg["Subject"] = f"🔔 [청약알림] 남양주시 맞춤 공고 {len(matched_items)}건 등록"
    msg["From"] = EMAIL_USER
    msg["To"] = EMAIL_RECEIVER
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, EMAIL_RECEIVER, msg.as_string())
        print("✅ 알림 이메일 발송 성공!")
    except Exception as e:
        print(f"❌ 이메일 발송 실패: {e}")

def check_subscription():
    params = {"page": 1, "perPage": 50, "serviceKey": SERVICE_KEY}
    try:
        res = requests.get(API_URL, params=params, timeout=10)
        res.raise_for_status()
        data = res.json().get("data", [])
    except Exception as e:
        print(f"API 호출 오류: {e}")
        return

    today_str = datetime.now().strftime("%Y-%m-%d")
    matched_items = []

    for item in data:
        addr = item.get("HSSPLY_ADRES", "")
        dtl_type = item.get("HOUSE_DTL_SECD_NM", "") or item.get("HOUSE_SECD_NM", "민영")
        rcept_endde = item.get("RCEPT_ENDDE", "")
        
        # 필터: 남양주 + 민영(세대원 가능) + 접수 마감 전 공고
        if "남양주" in addr and ("민영" in dtl_type or ("국민" not in dtl_type and "공공" not in dtl_type)):
            if not rcept_endde or rcept_endde >= today_str:
                matched_items.append({
                    "name": item.get("HOUSE_NM"),
                    "addr": addr,
                    "supply": f"{item.get('TOT_SUPLY_HSHLDCO', '-')}세대",
                    "sp_date": item.get("SPSPLY_RCEPT_BGNDE", "-"),
                    "rnk1_date": item.get("GNRL_RNK1_CRTR_RCEPT_PD", item.get("RCEPT_BGNDE", "-")),
                    "winner_date": item.get("PRZWLR_ANNC_DE", "-"),
                    "url": item.get("PBLANC_URL", "https://www.applyhome.co.kr")
                })

    if matched_items:
        print(f"조건 만족 공고 {len(matched_items)}건 발견. 메일을 전송합니다.")
        send_notification_email(matched_items)
    else:
        print("현재 조건에 맞는 신규/진행 공고가 없어 메일을 보내지 않습니다.")

if __name__ == "__main__":
    check_subscription()
