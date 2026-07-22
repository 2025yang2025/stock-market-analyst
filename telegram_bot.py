# telegram_bot.py
import json
import urllib.request
import urllib.parse
from settings import TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID

def send_telegram_message(text: str) -> bool:
    """
    發送訊息至 Telegram；若未設定金鑰，則轉為「測試模式」直接在 Terminal 印出
    """
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        print("\n================== ⚠️ 測試模式：未偵測到 Telegram 金鑰 ==================")
        print("【預覽即將發送至 Telegram 的報告內容】：\n")
        print(text)
        print("======================================================================")
        return True
        
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    
    headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    
    try:
        req = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode("utf-8"))
            return res.get("ok", False)
    except Exception as e:
        print(f"❌ Telegram 訊息發送失敗: {e}")
        return False

def format_report_message(summary_df, details_df) -> str:
    """
    將勝率排行榜與詳細數據排版成 Telegram Markdown 格式
    """
    msg = "📊 *【分析師 1 個月勝率與績效排行榜】*\n"
    msg += "-----------------------------------\n"
    
    for idx, row in summary_df.reset_index(drop=True).iterrows():
        rank = idx + 1
        win_rate = row['win_rate_pct']
        avg_ret = row['avg_1m_return_pct']
        
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else "🔹"
        
        msg += f"{medal} *{row['analyst']}*\n"
        msg += f"   • 總推薦數: {row['total_recs']} | 上漲數: {row['winning_recs']}\n"
        msg += f"   • *1個月勝率: {win_rate}%*\n"
        msg += f"   • 平均 1M 報酬: `{avg_ret:+.2f}%`\n\n"
        
    msg += "🔍 *【最新推薦追蹤明細】*\n"
    msg += "-----------------------------------\n"
    
    recent_details = details_df.head(10)  # 顯示前 10 筆明細
    for _, row in recent_details.iterrows():
        status = "✅ 上漲" if row['is_win'] == 1 else "🔻 下跌"
        
        # 組合「代號 + 中文名稱」
        stock_name = row.get('stock_name', '')
        if stock_name:
            stock_disp = f"{row['ticker']} {stock_name}"
        else:
            stock_disp = f"{row['ticker']}"
            
        msg += f"• *{stock_disp}* ({row['analyst']})\n"
        msg += f"  推薦日: {row['rec_date']} | 入場價: `{row['entry_price']}`\n"
        msg += f"  1M後價格: `{row['price_1m_after']}` ({row['return_1m_pct']:+.2f}%) [{status}]\n\n"
        
    return msg
