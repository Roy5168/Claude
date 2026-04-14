"""Pydantic 資料模型：Holding、Portfolio、各 agent 輸出格式。"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Holding(BaseModel):
    """單一持股/持債。"""

    symbol: str = Field(..., description="股票/債券代號，例如 AAPL、TLT、^TNX")
    asset_type: Literal["stock", "bond"]
    quantity: float = Field(..., gt=0, description="股數 / 債券單位數")
    cost_price: float = Field(..., gt=0, description="平均成本（USD）")
    bond_kind: Literal["treasury", "corporate", "etf"] | None = None


class Portfolio(BaseModel):
    """投資組合。"""

    holdings: list[Holding]
    as_of_date: str
    base_currency: Literal["USD"] = "USD"

    def total_cost(self) -> float:
        return sum(h.quantity * h.cost_price for h in self.holdings)


class HoldingView(BaseModel):
    """單一持股的 agent 評等。"""

    symbol: str
    rating: Literal["buy", "hold", "reduce", "sell"]
    rationale: str
    target_price: float | None = None


class AnalysisResult(BaseModel):
    """6 位分析師的標準輸出格式。"""

    agent_name: str
    summary: str = Field(..., description="對整體投資組合的高層次結論（繁中）")
    per_holding: list[HoldingView]
    portfolio_view: str = Field(..., description="從該 agent 投資哲學出發的整體評論（繁中）")


class RiskReport(BaseModel):
    """風險管理 agent 輸出。"""

    concentration: str = Field(..., description="集中度分析（單一部位/產業/類別佔比）")
    correlation: str = Field(..., description="相關性與分散度分析")
    volatility: str = Field(..., description="波動度與 drawdown 估計")
    tail_risks: list[str] = Field(..., description="尾部風險情境條列")
    overall_risk_level: Literal["low", "moderate", "high", "extreme"]
    key_findings: str = Field(..., description="彙整 6 位分析師後的關鍵發現")


class FinalAdvice(BaseModel):
    """投資組合經理最終輸出。"""

    executive_summary: str = Field(..., description="總覽摘要（繁中）")
    action_items: list[str] = Field(..., description="具體可執行的行動條目")
    rebalance_suggestions: list[str] = Field(..., description="再平衡建議")
    stop_loss_alerts: list[str] = Field(..., description="停損/風險警示")
    outlook: str = Field(..., description="短中期展望（繁中）")


class AgentBrief(BaseModel):
    """Stage 1 輸出：簡短的規劃/摘要，作為 stage 2 的結構骨架。

    目的：先讓 agent 產出短輸出（< 1024 tokens），再請它依此骨架
    擴寫完整分析，降低單次回應長度，避免 stream idle timeout。
    """

    overall_stance: str = Field(..., description="1-2 句的整體立場")
    key_themes: list[str] = Field(..., description="3-5 個關鍵觀察點")
    per_holding_stance: dict[str, str] = Field(
        ..., description="symbol → 'rating + 一句話理由'"
    )


class AgentOutcome(BaseModel):
    """單一 agent 執行結果的封裝（含失敗狀態）。"""

    agent_name: str
    role: str
    status: Literal["ok", "failed", "refused"]
    brief: AgentBrief | None = None
    result: AnalysisResult | RiskReport | FinalAdvice | None = None
    error: str | None = None
    cache_read_tokens: int = 0
    cache_creation_tokens: int = 0
    input_tokens: int = 0
    output_tokens: int = 0
