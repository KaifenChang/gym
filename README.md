# 松山運動中心人數追蹤

定時抓取台北松山國民運動中心的即時人數（游泳池、健身房），存成 CSV 累積歷史資料，用來分析尖離峰人潮。

## 資料來源

臺北市運動中心預約系統的即時人數 API：

```
POST https://booking-tpsc.sporetrofit.com/Home/loadLocationPeopleNum
```

回傳全台北市 11 個運動中心的即時資料，本專案只擷取松山（`LID = SSSC`）。

## 檔案

| 檔案 | 說明 |
|------|------|
| `fetch.py` | 抓一次資料並追加到 `data/sssc.csv`（純標準庫，零依賴） |
| `stats.py` | 讀 CSV，印出依時段／星期的平均人數統計 |
| `data/sssc.csv` | 歷史資料 |
| `.github/workflows/track.yml` | GitHub Actions 排程，每 10 分鐘抓一次 |

CSV 欄位：`timestamp_taipei, timestamp_utc, weekday, sw_people, sw_max, gym_people, gym_max`
（`sw` = 游泳池 swimming、`gym` = 健身房；`weekday` 0=週一 .. 6=週日）

## 本機使用

```bash
python3 fetch.py     # 抓一次
python3 stats.py     # 看統計
python3 stats.py --pool   # 只看游泳池
python3 stats.py --gym    # 只看健身房
```

## 雲端自動追蹤（GitHub Actions）

排程設定為台北營業時段（06:00–22:00）內每 10 分鐘抓一次，資料自動 commit 回 repo。

啟用步驟：

1. 在 GitHub 建一個 repo（可設為 private）。
2. 把這個目錄推上去：
   ```bash
   git remote add origin git@github.com:<你的帳號>/<repo名>.git
   git push -u origin main
   ```
3. 到 repo 的 **Settings → Actions → General → Workflow permissions**，
   確認勾選 **Read and write permissions**（讓 workflow 能 commit 資料）。
4. 到 **Actions** 分頁，可手動按 **Run workflow** 測試一次。

之後每 10 分鐘會自動累積一筆資料。

> 註：GitHub 排程用 UTC 且尖峰時可能延遲幾分鐘；長期沒有 push 活動的 repo
> 排程會被自動停用，但只要持續有資料 commit 就會保持啟用。
