# INT6165 在线购物购买率分析

比较新访客与回访者的购买率。数据来自 [UCI Online Shoppers Purchasing Intention Dataset](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset)。

## 目录

```text
src/analyze_shoppers.py                 分析程序
 data/raw/online_shoppers_intention.csv  原始数据（保留不改）
outputs/charts/                         图表（PNG 便于插入，SVG 便于放大）
outputs/tables/                         结果数据表（CSV）
README.md                               本文件：项目说明与运行方法
RESULTS.md                              阶段分析结果、公式、解释与局限
requirements.txt                        Python 依赖
MarkingStandard.pdf                     课程评分标准
```

## 运行

在项目根目录运行：

```bash
.venv/bin/python src/analyze_shoppers.py
```

需要重建环境时运行：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

程序使用 pandas 和 Python 标准库。运行后会更新 `outputs/tables/` 中的 CSV 与 `outputs/charts/` 中的 SVG，不会修改原始 CSV；PNG 图片不会自动更新。

## 主要结果

新访客购买率为 422/1,694 = 24.91%，回访者为 1,470/10,551 = 13.93%，相差 10.98 个百分点。区间、检验、分组结果和解释见 [RESULTS.md](RESULTS.md)。数据以访问会话为单位，观察到的差异不能证明因果关系。

## 输出文件速查

图表：`visitor_sessions`（访客数量）、`purchase_rate_bar`（购买率）、`purchase_rate_difference`（率差）、`stage2_purchase_rate_ci`（购买率区间）、`stage2_difference_ci`（率差区间）、`stage2_productrelated`（浏览量分组）、`stage2_raw_vs_standardized`（标准化比较）。除阶段二图外，前期图同时有 PNG 与 SVG。

数据表：`purchase_rate_by_visitor.csv`、`data_quality_summary.csv`、`missing_values_by_field.csv`；阶段二另有 `stage2_confidence_intervals.csv`、`stage2_test.csv`、`stage2_productrelated_groups.csv`、`stage2_group_weights.csv`、`stage2_standardized.csv`、`stage2_duplicate_sensitivity.csv`。
