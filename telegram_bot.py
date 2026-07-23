# telegram_bot.py
import urllib.request
import json
from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(message_text):
    """發送訊息至 Telegram Bot；若未設定金鑰則轉為預覽模式印出"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n================== ⚠️ 測試模式：未設定 Telegram 金鑰 ==================")
        print("【預覽即將發送至 Telegram 的報告內容】：\n")
        print(message_text)
        print("======================================================================\n")
        return True  # 回傳 True 讓主程式知道「測試預覽完成」
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message_text,
        "parse_mode": "Markdown"
    }
    
    try:
        data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except Exception as e:
        print(f"❌ Telegram 發送失敗: {e}")
        return False

def format_report_message(summary_df, details_df):
    """格式化勝率統計與明細報表（包含推薦日期）"""
    msg = "📊 *【台股投顧/分析師勝率追蹤週報】*\n"
    msg += "-----------------------------------\n\n"
    
    msg += "🏆 *分析師勝率排行榜*\n"
    for idx, row in summary_df.reset_index(drop=True).iterrows():
        rank = idx + 1
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
        msg += f"{medal} *{row['analyst']}*\n"
        msg += f"  • 推薦次數: {row['total_recs']} 次\n"
        msg += f"  • 1個月勝率: `{row['win_rate_pct']}%`\n"
        msg += f"  • 平均1個月報酬: `{row['avg_1m_return_pct']:+.2f}%`\n"
        msg += f"  • 30天內最高衝高: `{row['avg_max_return_pct']:+.2f}%`\n\n"
        
    msg += "-----------------------------------\n"
    msg += "🔍 *最新推薦績效明細*\n"
    recent_details = details_df.head(15)  # 展示前 15 筆明細
    for idx, row in recent_details.iterrows():
        status = "✅ 勝" if row['is_win'] == 1 else "❌ 敗"
        stock_disp = f"{row['ticker']} {row['stock_name']}".strip() if row.get('stock_name') else row['ticker']
        rec_date = row.get('rec_date', '未知日期')
        
        # 顯示格式：代碼 名稱 (分析師)
        #           📅 推薦日: 2026-05-04
        #           💰 買入價 ➔ 1月後價格 (報酬率 狀態)
        msg += f"• *{stock_disp}* ({row['analyst']})\n"
        msg += f"  📅 推薦日期: `{rec_date}`\n"
        msg += f"  💰 買入價: `{row['entry_price']}` ➔ 1月後: `{row['price_1m_after']}` ({row['return_1m_pct']:+.2f}% {status})\n\n"
        
    return msg
