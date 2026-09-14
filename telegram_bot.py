# telegram_bot.py
import urllib.request
import json
import pandas as pd
import datetime
import re
from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def escape_markdown(text):
    """轉義 MarkdownV2 中的所有特殊字符"""
    if text is None:
        return ""
    text = str(text)
    # Telegram MarkdownV2 必須轉義的字元
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def send_telegram_message(message_text):
    """發送訊息至 Telegram Bot"""
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
        "parse_mode": "MarkdownV2"  # 使用 MarkdownV2 更為穩定
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
    """格式化勝率統計與明細報表 (安全轉義版)"""
    msg = "📊 *【台股投顧/分析師勝率追蹤週報】*\n"
    msg += "-----------------------------------\n\n"
    
    # 1. 分析師勝率排行榜
    msg += "🏆 *分析師勝率排行榜 (已結算單)*\n"
    if not summary_df.empty:
        for idx, row in summary_df.reset_index(drop=True).iterrows():
            rank = idx + 1
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
            analyst_name = escape_markdown(row['analyst'])
            win_rate = escape_markdown(f"{row['win_rate_pct']}%")
            avg_1m = escape_markdown(f"{row['avg_1m_return_pct']:+.2f}%")
            avg_max = escape_markdown(f"{row['avg_max_return_pct']:+.2f}%")
            
            msg += f"{medal} *{analyst_name}*\n"
            msg += f"  • 結算推薦數: {row['total_recs']} 次\n"
            msg += f"  • 1個月勝率: `{win_rate}`\n"
            msg += f"  • 平均1個月報酬: `{avg_1m}`\n"
            msg += f"  • 30天內最高衝高: `{avg_max}`\n\n"
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
                stock_disp = escape_markdown(f"{row['ticker']} {row['stock_name']}".strip() if row.get('stock_name') else str(row['ticker']))
                analyst_name = escape_markdown(row['analyst'])
                rec_date = escape_markdown(row['rec_date'])
                entry_p = escape_markdown(str(row['entry_price']))
                
                msg += f"• *{stock_disp}*｜{analyst_name}\n"
                msg += f"  📅 日期: `{rec_date}`｜💰 推薦價: `{entry_p}`\n"
        else:
            msg += "  目前無最近 3 天內的最新推薦標的。\n"
    else:
        msg += "  尚無資料。\n"
        
    msg += "\n-----------------------------------\n"
    
    # 3. 歷史推薦績效明細（全數 28 筆依日期排列）
    msg += "🔍 *推薦績效明細*\n"
    if not details_df.empty:
        sorted_details = details_df.sort_values(by="rec_date", ascending=False).head(30)
        
        for idx, row in sorted_details.iterrows():
            rec_date = escape_markdown(row.get('rec_date', '未知日期'))
            analyst_name = escape_markdown(row['analyst'])
            stock_disp = escape_markdown(f"{row['ticker']} {row['stock_name']}".strip() if row.get('stock_name') else str(row['ticker']))
            entry_p = escape_markdown(str(row['entry_price']))
            
            if row.get('is_completed', False):
                status = "✅ 勝" if row['is_win'] == 1 else "❌ 敗"
                p_1m = escape_markdown(str(row['price_1m_after']))
                ret_1m = escape_markdown(f"{row['return_1m_pct']:+.2f}%")
                price_str = f"1月後: `{p_1m}` ({ret_1m} {status})"
            else:
                latest_p = escape_markdown(str(row.get('latest_price', row['entry_price'])))
                ret_curr = escape_markdown(f"{row['return_1m_pct']:+.2f}%")
                price_str = f"最新價: `{latest_p}` (目前 {ret_curr} ⏳ 追蹤中)"
                
            msg += f"• *{stock_disp}* ({analyst_name})\n"
            msg += f"  📅 推薦日期: `{rec_date}`\n"
            msg += f"  💰 買入價: `{entry_p}` ➔ {price_str}\n\n"
    else:
        msg += "  尚無明細資料。\n"
        
    return msg
