#!/usr/bin/env python3
"""抓取台北松山國民運動中心即時人數，附上時間戳記後追加到 CSV。

資料來源：臺北市運動中心預約系統
  POST https://booking-tpsc.sporetrofit.com/Home/loadLocationPeopleNum
回傳全台北市 11 個運動中心的即時游泳池 (swPeopleNum) 與健身房 (gymPeopleNum) 人數。
本腳本只擷取松山中心 (LID = SSSC)。
"""

import argparse
import csv
import json
import os
import time
import urllib.request
from datetime import datetime, timezone, timedelta

API_URL = "https://booking-tpsc.sporetrofit.com/Home/loadLocationPeopleNum"
TARGET_LID = "SSSC"  # 松山
TAIPEI = timezone(timedelta(hours=8))
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "sssc.csv")
HEADER = [
    "timestamp_taipei",  # 台北時間，方便直接閱讀
    "timestamp_utc",     # UTC，方便程式排序
    "weekday",           # 0=週一 .. 6=週日
    "sw_people",         # 游泳池目前人數
    "sw_max",            # 游泳池上限
    "gym_people",        # 健身房目前人數
    "gym_max",           # 健身房上限
]


def fetch_sssc():
    """打 API，回傳松山中心的那筆資料 dict。"""
    # 這個端點要求 POST 且必須帶 Content-Length，送空 body 即可。
    req = urllib.request.Request(
        API_URL,
        data=b"",
        method="POST",
        headers={
            "Content-Length": "0",
            "User-Agent": "Mozilla/5.0 (occupancy-tracker)",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        payload = json.loads(resp.read().decode("utf-8"))

    for row in payload.get("locationPeopleNums", []):
        if row.get("LID") == TARGET_LID:
            return row
    raise RuntimeError(f"回傳資料中找不到 LID={TARGET_LID}")


def append_row(row):
    now = datetime.now(TAIPEI)
    record = [
        now.strftime("%Y-%m-%d %H:%M:%S"),
        now.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        now.weekday(),
        int(row["swPeopleNum"]),
        int(row["swMaxPeopleNum"]),
        int(row["gymPeopleNum"]),
        int(row["gymMaxPeopleNum"]),
    ]

    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    new_file = not os.path.exists(DATA_FILE) or os.path.getsize(DATA_FILE) == 0
    with open(DATA_FILE, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(HEADER)
        writer.writerow(record)
    return record


def sample_once():
    record = append_row(fetch_sssc())
    print(
        f"[{record[0]}] 松山 游泳池 {record[3]}/{record[4]}、"
        f"健身房 {record[5]}/{record[6]}",
        flush=True,
    )


def main():
    # GitHub 排程不準時（可能延遲甚至跳過），所以每次觸發連續抓多筆，
    # 讓每次醒來都能補齊一小段時間的資料，降低漏抓影響。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--samples", type=int, default=1,
                        help="這次總共抓幾筆（預設 1）")
    parser.add_argument("--interval", type=int, default=180,
                        help="每筆之間相隔幾秒（預設 180 = 3 分鐘）")
    args = parser.parse_args()

    for i in range(args.samples):
        try:
            sample_once()
        except Exception as exc:  # 單筆失敗不要中斷整批
            print(f"抓取失敗（第 {i + 1} 筆）：{exc}", flush=True)
        if i < args.samples - 1:
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
