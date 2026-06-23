import sqlite3
from datetime import datetime

DB_PATH = 'stock_data.db'

def get_connection():
    return sqlite3.connect(DB_PATH)

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    # Bảng User/Group mapping (để bot biết gửi tin vào channel nào)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS server_settings (
            guild_id TEXT PRIMARY KEY,
            alert_channel_id TEXT
        )
    ''')
    # Bảng Portfolios (Quản lý danh mục cá nhân)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS portfolios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT,
            ticker TEXT,
            buy_price REAL,
            volume INTEGER,
            created_at TEXT
        )
    ''')
    conn.commit()
    conn.close()

def set_alert_channel(guild_id: str, channel_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO server_settings (guild_id, alert_channel_id)
        VALUES (?, ?)
        ON CONFLICT(guild_id) DO UPDATE SET alert_channel_id=excluded.alert_channel_id
    ''', (guild_id, channel_id))
    conn.commit()
    conn.close()

def get_all_alert_channels():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT alert_channel_id FROM server_settings')
    rows = cursor.fetchall()
    conn.close()
    return [row[0] for row in rows]

def add_to_portfolio(user_id: str, ticker: str, buy_price: float, volume: int):
    conn = get_connection()
    cursor = conn.cursor()
    ticker = ticker.upper()
    
    # Kiểm tra xem mã này đã có trong danh mục chưa, nếu có thì tính trung bình giá
    cursor.execute('SELECT id, buy_price, volume FROM portfolios WHERE user_id=? AND ticker=?', (user_id, ticker))
    row = cursor.fetchone()
    
    if row:
        record_id, old_price, old_vol = row
        new_vol = old_vol + volume
        new_price = ((old_price * old_vol) + (buy_price * volume)) / new_vol
        cursor.execute('''
            UPDATE portfolios 
            SET buy_price=?, volume=?, created_at=? 
            WHERE id=?
        ''', (new_price, new_vol, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), record_id))
    else:
        cursor.execute('''
            INSERT INTO portfolios (user_id, ticker, buy_price, volume, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, ticker, buy_price, volume, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    
    conn.commit()
    conn.close()

def remove_from_portfolio(user_id: str, ticker: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM portfolios WHERE user_id=? AND ticker=?', (user_id, ticker.upper()))
    deleted = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_user_portfolio(user_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT ticker, buy_price, volume FROM portfolios WHERE user_id=?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return [{"ticker": r[0], "buy_price": r[1], "volume": r[2]} for r in rows]

def get_all_portfolios():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, ticker, buy_price, volume FROM portfolios')
    rows = cursor.fetchall()
    conn.close()
    return rows

# Khởi tạo DB khi load module
init_db()
