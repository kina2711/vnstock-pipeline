# 📈 VNStock Data Pipeline & Alert Bot

Hệ thống Data Engineering tự động thu thập dữ liệu chứng khoán Việt Nam, lưu trữ trên **Google Cloud Platform (GCS & BigQuery)** và phân tích tín hiệu kỹ thuật (Technical Analysis) bằng Pandas-TA. 

## 🏗 Kiến trúc Hệ thống
1. **Bronze Layer**: Dữ liệu nến thô (OHLCV) kéo từ `yfinance` (.VN) được backup dưới định dạng `.csv` lên **Google Cloud Storage**.
2. **Silver Layer**: Dataframe được tự động chuẩn hóa và nạp vào **Google BigQuery** phục vụ tính toán khối lượng lớn.
3. **Gold Layer (Engine)**: Đọc từ BigQuery, tính toán MACD, RSI, Bollinger Bands và lọc ra các cổ phiếu có dòng tiền lớn.
4. **DevOps**: Tự động chạy hằng ngày (15:30 VN) thông qua **GitHub Actions** và gửi tín hiệu về **Discord**.

---
## 🤖 Trạng Thái Quét Gần Nhất (Auto-Updated)
*Hệ thống CI/CD sẽ tự động chạy và ghi đè kết quả mới nhất vào phần dưới đây mỗi ngày:*

<!-- LATEST_SIGNALS_START -->
**Cập nhật lần cuối:** `2026-06-19 16:07:28`

- **FPT** (`71500.0`): Tín hiệu `Tích lũy nền chặt (Giả lập Test Bot)` (RSI: 42.4, MACD: -302.08)
- **SSI** (`27150.0`): Tín hiệu `Tích lũy nền chặt (Giả lập Test Bot)` (RSI: 48.1, MACD: -139.24)
- **MBB** (`25000.0`): Tín hiệu `Tích lũy nền chặt (Giả lập Test Bot)` (RSI: 46.4, MACD: -120.62)
<!-- LATEST_SIGNALS_END -->

---
## 🚀 Hướng Dẫn Chạy Local
1. Clone repo và tạo môi trường ảo:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2. Đặt file `gcp_credentials.json` vào thư mục gốc.
3. Tạo file `.env` chứa `DISCORD_WEBHOOK_URL`, `GCP_PROJECT_ID`, `GCS_BUCKET_NAME`, `BQ_DATASET`.
4. Chạy crawler:
```bash
python crawler.py
python technical_engine.py
```
