# data_fetcher.py
import pandas as pd
import datetime
import yfinance as yf

# 內建常見台股名稱對照表（避免 API 失敗）
LOCAL_STOCK_NAMES = {
    "2330": "台積電",
    "2454": "聯發科",
    "2382": "廣達",
    "3231": "緯創",
    "2317": "鴻海",
    "2308": "台達電",
    "2303": "聯電",
    "3661": "世芯-KY",
    "2379": "瑞昱",
    "3034": "聯詠",
    "2357": "華碩",
    "2301": "光寶科",
    "6669": "緯穎"
}

def get_stock_name_map():
    """取得台股對照表 (優先回傳本機字典)"""
    return LOCAL_STOCK_NAMES

def get_stock_price_history(ticker, start_date=None, end_date=None):
    """使用 yfinance 免費抓取台股歷史價格"""
    try:
        # 台股上市股票在 yfinance 需加上 .TW (若為上櫃則加 .TWO)
        symbol = f"{str(ticker).strip()}.TW"
        
        # 設定預設抓取時間區間
        if not start_date:
            start_date = (datetime.datetime.now() - datetime.timedelta(days=120)).strftime("%Y-%m-%d")
        if not end_date:
            end_date = datetime.datetime.now().strftime("%Y-%m-%d")
            
        print(f"正在抓取股票 {ticker} ({LOCAL_STOCK_NAMES.get(str(ticker), '')}) 歷史價格...")
        
        # 下載歷史資料
        df = yf.download(symbol, start=start_date, end=end_date, progress=False)
        
        if df.empty:
            # 嘗試上櫃代碼 .TWO
            symbol_two = f"{str(ticker).strip()}.TWO"
            df = yf.download(symbol_two, start=start_date, end=end_date, progress=False)
            
        if df.empty:
            print(f"❌ 抓取 {ticker} 股價失敗: 查無資料")
            return None

        # 整理 yfinance 欄位結構
        df = df.reset_index()
        # 處理 MultiIndex 欄位名 (yfinance 近期版本特性)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = [col[0] for col in df.columns]

        df = df[['Date', 'Close', 'Open', 'High', 'Low']].copy()
        df.columns = ['date', 'close', 'open', 'high', 'low']
        df['date'] = df['date'].dt.strftime('%Y-%m-%d')
        df['ticker'] = str(ticker)
        
        return df

    except Exception as e:
        print(f"❌ 抓取 {ticker} 股價失敗: {e}")
        return None
