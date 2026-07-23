if __name__ == "__main__":
    recommendations = load_recommendations()
    details_df = evaluate_analyst_performance(recommendations)

    if not details_df.empty:
        # 勝率統計
        summary = details_df.groupby("analyst").agg(
            total_recs=("is_win", "count"),
            winning_recs=("is_win", "sum"),
            win_rate_pct=("is_win", lambda x: round(x.mean() * 100, 2)),
            avg_1m_return_pct=("return_1m_pct", "mean"),
            avg_max_return_pct=("max_return_pct", "mean")
        ).reset_index().sort_values(by="win_rate_pct", ascending=False)

        # 1. 發送/預覽完整報告
        report_text = format_report_message(summary, details_df)
        print("\n正在處理勝率報告...")
        send_telegram_message(report_text)

        # 2. 獨立印出最近 3 天推薦清單（控制台快速檢視）
        max_date = pd.to_datetime(details_df['rec_date']).max()
        three_days_ago = max_date - datetime.timedelta(days=3)
        recent_3days = details_df[pd.to_datetime(details_df['rec_date']) >= three_days_ago]
        
        print("\n📌 【控制台速查】最近 3 天推薦標的清單：")
        if not recent_3days.empty:
            print(recent_3days[['rec_date', 'analyst', 'ticker', 'stock_name', 'entry_price']].to_string(index=False))
        else:
            print("近 3 天無新增推薦。")

    else:
        print("沒有足夠的歷史資料可進行計算。")
