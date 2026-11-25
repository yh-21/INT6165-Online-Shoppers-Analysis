"""补充分析：ProductRelated 分组、Logistic 回归与 Beta-二项贝叶斯分析。

运行位置：项目根目录
命令：.venv/bin/python src/analyze_supplementary.py
输出：outputs/tables/ 与 outputs/charts/
"""
from pathlib import Path
import os
import warnings

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "data" / "raw" / "online_shoppers_intention.csv"
TABLES = ROOT / "outputs" / "tables"
CHARTS = ROOT / "outputs" / "charts"
TABLES.mkdir(parents=True, exist_ok=True)
CHARTS.mkdir(parents=True, exist_ok=True)
os.environ.setdefault("MPLCONFIGDIR", str(ROOT / ".matplotlib"))

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
import statsmodels.api as sm
from statsmodels.stats.proportion import proportion_confint
from scipy.stats import beta
from scipy.integrate import quad, IntegrationWarning
from scipy.optimize import brentq

VISITOR_TYPES = ["New_Visitor", "Returning_Visitor"]
VISITOR_NAMES = ["新访客", "回访者"]
COLORS = ["#087e8b", "#d97930"]
GROUP_LABELS = ["0–7", "8–18", "19–38", "≥39"]

available_fonts = {font.name for font in font_manager.fontManager.ttflist}
chinese_fonts = [name for name in ["Microsoft YaHei", "SimHei", "Noto Sans CJK SC"] if name in available_fonts]
plt.rcParams["font.sans-serif"] = chinese_fonts + ["DejaVu Sans"]
plt.rcParams["axes.unicode_minus"] = False
plt.rcParams.update({"font.size": 11, "axes.spines.top": False, "axes.spines.right": False})


def save_figure(fig, filename):
    """将图表同时保存为适合插入文档的 PNG 和适合放大的 SVG。"""
    fig.savefig(CHARTS / f"{filename}.png", dpi=220, bbox_inches="tight")
    fig.savefig(CHARTS / f"{filename}.svg", bbox_inches="tight")
    plt.close(fig)


def load_analysis_data():
    """读取项目原始数据，并准备两个补充分析共同使用的字段。"""
    raw = pd.read_csv(INPUT)
    data = raw[raw["VisitorType"].isin(VISITOR_TYPES)].copy()
    data["is_new"] = data["VisitorType"].eq(VISITOR_TYPES[0]).astype(int)
    data["purchased"] = data["Revenue"].astype(int)
    if len(data) != 12245:
        raise ValueError(f"预期两类访客共 12,245 条会话，实际为 {len(data):,} 条。")
    return data


def product_page_groups(data):
    """按合并样本四分位点分组，输出购买率和 Wilson 区间。"""
    quartiles = data["ProductRelated"].quantile([0.25, 0.5, 0.75]).astype(int).tolist()
    if quartiles != [7, 18, 38]:
        raise ValueError(f"ProductRelated 四分位点与报告记录不一致：{quartiles}")
    edges = [-np.inf, *quartiles, np.inf]
    data = data.copy()
    data["product_group"] = pd.cut(data["ProductRelated"], bins=edges, labels=GROUP_LABELS)

    rows = []
    for group in GROUP_LABELS:
        for visitor_type, visitor_name, color in zip(VISITOR_TYPES, VISITOR_NAMES, COLORS):
            cell = data[(data["product_group"] == group) & (data["VisitorType"] == visitor_type)]
            sessions = len(cell)
            purchases = int(cell["purchased"].sum())
            low, high = proportion_confint(purchases, sessions, method="wilson")
            rows.append({
                "product_group": group,
                "visitor_type": visitor_type,
                "label": visitor_name,
                "n": sessions,
                "purchases": purchases,
                "nonpurchases": sessions - purchases,
                "rate": purchases / sessions,
                "ci_low": low,
                "ci_high": high,
                "sparse": sessions < 30 or min(purchases, sessions - purchases) < 5,
            })

    result = pd.DataFrame(rows)
    result.to_csv(TABLES / "stage2_productrelated_detail.csv", index=False, encoding="utf-8-sig")

    fig, ax = plt.subplots(figsize=(10, 5.6), layout="constrained")
    for i, (visitor_type, visitor_name, color) in enumerate(zip(VISITOR_TYPES, VISITOR_NAMES, COLORS)):
        subset = result[result["visitor_type"] == visitor_type]
        xs = np.arange(len(GROUP_LABELS)) + (i - 0.5) * 0.25
        rates = subset["rate"].to_numpy() * 100
        lows = subset["ci_low"].to_numpy() * 100
        highs = subset["ci_high"].to_numpy() * 100
        ax.errorbar(xs, rates, yerr=[rates - lows, highs - rates], fmt="o-", capsize=5,
                    color=color, label=visitor_name)
        for x, row in zip(xs, subset.itertuples()):
            ax.text(x, row.ci_high * 100 + 1.2, f"{row.rate:.1%}\n{row.purchases}/{row.n:,}",
                    ha="center", color=color, fontsize=9)
    ax.set(xticks=range(len(GROUP_LABELS)), xticklabels=GROUP_LABELS, ylim=(0, 50),
           ylabel="购买率（%）", xlabel="产品相关页面浏览量分组",
           title="相近浏览量组内的新访客与回访者购买率（Wilson 95% 区间）")
    ax.legend(loc="upper left")
    ax.yaxis.grid(alpha=0.2)
    save_figure(fig, "stage2_productrelated_detail")
    return result


def logistic_models(data):
    """拟合两种预先指定的 Logistic 调整模型，并导出系数与诊断。"""
    model_data = data.copy()
    model_data["product_group"] = pd.cut(
        model_data["ProductRelated"], [-np.inf, 7, 18, 38, np.inf], labels=GROUP_LABELS
    )
    designs = {
        "group_adjusted": sm.add_constant(pd.concat([
            model_data[["is_new"]],
            pd.get_dummies(model_data["product_group"], prefix="group", drop_first=True, dtype=float),
        ], axis=1)).astype(float),
        "log1p_adjusted": sm.add_constant(pd.DataFrame({
            "is_new": model_data["is_new"],
            "log1p_ProductRelated": np.log1p(model_data["ProductRelated"]),
        })).astype(float),
    }
    coefficient_rows, diagnostic_rows = [], []
    for model_name, design in designs.items():
        fitted = sm.Logit(model_data["purchased"], design).fit(disp=False, maxiter=100)
        if not fitted.mle_retvals["converged"]:
            raise RuntimeError(f"Logistic 模型未收敛：{model_name}")
        score = float(np.max(np.abs(fitted.model.score(fitted.params))))
        if score >= 1e-7:
            raise RuntimeError(f"Logistic 模型梯度检查未通过：{model_name}，最大绝对值={score}")
        for term in design.columns:
            low, high = fitted.conf_int().loc[term]
            coefficient_rows.append({
                "model": model_name,
                "term": str(term),
                "coefficient": fitted.params[term],
                "standard_error": fitted.bse[term],
                "odds_ratio": np.exp(fitted.params[term]),
                "or_ci_low": np.exp(low),
                "or_ci_high": np.exp(high),
                "p_value": fitted.pvalues[term],
            })
        diagnostic_rows.append({
            "model": model_name, "converged": True, "sessions": int(fitted.nobs),
            "log_likelihood": fitted.llf, "max_abs_score": score,
        })

    pd.DataFrame(coefficient_rows).to_csv(TABLES / "stage2_logistic_coefficients.csv", index=False, encoding="utf-8-sig")
    pd.DataFrame(diagnostic_rows).to_csv(TABLES / "stage2_logistic_diagnostics.csv", index=False, encoding="utf-8-sig")
    return coefficient_rows


def beta_binomial_analysis(data):
    """计算两组购买率后验、差值可信区间和先验敏感性。"""
    posterior_rows, comparison_rows = [], []
    prior_specs = [("Uniform", 1.0, 1.0), ("Jeffreys", 0.5, 0.5)]
    for prior_name, prior_a, prior_b in prior_specs:
        distributions = []
        for visitor_type, visitor_name in zip(VISITOR_TYPES, VISITOR_NAMES):
            cell = data[data["VisitorType"] == visitor_type]
            sessions = len(cell)
            purchases = int(cell["purchased"].sum())
            posterior = beta(prior_a + purchases, prior_b + sessions - purchases)
            low, high = posterior.ppf([0.025, 0.975])
            posterior_rows.append({
                "prior": prior_name, "visitor_type": visitor_type, "label": visitor_name,
                "prior_alpha": prior_a, "prior_beta": prior_b,
                "n": sessions, "purchases": purchases,
                "alpha": prior_a + purchases, "beta": prior_b + sessions - purchases,
                "posterior_mean": posterior.mean(), "credible_low": low, "credible_high": high,
            })
            distributions.append(posterior)

        new, returning = distributions
        points = sorted(set([0.0, 1.0] + [float(np.clip(returning.mean() + k * returning.std(), 0, 1))
                                           for k in [-10, -5, 0, 5, 10]]))

        def difference_cdf(delta, tight=False):
            return quad(lambda r: returning.pdf(r) * new.cdf(r + delta), 0, 1, points=points,
                        epsabs=1e-55 if tight else 1e-10, epsrel=1e-9, limit=300)

        with warnings.catch_warnings():
            warnings.simplefilter("error", IntegrationWarning)
            lower = brentq(lambda value: difference_cdf(value)[0] - 0.025, -1, 1, xtol=1e-12)
            upper = brentq(lambda value: difference_cdf(value)[0] - 0.975, -1, 1, xtol=1e-12)
            reverse_probability, integration_error = difference_cdf(0, tight=True)
            alternate, _ = quad(lambda n: new.pdf(n) * returning.sf(n), 0, 1, points=points,
                                epsabs=1e-55, epsrel=1e-9, limit=300)
        if integration_error / reverse_probability >= 1e-6 or not np.isclose(alternate / reverse_probability, 1, rtol=1e-8):
            raise RuntimeError(f"后验差值积分精度检查未通过：{prior_name}")
        comparison_rows.append({
            "prior": prior_name,
            "posterior_mean_difference": new.mean() - returning.mean(),
            "credible_low": lower,
            "credible_high": upper,
            "probability_new_le_returning": reverse_probability,
            "integration_error": integration_error,
        })

    posteriors = pd.DataFrame(posterior_rows)
    comparisons = pd.DataFrame(comparison_rows)
    posteriors.to_csv(TABLES / "stage2_bayesian_posteriors.csv", index=False, encoding="utf-8-sig")
    comparisons.to_csv(TABLES / "stage2_bayesian_comparisons.csv", index=False, encoding="utf-8-sig")

    rng = np.random.default_rng(20261124)
    uniform = posteriors[posteriors["prior"] == "Uniform"]
    simulated_difference = rng.beta(uniform.iloc[0].alpha, uniform.iloc[0].beta, 1_000_000) - \
        rng.beta(uniform.iloc[1].alpha, uniform.iloc[1].beta, 1_000_000)
    simulated_interval = np.quantile(simulated_difference, [0.025, 0.975])
    reported_interval = comparisons.iloc[0][["credible_low", "credible_high"]].to_numpy(dtype=float)
    if np.max(np.abs(simulated_interval - reported_interval)) >= 0.0003:
        raise RuntimeError("贝叶斯差值区间与固定随机种子的抽样核对差异过大。")

    main = posteriors[posteriors["prior"] == "Uniform"]
    fig, ax = plt.subplots(figsize=(9, 4.5), layout="constrained")
    grid = np.linspace(0.10, 0.31, 1000)
    for row, color in zip(main.itertuples(), COLORS):
        ax.plot(grid * 100, beta.pdf(grid / 100, row.alpha, row.beta),
                color=color, label=f"{row.label}：Beta({row.alpha:g}, {row.beta:g})")
        inside = (grid / 100 >= row.credible_low) & (grid / 100 <= row.credible_high)
        ax.fill_between(grid, beta.pdf(grid / 100, row.alpha, row.beta),
                        where=inside, alpha=0.2, color=color)
    ax.set(xlabel="购买率（%）", ylabel="后验密度", title="新访客与回访者购买率的后验分布（均匀先验）")
    ax.legend()
    ax.text(0.02, 0.72, "阴影：各组 95% 等尾后验可信区间", transform=ax.transAxes, fontsize=10)
    save_figure(fig, "stage2_bayesian_posteriors")

    fig, ax = plt.subplots(figsize=(9, 3.7), layout="constrained")
    for i, row in enumerate(comparisons.itertuples()):
        mean = row.posterior_mean_difference * 100
        ax.errorbar(mean, i, xerr=[[mean - row.credible_low * 100], [row.credible_high * 100 - mean]],
                    fmt="o", capsize=6, color=COLORS[i])
        ax.text(mean, i + 0.17,
                f"{mean:.2f}；95% 可信区间 [{row.credible_low*100:.2f}, {row.credible_high*100:.2f}]",
                ha="center", fontsize=9)
    ax.axvline(0, color="#888", linestyle="--")
    ax.set(yticks=[0, 1], yticklabels=["均匀先验 Beta(1,1)", "Jeffreys 先验 Beta(0.5,0.5)"],
           ylim=(-0.5, 1.6), xlim=(-1, 16), xlabel="新访客 − 回访者（百分点）",
           title="购买率差值后验区间与先验敏感性")
    save_figure(fig, "stage2_bayesian_difference")


def main():
    data = load_analysis_data()
    groups = product_page_groups(data)
    coefficients = logistic_models(data)
    beta_binomial_analysis(data)
    print(f"补充分析完成：{len(data):,} 条新访客与回访者会话")
    print(f"分组结果：{TABLES / 'stage2_productrelated_detail.csv'}")
    print(f"Logistic 系数：{TABLES / 'stage2_logistic_coefficients.csv'}")
    print(f"贝叶斯结果：{TABLES / 'stage2_bayesian_posteriors.csv'}")
    print(f"图表目录：{CHARTS}")


if __name__ == "__main__":
    main()
