import os
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

def send_alert(ticker: str, signal_type: str, price: float, volume: int, message: str, target: float = None, cutloss: float = None, action: str = "QUAN SÁT"):
    """
    Gửi cảnh báo sang Discord thông qua Webhook với format chuyên nghiệp (FireAnt/Simplize).
    """
    if not DISCORD_WEBHOOK_URL:
        print(f"[CẢNH BÁO LOCAL] {ticker} - {signal_type}: {message} (Price: {price}, Vol: {volume})")
        return

    # Xác định màu sắc dựa trên Hành động
    if "MUA" in action.upper() or "TÍCH CỰC" in signal_type.upper():
        color = 0x2ECC71 # Xanh lá
        emoji = "🟢"
    elif "BÁN" in action.upper() or "TIÊU CỰC" in signal_type.upper():
        color = 0xE74C3C # Đỏ
        emoji = "🔴"
    else:
        color = 0xF1C40F # Vàng
        emoji = "🟡"

    # Tính phần trăm Target và Cutloss
    target_str = "N/A"
    cutloss_str = "N/A"
    if target and target > 0:
        pct = (target - price) / price * 100
        target_str = f"{target:,.0f} VND (+{pct:.1f}%)"
    if cutloss and cutloss > 0:
        pct = (cutloss - price) / price * 100
        cutloss_str = f"{cutloss:,.0f} VND ({pct:.1f}%)"

    payload = {
        "username": "VNStock Robo-Advisor",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2933/2933116.png",
        "embeds": [
            {
                "title": f"{emoji} KHUYẾN NGHỊ {action}: {ticker.upper()}",
                "description": f"**Luận điểm:** {message}",
                "color": color,
                "fields": [
                    {"name": "Giá hiện tại", "value": f"**{price:,.0f}** VND", "inline": True},
                    {"name": "Khối lượng", "value": f"{volume:,}", "inline": True},
                    {"name": "\u200b", "value": "\u200b", "inline": True}, # Dòng trống để căn chỉnh
                    {"name": "🎯 Target (Chốt lời)", "value": target_str, "inline": True},
                    {"name": "🛡️ Cutloss (Cắt lỗ)", "value": cutloss_str, "inline": True},
                    {"name": "\u200b", "value": "\u200b", "inline": True},
                    {"name": "Hành động đề xuất", "value": f"*{action} quanh vùng giá {price:,.0f}*", "inline": False}
                ],
                "footer": {
                    "text": f"Dữ liệu cập nhật lúc {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | VNStock Data Pipeline"
                }
            }
        ]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"Đã gửi khuyến nghị cho {ticker} tới Discord.")
    except Exception as e:
        print(f"Lỗi khi gửi Discord Webhook: {e}")


