# 投資顧問 AI 代理人系統 — 繼續實作說明

## 目前進度

### 已完成的檔案
1. ✅ `requirements.txt` — 已加入 `anthropic>=0.40.0`, `pydantic>=2.0.0`
2. ✅ `advisor/__init__.py`
3. ✅ `advisor/models.py` — Pydantic 資料模型（Holding, Portfolio, AnalysisResult, RiskReport, FinalAdvice, AgentBrief, AgentOutcome）
4. ✅ `advisor/market_data.py` — yfinance 市場快照（含 SMA/RSI/MACD 計算 + 基本面欄位白名單 + deterministic serialize）

### 待完成的檔案
5. ⏳ `advisor/agents.py` — 8 個 agent 的繁中 system prompt + AgentSpec 定義
6. ⏳ `advisor/client.py` — AsyncAnthropic wrapper（含長 timeout + 重試 + 兩階段輸出）
7. ⏳ `advisor/orchestrator.py` — pipeline 協調（asyncio.gather 並行執行 6 分析師）
8. ⏳ `advisor/cli.py` — 互動式 CLI 逐筆輸入持股
9. ⏳ `main.py` — 程式入口
10. ⏳ `README.md` — 新增使用章節

---

## 重要設計決策

### 使用者選擇
- **Claude 模型**：`claude-sonnet-4-6`（預設，可用 `--model` 切換）
- **輸入方式**：CLI 互動模式（逐筆詢問）
- **輸出語言**：繁體中文
- **市場**：美股 + 債券（不支援台股）

### 關鍵技術決策
1. **單一檔案設計 8 個 agent** — 不用 BaseAgent ABC，避免過度抽象
2. **共享 MarketSnapshot** — 一次抓齊餵給所有 agents，避免 rate limit 與資料不一致
3. **Pydantic `messages.parse()`** — 取代 tool_use 作結構化輸出
4. **Prompt caching** — 每個 agent 的 system prompt 加 `cache_control: ephemeral`
5. **Adaptive thinking** — 僅 Risk Manager / Portfolio Manager 啟用（分析師不開以加速）
6. **兩階段輸出**（因應 Stream idle timeout 問題）：
   - Stage 1：`AgentBrief`（短，< 1024 tokens）→ 決定立場與骨架
   - Stage 2：`AnalysisResult`（長，< 2000 tokens）→ 依骨架擴寫

### Stream idle timeout 解決方案（要套用到 client.py）
```python
import httpx
from anthropic import AsyncAnthropic

client = AsyncAnthropic(
    timeout=httpx.Timeout(connect=10.0, read=600.0, write=30.0, pool=10.0),
    max_retries=3,
)
```

另外加 wrapper 處理「partial response」：
```python
async def call_with_retry(fn, max_attempts=4):
    for attempt in range(max_attempts):
        try:
            return await fn()
        except (APIError, httpx.ReadTimeout) as e:
            if attempt < max_attempts - 1:
                await asyncio.sleep(2 ** attempt)  # 1, 2, 4, 8s
                continue
            raise
```

---

## Pipeline 流程

```
CLI 互動輸入持股 → Portfolio
   ↓
市場快照 (MarketSnapshot) — 一次抓齊
   ↓
┌─ 6 位分析師並行（asyncio.gather） ─┐
│  1. 技術分析（SMA/RSI/MACD）        │
│  2. 基本面（P/E/ROE/FCF）           │
│  3. 巴菲特（護城河/內在價值）       │
│  4. Peter Lynch（PEG/六分類）       │
│  5. Cathie Wood（顛覆創新）         │
│  6. Bill Ackman（集中型品質）       │
└────────────────────────────────────┘
   ↓
風險管理（彙整 + VaR 概念） — 啟用 adaptive thinking
   ↓
投資組合經理（綜合建議） — 啟用 adaptive thinking
   ↓
Markdown 報告（繁中 + 法律免責聲明）
```

---

## 下一步：實作 advisor/agents.py

### 結構
```python
from dataclasses import dataclass
from advisor.models import AnalysisResult, RiskReport, FinalAdvice

@dataclass
class AgentSpec:
    name: str
    role: str
    system_prompt: str           # 繁中，≥ 2048 tokens（觸發 cache）
    response_model: type
    enable_thinking: bool = False

# 8 個 system prompt（每個約 2500-3500 中文字）
SYS_TECH = """你是一位資深技術分析師..."""
SYS_FUND = """你是一位基本面分析師..."""
SYS_BUFFETT = """你是巴菲特投資哲學的忠實奉行者..."""
SYS_LYNCH = """你是 Peter Lynch 的投資哲學追隨者..."""
SYS_WOOD = """你是 Cathie Wood（ARK Invest）的投資哲學信徒..."""
SYS_ACKMAN = """你是 Bill Ackman 集中型投資哲學的實踐者..."""
SYS_RISK = """你是一位投資組合風險管理專家..."""
SYS_PM = """你是一位資深投資組合經理..."""

AGENT_SPECS = [
    AgentSpec("technical", "技術分析師", SYS_TECH, AnalysisResult),
    AgentSpec("fundamental", "基本面分析師", SYS_FUND, AnalysisResult),
    AgentSpec("buffett", "巴菲特哲學", SYS_BUFFETT, AnalysisResult),
    AgentSpec("lynch", "Peter Lynch 哲學", SYS_LYNCH, AnalysisResult),
    AgentSpec("wood", "Cathie Wood 哲學", SYS_WOOD, AnalysisResult),
    AgentSpec("ackman", "Bill Ackman 哲學", SYS_ACKMAN, AnalysisResult),
]
RISK_SPEC = AgentSpec("risk", "風險管理專家", SYS_RISK, RiskReport, enable_thinking=True)
PM_SPEC = AgentSpec("pm", "投資組合經理", SYS_PM, FinalAdvice, enable_thinking=True)
```

### 各 agent system prompt 應涵蓋
| Agent | 核心框架 |
|-------|----------|
| 技術分析 | 趨勢/SMA 5/20/60/RSI/MACD/支撐壓力/量價關係 |
| 基本面 | P/E、P/B、PEG、ROE、毛利率、營收成長、負債比、FCF yield |
| 巴菲特 | 護城河 4 類型、ROIC > 15%、管理層誠信、內在價值 DCF、安全邊際 |
| Peter Lynch | 六分類（穩健/快速/景氣/資產/轉機/緩慢）、PEG < 1、Story+Numbers、十倍股特徵 |
| Cathie Wood | 五大創新平台（AI/機器人/能源儲存/區塊鏈/基因）、Wright's Law、5 年 CAGR |
| Bill Ackman | 簡單可預測業務、高 ROIC、集中投資 8-12 檔、催化劑、管理層行動 |
| 風險管理 | 集中度（單一部位 > 10% 警示）、相關性、波動度、max drawdown、尾部風險、VaR 概念 |
| 投資組合經理 | 綜合 6 + 風險 → executive summary + action items + rebalance + stop loss + outlook |

---

## 下一步：advisor/client.py 骨架

```python
import asyncio
import httpx
from anthropic import AsyncAnthropic, APIError
from advisor.models import AgentBrief, AnalysisResult, RiskReport, FinalAdvice, AgentOutcome
from advisor.agents import AgentSpec

_client = AsyncAnthropic(
    timeout=httpx.Timeout(connect=10.0, read=600.0, write=30.0, pool=10.0),
    max_retries=3,
)

async def run_agent(
    spec: AgentSpec,
    user_content: str,
    model: str = "claude-sonnet-4-6",
) -> AgentOutcome:
    """兩階段執行：先 brief（短）→ 再 full（長）。"""
    # Stage 1: brief
    try:
        brief = await _call_stage1(spec, user_content, model)
    except Exception as e:
        return AgentOutcome(agent_name=spec.name, role=spec.role, status="failed", error=str(e))

    # Stage 2: full structured output（使用 brief 作骨架）
    try:
        result = await _call_stage2(spec, user_content, brief, model)
    except Exception as e:
        return AgentOutcome(agent_name=spec.name, role=spec.role, status="failed",
                            brief=brief, error=str(e))

    return AgentOutcome(
        agent_name=spec.name, role=spec.role, status="ok",
        brief=brief, result=result,
    )


async def _call_stage1(spec, user_content, model) -> AgentBrief:
    """請 agent 產生簡短 brief（立場、關鍵點、per-holding 態度）。"""
    msg = await _client.messages.parse(
        model=model,
        max_tokens=1024,
        system=[{
            "type": "text",
            "text": spec.system_prompt,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": f"{user_content}\n\n請先產出 AgentBrief（簡短摘要）。",
        }],
        response_model=AgentBrief,
    )
    return msg.parsed


async def _call_stage2(spec, user_content, brief, model):
    """依 brief 擴寫完整結構化輸出。"""
    brief_json = brief.model_dump_json(indent=2)
    msg = await _client.messages.parse(
        model=model,
        max_tokens=2048,
        system=[{
            "type": "text",
            "text": spec.system_prompt,
            "cache_control": {"type": "ephemeral"},
        }],
        messages=[{
            "role": "user",
            "content": f"{user_content}\n\n你先前已產出這份 brief:\n{brief_json}\n\n"
                       f"請依此骨架產出完整結構化分析。",
        }],
        response_model=spec.response_model,
        thinking={"type": "adaptive"} if spec.enable_thinking else None,
    )
    return msg.parsed
```

---

## 下一步：advisor/orchestrator.py 骨架

```python
import asyncio
import datetime
from advisor.agents import AGENT_SPECS, RISK_SPEC, PM_SPEC
from advisor.client import run_agent
from advisor.market_data import build_market_snapshot, serialize_snapshot
from advisor.models import Portfolio


async def run_pipeline(portfolio: Portfolio, model: str) -> str:
    print("→ 抓取市場快照中...")
    snapshot = build_market_snapshot(portfolio)
    snap_text = serialize_snapshot(snapshot)

    portfolio_text = portfolio.model_dump_json(indent=2)
    user_content = f"# 投資組合\n```json\n{portfolio_text}\n```\n\n# 市場快照\n```json\n{snap_text}\n```"

    print("→ 6 位分析師並行分析中...")
    analysts = await asyncio.gather(
        *[run_agent(spec, user_content, model) for spec in AGENT_SPECS],
        return_exceptions=True,
    )
    for a in analysts:
        if hasattr(a, 'status'):
            status_icon = "✓" if a.status == "ok" else "✗"
            print(f"  {status_icon} {a.role}")

    # 序列化 analyst 結果作為 risk manager 輸入
    analyst_summaries = "\n\n".join(
        f"## {a.role}\n{a.result.model_dump_json(indent=2)}"
        for a in analysts if hasattr(a, 'result') and a.result
    )

    print("→ 風險管理彙整中...")
    risk_input = f"{user_content}\n\n# 6 位分析師輸出\n{analyst_summaries}"
    risk_outcome = await run_agent(RISK_SPEC, risk_input, model)

    print("→ 投資組合經理綜合建議中...")
    pm_input = f"{risk_input}\n\n# 風險管理報告\n{risk_outcome.result.model_dump_json(indent=2)}"
    pm_outcome = await run_agent(PM_SPEC, pm_input, model)

    # 組裝 Markdown 報告
    return assemble_report(portfolio, analysts, risk_outcome, pm_outcome)


def assemble_report(portfolio, analysts, risk_outcome, pm_outcome) -> str:
    lines = ["# 投資組合分析報告", ""]
    # ... 組裝各段落 + 法律免責聲明
    return "\n".join(lines)
```

---

## 下一步：advisor/cli.py 骨架

```python
from advisor.models import Holding, Portfolio
import datetime


def interactive_input() -> Portfolio:
    print("=== 投資顧問 AI 代理人 ===\n")
    print("請輸入持股（輸入 'done' 結束）：\n")
    holdings = []
    idx = 1
    while True:
        print(f"[#{idx}]")
        asset_type = input("  資產類型 (stock / bond / done): ").strip().lower()
        if asset_type == "done":
            break
        if asset_type not in ("stock", "bond"):
            print("  ⚠ 請輸入 stock 或 bond")
            continue
        symbol = input("  代號: ").strip().upper()
        bond_kind = None
        if asset_type == "bond":
            bond_kind = input("  債券類型 (treasury/corporate/etf): ").strip().lower()
        qty = float(input("  數量: "))
        cost = float(input("  平均成本 (USD): "))
        holdings.append(Holding(
            symbol=symbol, asset_type=asset_type,
            quantity=qty, cost_price=cost, bond_kind=bond_kind,
        ))
        print(f"  ✓ 已加入 {symbol} × {qty} @ ${cost}\n")
        idx += 1

    if not holdings:
        raise SystemExit("沒有輸入任何持股，結束。")

    today = datetime.date.today().isoformat()
    return Portfolio(holdings=holdings, as_of_date=today)
```

---

## 下一步：main.py

```python
import argparse
import asyncio
import datetime
import os
from pathlib import Path
from advisor.cli import interactive_input
from advisor.orchestrator import run_pipeline


def main():
    parser = argparse.ArgumentParser(description="投資顧問 AI 代理人")
    parser.add_argument("--model", default="claude-sonnet-4-6")
    parser.add_argument("--output", default=None)
    args = parser.parse_args()

    portfolio = interactive_input()

    confirm = input("\n確認送出分析？(Y/n): ").strip().lower()
    if confirm == "n":
        return

    report = asyncio.run(run_pipeline(portfolio, args.model))

    output_path = args.output or f"reports/{datetime.datetime.now():%Y-%m-%d_%H%M}_portfolio_report.md"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    Path(output_path).write_text(report, encoding="utf-8")
    print(f"\n✓ 報告已儲存：{output_path}")


if __name__ == "__main__":
    main()
```

---

## 安裝與執行

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...
python main.py
```

---

## 待辦清單（回家繼續時）

- [ ] 實作 `advisor/agents.py`（8 個詳細中文 system prompt）
- [ ] 實作 `advisor/client.py`（AsyncAnthropic + timeout + 兩階段）
- [ ] 實作 `advisor/orchestrator.py`（pipeline + Markdown 組裝）
- [ ] 實作 `advisor/cli.py`（互動輸入）
- [ ] 實作 `main.py`
- [ ] 更新 `README.md` 加入使用章節
- [ ] 端到端測試：AAPL + NVDA + BRK-B + TLT + LQD
- [ ] 驗證 prompt cache 命中（第二次執行 `usage.cache_read_input_tokens > 0`）
- [ ] Commit + push 到 `claude/investment-advisor-ai-agents-7tBxh` branch
