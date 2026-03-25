---
name: 日報
description: 擷取台灣金融市場日報資料：台債殖利率、台股指數、三大法人買賣超、隔夜拆款利率、RP利率，含與前一交易日變動。觸發方式：/日報 或 /日報 YYYY/MM/DD
version: 0.1.0
tools: Bash, WebFetch, Read, Write
user-invocable: true
---

# 台灣金融市場日報

擷取當日（或指定日期）台灣金融市場關鍵資料，計算與前一交易日變動，以列表呈現。

## 使用方式
- `/日報` — 擷取最近一個交易日資料
- `/日報 YYYY/MM/DD` — 擷取指定日期資料（西元年格式）

## Step 1：判斷目標日期

如果使用者提供日期參數，使用該日期。否則：
- 取得今天日期
- 若為週六，目標日 = 週五；若為週日，目標日 = 上週五
- 若為週一～五且尚未收盤（15:00 前），目標日 = 前一個交易日

設定兩個日期變數：
- `TARGET_DATE`：目標日（格式 YYYY/MM/DD 用於 TPEx，YYYYMMDD 用於 TWSE）
- `PREV_DATE`：前一個交易日（TARGET_DATE 往前推一個工作日，跳過週末）

## Step 2：台債指標債殖利率（5年期、10年期）

**來源**：櫃買中心 BDdys100 XLS

1. 直接下載 XLS（URL 格式固定）：
```bash
curl -s -o /tmp/bond_yield.xls \
  'https://www.tpex.org.tw/storage/bond_zone/tradeinfo/govbond/{YYYY}/{YYYYMM}/BDdys100.{YYYYMMDD}-C.xls' \
  -H 'User-Agent: Mozilla/5.0'
```

2. 用 Python xlrd 解析：
```python
import xlrd
wb = xlrd.open_workbook('/tmp/bond_yield.xls')
ws = wb.sheet_by_index(0)
# row 5 = 5年期, row 6 = 10年期（row index 從 0 起算，資料從 row 4 開始）
# 欄位：到期年限(0), 指標公債代號(1), 平均殖利率%(2), 平均百元價(3), 殖利率漲跌bp(4)
for row_idx in [5, 6]:
    tenor = ws.cell_value(row_idx, 0)
    bond_code = ws.cell_value(row_idx, 1)
    avg_yield = ws.cell_value(row_idx, 2)
    yield_change_bp = ws.cell_value(row_idx, 4)
```

**注意**：日期使用**西元年** YYYY/MM/DD 格式，不是民國年。

## Step 3：台股加權指數

**來源**：證交所 MI_INDEX API

```bash
curl -s 'https://www.twse.com.tw/exchangeReport/MI_INDEX?response=json&date={YYYYMMDD}&type=IND' \
  -H 'User-Agent: Mozilla/5.0'
```

- 回傳 `tables[0].data` 中找「發行量加權股價指數」（通常在第 2 筆，index 1）
- 欄位：指數名稱、收盤指數、漲跌(+/-)、漲跌點數、漲跌百分比(%)

API 已含漲跌資訊，無需另取前一日。

## Step 4：三大法人買賣超

**來源**：證交所 BFI82U API

分別取當日與前一交易日：
```bash
# 當日
curl -s 'https://www.twse.com.tw/fund/BFI82U?response=json&dayDate={YYYYMMDD}&type=day' \
  -H 'User-Agent: Mozilla/5.0'

# 前一交易日
curl -s 'https://www.twse.com.tw/fund/BFI82U?response=json&dayDate={PREV_YYYYMMDD}&type=day' \
  -H 'User-Agent: Mozilla/5.0'
```

- `data` 陣列依序：自營商(自行買賣)、自營商(避險)、投信、外資及陸資、外資自營商、合計
- 欄位：單位名稱、買進金額、賣出金額、買賣差額
- 金額單位為「元」，呈現時換算為「億元」（除以 100,000,000）
- 重點呈現：**外資（index 3）、投信（index 2）、自營商合計（index 0 + index 1 的買賣差額）**
- 計算當日 vs 前日淨買賣超變動

## Step 5：金融業隔夜拆款利率

**來源**：央行 CSV

```bash
curl -s 'https://www.cbc.gov.tw/public/data/OpenData/WebF2.csv' \
  -H 'User-Agent: Mozilla/5.0' | iconv -f big5 -t utf-8
```

- CSV 欄位：日期（YYYY/M/D）, 利率(%)
- 取最後兩筆資料（最近兩個交易日）
- 計算利率變動（當日 - 前日），以 bp 呈現（1bp = 0.01%，即差值 × 100）
- 注意：CSV 更新可能延遲 1-2 天

**備用方案**：若 CSV 無當日資料，改用 WebFetch 擷取：
```
https://www.cbc.gov.tw/tw/lp-641-1.html
```

## Step 6：2-10天期附買回（RP）利率

**來源**：櫃買中心 BDdcs001 XLS（BDdcs01b 活頁）

分別取當日與前一交易日：

1. 直接下載 XLS（URL 格式固定）：
```bash
# 當日
curl -s -o /tmp/repo_today.xls \
  'https://www.tpex.org.tw/storage/bond_zone/tradeinfo/govbond/{YYYY}/{YYYYMM}/BDdcs001.{YYYYMMDD}-C.xls' \
  -H 'User-Agent: Mozilla/5.0'
# 前一交易日
curl -s -o /tmp/repo_prev.xls \
  'https://www.tpex.org.tw/storage/bond_zone/tradeinfo/govbond/{PREV_YYYY}/{PREV_YYYYMM}/BDdcs001.{PREV_YYYYMMDD}-C.xls' \
  -H 'User-Agent: Mozilla/5.0'
```

2. 用 Python xlrd 解析 BDdcs01b 活頁：
```python
import xlrd
wb = xlrd.open_workbook('/tmp/repo.xls')
ws = wb.sheet_by_name('BDdcs01b')
# 欄位 index：約定天數(4)、最高利率(5)、最低利率(6)、加權平均利率(7)、金額(8)
# 注意：TWD 區塊起始 row 會因 CNY 資料筆數不同而變動，不可用固定 row index
# 必須搜尋「TWD」列後，再往下找約定天數欄為「2-10」的列
twd_row = None
for r in range(ws.nrows):
    if ws.cell_value(r, 0) == 'TWD':
        twd_row = r
        break

rate_2_10 = None
amount_2_10 = None
if twd_row is not None:
    for r in range(twd_row, ws.nrows):
        if ws.cell_value(r, 4) == '2-10':
            # 確認在附買回區塊（非附賣回），往上找最近的「原始附買回」標記
            is_repo = False
            for rr in range(r, twd_row - 1, -1):
                v = ws.cell_value(rr, 1)
                if '原始附買回' in str(v):
                    is_repo = True
                    break
                elif '原始附賣回' in str(v):
                    break
            if is_repo:
                rate_2_10 = ws.cell_value(r, 7)   # 加權平均利率
                amount_2_10 = ws.cell_value(r, 8)  # 金額（元）
                break
```

3. 取 2-10 天期的**加權平均利率**（col 7）與**金額**（col 8）
4. 金額單位為元，呈現時換算為億元
5. 計算與前一日的利率變動（以 bp 呈現，1bp = 0.01%，即差值 × 100）及金額變動

## Step 7：輸出格式

以下列 Markdown 格式輸出結果：

```
## 台灣金融市場日報（{YYYY/MM/DD}）

### 台債指標債殖利率
- 5年期：{yield}%（{+/-}{bp}bp）　指標券：{bond_code}
- 10年期：{yield}%（{+/-}{bp}bp）　指標券：{bond_code}

### 台股加權指數
- 收盤：{index}（{+/-}{points}，{+/-}{pct}%）

### 三大法人買賣超（億元）
- 外資：{+/-}{amount}（前日 {prev}，變動 {+/-}{diff}）
- 投信：{+/-}{amount}（前日 {prev}，變動 {+/-}{diff}）
- 自營商：{+/-}{amount}（前日 {prev}，變動 {+/-}{diff}）

### 金融業隔夜拆款利率
- 加權平均：{rate}%（前日 {prev_rate}%，變動 {+/-}{diff}bp）

### 2-10天期附買回利率
- 加權平均：{rate}%（前日 {prev_rate}%，變動 {+/-}{diff}bp）
- 成交金額：{amount} 億元（前日 {prev_amount} 億元）
```

## 注意事項
- TPEx 日期格式為**西元年** YYYY/MM/DD，非民國年
- TWSE 日期格式為 YYYYMMDD（無分隔符）
- 所有 API 請求需加 `User-Agent` header
- 非交易日可能無資料，應提示使用者
- 金額單位需從「元」換算為「億元」
- 三大法人中「自營商」= 自行買賣 + 避險 合計
