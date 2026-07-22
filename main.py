# main.py
import urllib.request
import json
import pandas as pd
import numpy as np
import datetime

from settings import HOLDING_TRADING_DAYS
from telegram_bot import send_telegram_message, format_report_message

# 1. 分析師推薦紀錄
sample_recommendations = [
    {"analyst": "凱基 - 張家銘", "ticker": "2330", "rec_date": "2026-05-04", "target_price": 1050},
    {"analyst": "凱基 - 張家銘", "ticker": "2382", "rec_date": "2026-05-11", "target_price": 320},
    {"analyst": "凱基 - 張家銘", "ticker": "2454", "rec_date": "2026-05-18", "target_price": 1300},
    {"analyst": "富邦 - 陳偉倫", "ticker": "2317", "rec_date": "2026-05-04", "target_price": 220},
    {"analyst": "富邦 - 陳偉倫", "ticker": "3231", "rec_date": "2026-05-12", "target_price": 110},
    {"analyst": "富邦 - 陳偉倫", "ticker": "2308", "rec_date": "2026-05-20", "target_price": 380},
    {"analyst": "元大 - 林志豪", "ticker": "2330", "rec_date": "2026-05-05", "target_price": 1000},
    {"analyst": "元大 - 林志豪", "ticker": "2303", "rec_date": "2026-05-15", "target_price": 60},
]

# 2. 自動抓取台股全清單對照表 (取得股票中文名稱)
def fetch_stock_name_map():
    url = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo"
    name_map = {}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('msg') == 'success':
                for item in data.get('data', []):
                    # 建立 dict 映射: {"2330": "台積電", "2382": "廣達"}
                    name_map[item.get('stock_id')] = item.get('stock_name', '')
    except Exception as e:
        print(f"⚠️ 抓取股票名稱清單失敗: {e}")
    return name_map

# 3. 自動抓取歷史價格 API
def fetch_stock_price_finmind(ticker, start_date):
    url = f"https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockPrice&data_id={ticker}&start_date={start_date}"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('msg') == 'success' and len(data.get('data', [])) > 0:
                df = pd.DataFrame(data['data'])
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date').sort_index()
                return df['close']
    except Exception as e:
        print(f"抓取 {ticker} 股價失敗: {e}")
    return pd.Series(dtype=float)

# 4. 評估分析師勝率
def evaluate_analyst_performance(recs_list, holding_days=HOLDING_TRADING_DAYS):
    recs_df = pd.DataFrame(recs_list)
    recs_df['rec_date'] = pd.to_datetime(recs_df['rec_date'])
    
    # 一次性載入股票名稱字典
    stock_name_map = fetch_stock_name_map()
    
    min_date = (recs_df['rec_date'].min() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    
    stock_prices = {}
    tickers = recs_df['ticker'].unique()
    for t in tickers:
        stock_name = stock_name_map.get(str(t), "")
        display_name = f"{t} {stock_name}".strip()
        print(f"正在抓取股票 {display_name} 歷史價格...")
        stock_prices[t] = fetch_stock_price_finmind(t, min_date)
        
    results = []
    
    for idx, row in recs_df.iterrows():
        ticker = str(row['ticker'])
        analyst = row['analyst']
        rec_date = row['rec_date']
        target_price = row.get('target_price', None)
        
        # 自動取得中文名稱
        stock_name = stock_name_map.get(ticker, "")
        
        prices = stock_prices.get(ticker)
        if prices is None or prices.empty:
            continue
            
        available_dates = prices.index[prices.index >= rec_date]
        if len(available_dates) == 0:
            continue
            
        p0_date = available_dates[0]
        p0_idx = prices.index.get_loc(p0_date)
        
        future_prices = prices.iloc[p0_idx : p0_idx + holding_days + 1]
        if len(future_prices) <= 1:
            continue
            
        p0 = future_prices.iloc[0]
        p_end = future_prices.iloc[-1]
        p_max = future_prices.max()
        
        return_1m = (p_end - p0) / p0
        max_return_1m = (p_max - p0) / p0
        is_win = 1 if return_1m > 0 else 0
        reach_target = 1 if (target_price and p_max >= target_price) else 0
        
        results.append({
            "analyst": analyst,
            "ticker": ticker,
            "stock_name": stock_name,
            "rec_date": rec_date.strftime("%Y-%m-%d"),
            "entry_price": round(p0, 2),
            "price_1m_after": round(p_end, 2),
            "max_price_1m": round(p_max, 2),
            "return_1m_pct": round(return_1m * 100, 2),
            "max_return_pct": round(max_return_1m * 100, 2),
            "is_win": is_win,
            "reach_target": reach_target
        })
        
    return pd.DataFrame(results)

if __name__ == "__main__":
    details_df = evaluate_analyst_performance(sample_recommendations)

    if not details_df.empty:
        summary = details_df.groupby("analyst").agg(
            total_recs=("is_win", "count"),
            winning_recs=("is_win", "sum"),
            win_rate_pct=("is_win", lambda x: round(x.mean() * 100, 2)),
            avg_1m_return_pct=("return_1m_pct", "mean"),
            avg_max_return_pct=("max_return_pct", "mean")
        ).reset_index().sort_values(by="win_rate_pct", ascending=False)

        report_text = format_report_message(summary, details_df)
        print("\n正在處理勝率報告...")
        
        if send_telegram_message(report_text):
            print("✅ 報表處理/發送成功！")
        else:
            print("❌ 處理失敗，請檢查設定。")
    else:
        print("沒有足夠的歷史資料可進行計算。")
