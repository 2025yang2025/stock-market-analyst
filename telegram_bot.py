# telegram_bot.py
import urllib.request
import json
import pandas as pd
import datetime
import html
from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(message_text):
    """發送訊息至 Telegram Bot (改用穩定且不易壞掉的 HTML 格式)"""
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
        "parse_mode": "HTML"  # 💡 使用 HTML 模式，完全防範 400 Bad Request
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
    """格式化勝率統計與明細報表 (HTML 穩定排版版)"""
    msg = "📊 <b>【台股投顧/分析師勝率追蹤週報】</b>\n"
    msg += "-----------------------------------\n\n"
    
    # 1. 分析師勝率排行榜
    msg += "🏆 <b>分析師勝率排行榜 (已結算單)</b>\n"
    if not summary_df.empty:
        for idx, row in summary_df.reset_index(drop=True).iterrows():
            rank = idx + 1
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
            analyst_name = html.escape(str(row['analyst']))
            
            msg += f"{medal} <b>{analyst_name}</b>\n"
            msg += f"  • 結算推薦數: {row['total_recs']} 次\n"
            msg += f"  • 1個月勝率: <code>{row['win_rate_pct']}%</code>\n"
            msg += f"  • 平均1個月報酬: <code>{row['avg_1m_return_pct']:+.2f}%</code>\n"
            msg += f"  • 30天內最高衝高: <code>{row['avg_max_return_pct']:+.2f}%</code>\n\n"
    else:
        msg += "  目前尚無已滿持股天數結算之勝率統計。\n\n"
        
    msg += "-----------------------------------\n"
    
    # 2. 最近 3 天最新推薦標的專區
    msg += "🔥 <b>【最近 3 天最新推薦標的】</b>\n"
    if not details_df.empty:
        max_date = pd.to_datetime(details_df['rec_date']).max()
        three_days_ago = max_date - datetime.timedelta(days=3)
        
        recent_3days_df = details_df[pd.to_datetime(details_df['rec_date']) >= three_days_ago].sort_values(by="rec_date", ascending=False)
        
        if not recent_3days_df.empty:
            for idx, row in recent_3days_df.iterrows():
                stock_raw = f"{row['ticker']} {row['stock_name']}".strip() if row.get('stock_name') else str(row['ticker'])
                stock_disp = html.escape(stock_raw)
                analyst_name = html.escape(str(row['analyst']))
                rec_date = html.escape(str(row['rec_date']))
                entry_p = html.escape(str(row['entry_price']))
                
                msg += f"• <b>{stock_disp}</b>｜{analyst_name}\n"
                msg += f"  📅 日期: <code>{rec_date}</code>｜💰 推薦價: <code>{entry_p}</code>\n"
        else:
            msg += "  目前無最近 3 天內的最新推薦標的。\n"
    else:
        msg += "  尚無資料。\n"
        
    msg += "\n-----------------------------------\n"
    
    # 3. 歷史推薦績效明細（完整輸出，顯示最新價）
    msg += "🔍 <b>推薦績效明細</b>\n"
    if not details_df.empty:
        sorted_details = details_df.sort_values(by="rec_date", ascending=False).head(30)
        
        for idx, row in sorted_details.iterrows():
            rec_date = html.escape(str(row.get('rec_date', '未知日期')))
            analyst_name = html.escape(str(row['analyst']))
            stock_raw = f"{row['ticker']} {row['stock_name']}".strip() if row.get('stock_name') else str(row['ticker'])
            stock_disp = html.escape(stock_raw)
            entry_p = html.escape(str(row['entry_price']))
            
            if row.get('is_completed', False):
                status = "✅ 勝" if row['is_win'] == 1 else "❌ 敗"
                p_1m = html.escape(str(row['price_1m_after']))
                ret_1m = html.escape(f"{row['return_1m_pct']:+.2f}%")
                price_str = f"1月後: <code>{p_1m}</code> ({ret_1m} {status})"
            else:
                latest_p = html.escape(str(row.get('latest_price', row['entry_price'])))
                ret_curr = html.escape(f"{row['return_1m_pct']:+.2f}%")
                price_str = f"最新價: <code>{latest_p}</code> (目前 {ret_curr} ⏳ 追蹤中)"
                
            msg += f"• <b>{stock_disp}</b> ({analyst_name})\n"
            msg += f"  📅 推薦日期: <code>{rec_date}</code>\n"
            msg += f"  💰 買入價: <code>{entry_p}</code> ➔ {price_str}\n\n"
    else:
        msg += "  尚無明細資料。\n"
        
    return msg
