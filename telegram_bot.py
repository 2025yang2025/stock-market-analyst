# telegram_bot.py
import urllib.request
import json
from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(message_text):
    """發送訊息至 Telegram Bot"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("⚠️ 未設定 Telegram Token 或 Chat ID，跳過發送。")
        return False
        
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
    """格式化勝率統計與明細報表"""
    msg = "📊 **台股投顧/分析師勝率追蹤週報**\n"
    msg += "-----------------------------------\n\n"
    
    msg += "🏆 **分析師勝率排行榜**\n"
    for idx, row in summary_df.iterrows():
        msg += f"👤 *{row['analyst']}*\n"
        msg += f"  • 推薦次數: {row['total_recs']} 次\n"
        msg += f"  • 1個月勝率: `{row['win_rate_pct']}%`\n"
        msg += f"  • 平均1個月報酬: `{row['avg_1m_return_pct']}%`\n"
        msg += f"  • 30天內最高衝高: `{row['avg_max_return_pct']}%`\n\n"
        
    msg += "-----------------------------------\n"
    msg += "📌 *詳細推薦績效*\n"
    for idx, row in details_df.iterrows():
        status = "✅ 勝" if row['is_win'] == 1 else "❌ 敗"
        msg += f"• {row['analyst']} | {row['ticker']} {row['stock_name']}\n"
        msg += f"  買入價: {row['entry_price']} ➔ 1月後: {row['price_1m_after']} ({row['return_1m_pct']}% {status})\n"
        
    return msg
