# fetch_recommendations.py
import json
import re
import os
import datetime

# 1. 模擬/抓取分析師最新訊息 (可替換為 Telegram Client 或 Web 爬蟲)
def fetch_raw_messages():
    # 範例：從爬蟲或 API 取得的原始訊息文字
    return [
        {"analyst": "老王 (王倚聖)", "text": "今日推薦 2330 台積電，目標價 1200", "date": "2026-07-28"},
        {"analyst": "萬寶 - 莊正賢", "text": "看好 2454 聯發科 潛力強勁", "date": "2026-07-28"},
        {"analyst": "陳威良", "text": "留意 3661 世芯-KY 佈局時機", "date": "2026-07-28"}
    ]

# 2. 正則表達式抓取 4 位數股票代碼
def parse_stock_code(text):
    match = re.search(r'\b\d{4}\b', text)
    return match.group(0) if match else None

# 3. 自動更新 recommendations.json
def update_json():
    json_path = "recommendations.json"
    
    # 讀取既有資料
    existing_data = []
    if os.path.exists(json_path):
        with open(json_path, "r", encoding="utf-8") as f:
            try:
                existing_data = json.load(f)
            except:
                existing_data = []

    raw_msgs = fetch_raw_messages()
    new_records = []

    for item in raw_msgs:
        ticker = parse_stock_code(item["text"])
        if ticker:
            record = {
                "analyst": item["analyst"],
                "ticker": ticker,
                "rec_date": item["date"],
                "target_price": None
            }
            # 檢查是否重複 (相同分析師 + 相同股票 + 相同日期)
            is_duplicate = any(
                e["analyst"] == record["analyst"] and 
                e["ticker"] == record["ticker"] and 
                e["rec_date"] == record["rec_date"] 
                for e in existing_data
            )
            if not is_duplicate:
                new_records.append(record)

    if new_records:
        existing_data.extend(new_records)
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(existing_data, f, ensure_ascii=False, indent=2)
        print(f"✅ 成功新增 {len(new_records)} 筆推薦資料至 recommendations.json")
    else:
        print("ℹ️ 無新推薦資料需更新。")

if __name__ == "__main__":
    update_json()
