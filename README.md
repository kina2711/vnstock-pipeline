# 📈 VNStock Data Pipeline & AI Trading Sage Bot

Hệ thống tự động thu thập dữ liệu chứng khoán Việt Nam, phân tích tín hiệu kỹ thuật (Technical Analysis), và cung cấp Trợ lý AI (Trading Sage) thông minh qua Discord. 

## ⚙️ Kiến Trúc Hệ Thống

### 1. Data Pipeline (Thu thập & Xử lý Dữ liệu)
- **Công nghệ**: `yfinance`, `pandas`, `google-cloud-storage`, `pandas-gbq`, **Google BigQuery**
- **Quy trình**: File `crawler.py` tự động lấy dữ liệu EOD và Intraday của Top 20 mã cổ phiếu hot (VN30), lưu trữ tại GCS (Bronze Layer) và BigQuery (Silver Layer).

### 2. Technical Engine (Cỗ Máy Lượng Tử)
- **Công nghệ**: `pandas`, `ta`
- **Quy trình**: File `technical_engine.py` lấy dữ liệu từ BigQuery, tính toán các chỉ báo (MACD, RSI, Bollinger Bands) để phát hiện các điểm nổ dòng tiền.

### 3. AI Trading Sage (Trợ lý Phân tích Chuyên sâu)
- **Công nghệ**: `google-generativeai` (Gemini API), API Phân tích Cơ bản TCBS.
- **Quy trình**: File `trading_sage.py` kết hợp dữ liệu Kỹ thuật (TA) và Cơ bản (FA: P/E, P/B, ROE...) đưa vào mô hình AI Gemini để tạo ra một Kịch bản giao dịch (Trade Setup) cực kỳ sắc bén như một chuyên gia tài chính.

### 4. Discord Bot (Giao diện Người dùng)
- **Công nghệ**: `discord.py`
- **Quy trình**: File `discord_bot.py` là một Bot tương tác chạy 24/24. Cung cấp các lệnh gạch chéo (`/sage_analyze`) để người dùng yêu cầu AI phân tích tức thì ngay trên Discord.

### 5. Automation & Alerting (CI/CD)
- **Công nghệ**: **GitHub Actions**, **Discord Webhook**
- Data Pipeline chạy tự động mỗi giờ (Cronjob `0 * * * *`). Tự động quét thị trường, gửi Alert về Discord và ghi đè kết quả phân tích vào chính file `README.md` này.

---
## 🤖 Trạng Thái Quét Gần Nhất (Auto-Updated)
*Hệ thống CI/CD sẽ tự động chạy và ghi đè kết quả mới nhất vào phần dưới đây mỗi ngày:*

<!-- LATEST_SIGNALS_START -->
**Cập nhật lần cuối:** `2026-06-29 20:53:08`

- **SAB** (`48700.0`): MUA MỚI - Tín hiệu `MACD Golden Cross` (Target: 53,570, Cutloss: 46,265)
<!-- LATEST_SIGNALS_END -->

---
## 🚀 Hướng Dẫn Cài Đặt & Chạy Local
1. Clone repo và tạo môi trường ảo:
```bash
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
2. Đặt file `gcp_credentials.json` vào thư mục gốc (để dùng tính năng BigQuery).
3. Tạo file `.env` với các cấu hình sau:
```env
DISCORD_BOT_TOKEN="Token_Bot_Discord_Của_Bạn"
GEMINI_API_KEY="Key_Gemini_Của_Bạn"
DISCORD_WEBHOOK_URL="Webhook_Báo_Cáo_Tự_Động"
GCP_PROJECT_ID="Tên_Project_GCP"
GCS_BUCKET_NAME="Tên_Bucket"
BQ_DATASET="Tên_Dataset"
```
4. Chạy hệ thống:
- Chạy Pipeline lấy data: `python crawler.py`
- Chạy quét kỹ thuật: `python technical_engine.py`
- Bật Bot Discord AI (Treo 24/24): `python discord_bot.py`
