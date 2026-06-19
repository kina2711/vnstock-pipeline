# Sử dụng Python 3.11 slim để image nhẹ và an toàn
FROM python:3.11-slim

# Cài đặt các thư viện hệ thống cần thiết cho psycopg2 (PostgreSQL) và biên dịch
RUN apt-get update && apt-get install -y \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

# Đặt thư mục làm việc trong container
WORKDIR /app

# Copy file requirements và cài đặt thư viện Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy toàn bộ mã nguồn vào thư mục làm việc
COPY . .

# Định nghĩa biến môi trường mặc định (Có thể ghi đè lúc chạy container)
ENV PYTHONUNBUFFERED=1
ENV TZ=Asia/Ho_Chi_Minh

# Lệnh khởi chạy mặc định (Ví dụ chạy crawler sau đó chạy engine)
# Trong thực tế, có thể chạy một file main.py có chứa schedule loop.
CMD ["sh", "-c", "python crawler.py && python technical_engine.py"]
