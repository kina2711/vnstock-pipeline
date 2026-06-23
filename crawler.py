import os
import pandas as pd
from datetime import datetime, timedelta
import yfinance as yf
from discord_alert import send_alert
from google.cloud import storage
import pandas_gbq
from dotenv import load_dotenv

load_dotenv()

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
BQ_DATASET = os.getenv("BQ_DATASET")

def upload_to_gcs(df, ticker, data_type):
    """Lưu dữ liệu thô (Bronze Layer) vào Google Cloud Storage"""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(GCS_BUCKET_NAME)
        
        # Định dạng tên file: daily_FPT_20260619.csv
        date_str = datetime.now().strftime('%Y%m%d')
        blob_name = f"raw_data/{data_type}_{ticker}_{date_str}.csv"
        
        blob = bucket.blob(blob_name)
        blob.upload_from_string(df.to_csv(index=False), 'text/csv')
        print(f"[{ticker}] Đã lưu backup {data_type} vào GCS: gs://{GCS_BUCKET_NAME}/{blob_name}")
    except Exception as e:
        print(f"[{ticker}] Lỗi khi upload GCS: {e}")

def fetch_daily_data(tickers, days=30):
    """
    Luồng 1: Chạy cuối ngày (EOD) cào dữ liệu nến ngày.
    Thường được setup qua Airflow hoặc GitHub Actions Cron.
    """
    print(f"\n=== BẮT ĐẦU LUỒNG DAILY CRAWLER (EOD) ===")
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d')
    
    for ticker in tickers:
        try:
            print(f"[{ticker}] Đang kéo dữ liệu Daily bằng yfinance...")
            # yfinance dùng hậu tố .VN cho chứng khoán Việt Nam
            stock = yf.Ticker(f"{ticker}.VN")
            df = stock.history(period=f"{days}d")
            
            if df.empty:
                continue
                
            df = df.reset_index()
            # Xóa các cột thừa của yfinance
            df = df[['Date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            
            # Đẩy lên GCS (Bronze Layer)
            upload_to_gcs(df, ticker, "daily")
            
            # Đẩy lên BigQuery (Silver Layer)
            table_id = f"{BQ_DATASET}.daily_{ticker}"
            print(f"[{ticker}] Đang ghi {len(df)} bản ghi vào BigQuery ({table_id})...")
            pandas_gbq.to_gbq(df, destination_table=table_id, project_id=GCP_PROJECT_ID, if_exists='replace')
            print(f"[{ticker}] Đã ghi xong vào BigQuery.")
            
            # --- RULES ENGINE (TÍNH TOÁN CẢNH BÁO) ---
            # Chỉ báo 1: Khối lượng đột biến
            latest = df.iloc[-1]
            avg_vol = df['volume'].mean()
            
            if latest['volume'] > avg_vol * 1.5 and latest['close'] > latest['open']:
                send_alert(
                    ticker=ticker,
                    signal_type="BREAKOUT VOLUME (Daily)",
                    price=latest['close'],
                    volume=int(latest['volume']),
                    message=f"Phát hiện dòng tiền lớn nhập cuộc: Khối lượng hôm nay đạt {latest['volume']:,} vượt 150% trung bình {days} phiên."
                )
                
        except Exception as e:
            print(f"[{ticker}] Lỗi khi kéo dữ liệu Daily: {e}")

def fetch_realtime_data(tickers):
    """
    Luồng 2: Cào dữ liệu Real-time (Intraday) liên tục trong phiên.
    Sẽ được trigger mỗi 1 phút bằng schedule.
    """
    print(f"\n=== BẮT ĐẦU LUỒNG REAL-TIME CRAWLER (Intraday) ===")
    
    today = datetime.now().strftime('%Y-%m-%d')
    # Nếu chạy ngày nghỉ/ngoài giờ giao dịch, có thể sẽ không có data của `today`
    # Nên để demo, ta lấy ngày làm việc gần nhất bằng cách kéo dải thời gian 3 ngày
    start_date = (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d')
    
    for ticker in tickers:
        try:
            print(f"[{ticker}] Đang kéo dữ liệu Intraday (1 phút)...")
            stock = yf.Ticker(f"{ticker}.VN")
            
            # yfinance cho phép lấy data 1m trong 7 ngày gần nhất
            df = stock.history(period="1d", interval="1m")
            
            if df.empty:
                print(f"[{ticker}] Chưa có dữ liệu intraday mới (Có thể ngoài giờ GD).")
                continue
                
            df = df.reset_index()
            df = df[['Datetime', 'Open', 'High', 'Low', 'Close', 'Volume']]
            df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']
            # Chuyển Datetime object thành string để tương thích BigQuery schema
            df['time'] = df['time'].astype(str)
            
            # Đẩy lên GCS (Bronze Layer)
            upload_to_gcs(df, ticker, "intraday")
            
            # Đẩy lên BigQuery (Silver/Gold Layer)
            table_id = f"{BQ_DATASET}.intraday_{ticker}"
            pandas_gbq.to_gbq(df, destination_table=table_id, project_id=GCP_PROJECT_ID, if_exists='replace')
            
            # Đã nạp thành công dữ liệu Intraday vào DB
            print(f"[{ticker}] (Stream) Nạp thành công {len(df)} nến 1 phút mới nhất.")
            
        except Exception as e:
            print(f"[{ticker}] Lỗi khi kéo dữ liệu Intraday: {e}")

if __name__ == "__main__":
    # Danh sách cổ phiếu quan tâm (Watchlist Top 20)
    WATCHLIST = [
        "FPT", "SSI", "HPG", "VCB", "CTG", "MBB", "TCB", "VPB", 
        "MWG", "VHM", "VIC", "VNM", "PNJ", "MSN", "SAB", "STB", 
        "HDB", "VIB", "ACB", "BCM"
    ]
    
    print("🚀 Khởi chạy hệ thống thu thập dữ liệu & cảnh báo chứng khoán VN")
    
    # Chạy mô phỏng 2 luồng
    fetch_daily_data(WATCHLIST, days=50)
    fetch_realtime_data(WATCHLIST)
