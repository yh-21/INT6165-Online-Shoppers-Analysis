# INT6165 在线购物购买率分析

> 本项目比较在线购物数据中的新访客与回访者：每次访问的购买比例是否不同、相差多少，以及分组后差异是否仍在。

数据来自 [UCI Online Shoppers Purchasing Intention Dataset](https://archive.ics.uci.edu/dataset/468/online+shoppers+purchasing+intention+dataset)。逐步解释、公式和完整结果见 [RESULTS.md](RESULTS.md)。

| 课程项目 | 分析主题 | 主要工具 | 研究对象 |
|---|---|---|---|
| INT6165 | 购买率与统计比较 | Python · pandas | 新访客与回访者 |

### 快速导航

[结论摘要](#先看结论) · [数据说明](#数据是什么) · [项目结构](#文件夹结构) · [运行方法](#如何运行) · [技术与限制](#技术栈)

---

## 先看结论

| 指标 | 新访客 | 回访者 |
|---|---:|---:|
| 访问会话数 | 1,694 | 10,551 |
| 购买会话数 | 422 | 1,470 |
| 购买率 | **24.91%** | **13.93%** |
| Wilson 95% 置信区间 | 22.91%–27.03% | 13.28%–14.61% |

新访客减回访者的购买率差为 **10.98 个百分点**，Newcombe 95% 区间为 **8.87–13.19 个百分点**。双侧两组比例检验得到 Z=11.6053、p=3.87×10⁻³¹，数据支持两组购买率存在统计差异。

> **如何解读：**这说明这份数据中两类**访问会话的购买比例不同**，不证明访客类型导致差异。数据是观察性记录，且没有用户编号来识别独立用户。

![新访客与回访者购买率对比](outputs/charts/purchase_rate_bar.svg)

[购买率区间图](outputs/charts/stage2_purchase_rate_ci.svg) · [差值区间图](outputs/charts/stage2_difference_ci.svg) · [页面浏览量分组图](outputs/charts/stage2_productrelated.svg)

---

## 数据是什么？

数据集有 12,330 条访问会话、18 个字段。一行代表一次访问，不一定是一个不同的人；一个人可能多次访问。

| 字段 | 白话解释 | 用途 |
|---|---|---|
| `VisitorType` | 新访客、回访者或 Other | 区分组别 |
| `Revenue` | 本次是否购买；True 是，False 否 | 计算购买次数 |
| `ProductRelated` | 本次浏览的产品相关页面数 | 延伸分组比较 |

**购买率 = 购买会话数 ÷ 访问会话数。**例如新访客 422/1,694=24.91%，表示每 100 次新访客访问约有 25 次购买，不是独立用户购买比例。

检查发现 0 个缺失值、125 条完全相同记录。主分析保留重复记录，因为内容相同不等于确认记录错误；另做去重敏感性分析。Other 有 85 次访问、16 次购买，保留在数据中，但不纳入新访客与回访者的两组比较。

---

## 文件夹结构

```text
data/raw/online_shoppers_intention.csv  原始数据，程序不会修改
src/analyze_shoppers.py                 分析和作图程序
outputs/charts/                         SVG 图；部分早期图另有 PNG
outputs/tables/                         CSV 结果表，可用 Excel/Numbers 打开
README.md                               项目介绍与运行方法
RESULTS.md                              详细步骤、公式、结果和限制
requirements.txt                        Python 依赖清单
MarkingStandard.pdf                     课程评分标准
```

本机的 `.venv/` 是项目专用 Python 环境，其他电脑要各自创建。图表、表格只保存在本地，不会自动出现在飞书；放进飞书或幻灯片需要上传/插入。

### 图表速查

| 图表文件 | 展示内容 |
|---|---|
| `purchase_rate_bar.svg` | 两类访客购买率 |
| `purchase_rate_difference.svg` | 两组购买率差（百分点） |
| `visitor_sessions.svg` | 各类型访问次数 |
| `stage2_purchase_rate_ci.svg` | 购买率和各自的 95% 区间 |
| `stage2_difference_ci.svg` | 差值及其 95% 区间 |
| `stage2_productrelated.svg` | 按产品相关页面数分组的购买率 |
| `stage2_raw_vs_standardized.svg` | 原始差值与标准化差值 |

主要结果表包括 `purchase_rate_by_visitor.csv`、`data_quality_summary.csv`、`missing_values_by_field.csv`；阶段二的置信区间、检验、分组、标准化和重复记录敏感性结果均在 `outputs/tables/`，详细说明见 [RESULTS.md](RESULTS.md)。

---

## 如何运行？

用 VS Code 打开项目文件夹，选择“终端 → 新建终端”。确认终端当前目录是项目根目录（能看到 `src`、`data`、`outputs`）。

### 已有环境（Mac）

```bash
.venv/bin/python src/analyze_shoppers.py
```

### 第一次运行或重建环境（Mac）

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python src/analyze_shoppers.py
```

1. 第一行在项目中建独立 Python 环境，不影响其他项目。
2. 第二行安装依赖清单中的套件。
3. 第三行运行分析程序。

平时不需要重复安装，直接运行第三行即可。Windows 可使用：

```powershell
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe src\analyze_shoppers.py
```

程序读取原始 CSV，更新 `outputs/tables/` 中的 CSV 和 `outputs/charts/` 中的 SVG，不修改原始数据。已有 PNG 不会自动更新；使用 PNG 前要确认它和当前结果一致。

---

## 技术栈

Python 3 运行程序；pandas 读取及汇总 CSV；Python 标准库做数学与统计计算并生成 SVG。CSV 可用表格软件打开，SVG 放大时仍清晰。**这是统计分析项目，没有训练机器学习预测模型。**

---

## 解读时的限制

- 统计单位是访问会话，不是已确认的独立用户。
- 访客类型不是随机分配的，关联不能证明因果。
- 无法断定完全相同记录一定是错误数据。
- ProductRelated 是访问期间形成的行为，分组与标准化只是描述性比较，不是因果控制。
- 结论针对本数据集，不能直接推广到所有网站或时期。

建议先看本文件的结论，再按 [RESULTS.md](RESULTS.md) 的顺序理解计算和解释。

---

*INT6165 · Online Shoppers Purchase Rate Analysis*
