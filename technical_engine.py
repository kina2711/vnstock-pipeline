import os
import pandas as pd
from ta.momentum import RSIIndicator
from ta.trend import MACD
from ta.volatility import BollingerBands
from discord_alert import send_alert
from dotenv import load_dotenv
import pandas_gbq
import database

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BQ_DATASET = os.getenv("BQ_DATASET")
WATCHLIST = [
    "FPT", "SSI", "HPG", "VCB", "CTG", "MBB", "TCB", "VPB", 
    "MWG", "VHM", "VIC", "VNM", "PNJ", "MSN", "SAB", "STB", 
    "HDB", "VIB", "ACB", "BCM"
]

def update_readme(results_str):
    """Cập nhật nội dung báo cáo tự động vào README.md"""
    readme_path = "README.md"
    if os.path.exists(readme_path):
        import re
        with open(readme_path, "r", encoding="utf-8") as f:
            content = f.read()
        
        # Tạo template thời gian chạy
        from datetime import datetime
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        new_block = f"<!-- LATEST_SIGNALS_START -->\n**Cập nhật lần cuối:** `{now_str}`\n\n{results_str}\n<!-- LATEST_SIGNALS_END -->"
        
        new_content = re.sub(
            r"<!-- LATEST_SIGNALS_START -->.*<!-- LATEST_SIGNALS_END -->",
            new_block,
            content,
            flags=re.DOTALL
        )
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(new_content)

def calculate_technical_indicators(df):
    """
    Sử dụng thư viện ta (Technical Analysis) để tính toán các chỉ báo cho Dataframe.
    """
    # 1. Tính RSI (Relative Strength Index)
    rsi = RSIIndicator(close=df['close'], window=14)
    df['rsi'] = rsi.rsi()

    # 2. Tính MACD
    macd = MACD(close=df['close'], window_slow=26, window_fast=12, window_sign=9)
    df['macd'] = macd.macd()
    df['macd_signal'] = macd.macd_signal()
    df['macd_diff'] = macd.macd_diff() # Histogram

    # 3. Tính Bollinger Bands
    bb = BollingerBands(close=df['close'], window=20, window_dev=2)
    df['bb_high'] = bb.bollinger_hband()
    df['bb_low'] = bb.bollinger_lband()
    
    return df

def run_eod_scanner():
    """
    Quét dữ liệu cuối ngày (EOD) để tìm kiếm các tín hiệu mua/bán chuẩn kỹ thuật.
    """
    print("\n[+] BẮT ĐẦU QUÉT TÍN HIỆU KỸ THUẬT (EOD)")
    readme_results = []
    
    for ticker in WATCHLIST:
        try:
            # Lấy data từ BigQuery
            query = f"SELECT * FROM `{GCP_PROJECT_ID}.{BQ_DATASET}.daily_{ticker}` ORDER BY time ASC"
            df = pandas_gbq.read_gbq(query, project_id=GCP_PROJECT_ID)
            
            if len(df) < 26:
                msg = f"[{ticker}] Không đủ dữ liệu để tính toán MACD (Cần > 26 phiên). Bỏ qua."
                print(msg)
                readme_results.append(f"- **{ticker}**: Không đủ dữ liệu.")
                continue
                
            # Tính toán các chỉ báo
            df = calculate_technical_indicators(df)
            
            # Lấy 2 phiên gần nhất để so sánh xu hướng (Hôm qua và Hôm nay)
            latest = df.iloc[-1]
            previous = df.iloc[-2]
            
            # --- RULES ENGINE ---
            signals = []
            
            # Rule 1: MACD Golden Cross (MACD cắt lên Signal)
            if previous['macd'] <= previous['macd_signal'] and latest['macd'] > latest['macd_signal']:
                signals.append("MACD Golden Cross")
                
            # Rule 2: RSI Quá bán (Oversold) bật lên
            if previous['rsi'] < 30 and latest['rsi'] >= 30:
                signals.append("RSI bật khỏi vùng quá bán")
                
            # Rule 3: Giá thủng dải Bollinger Dưới (Dấu hiệu đảo chiều tiềm năng)
            if latest['close'] <= latest['bb_low']:
                signals.append("Giá chạm đáy Bollinger Bands")
                
            # Tổng hợp và bắn Alert
            if signals:
                signal_str = " + ".join(signals)
                msg = f"Hệ thống TA tự động phát hiện cụm tín hiệu: **{signal_str}**.\nChỉ báo hiện tại: RSI = {latest['rsi']:.1f}, MACD = {latest['macd']:.2f}"
                
                # Tính toán Target và Cutloss mặc định (Target +10%, Cutloss -5%)
                current_price = latest['close']
                target_price = current_price * 1.10
                cutloss_price = current_price * 0.95
                action_str = "MUA MỚI" if "MACD" in signal_str or "RSI" in signal_str else "QUAN SÁT"
                
                send_alert(
                    ticker=ticker, 
                    signal_type="TÍN HIỆU TECHNICAL", 
                    price=current_price, 
                    volume=int(latest['volume']), 
                    message=msg,
                    target=target_price,
                    cutloss=cutloss_price,
                    action=action_str
                )
                
                # Lưu vào list để ghi ra README
                readme_results.append(f"- **{ticker}** (`{current_price}`): {action_str} - Tín hiệu `{signal_str}` (Target: {target_price:,.0f}, Cutloss: {cutloss_price:,.0f})")
                
                # Lưu lịch sử khuyến nghị vào Database để thống kê (Chỉ lưu lệnh MUA)
                if action_str == "MUA MỚI":
                    database.log_recommendation(
                        ticker=ticker,
                        action="MUA",
                        price=current_price,
                        target=target_price,
                        cutloss=cutloss_price,
                        reason=signal_str
                    )
                
        except Exception as e:
            print(f"Lỗi khi xử lý kỹ thuật mã {ticker}: {e}")
            readme_results.append(f"- **{ticker}**: Lỗi hệ thống ({e})")
            
    # Ghi đè file README
    if readme_results:
        update_readme("\n".join(readme_results))
        print("[+] Đã cập nhật kết quả vào README.md")
        
    print("[+] KẾT THÚC QUÉT TÍN HIỆU.")

if __name__ == "__main__":
    run_eod_scanner()
