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
| `fetch.py` | 抓資料並追加到 `data/sssc.csv`（純標準庫，零依賴） |
| `stats.py` | 讀 CSV，印出依時段／星期的平均人數統計（文字版，零依賴） |
| `chart.py` | 讀 CSV，畫出趨勢圖 `chart.png`（需 matplotlib） |
| `data/sssc.csv` | 歷史資料 |
| `.github/workflows/track.yml` | GitHub Actions 排程，自動持續抓取 |

**游泳池每日 10:00–10:30 清場**，這段人數會歸零。`stats.py` 與 `chart.py` 在統計／
畫圖時，會自動把游泳池的這半小時排除，以免把「強制清場」誤算成「離峰」（健身房不受影響）。

CSV 欄位：`timestamp_taipei, timestamp_utc, weekday, sw_people, sw_max, gym_people, gym_max`
（`sw` = 游泳池 swimming、`gym` = 健身房；`weekday` 0=週一 .. 6=週日）

## 本機使用

```bash
python3 fetch.py                              # 抓一次
python3 fetch.py --interval 600 --duration-minutes 240   # 持續 4 小時、每 10 分鐘一筆
python3 stats.py     # 看統計（文字版）
python3 stats.py --pool   # 只看游泳池
python3 stats.py --gym    # 只看健身房

pip install -r requirements.txt   # 畫圖前先裝 matplotlib（只需一次）
python3 chart.py             # 畫趨勢圖 → chart.png
python3 chart.py --days 7    # 只畫最近 7 天
```

`fetch.py` 參數：
- `--duration-minutes N`：持續執行 N 分鐘（0 = 只抓一筆）。超過台北 22:00 自動停止。
- `--interval S`：每筆相隔幾秒（預設 600 = 10 分鐘）。
- `--push`：每抓一筆就 `git commit` + `push`（給 CI 用，本機通常不需要）。

## 雲端自動追蹤（GitHub Actions）

**為什麼不是單純每 10 分鐘觸發？** GitHub 排程對高頻率（如 `*/10`）很不可靠，
常延遲或整個跳過。但一旦 job 開始跑，job 內的 `sleep` 是精準的。

所以策略是反過來：**一天只低頻觸發 4 次**（台北 06/10/14/18 點，這種低頻率
GitHub 才可靠），**每次觸發後 job 持續跑約 4 小時**，內部精準每 10 分鐘抓一筆、
且每抓一筆就 push（job 中途被砍也不掉資料）。四段接力涵蓋整個營業時段。

啟用步驟：

1. 在 GitHub 建一個 repo。**建議設為 public** —— public repo 的 Actions 分鐘數
   無限免費；private 每月只有 2000 分鐘，長時間執行會超支。運動中心人數非敏感資料。
2. 把這個目錄推上去：
   ```bash
   git remote add origin git@github.com:<你的帳號>/<repo名>.git
   git push -u origin main
   ```
3. 到 repo 的 **Settings → Actions → General → Workflow permissions**，
   確認勾選 **Read and write permissions**（讓 workflow 能 push 資料）。
4. 到 **Actions** 分頁，可手動按 **Run workflow** 測試（會持續跑數小時）。

> 註：GitHub 排程用 UTC；低頻觸發雖可靠很多，仍可能延遲幾分鐘。若某次觸發整個
> 被跳過，會損失該 4 小時區塊——需要更高可靠度時可改用本機 launchd 或雲端 VM。
