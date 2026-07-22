# settings.py
import os

# 從 GitHub Secrets 或伺服器環境變數中讀取 Token 與 Chat ID
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID")

# 回測設定 (20 個交易日約等於 1 個月)
HOLDING_TRADING_DAYS = 20
