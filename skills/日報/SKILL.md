---
name: 日報
description: 擷取台灣金融市場日報資料：台債殖利率、台股指數、三大法人買賣超、隔夜拆款利率、RP利率，含與前一交易日變動。觸發方式：/日報 或 /日報 YYYY/MM/DD
version: 0.2.0
tools: Bash, WebFetch
user-invocable: true
---

# 台灣金融市場日報

執行 skill 目錄內的 `daily_report.py` 腳本，擷取並輸出台灣金融市場當日關鍵資料。

## 使用方式
- `/日報` — 擷取最近一個交易日資料
- `/日報 YYYY/MM/DD` — 擷取指定日期資料（西元年格式）

## 執行步驟

### Step 1：確認依賴

```bash
python3 -c "import xlrd" 2>/dev/null || pip install xlrd -q
```

### Step 2：執行腳本

若使用者有提供日期參數 `{ARGUMENTS}`，執行：

```bash
python3 ~/.claude/skills/日報/daily_report.py "{ARGUMENTS}"
```

若無日期參數，執行：

```bash
python3 ~/.claude/skills/日報/daily_report.py
```

### Step 3：處理隔夜拆款利率延遲

若腳本輸出隔夜拆款「無資料（CSV更新延遲）」，改用 WebFetch 補充：

```
https://www.cbc.gov.tw/tw/lp-641-1.html
```

從網頁中找出當日與前一交易日的加權平均利率，填入報表。

### Step 4：輸出

將腳本輸出的 Markdown 表格直接呈現給使用者。
