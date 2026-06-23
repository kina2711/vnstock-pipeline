import discord
from discord.ext import commands, tasks
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from discord import app_commands
import os
import yfinance as yf
from datetime import datetime
import asyncio
from dotenv import load_dotenv
import database
import trading_sage
load_dotenv()
TOKEN = os.getenv("DISCORD_BOT_TOKEN")

# Khởi tạo Intents
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"[+] Bot đã online với tên: {bot.user}")
    try:
        # Đồng bộ Global (thường mất 1 tiếng)
        synced = await bot.tree.sync()
        print(f"[+] Đã đồng bộ {len(synced)} lệnh Slash command(s) (Global).")
        
        # Ép đồng bộ Local cho từng Server để hiện ngay lập tức
        for guild in bot.guilds:
            bot.tree.copy_global_to(guild=guild)
            await bot.tree.sync(guild=guild)
        print("[+] Đã ép đồng bộ lệnh ngay lập tức cho các Server.")
    except Exception as e:
        print(f"[!] Lỗi đồng bộ lệnh: {e}")
    
    # Khởi động daily task
    if not daily_report_task.is_running():
        daily_report_task.start()

# Lệnh cấu hình kênh nhận thông báo chung
@bot.tree.command(name="set_channel", description="[Admin] Đặt kênh hiện tại làm kênh nhận cảnh báo Daily & Tín hiệu")
@app_commands.default_permissions(administrator=True)
async def set_channel(interaction: discord.Interaction):
    if interaction.guild is None:
        await interaction.response.send_message("❌ Lệnh này dùng để cấu hình nhận tin chung cho cả Group, anh/chị vui lòng chạy lệnh này ở trong một Server (Máy chủ) nhé, không dùng trong tin nhắn riêng ạ.", ephemeral=True)
        return
        
    database.set_alert_channel(str(interaction.guild_id), str(interaction.channel_id))
    await interaction.response.send_message(f"✅ Đã cấu hình kênh **{interaction.channel.name}** để nhận thông báo thị trường.")

# Lệnh thêm danh mục
@bot.tree.command(name="buy", description="Thêm cổ phiếu vào danh mục theo dõi (VD: /buy FPT 130000 100)")
@app_commands.describe(ticker="Mã cổ phiếu (VD: FPT)", price="Giá mua", volume="Số lượng mua")
async def buy(interaction: discord.Interaction, ticker: str, price: float, volume: int):
    database.add_to_portfolio(str(interaction.user.id), ticker.upper(), price, volume)
    await interaction.response.send_message(f"✅ Đã thêm **{volume}** cổ phiếu **{ticker.upper()}** (Giá: {price:,.0f} VND) vào danh mục của bạn.")

# Lệnh xóa danh mục
@bot.tree.command(name="sell", description="Xóa toàn bộ mã cổ phiếu khỏi danh mục")
async def sell(interaction: discord.Interaction, ticker: str):
    success = database.remove_from_portfolio(str(interaction.user.id), ticker.upper())
    if success:
        await interaction.response.send_message(f"✅ Đã bán/xóa mã **{ticker.upper()}** khỏi danh mục.")
    else:
        await interaction.response.send_message(f"❌ Bạn không có mã **{ticker.upper()}** trong danh mục.", ephemeral=True)

# Xem danh mục
@bot.tree.command(name="portfolio", description="Xem danh mục đầu tư hiện tại kèm Lãi/Lỗ")
async def portfolio(interaction: discord.Interaction):
    user_id = str(interaction.user.id)
    items = database.get_user_portfolio(user_id)
    
    if not items:
        await interaction.response.send_message("📊 Danh mục của bạn hiện đang trống. Hãy dùng lệnh `/buy` để thêm mã nhé.")
        return

    await interaction.response.defer()
    
    embed = discord.Embed(title=f"📊 DANH MỤC CỦA {interaction.user.display_name.upper()}", color=0x3498DB)
    total_investment = 0
    total_current_value = 0

    for item in items:
        ticker = item['ticker']
        buy_price = item['buy_price']
        volume = item['volume']
        
        # Lấy giá realtime
        try:
            stock = yf.Ticker(f"{ticker}.VN")
            df = stock.history(period="1d")
            if not df.empty:
                current_price = df['Close'].iloc[-1]
            else:
                current_price = buy_price # Fallback
        except:
            current_price = buy_price
            
        pnl_value = (current_price - buy_price) * volume
        pnl_percent = (current_price - buy_price) / buy_price * 100
        
        icon = "🟢" if pnl_percent > 0 else "🔴" if pnl_percent < 0 else "⚪"
        
        total_investment += buy_price * volume
        total_current_value += current_price * volume
        
        embed.add_field(
            name=f"{icon} {ticker} | SL: {volume:,}",
            value=f"Giá mua: {buy_price:,.0f} đ\nGiá TT: {current_price:,.0f} đ\nLãi/Lỗ: **{pnl_percent:+.2f}%** ({pnl_value:+,.0f} đ)",
            inline=False
        )
        
    total_pnl_percent = (total_current_value - total_investment) / total_investment * 100 if total_investment > 0 else 0
    embed.description = f"**Tổng vốn:** {total_investment:,.0f} đ\n**Giá trị TT:** {total_current_value:,.0f} đ\n**Tổng PnL:** **{total_pnl_percent:+.2f}%**"
    
    await interaction.followup.send(embed=embed)

# Lệnh Khuyến nghị Kỹ thuật tức thì
@bot.tree.command(name="recommend", description="Phân tích kỹ thuật (MACD, RSI) và đưa ra khuyến nghị Mua/Bán cho 1 mã")
@app_commands.describe(ticker="Mã cổ phiếu (VD: FPT, SSI, HPG)")
async def recommend_stock(interaction: discord.Interaction, ticker: str):
    ticker = ticker.upper()
    await interaction.response.defer()
    try:
        stock = yf.Ticker(f"{ticker}.VN")
        df = stock.history(period="3mo")
        if len(df) < 30:
            await interaction.followup.send(f"❌ Không đủ dữ liệu để phân tích mã {ticker}.")
            return
            
        from ta.momentum import RSIIndicator
        from ta.trend import MACD
        
        rsi = RSIIndicator(close=df['Close'], window=14).rsi().iloc[-1]
        
        macd_obj = MACD(close=df['Close'], window_slow=26, window_fast=12, window_sign=9)
        macd = macd_obj.macd().iloc[-1]
        macd_signal = macd_obj.macd_signal().iloc[-1]
        macd_hist = macd_obj.macd_diff().iloc[-1]
        
        cprice = df['Close'].iloc[-1]
        
        action = "NẮM GIỮ / QUAN SÁT"
        color = 0x808080
        icon = "⚪"
        reason = []
        
        if rsi < 30:
            reason.append("RSI < 30: Đang ở vùng Quá Bán (Oversold), có thể cân nhắc bắt đáy.")
            action = "MUA MỚI / BẮT ĐÁY"
            color = 0x00FF00
            icon = "🟢"
        elif rsi > 70:
            reason.append("RSI > 70: Đang ở vùng Quá Mua (Overbought), rủi ro điều chỉnh cao.")
            action = "CHỐT LỜI / BÁN"
            color = 0xFF0000
            icon = "🔴"
            
        if macd > macd_signal and macd_hist > 0:
            reason.append("MACD cắt lên Signal: Xu hướng Tăng (Golden Cross).")
            if "BÁN" not in action:
                action = "MUA MỚI"
                color = 0x00FF00
                icon = "🟢"
        elif macd < macd_signal and macd_hist < 0:
            reason.append("MACD cắt xuống Signal: Xu hướng Giảm (Death Cross).")
            if "MUA" not in action:
                action = "BÁN / CẮT LỖ"
                color = 0xFF0000
                icon = "🔴"
                
        if not reason:
            reason.append("Các chỉ báo ở mức trung bình, chưa có xu hướng rõ ràng.")
            
        embed = discord.Embed(title=f"{icon} PHÂN TÍCH KỸ THUẬT: {ticker}", color=color)
        embed.add_field(name="Giá Hiện Tại", value=f"**{cprice:,.0f} đ**", inline=False)
        embed.add_field(name="Chỉ báo RSI (14)", value=f"{rsi:.1f} {'(Quá Mua)' if rsi>70 else '(Quá Bán)' if rsi<30 else '(Trung tính)'}", inline=True)
        embed.add_field(name="Chỉ báo MACD", value=f"MACD: {macd:.1f}\nSignal: {macd_signal:.1f}", inline=True)
        embed.add_field(name="Chi tiết", value="\n".join([f"- {r}" for r in reason]), inline=False)
        embed.add_field(name="KHUYẾN NGHỊ TỰ ĐỘNG", value=f"🔥 **{action}**", inline=False)
        
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Có lỗi xảy ra: {e}")

# Lệnh Trading Sage (AI Phân tích)
@bot.tree.command(name="sage_analyze", description="[AI] Trading Sage phân tích toàn diện TA, FA và đưa ra Kịch bản giao dịch (Trade Setup)")
@app_commands.describe(ticker="Mã cổ phiếu (VD: FPT, SSI, HPG)")
async def sage_analyze(interaction: discord.Interaction, ticker: str):
    await interaction.response.defer(thinking=True)
    try:
        # Chạy hàm phân tích trên một thread khác để không block Discord event loop
        analysis_text, price = await asyncio.to_thread(trading_sage.analyze_stock_with_sage, ticker)
        
        # Vì Discord giới hạn 4096 ký tự cho embed description
        if len(analysis_text) > 4000:
            analysis_text = analysis_text[:4000] + "...\n(Đã cắt bớt do quá dài)"
            
        embed = discord.Embed(
            title=f"🧙‍♂️ TRADING SAGE: PHÂN TÍCH TOÀN DIỆN MÃ {ticker.upper()}", 
            description=analysis_text,
            color=0xFFD700  # Màu vàng Gold thể hiện Sage/Premium
        )
        embed.set_footer(text="Phân tích được tạo tự động bởi AI (Gemini) kết hợp số liệu TA & FA thực tế. Khuyến nghị chỉ mang tính tham khảo.")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Trading Sage gặp sự cố: {e}", ephemeral=True)

# Lệnh Thống kê Lịch sử Khuyến nghị
@bot.tree.command(name="sage_stats", description="📊 Xem Thống kê Lịch sử Khuyến nghị tự động (Win-rate, Các lệnh đang mở)")
async def sage_stats(interaction: discord.Interaction):
    await interaction.response.defer()
    try:
        stats = database.get_trade_statistics()
        open_trades = database.get_open_trades()
        
        embed = discord.Embed(
            title="📊 BÁO CÁO HIỆU QUẢ GIAO DỊCH (TRADE STATISTICS)", 
            color=0x00FF00 if stats["win_rate"] >= 50 else 0xFF0000
        )
        embed.add_field(name="Tổng số lệnh phím", value=f"**{stats['total']}**", inline=True)
        embed.add_field(name="Lệnh Đang Mở (OPEN)", value=f"**{stats['open']}**", inline=True)
        embed.add_field(name="Tỷ lệ Thắng (Win-rate)", value=f"**{stats['win_rate']}%**", inline=True)
        embed.add_field(name="Chốt lời thành công", value=f"🟢 {stats['win']}", inline=True)
        embed.add_field(name="Cắt lỗ", value=f"🔴 {stats['loss']}", inline=True)
        
        # Hiển thị tối đa 5 lệnh đang mở mới nhất
        if open_trades:
            open_txt = ""
            for t in open_trades[:5]:
                open_txt += f"• **{t['ticker']}** (Mua: {t['price']:,.0f}) 🎯 Target: {t['target']:,.0f} | 🛡️ Cutloss: {t['cutloss']:,.0f}\n"
            embed.add_field(name="📋 Top 5 lệnh Đang mở (OPEN) mới nhất", value=open_txt, inline=False)
        else:
            embed.add_field(name="📋 Lệnh Đang mở (OPEN)", value="Hiện tại không có lệnh Mua nào đang mở.", inline=False)
            
        embed.set_footer(text="Hệ thống tự động ghi nhận khi Technical Engine báo 'MUA MỚI'")
        await interaction.followup.send(embed=embed)
    except Exception as e:
        await interaction.followup.send(f"❌ Có lỗi xảy ra: {e}")

# Task chạy tự động (VD: cứ mỗi 30 phút check 1 lần để scan PnL và News, demo để 5 phút)
@tasks.loop(minutes=30)
async def daily_report_task():
    print("[Task] Bắt đầu quét PnL danh mục để gửi Alert...")
    all_portfolios = database.get_all_portfolios()
    
    # Gộp theo User
    users_data = {}
    for row in all_portfolios:
        uid, ticker, bprice, vol = row
        if uid not in users_data:
            users_data[uid] = []
        users_data[uid].append({"ticker": ticker, "buy_price": bprice, "volume": vol})
        
    # Check trigger Lãi >10% hoặc Lỗ >5%
    for uid, items in users_data.items():
        user = await bot.fetch_user(int(uid))
        if not user: continue
        
        alerts = []
        for item in items:
            ticker = item['ticker']
            bprice = item['buy_price']
            try:
                stock = yf.Ticker(f"{ticker}.VN")
                df = stock.history(period="1d")
                if not df.empty:
                    cprice = df['Close'].iloc[-1]
                    pnl_pct = (cprice - bprice) / bprice * 100
                    
                    if pnl_pct >= 10:
                        alerts.append(f"🟢 **{ticker}** chạm mức Lãi **+{pnl_pct:.1f}%**. Xem xét chốt lời!")
                    elif pnl_pct <= -5:
                        alerts.append(f"🔴 **{ticker}** chạm mức Lỗ **{pnl_pct:.1f}%**. Khuyến nghị tuân thủ Cutloss!")
            except:
                continue
                
        if alerts:
            msg = f"⚠️ **CẢNH BÁO DANH MỤC**\n" + "\n".join(alerts)
            
            # Gửi DM
            try:
                await user.send(msg)
            except:
                pass
                
            # Gửi lên Group
            channels = database.get_all_alert_channels()
            for ch_id in channels:
                channel = bot.get_channel(int(ch_id))
                if channel:
                    await channel.send(f"<@{uid}>\n{msg}")
                    
        # TÍNH NĂNG: Báo cáo Tin tức Daily cho các mã trong danh mục
        if len(items) > 0:
            news_msg = "📰 **TIN TỨC DAILY CHO DANH MỤC CỦA BẠN**\n"
            for item in items:
                ticker = item['ticker']
                try:
                    from vnstock import company_news
                    news_df = company_news(ticker)
                    if not news_df.empty:
                        # Lấy 1 tin mới nhất
                        row = news_df.iloc[0]
                        news_msg += f"🔹 **{ticker}**: [{row['title']}]({row['url']})\n"
                    else:
                        news_msg += f"🔹 **{ticker}**: [Đọc tin mới nhất trên CafeF](https://s.cafef.vn/tin-tuc/{ticker}.chn)\n"
                except:
                    # Fallback nếu lỗi vnstock
                    news_msg += f"🔹 **{ticker}**: [Đọc tin mới nhất trên CafeF](https://s.cafef.vn/tin-tuc/{ticker}.chn)\n"
            
            # Gửi tin tức vào DM hoặc Group (Ở đây gửi vào Group)
            channels = database.get_all_alert_channels()
            for ch_id in channels:
                channel = bot.get_channel(int(ch_id))
                if channel:
                    await channel.send(f"<@{uid}>\n{news_msg}")

class DummyHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
        self.wfile.write(b"Discord Bot is alive!")

def run_dummy_server():
    port = int(os.environ.get("PORT", 8080))
    server = HTTPServer(('0.0.0.0', port), DummyHandler)
    server.serve_forever()

def keep_alive():
    t = threading.Thread(target=run_dummy_server)
    t.daemon = True
    t.start()

if __name__ == "__main__":
    if TOKEN:
        print("[*] Đang khởi động Bot...")
        keep_alive()  # Khởi chạy server ảo để vượt qua bài kiểm tra Port của Render
        bot.run(TOKEN)
    else:
        print("[!] Không tìm thấy DISCORD_BOT_TOKEN trong file .env")

