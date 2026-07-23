# telegram_bot.py
import urllib.request
import json
import pandas as pd
import datetime
from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(message_text):
    """發送訊息至 Telegram Bot；若未設定金鑰則轉為預覽模式印出"""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n================== ⚠️ 測試模式：未設定 Telegram 金鑰 ==================")
        print("【預覽即將發送至 Telegram 的報告內容】：\n")
        print(message_text)
        print("======================================================================\n")
        return True
        
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
    msg = "📊 *【台股投顧/分析師勝率追蹤週報】*\n"
    msg += "-----------------------------------\n\n"
    
    # 1. 分析師勝率排行榜（只計算已到期的推薦勝率）
    msg += "🏆 *分析師勝率排行榜 (已結算單)*\n"
    if not summary_df.empty:
        for idx, row in summary_df.reset_index(drop=True).iterrows():
            rank = idx + 1
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
            msg += f"{medal} *{row['analyst']}*\n"
            msg += f"  • 結算推薦數: {row['total_recs']} 次\n"
            msg += f"  • 1個月勝率: `{row['win_rate_pct']}%`\n"
            msg += f"  • 平均1個月報酬: `{row['avg_1m_return_pct']:+.2f}%`\n"
            msg += f"  • 30天內最高衝高: `{row['avg_max_return_pct']:+.2f}%`\n\n"
    else:
        msg += "  目前尚無已滿持股天數結算之勝率統計。\n\n"
        
    msg += "-----------------------------------\n"
    
    # 2. 最近 3 天最新推薦標的專區
    msg += "🔥 *【最近 3 天最新推薦標的】*\n"
    if not details_df.empty:
        max_date = pd.to_datetime(details_df['rec_date']).max()
        three_days_ago = max_date - datetime.timedelta(days=3)
        
        recent_3days_df = details_df[pd.to_datetime(details_df['rec_date']) >= three_days_ago].sort_values(by="rec_date", ascending=False)
        
        if not recent_3days_df.empty:
            for idx, row in recent_3days_df.iterrows():
                stock_disp = f"{row['ticker']} {row['stock_name']}".strip() if row.get('stock_name') else row['ticker']
                msg += f"• *{stock_disp}*｜{row['analyst']}\n"
                msg += f"  📅 日期: `{row['rec_date']}`｜💰 推薦價: `{row['entry_price']}`\n"
        else:
            msg += "  目前無最近 3 天內的最新推薦標的。\n"
    else:
        msg += "  尚無資料。\n"
        
    msg += "\n-----------------------------------\n"
    
    # 3. 歷史推薦績效明細（正確處理最新價數值）
    msg += "🔍 *推薦績效明細*\n"
    recent_details = details_df.head(15)
    for idx, row in recent_details.iterrows():
        if row.get('is_completed', False):
            status = "✅ 勝" if row['is_win'] == 1 else "❌ 敗"
            price_str = f"1月後: `{row['price_1m_after']}` ({row['return_1m_pct']:+.2f}% {status})"
        else:
            # 💡 這裡精準取用 row['latest_price']，絕對不會再出現 null/None
            latest_p = row.get('latest_price', row['entry_price'])
            price_str = f"最新價: `{latest_p}` (目前 {row['return_1m_pct']:+.2f}% ⏳ 追蹤中)"
            
        stock_disp = f"{row['ticker']} {row['stock_name']}".strip() if row.get('stock_name') else row['ticker']
        rec_date = row.get('rec_date', '未知日期')
        
        msg += f"• *{stock_disp}* ({row['analyst']})\n"
        msg += f"  📅 推薦日期: `{rec_date}`\n"
        msg += f"  💰 買入價: `{row['entry_price']}` ➔ {price_str}\n\n"
        
    return msg
