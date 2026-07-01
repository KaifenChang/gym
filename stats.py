#!/usr/bin/env python3
"""讀取 data/sssc.csv，印出松山運動中心的尖離峰統計。

用法：
  python3 stats.py            # 全部資料
  python3 stats.py --pool     # 只看游泳池（預設同時看兩者）
  python3 stats.py --gym      # 只看健身房

零依賴，純標準庫。之後資料累積夠多，這裡就能看出每天/每小時的人潮規律。
"""

import csv
import os
import sys
from collections import defaultdict

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "sssc.csv")
WEEKDAYS = ["週一", "週二", "週三", "週四", "週五", "週六", "週日"]

# 游泳池每日 10:00–10:30 清場，人數會歸零；統計游泳池時排除這段
CLEAR_START = (10, 0)
CLEAR_END = (10, 30)


def in_pool_clearing(ts):
    """ts 形如 '2026-07-01 10:15:00'，判斷是否落在清場時段。"""
    hm = (int(ts[11:13]), int(ts[14:16]))
    return CLEAR_START <= hm < CLEAR_END


def load():
    with open(DATA_FILE, encoding="utf-8") as f:
        return list(csv.DictReader(f))


def bar(value, max_value, width=30):
    filled = int(round(width * value / max_value)) if max_value else 0
    return "█" * filled + "·" * (width - filled)


def summarize(rows, people_key, max_key, label, is_pool=False):
    by_hour = defaultdict(list)
    by_weekday = defaultdict(list)
    for r in rows:
        if is_pool and in_pool_clearing(r["timestamp_taipei"]):
            continue  # 排除游泳池清場時段
        hour = int(r["timestamp_taipei"][11:13])
        by_hour[hour].append(int(r[people_key]))
        by_weekday[int(r["weekday"])].append(int(r[people_key]))

    cap = max(int(r[max_key]) for r in rows)
    print(f"\n=== {label}（上限 {cap} 人，共 {len(rows)} 筆）===")

    print("\n  依時段平均：")
    for h in sorted(by_hour):
        vals = by_hour[h]
        avg = sum(vals) / len(vals)
        print(f"    {h:02d}:00  {avg:5.0f}  {bar(avg, cap)}")

    print("\n  依星期平均：")
    for d in sorted(by_weekday):
        vals = by_weekday[d]
        avg = sum(vals) / len(vals)
        print(f"    {WEEKDAYS[d]}  {avg:5.0f}  {bar(avg, cap)}")


def main():
    if not os.path.exists(DATA_FILE):
        sys.exit("找不到資料檔，請先執行 fetch.py 累積資料。")
    rows = load()
    if not rows:
        sys.exit("資料檔是空的。")

    show_pool = "--gym" not in sys.argv
    show_gym = "--pool" not in sys.argv
    if show_pool:
        summarize(rows, "sw_people", "sw_max", "游泳池（已排除 10:00–10:30 清場）", is_pool=True)
    if show_gym:
        summarize(rows, "gym_people", "gym_max", "健身房")


if __name__ == "__main__":
    main()
