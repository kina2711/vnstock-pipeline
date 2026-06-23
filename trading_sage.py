import os
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from ta.momentum import RSIIndicator, StochasticOscillator
from ta.trend import MACD, EMAIndicator
from ta.volatility import BollingerBands, AverageTrueRange
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
if api_key:
    genai.configure(api_key=api_key)

SYSTEM_PROMPT = """
Bạn là VNStock Trading Sage, một trợ lý giao dịch Chứng khoán Cơ sở Việt Nam chuyên nghiệp và tinh anh.
Sứ mệnh cốt lõi: Hỗ trợ trader đưa ra quyết định giao dịch thông minh dựa trên dữ liệu Phân tích Kỹ thuật (TA), Cơ bản (FA).

NGUYÊN TẮC HOẠT ĐỘNG TẠO SỰ "WOW":
1. Trình bày cực kỳ chuyên nghiệp, sử dụng markdown mạnh mẽ (In đậm, Bullet points, Emoji) để tạo cảm giác chuyên gia.
2. Phân Tích Đa Chiều: Nhận xét sâu sắc về sức mạnh giá qua EMA, RSI, MACD. Đánh giá nhanh định giá qua P/E, ROE.
3. BẮT BUỘC Đưa ra Kịch bản hành động (Trade Setup) ĐỈNH CAO:
   - Nếu có tín hiệu tốt -> Khuyến nghị MUA. Nếu rủi ro -> QUAN SÁT/BÁN.
   - Entry Zone (Vùng mua)
   - Stop Loss (Cắt lỗ): Dựa vào ATR được cung cấp để trừ đi cho chuẩn.
   - Take Profit (Chốt lời): Đưa ra 2 mốc TP1 (RR 1:1.5) và TP2 (RR 1:2.5).
   - Position Sizing (Quản trị vốn): Khuyến nghị % giải ngân.

Hãy phân tích dữ liệu được cung cấp và đưa ra báo cáo. Ghi nhớ KHÔNG giải thích lằng nhằng, hãy hành văn như một Sói Già Phố Wall (ngắn gọn, bén, dứt khoát).
"""

def get_fundamental_data(ticker):
    import requests
    try:
        url = f"https://apipubaws.tcbs.com.vn/tcanalysis/v1/ticker/{ticker}/financial-ratio"
        headers = {"User-Agent": "Mozilla/5.0"}
        resp = requests.get(url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list) and len(data) > 0:
                latest = data[0]
                return {
                    "P/E": latest.get('priceToEarning', 'N/A'),
                    "P/B": latest.get('priceToBook', 'N/A'),
                    "ROE": latest.get('roe', 'N/A'),
                    "ROA": latest.get('roa', 'N/A'),
                    "Biên LNG": latest.get('grossProfitMargin', 'N/A')
                }
    except Exception as e:
        print(f"Lỗi khi lấy FA cho {ticker}: {e}")
    return {"P/E": "N/A", "P/B": "N/A", "ROE": "N/A", "Biên LNG": "N/A"}

def analyze_stock_with_sage(ticker: str):
    ticker = ticker.upper()
    stock = yf.Ticker(f"{ticker}.VN")
    df = stock.history(period="6mo")
    
    if len(df) < 60:
        raise ValueError(f"Không đủ dữ liệu giao dịch cho mã {ticker}.")
        
    # Tính TA
    # 1. RSI
    rsi = RSIIndicator(close=df['Close'], window=14).rsi().iloc[-1]
    
    # 2. MACD
    macd_obj = MACD(close=df['Close'], window_slow=26, window_fast=12, window_sign=9)
    macd = macd_obj.macd().iloc[-1]
    macd_signal = macd_obj.macd_signal().iloc[-1]
    
    # 3. EMA
    ema20 = EMAIndicator(close=df['Close'], window=20).ema_indicator().iloc[-1]
    ema50 = EMAIndicator(close=df['Close'], window=50).ema_indicator().iloc[-1]
    ema200 = EMAIndicator(close=df['Close'], window=200).ema_indicator().iloc[-1]
    
    # 4. Bollinger Bands
    bb = BollingerBands(close=df['Close'], window=20, window_dev=2)
    bb_high = bb.bollinger_hband().iloc[-1]
    bb_low = bb.bollinger_lband().iloc[-1]
    
    # 5. ATR (Average True Range)
    atr = AverageTrueRange(high=df['High'], low=df['Low'], close=df['Close'], window=14).average_true_range().iloc[-1]
    
    # 6. Stochastic
    stoch = StochasticOscillator(high=df['High'], low=df['Low'], close=df['Close'], window=14, smooth_window=3).stoch().iloc[-1]
    
    current_price = df['Close'].iloc[-1]
    current_vol = df['Volume'].iloc[-1]
    avg_vol = df['Volume'].rolling(window=20).mean().iloc[-1]
    
    # Lấy FA
    fa_data = get_fundamental_data(ticker)
    
    # Xây dựng Context Prompt
    context = f"""
    Mã cổ phiếu: {ticker}
    Giá hiện tại: {current_price:,.0f} VND
    Khối lượng hôm nay: {current_vol:,.0f} (Trung bình 20 phiên: {avg_vol:,.0f})
    
    --- DỮ LIỆU KỸ THUẬT (TA) ---
    - RSI (14): {rsi:.2f}
    - MACD: {macd:.2f}, Signal: {macd_signal:.2f}
    - Stochastic: {stoch:.2f}
    - EMA 20: {ema20:,.0f}
    - EMA 50: {ema50:,.0f}
    - EMA 200: {ema200:,.0f}
    - Bollinger Bands: High {bb_high:,.0f}, Low {bb_low:,.0f}
    - ATR (14): {atr:,.0f} VND
    
    --- DỮ LIỆU CƠ BẢN (FA) ---
    - P/E: {fa_data['P/E']}
    - P/B: {fa_data['P/B']}
    - ROE: {fa_data['ROE']}%
    - Biên lợi nhuận gộp: {fa_data['Biên LNG']}%
    
    Dựa trên số liệu trên, hãy đóng vai Trading Sage và đưa ra bản phân tích siêu cấp vip pro.
    """
    
    if not os.getenv("GEMINI_API_KEY"):
         raise Exception("Bạn cần cấu hình GEMINI_API_KEY trong file .env để dùng tính năng AI Trading Sage.")
         
    try:
        model = genai.GenerativeModel('gemini-flash-latest', system_instruction=SYSTEM_PROMPT)
        response = model.generate_content(context)
        return response.text, current_price
    except Exception as e:
        raise Exception(f"Lỗi gọi Gemini API: {e}. Vui lòng kiểm tra lại Key.")

if __name__ == "__main__":
    print(analyze_stock_with_sage("FPT"))
