# ARKHÉ Statistical Analysis Plan (SAP)

## 1. Study Rationale & Research Hypotheses

Autonomous AI agents executing multi-step tool calls encounter complex operational contexts. Defensive mechanisms that evaluate individual events in isolation (e.g., regex patterns, single-event LLM guardrails) suffer from high false positive rates when agents perform authorized exploratory steps (such as verifying permissions or reading configuration files) that mimic malicious reconnaissance.

### Primary Hypothesis ($H_1$ — False Positive Mitigation)
$$\begin{cases}
H_{1,0}: & FP_{\text{arkhe}} \ge FP_{\text{baseline}} \quad \text{or} \quad \text{Recall}_{\text{arkhe}} < \text{Recall}_{\text{baseline}} \\
H_{1,A}: & FP_{\text{arkhe}} < FP_{\text{baseline}} \quad \text{and} \quad \text{Recall}_{\text{arkhe}} \ge \text{Recall}_{\text{baseline}}
\end{cases}$$
*Operational statement:* Trajectory-aware observability significantly reduces false positive classifications on complex benign and near-violation trajectories without sacrificing detection sensitivity (recall) on true boundary breaches.

### Secondary Hypothesis ($H_2$ — Early Boundary Anticipation)
$$\begin{cases}
H_{2,0}: & N_{\text{lead}}(\text{ARKHÉ}) \le N_{\text{lead}}(\text{baseline}) \\
H_{2,A}: & N_{\text{lead}}(\text{ARKHÉ}) > N_{\text{lead}}(\text{baseline})
\end{cases}$$
*Operational statement:* Trajectory tracking detects mission drift and adversarial ingress steps before an irreversible boundary violation occurs ($N_{\text{lead}} > 0$).

---

## 2. Primary Metrics & Interval Estimation

### 2.1 Wilson Score Confidence Intervals (Proportions)
For binomial proportions $\hat{p} = \frac{k}{n}$ (Precision, Recall, Specificity, Accuracy), normal approximations fail when sample sizes are small or proportions approach $0.0$ or $1.0$. ARKHÉ implements the Wilson score interval with continuity bounds:

$$w = \frac{\hat{p} + \frac{z^2}{2n} \pm z \sqrt{\frac{\hat{p}(1 - \hat{p})}{n} + \frac{z^2}{4n^2}}}{1 + \frac{z^2}{n}}$$

Where $z = 1.95996$ for the two-sided 95% confidence level.

### 2.2 Non-Parametric Bootstrap Confidence Intervals (Lead Steps)
Anticipation lead steps $N_{\text{lead}} = \max(0, \text{step}_{\text{violation}} - \text{step}_{\text{first\_alert}})$ follow a non-normal, right-skewed discrete distribution with a point mass at zero.
- **Statistic of Interest:** Sample Median $M$ and Mean $\mu$.
- **Bootstrap Method:** $B = 2{,}000$ non-parametric resamples with replacement.
- **Interval Bounds:** Percentile bootstrap confidence interval $[\theta^*_{\alpha/2}, \theta^*_{1 - \alpha/2}]$ at $\alpha = 0.05$.

---

## 3. Paired Hypothesis Testing Framework

Because all detectors evaluate identical trajectories within the benchmark, independent samples tests (e.g. standard two-sample t-test or chi-square test of independence) are statistically invalid. ARKHÉ employs paired tests.

### 3.1 McNemar Test for Paired Classification Discordance
For paired binary classification accuracy between ARKHÉ and a baseline:

| | Baseline Correct | Baseline Incorrect |
| :--- | :---: | :---: |
| **ARKHÉ Correct** | $a$ (Both correct) | $b$ (ARKHÉ correct, Baseline failed) |
| **ARKHÉ Incorrect** | $c$ (ARKHÉ failed, Baseline correct) | $d$ (Both failed) |

#### Exact Binomial Test (Default for small samples $b+c < 25$):
Under the null hypothesis $H_0: p_b = p_c = 0.5$, the discordant pair count $b$ follows:
$$b \sim \text{Binomial}(n = b + c, p = 0.5)$$
The two-tailed exact p-value is computed as:
$$p = \sum_{k: \left|k - \frac{b+c}{2}\right| \ge \left|b - \frac{b+c}{2}\right|} \binom{b+c}{k} \left(\frac{1}{2}\right)^{b+c}$$

#### Continuity-Corrected $\chi^2$ (Asymptotic for $b+c \ge 25$):
$$\chi^2 = \frac{(|b - c| - 1)^2}{b + c}, \quad \text{df} = 1$$

#### Odds Ratio:
$$\text{OR} = \frac{b}{c}$$

### 3.2 Wilcoxon Signed-Rank Test (Paired Anticipation Steps)
To evaluate whether ARKHÉ provides systematically earlier warning than baseline detectors on identical breach trajectories, we analyze differences:
$$D_i = N_{\text{lead}, i}(\text{ARKHÉ}) - N_{\text{lead}, i}(\text{Baseline})$$
- Zero differences are excluded.
- Absolute differences $|D_i|$ are ranked with average ranks assigned to ties.
- Signed rank sums $W^+$ and $W^-$ are evaluated.
- For $n \ge 5$, asymptotic normal approximation is applied with continuity correction:
  $$Z = \frac{W^+ - \frac{n(n+1)}{4}}{\sqrt{\frac{n(n+1)(2n+1)}{24}}}$$

---

## 4. Multiplicity & Small Sample Protocol

1. **Pilot Phase Caution ($n=30$):**
   In small pilot samples, statistical power is constrained. Wilson score intervals and exact binomial tests are explicitly reported alongside confidence intervals rather than declaring premature definitive superiority.
2. **Expansion to Full Benchmark ($N=300$):**
   Full grant candidate evaluation scales to $N=300$ across 5 attack families, providing statistical power $(1 - \beta) > 0.90$ to detect an absolute reduction of $\ge 15\%$ in False Positive rate at $\alpha = 0.01$.
3. **No Fabricated Statistics:**
   All test statistics, p-values, and confidence intervals are computed at runtime by `evaluator/evaluate.py` directly from `predictions.jsonl` and `datasets/ground_truth/`. No statistical output is hardcoded.
