# main.py
import urllib.request
import json
import os
import pandas as pd
import numpy as np
import datetime

from settings import HOLDING_TRADING_DAYS
from telegram_bot import send_telegram_message, format_report_message

# 1. 讀取推薦資料 (優先讀取 recommendations.json)
def load_recommendations():
    json_path = "recommendations.json"
    if os.path.exists(json_path):
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                print(f"📂 成功載入 {json_path}，共 {len(data)} 筆推薦紀錄。")
                return data
        except Exception as e:
            print(f"⚠️ 讀取 {json_path} 失敗: {e}")
    else:
        print(f"⚠️ 找不到 {json_path}，請確認檔案是否存在。")
    return []

# 2. 自動抓取台股全清單對照表 (FinMind 全台股上市上櫃名稱)
def fetch_stock_name_map():
    url = "https://api.finmindtrade.com/api/v4/data?dataset=TaiwanStockInfo"
    name_map = {}
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            if data.get('msg') == 'success':
                for item in data.get('data', []):
                    name_map[str(item.get('stock_id'))] = str(item.get('stock_name', ''))
    except Exception as e:
        print(f"⚠️ 抓取股票名稱清單失敗: {e}")
    return name_map

# 3. 自動抓取歷史價格 API (通用全台股)
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
        print(f"❌ 抓取 {ticker} 股價失敗: {e}")
    return pd.Series(dtype=float)

# 4. 評估分析師勝率與績效
def evaluate_analyst_performance(recs_list, holding_days=HOLDING_TRADING_DAYS):
    if not recs_list:
        return pd.DataFrame()

    recs_df = pd.DataFrame(recs_list)
    recs_df['rec_date'] = pd.to_datetime(recs_df['rec_date'])
    
    print("正在取得台股全清單股票名稱對照表...")
    stock_name_map = fetch_stock_name_map()
    
    min_date = (recs_df['rec_date'].min() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    
    stock_prices = {}
    tickers = recs_df['ticker'].astype(str).unique()
    for t in tickers:
        stock_name = stock_name_map.get(t, "")
        display_name = f"{t} {stock_name}".strip()
        print(f"正在抓取股票 {display_name} 歷史價格...")
        stock_prices[t] = fetch_stock_price_finmind(t, min_date)
        
    results = []
    for idx, row in recs_df.iterrows():
        ticker = str(row['ticker'])
        analyst = row['analyst']
        rec_date = row['rec_date']
        target_price = row.get('target_price', None)
        
        stock_name = stock_name_map.get(ticker, "")
        prices = stock_prices.get(ticker)
        
        if prices is None or prices.empty:
            continue
            
        available_dates = prices.index[prices.index >= rec_date]
        if len(available_dates) == 0:
            continue
            
        p0_date = available_dates[0]
        p0_idx = prices.index.get_loc(p0_date)
        
        # 取得從推薦日開始的所有價格
        future_prices = prices.iloc[p0_idx:]
        if len(future_prices) == 0:
            continue

        p0 = future_prices.iloc[0]
        latest_price = future_prices.iloc[-1]  # 💡 保存最新的實體股價數字
        
        # 💡 檢查交易日天數是否滿 1 個月 (holding_days)
        if len(future_prices) >= holding_days + 1:
            p_end = future_prices.iloc[holding_days]
            is_completed = True
        else:
            p_end = latest_price
            is_completed = False
            
        p_max = future_prices.max()
        
        return_1m = (p_end - p0) / p0
        max_return_1m = (p_max - p0) / p0
        
        # 勝負判定：僅計算已結算單
        is_win = 1 if (return_1m > 0 and is_completed) else 0
        reach_target = 1 if (target_price and p_max >= target_price) else 0
        
        results.append({
            "analyst": analyst,
            "ticker": ticker,
            "stock_name": stock_name,
            "rec_date": rec_date.strftime("%Y-%m-%d"),
            "entry_price": round(p0, 2),
            "latest_price": round(latest_price, 2),  # 💡 實體最新價格欄位
            "price_1m_after": round(p_end, 2) if is_completed else None,
            "max_price_1m": round(p_max, 2),
            "return_1m_pct": round(return_1m * 100, 2),
            "max_return_pct": round(max_return_1m * 100, 2),
            "is_win": is_win,
            "is_completed": is_completed,            # 是否滿 20 個交易日
            "reach_target": reach_target
        })
        
    return pd.DataFrame(results)

if __name__ == "__main__":
    recommendations = load_recommendations()
    details_df = evaluate_analyst_performance(recommendations)

    if not details_df.empty:
        # 只針對「已滿 20 個交易日結算」的單計算勝率
        completed_df = details_df[details_df['is_completed'] == True]
        
        if not completed_df.empty:
            summary = completed_df.groupby("analyst").agg(
                total_recs=("is_win", "count"),
                winning_recs=("is_win", "sum"),
                win_rate_pct=("is_win", lambda x: round(x.mean() * 100, 2)),
                avg_1m_return_pct=("return_1m_pct", "mean"),
                avg_max_return_pct=("max_return_pct", "mean")
            ).reset_index().sort_values(by="win_rate_pct", ascending=False)
        else:
            # 若無已結算單，建立空的排行榜以供 Telegram Bot 防錯呈現
            summary = pd.DataFrame(columns=["analyst", "total_recs", "winning_recs", "win_rate_pct", "avg_1m_return_pct", "avg_max_return_pct"])

        report_text = format_report_message(summary, details_df)
        print("\n正在處理勝率報告...")
        
        if send_telegram_message(report_text):
            print("✅ 報表處理/測試預覽成功！")
        else:
            print("❌ 處理失敗，請檢查設定。")
    else:
        print("⚠️ 沒有足夠的歷史資料可進行計算。")
