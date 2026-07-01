#!/usr/bin/env python3
"""讀 data/sssc.csv，畫出松山運動中心的人潮趨勢圖，輸出成 chart.png。

產生兩張圖（上下排列）：
  1. 佔用率隨時間變化（游泳池、健身房；以「佔上限的百分比」呈現，方便比較）
  2. 依時段平均佔用率（尖離峰輪廓）

游泳池每日 10:00–10:30 清場，人數會歸零；這段從游泳池資料中排除，
以免把「強制清場」誤算成「離峰」。健身房不受影響。

用法：
  python3 chart.py                 # 全部資料
  python3 chart.py --days 7        # 只畫最近 7 天
需要 matplotlib：pip install matplotlib
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import datetime, timedelta

import matplotlib
matplotlib.use("Agg")  # 無視窗環境也能出圖
import matplotlib.pyplot as plt
from matplotlib import font_manager

DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "sssc.csv")
OUT_FILE = os.path.join(os.path.dirname(__file__), "chart.png")

# 游泳池清場時段（台北時間），這段游泳池資料不列入
CLEAR_START = (10, 0)   # 10:00
CLEAR_END = (10, 30)    # 10:30


def setup_cjk_font():
    """盡量找一個支援中日韓的字型，避免圖上出現豆腐方塊。找不到就用預設。"""
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",          # macOS
        "/System/Library/Fonts/Hiragino Sans GB.ttc",  # macOS
        "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",  # Linux
        "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",            # Linux
    ]
    for path in candidates:
        if os.path.exists(path):
            font_manager.fontManager.addfont(path)
            name = font_manager.FontProperties(fname=path).get_name()
            plt.rcParams["font.family"] = name
            break
    plt.rcParams["axes.unicode_minus"] = False


def in_clearing(dt):
    return (CLEAR_START[0], CLEAR_START[1]) <= (dt.hour, dt.minute) < (CLEAR_END[0], CLEAR_END[1])


def load(days):
    with open(DATA_FILE, encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    parsed = []
    for r in rows:
        dt = datetime.strptime(r["timestamp_taipei"], "%Y-%m-%d %H:%M:%S")
        parsed.append((dt, int(r["sw_people"]), int(r["sw_max"]),
                       int(r["gym_people"]), int(r["gym_max"])))
    if days:
        cutoff = max(p[0] for p in parsed) - timedelta(days=days)
        parsed = [p for p in parsed if p[0] >= cutoff]
    return parsed


def plot_timeseries(ax, data):
    # 游泳池：排除清場時段
    pool_t = [d[0] for d in data if not in_clearing(d[0])]
    pool_y = [100 * d[1] / d[2] for d in data if not in_clearing(d[0])]
    gym_t = [d[0] for d in data]
    gym_y = [100 * d[3] / d[4] for d in data]

    ax.plot(pool_t, pool_y, label="游泳池", color="#1f77b4", linewidth=1.5)
    ax.plot(gym_t, gym_y, label="健身房", color="#ff7f0e", linewidth=1.5)
    ax.set_title("松山運動中心 佔用率趨勢")
    ax.set_ylabel("佔用率 (%)")
    ax.set_ylim(0, 100)
    ax.legend()
    ax.grid(True, alpha=0.3)
    fig = ax.get_figure()
    fig.autofmt_xdate()


def plot_hourly(ax, data):
    pool = defaultdict(list)
    gym = defaultdict(list)
    for dt, sw, sw_max, g, g_max in data:
        if not in_clearing(dt):
            pool[dt.hour].append(100 * sw / sw_max)
        gym[dt.hour].append(100 * g / g_max)

    hours = sorted(set(pool) | set(gym))
    pool_avg = [sum(pool[h]) / len(pool[h]) if pool.get(h) else None for h in hours]
    gym_avg = [sum(gym[h]) / len(gym[h]) if gym.get(h) else None for h in hours]

    ax.plot(hours, pool_avg, "o-", label="游泳池", color="#1f77b4")
    ax.plot(hours, gym_avg, "o-", label="健身房", color="#ff7f0e")
    ax.set_title("依時段平均佔用率（尖離峰）")
    ax.set_xlabel("時段（台北時間）")
    ax.set_ylabel("平均佔用率 (%)")
    ax.set_xticks(hours)
    ax.set_ylim(0, 100)
    ax.legend()
    ax.grid(True, alpha=0.3)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=0,
                        help="只畫最近幾天（預設 0 = 全部）")
    args = parser.parse_args()

    if not os.path.exists(DATA_FILE):
        sys.exit("找不到資料檔，請先執行 fetch.py 累積資料。")
    data = load(args.days)
    if not data:
        sys.exit("沒有可畫的資料。")

    setup_cjk_font()
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(11, 9))
    plot_timeseries(ax1, data)
    plot_hourly(ax2, data)
    fig.tight_layout()
    fig.savefig(OUT_FILE, dpi=120)
    print(f"已輸出 {OUT_FILE}（{len(data)} 筆資料，游泳池已排除 10:00–10:30 清場時段）")


if __name__ == "__main__":
    main()
