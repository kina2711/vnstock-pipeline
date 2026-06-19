# 📈 VNStock Data Pipeline & Alert Bot

Hệ thống Data Engineering tự động thu thập dữ liệu chứng khoán Việt Nam, lưu trữ trên **Google Cloud Platform (GCS & BigQuery)** và phân tích tín hiệu kỹ thuật (Technical Analysis) bằng Pandas-TA. 

## ⚙️ Quy trình Kỹ thuật Chi tiết (Technical Workflow)

Hệ thống được thiết kế theo mô hình Medallion Architecture (Bronze - Silver - Gold) chuẩn Data Engineering, đảm bảo khả năng mở rộng và xử lý lỗi (Fault Tolerance) cao:

### 1. Ingestion Layer (Thu thập dữ liệu)
- **Công nghệ**: `yfinance`, `pandas`
- **Quy trình**: File `crawler.py` sẽ tự động kết nối và tải về dữ liệu lịch sử nến ngày (EOD - 50 phiên gần nhất) và nến phút (Intraday - 1 phút) của các mã cổ phiếu trong Watchlist (VD: FPT, SSI, MBB).
- **Fallback Mechanism**: Việc sử dụng `yfinance` thay vì API nội địa giúp tránh triệt để tình trạng lỗi `403 Forbidden` khi bị các CTCK chặn IP scrapers.

### 2. Bronze Layer (Lưu trữ Dữ liệu Thô)
- **Công nghệ**: `google-cloud-storage`
- **Quy trình**: Toàn bộ Dataframe thô (chứa Datetime, Open, High, Low, Close, Volume) sẽ được chuyển đổi ngay lập tức thành định dạng `.csv` và ném vào bucket **Google Cloud Storage** (`vnstock-raw-bucket`).
- **Mục đích**: Lưu trữ Data Lake giá rẻ, phục vụ backtest hoặc rebuild Database trong trường hợp rủi ro mất dữ liệu.

### 3. Silver Layer (Data Warehouse)
- **Công nghệ**: `pandas-gbq`, **Google BigQuery**
- **Quy trình**: Dữ liệu sau khi làm sạch các cột dư thừa sẽ được ánh xạ (mapping) và `UPSERT` vào BigQuery Dataset (`stock_dataset`).
- **Mục đích**: Tận dụng engine tính toán phân tán siêu mạnh của BigQuery để lưu trữ tập dữ liệu khổng lồ theo thời gian và cho phép truy vấn cực nhanh (Sub-second query) bằng SQL.

### 4. Gold Layer (Technical Engine)
- **Công nghệ**: `pandas`, `ta` (Technical Analysis library)
- **Quy trình**: File `technical_engine.py` gọi truy vấn SQL vào BigQuery để rút dữ liệu ngược về RAM. Sau đó, nó sử dụng thư viện `ta` để tính toán chính xác các tham số lượng tử:
  - **MACD**: (Window Slow=26, Window Fast=12, Sign=9) -> Bắt tín hiệu *Golden Cross*.
  - **RSI**: (Window=14) -> Bắt tín hiệu *Oversold Pullback* (<30 bật lên).
  - **Bollinger Bands**: (Window=20, Dev=2) -> Bắt tín hiệu xuyên thủng hỗ trợ dải dưới.
- **Mục đích**: Thay thế con người quét qua hàng trăm mã để lọc ra các cổ phiếu đang nằm ở điểm nổ dòng tiền.

### 5. Automation & Alerting (CI/CD)
- **Công nghệ**: **GitHub Actions**, **Discord Webhook**
- **Quy trình**: File `.github/workflows/bot_pipeline.yml` định nghĩa một máy chủ ảo Ubuntu chạy tự động dựa trên Cronjob (`30 8 * * 1-5` - tức 15h30 chiều VN).
- Nó cài đặt môi trường, chạy 2 scripts trên, và đẩy JSON Alert về Discord. Cuối cùng, Git Bot sẽ tự động **Commit & Push** các thông số vừa tính toán ngược lại vào chính file `README.md` này để tạo ra một Dashboard Real-time.

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
