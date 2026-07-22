import urllib.request
import json
import pandas as pd
import numpy as np
import datetime

# ---------------------------------------------------------
# 1. 輸入測試用「分析師推薦紀錄」
# ---------------------------------------------------------
sample_recommendations = [
    {"analyst": "張分析師 (A券商)", "ticker": "2330", "rec_date": "2026-05-04", "target_price": 1050},
    {"analyst": "張分析師 (A券商)", "ticker": "2382", "rec_date": "2026-05-11", "target_price": 320},
    {"analyst": "張分析師 (A券商)", "ticker": "2454", "rec_date": "2026-05-18", "target_price": 1300},
    {"analyst": "李分析師 (B券商)", "ticker": "2317", "rec_date": "2026-05-04", "target_price": 220},
    {"analyst": "李分析師 (B券商)", "ticker": "3231", "rec_date": "2026-05-12", "target_price": 110},
    {"analyst": "李分析師 (B券商)", "ticker": "2308", "rec_date": "2026-05-20", "target_price": 380},
    {"analyst": "王分析師 (C券商)", "ticker": "2330", "rec_date": "2026-05-05", "target_price": 1000},
    {"analyst": "王分析師 (C券商)", "ticker": "2303", "rec_date": "2026-05-15", "target_price": 60},
]

# ---------------------------------------------------------
# 2. 自動抓取台股日 K 線收盤價 (以 FinMind 免費 API 為例)
# ---------------------------------------------------------
def fetch_stock_price_finmind(ticker, start_date):
    """
    從 FinMind 抓取台股每日收盤價
    """
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

# ---------------------------------------------------------
# 3. 核心比對與勝率計算邏輯
# ---------------------------------------------------------
def evaluate_analyst_performance(recs_list, holding_days=20):
    """
    比對分析師推薦日與 1 個月後 (預設 20 個交易日) 的價格，計算漲跌幅與勝率
    """
    recs_df = pd.DataFrame(recs_list)
    recs_df['rec_date'] = pd.to_datetime(recs_df['rec_date'])
    
    # 計算最早需要抓取股價的日期
    min_date = (recs_df['rec_date'].min() - datetime.timedelta(days=5)).strftime("%Y-%m-%d")
    
    # 抓取每檔股票價格
    stock_prices = {}
    tickers = recs_df['ticker'].unique()
    for t in tickers:
        print(f"正在抓取股票 {t} 歷史價格...")
        stock_prices[t] = fetch_stock_price_finmind(t, min_date)
        
    results = []
    
    for idx, row in recs_df.iterrows():
        ticker = row['ticker']
        analyst = row['analyst']
        rec_date = row['rec_date']
        target_price = row.get('target_price', None)
        
        prices = stock_prices.get(ticker)
        if prices is None or prices.empty:
            continue
            
        # 取得推薦當天或推薦日後的第一個交易日
        available_dates = prices.index[prices.index >= rec_date]
        if len(available_dates) == 0:
            continue
            
        p0_date = available_dates[0]
        p0_idx = prices.index.get_loc(p0_date)
        
        # 取出未來 20 個交易日 (約 1 個月) 的價格區間
        future_prices = prices.iloc[p0_idx : p0_idx + holding_days + 1]
        if len(future_prices) <= 1:
            # 推薦時間太近，還滿不到 1 個月交易日
            continue
            
        p0 = future_prices.iloc[0]       # 推薦當日/次日收盤價
        p_end = future_prices.iloc[-1]   # 1 個月後收盤價
        p_max = future_prices.max()       # 1 個月內最高價
        
        return_1m = (p_end - p0) / p0
        max_return_1m = (p_max - p0) / p0
        is_win = 1 if return_1m > 0 else 0
        reach_target = 1 if (target_price and p_max >= target_price) else 0
        
        results.append({
            "analyst": analyst,
            "ticker": ticker,
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

# ---------------------------------------------------------
# 4. 執行計算與輸出統計排行榜
# ---------------------------------------------------------
if __name__ == "__main__":
    # 執行評估
    details_df = evaluate_analyst_performance(sample_recommendations)

    if not details_df.empty:
        # 彙整分析師 1 個月勝率與績效
        summary = details_df.groupby("analyst").agg(
            total_recs=("is_win", "count"),
            winning_recs=("is_win", "sum"),
            win_rate_pct=("is_win", lambda x: round(x.mean() * 100, 2)),
            avg_1m_return_pct=("return_1m_pct", "mean"),
            avg_max_return_pct=("max_return_pct", "mean")
        ).reset_index()

        summary = summary.sort_values(by="win_rate_pct", ascending=False)

        print("\n================== 1. 個別推薦回測明細 ==================")
        print(details_df[['analyst', 'ticker', 'rec_date', 'entry_price', 'price_1m_after', 'return_1m_pct', 'is_win']].to_string(index=False))

        print("\n================== 2. 分析師 1 個月勝率排行榜 ==================")
        print(summary.to_string(index=False))
    else:
        print("沒有足夠的歷史資料可供比對。")
