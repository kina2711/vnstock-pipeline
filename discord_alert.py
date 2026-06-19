import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

DISCORD_WEBHOOK_URL = os.getenv("DISCORD_WEBHOOK_URL", "")

def send_alert(ticker: str, signal_type: str, price: float, volume: int, message: str):
    """
    Gửi cảnh báo sang Discord thông qua Webhook.
    """
    if not DISCORD_WEBHOOK_URL:
        print(f"[CẢNH BÁO LOCAL] {ticker} - {signal_type}: {message} (Price: {price}, Vol: {volume})")
        return

    color = 0x00FF00 if "MUA" in signal_type.upper() or "TÍCH CỰC" in signal_type.upper() else 0xFF0000

    payload = {
        "username": "Stock Alert Bot (Data Engineer)",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/2933/2933116.png",
        "embeds": [
            {
                "title": f"🚨 CẢNH BÁO TÍN HIỆU: {ticker}",
                "description": message,
                "color": color,
                "fields": [
                    {"name": "Tín hiệu", "value": signal_type, "inline": True},
                    {"name": "Giá kích hoạt", "value": f"{price:,.0f} VND", "inline": True},
                    {"name": "Khối lượng", "value": f"{volume:,}", "inline": True},
                    {"name": "Thời gian", "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "inline": False}
                ],
                "footer": {
                    "text": "Powered by VNStock Pipeline & GitHub Actions"
                }
            }
        ]
    }

    try:
        response = requests.post(DISCORD_WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"Đã gửi cảnh báo cho {ticker} tới Discord.")
    except Exception as e:
        print(f"Lỗi khi gửi Discord Webhook: {e}")

if __name__ == "__main__":
    # Test webhook locally
    send_alert("FPT", "BREAKOUT MUA", 135000, 2500000, "FPT vừa phá đỉnh lịch sử kèm khối lượng giao dịch đột biến gấp 2 lần trung bình 20 phiên!")
