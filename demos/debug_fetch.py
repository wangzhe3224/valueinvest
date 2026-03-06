#!/usr/bin/env python3
"""Debug data fetching for 600887."""
import akshare as ak
import json

print("Fetching real-time data for 600887...")

try:
    # 尝试获取实时数据
    df = ak.stock_zh_a_spot_em()
    stock_data = df[df["代码"] == "600887"]

    if not stock_data.empty:
        print("Found stock data:")
        print(stock_data.to_string())

        # 提取关键信息
        row = stock_data.iloc[0]
        data = {
            "name": row["名称"],
            "ticker": row["代码"],
            "current_price": float(row["最新价"]),
            "change_pct": float(row["涨跌幅"]),
            "volume": float(row["成交量"]),
            "amount": float(row["成交额"]),
            "amplitude": float(row["振幅"]),
            "high": float(row["最高"]),
            "low": float(row["最低"]),
            "open": float(row["今开"]),
            "prev_close": float(row["昨收"]),
            "volume_ratio": float(row["量比"]),
            "turnover_rate": float(row["换手率"]),
            "pe_ratio": float(row["市盈率-动态"]),
            "pb_ratio": float(row["市净率"]),
            "total_mv": float(row["总市值"]),
            "circ_mv": float(row["流通市值"]),
        }

        print("\nExtracted data:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("Stock 600887 not found in data")

except Exception as e:
    print(f"Error: {e}")
    import traceback

    traceback.print_exc()
