# Monte Carlo 壓力測試數學公式說明

---

## 一、投資組合參數設定

設儲備資產由 $n = 5$ 種資產構成，資產集合為：

$$\mathcal{A} = \{\text{USD Bonds},\ \text{EUR Bonds},\ \text{JPY Bonds},\ \text{GBP Bonds},\ \text{Gold}\}$$

**年化期望報酬向量：**

$$\boldsymbol{\mu} = [\mu_1, \mu_2, \ldots, \mu_n]^\top \in \mathbb{R}^n$$

**年化波動率向量：**

$$\boldsymbol{\sigma} = [\sigma_1, \sigma_2, \ldots, \sigma_n]^\top \in \mathbb{R}^n$$

**相關係數矩陣：**

$$\mathbf{P} = [\rho_{ij}]_{n \times n}, \quad \rho_{ij} \in [-1, 1],\ \rho_{ii} = 1$$

**年化共變異數矩陣（Covariance Matrix）：**

$$\boldsymbol{\Sigma} = \boldsymbol{\sigma}\boldsymbol{\sigma}^\top \odot \mathbf{P}$$

其中 $\odot$ 表示 Hadamard（逐元素）乘積，即：

$$\Sigma_{ij} = \sigma_i \cdot \sigma_j \cdot \rho_{ij}$$

---

## 二、投資組合權重

定義投資組合權重向量 $\mathbf{w} \in \mathbb{R}^n$，滿足：

$$\sum_{i=1}^{n} w_i = 1, \quad w_i \geq 0$$

本文比較兩組配置：

| 投資組合 | 黃金配置 | 權重向量 $\mathbf{w}$ |
|---------|---------|----------------------|
| 現行 (Current) | 3% | $[0.60,\ 0.15,\ 0.12,\ 0.10,\ 0.03]^\top$ |
| 提議 (Proposed) | 8% | $[0.55,\ 0.14,\ 0.11,\ 0.12,\ 0.08]^\top$ |

---

## 三、月度參數轉換

將年化參數轉換為月度參數（模擬步長 $\Delta t = 1/12$ 年）：

$$\boldsymbol{\mu}^{(m)} = \frac{\boldsymbol{\mu}}{12}$$

$$\boldsymbol{\Sigma}^{(m)} = \frac{\boldsymbol{\Sigma}}{12}$$

---

## 四、Cholesky 分解

對月度共變異數矩陣進行 Cholesky 分解，以生成相關隨機變數：

$$\boldsymbol{\Sigma}^{(m)} = \mathbf{L}\mathbf{L}^\top$$

其中 $\mathbf{L} \in \mathbb{R}^{n \times n}$ 為下三角矩陣。

---

## 五、隨機報酬生成（Student-$t$ 肥尾模型）

為捕捉金融報酬之**肥尾特性（Fat Tails）**，創新項採用自由度 $\nu = 5$ 的多元 Student-$t$ 分佈，而非標準常態分佈。

**第 $s$ 次模擬、第 $m$ 個月的資產報酬向量：**

$$\mathbf{r}_{s,m} = \boldsymbol{\mu}^{(m)} + \mathbf{L}\,\mathbf{z}_{s,m}$$

其中隨機創新向量：

$$\mathbf{z}_{s,m} \sim t(\nu),\quad z_{i,s,m} \overset{\text{i.i.d.}}{\sim} t_\nu, \quad \nu = 5$$

即每個分量獨立抽自自由度 $\nu=5$ 的 Student-$t$ 分佈，再經 Cholesky 矩陣 $\mathbf{L}$ 引入截面相關性。

---

## 六、投資組合報酬模擬

**第 $s$ 次模擬、第 $m$ 個月的投資組合報酬率：**

$$R_{s,m} = \mathbf{w}^\top \mathbf{r}_{s,m} = \sum_{i=1}^{n} w_i\, r_{i,s,m}$$

**12 個月期末累積報酬（複利）：**

$$V_s = \prod_{m=1}^{T}(1 + R_{s,m}) - 1, \quad T = 12$$

對 $s = 1, 2, \ldots, S$（本文 $S = 100{,}000$）重複以上步驟，得到報酬分配：

$$\{V_s\}_{s=1}^{S}$$

---

## 七、風險值（Value at Risk, VaR）

在信賴水準 $\alpha$（本文取 $\alpha \in \{95\%, 99\%\}$）下，**投資組合損失**的 VaR 定義為：

$$\text{VaR}_\alpha = -\inf\left\{x : P(V_s \leq x) \geq 1-\alpha \right\} = -Q_{1-\alpha}\!\left(\{V_s\}\right)$$

以 $S$ 條模擬路徑之百分位數估計：

$$\widehat{\text{VaR}}_\alpha = -\text{percentile}\!\left(\{V_s\},\ (1-\alpha)\times 100\right)$$

等價地，$\text{VaR}_{95\%}$ 對應第 5 百分位數，$\text{VaR}_{99\%}$ 對應第 1 百分位數。

以絕對金額表示：

$$\text{VaR}_\alpha^{\$} = \widehat{\text{VaR}}_\alpha \times W_0$$

其中 $W_0 = \$600\text{ billion}$ 為儲備總規模。

---

## 八、條件風險值（Conditional VaR / Expected Shortfall）

CVaR（又稱 Expected Shortfall, ES）衡量**超過 VaR 門檻的尾端平均損失**：

$$\text{CVaR}_\alpha = -\mathbb{E}\!\left[V_s \mid V_s \leq Q_{1-\alpha}\!\left(\{V_s\}\right)\right]$$

以樣本估計：

$$\widehat{\text{CVaR}}_\alpha = -\frac{1}{|\mathcal{T}_\alpha|}\sum_{s \in \mathcal{T}_\alpha} V_s$$

其中尾端集合：

$$\mathcal{T}_\alpha = \left\{s : V_s \leq \text{percentile}\!\left(\{V_s\},\ (1-\alpha)\times 100\right)\right\}$$

---

## 九、確定性情境分析（Deterministic Stress Testing）

對情境 $k$，定義衝擊向量 $\boldsymbol{\delta}^{(k)} \in \mathbb{R}^n$，各元素為各資產在該情境下的即時報酬率。

**投資組合衝擊損益：**

$$\Pi^{(k)} = \mathbf{w}^\top \boldsymbol{\delta}^{(k)} \cdot W_0 = \sum_{i=1}^{n} w_i\, \delta_i^{(k)} \cdot W_0$$

**提議組合相較現行組合之增益：**

$$\Delta\Pi^{(k)} = \Pi_{\text{proposed}}^{(k)} - \Pi_{\text{current}}^{(k)} = \left(\mathbf{w}_{\text{proposed}} - \mathbf{w}_{\text{current}}\right)^\top \boldsymbol{\delta}^{(k)} \cdot W_0$$

---

## 十、模擬流程總覽

$$\boxed{
\begin{aligned}
&\textbf{For } s = 1 \text{ to } S: \\
&\quad V_s^{(0)} \leftarrow 1 \\
&\quad \textbf{For } m = 1 \text{ to } T: \\
&\quad\quad \mathbf{z}_{s,m} \sim t_\nu^{\otimes n} \\
&\quad\quad \mathbf{r}_{s,m} = \boldsymbol{\mu}^{(m)} + \mathbf{L}\,\mathbf{z}_{s,m} \\
&\quad\quad R_{s,m} = \mathbf{w}^\top \mathbf{r}_{s,m} \\
&\quad\quad V_s^{(m)} = V_s^{(m-1)} \cdot (1 + R_{s,m}) \\
&\quad V_s = V_s^{(T)} - 1 \\
&\textbf{Output: } \{V_s\}_{s=1}^{S} \rightarrow \widehat{\text{VaR}}_\alpha,\ \widehat{\text{CVaR}}_\alpha
\end{aligned}
}$$
