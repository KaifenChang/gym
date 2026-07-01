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
import subprocess
import time
import urllib.request
from datetime import datetime, timezone, timedelta

API_URL = "https://booking-tpsc.sporetrofit.com/Home/loadLocationPeopleNum"
TARGET_LID = "SSSC"  # 松山
TAIPEI = timezone(timedelta(hours=8))
OPEN_HOUR = 6    # 營業起始（台北時間）
CLOSE_HOUR = 22  # 營業結束（台北時間）
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


def git_push():
    """把新資料 commit 並 push 回 remote，容忍偶發衝突。

    在 GitHub Actions 長時間執行時，每抓一筆就 push 一次，
    這樣就算 job 中途被砍，已抓的資料也已經安全存進 remote。
    """
    def run(*args):
        return subprocess.run(["git", *args], cwd=os.path.dirname(__file__) or ".",
                              capture_output=True, text=True)

    if not run("diff", "--quiet", "--", DATA_FILE).returncode:
        return  # 沒有變化就不 commit
    run("add", DATA_FILE)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    run("commit", "-m", f"data: 松山人數 {stamp}")
    # 先 rebase 再 push，重試幾次以應付偶發並行衝突
    for _ in range(3):
        run("pull", "--rebase", "--autostash")
        if run("push").returncode == 0:
            return
        time.sleep(2)
    print("push 失敗（已重試 3 次），下一筆會再嘗試", flush=True)


def within_hours(now):
    return OPEN_HOUR <= now.hour < CLOSE_HOUR


def main():
    # GitHub 排程「觸發頻率」不可靠，但 job 內的 sleep 是精準的。
    # 所以改成：一天低頻觸發幾次，每次觸發後這個 job 就持續跑好幾個小時，
    # 內部精準地每隔 interval 抓一筆，直到 duration 到或超過營業時間為止。
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=int, default=600,
                        help="每筆之間相隔幾秒（預設 600 = 10 分鐘）")
    parser.add_argument("--duration-minutes", type=int, default=0,
                        help="持續執行幾分鐘；0（預設）表示只抓一筆就結束")
    parser.add_argument("--push", action="store_true",
                        help="每抓一筆就 git commit + push（給 CI 用）")
    args = parser.parse_args()

    def one():
        try:
            sample_once()
            if args.push:
                git_push()
        except Exception as exc:  # 單筆失敗不要中斷整個迴圈
            print(f"抓取失敗：{exc}", flush=True)

    if args.duration_minutes <= 0:
        one()
        return

    end = time.time() + args.duration_minutes * 60
    while time.time() < end:
        if within_hours(datetime.now(TAIPEI)):
            one()
        else:
            print("非營業時段，停止本次執行", flush=True)
            break
        if time.time() + args.interval < end:
            time.sleep(args.interval)
        else:
            break


if __name__ == "__main__":
    main()
