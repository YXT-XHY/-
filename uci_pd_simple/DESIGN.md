# 程序设计说明（UCI 最简基线）

## 1. 目标与非目标

**目标**
- 在单机上跑通 UCI 帕金森语音数据的二分类：195 条录音、22 维特征。
- 评估必须按 **subject** 分组，避免同一人的多条录音同时进训练/测试。
- 输出可解释的模型（22 个系数 + 截距）和可复现的指标。
- 只依赖 `numpy` + `pandas`，不依赖 sklearn、数据库、Web 框架。

**非目标**
- 不做临床诊断、不做早期筛查声称。
- 不做原始音频处理（UCI 提供的是特征表）。
- 不做深度学习、不做超参数大规模搜索。
- 不做多中心/外部验证（当前数据不允许）。

## 2. 约束

| 约束 | 影响 |
|---|---|
| 195 行、32 个 subject（文件实际值） | 模型必须小而正则化强；评估必须重复 |
| 8 例健康对照 | 特异度估计很不稳定；不能只报 accuracy |
| 22 维特征量纲差异大 | 必须先标准化 |
| 同一 subject 6–7 条录音 | 严禁按行随机切分 |
| 运行环境只保证 numpy/pandas | 自己实现逻辑回归、AUC、分组 CV |

## 3. 总体架构

```text
[data/parkinsons.data]
        │
        ▼
[core.load_data]───校验列/缺失/标签/解析 subject
        │
        ├──────────────► [core.summary] ──► CLI summary
        │
        ▼
[core.cross_validate]
   │  make_subject_folds（分层、按 subject）
   │  for each fold: fit_on_subset → predict_proba
   │  重复 N 次 → metrics
   ▼
[core.random_row_split_check]（仅泄漏对照，不用于报告）
        │
        ▼
[core.fit_on_subset] ──► Standardizer + LogisticRegression
        │
        ▼
[core.save_model] ──► artifacts/model.json
        │
        ▼
[core.predict_frame] ──► CLI predict ──► CSV（probability / risk_band）
```

**分层：** 数据层（CSV）→ 校验层（load_data）→ 评估层（cross_validate）→ 模型层（Standardizer + LogisticRegression）→ 产物层（JSON）→ 接口层（CLI）。没有服务端、没有数据库、没有后台任务。

## 4. 模块与接口

### `core.py`

| 函数/类 | 职责 | 输入 → 输出 |
|---|---|---|
| `load_data(path)` | 读取、校验、解析 subject | CSV → DataFrame（195×25，含 subject） |
| `summarize(df)` | 数据概览 | DataFrame → dict |
| `Standardizer` | 训练集均值/标准差标准化 | `fit(X)`, `transform(X)` |
| `LogisticRegression` | L2 逻辑回归（IRLS） | `fit(X,y)`, `predict_proba(X)` |
| `roc_auc(y,p)` | 成对比较、处理并列 | 向量 → float |
| `compute_metrics(y,p,threshold)` | AUC/敏感度/特异度/F1/Brier/混淆矩阵 | 向量 → dict |
| `calibration_table(y,p,bins)` | 校准分箱 | 向量 → list |
| `make_subject_folds(df,n_splits,seed)` | 分层、按 subject 分折 | DataFrame → list[list[subject]] |
| `fit_on_subset(df,mask,l2)` | 在一个子集上拟合 | DataFrame + mask → (scaler, model) |
| `cross_validate(...)` | 重复分组 CV + OOF | DataFrame → (metrics_df, oof_df) |
| `random_row_split_check(...)` | 错误切分对照 | DataFrame → metrics_df |
| `save_model/load_model` | JSON 持久化 | 路径 ↔ dict |
| `predict_frame(df,payload)` | 对新数据打分 | DataFrame → DataFrame（probability/risk_band） |

### `app.py`

| 子命令 | 作用 | 主要输出 |
|---|---|---|
| `summary` | 数据概览 | 终端 JSON + 每 subject 录音数 |
| `evaluate` | 重复分组 CV + 泄漏对照 | `cv_summary.json`、`cv_metrics.csv`、`oof_predictions.csv` |
| `train` | 全量拟合 + 评估 + 保存 | `model.json`、`model_card.json`、CV 产物 |
| `predict` | 加载模型对新 CSV 打分 | `predictions.csv`；若含 status 则附 in-sample 指标警告 |

## 5. 数据契约

**输入 CSV 必需列：**

- `name`：录音 ID，格式 `phon_R01_S01_1`，用于解析 subject。
- `status`：1 = PD，0 = HC（训练/评估必需；预测可选）。
- 22 个特征列，顺序不限，名字必须与 `core.FEATURES` 一致。

**输出 CSV 追加列：**

| 列 | 含义 |
|---|---|
| `probability` | 校准前的模型概率（0–1） |
| `prediction` | 按阈值（默认 0.5）的二值输出 |
| `risk_band` | `<0.35` low，`0.35–0.65` medium，`≥0.65` high |

**subject 解析规则：** 正则 `S\d+`，例如 `phon_R01_S01_1 → S01`。同一 subject 只能有一个标签，否则 `load_data` 直接报错。

## 6. 模型与训练

**标准化：**

```
x' = (x - mean_train) / std_train
std_train = 0 时置 1
```

**逻辑回归（IRLS / Newton）：**

```
Xb = [1, X']
β = 0
重复直到收敛：
  p = sigmoid(Xb β)
  w = clip(p(1-p), 1e-6, ∞)
  z = Xb β + (y - p) / w
  A = Xbᵀ diag(w) Xb + λ diag(0,1,...,1)
  b = Xbᵀ diag(w) z
  β = solve(A, b)
```

- `λ=1.0` 默认，可用 `--l2` 调整。
- 不惩罚截距。
- 输出概率 `sigmoid(β0 + x'β)`。
- 阈值默认 0.5；**没有**在测试折上调阈值。

## 7. 评估协议

**受试者分组 CV：**

1. 取每个 subject 的标签（一人一标签）。
2. 按类别分别打乱 subject。
3. 轮转分配到 `n_splits` 折；每折的 PD/HC 数量尽量均衡。
4. 每一折：该折 subject 的全部录音作为测试，其余 subject 的全部录音作为训练。
5. 重复 `repeats` 次（不同随机种子），每次计算全部 OOF 预测的指标。
6. 报告均值、标准差、2.5%/97.5% 分位。

**泄漏对照：**

- 随机按行 80/20 切分，重复同样次数。
- 同一个 subject 可能同时出现在训练/测试，AUC 会被高估。
- 该结果只用于教学/诊断，不写入模型卡作为性能。

**指标：**

- AUC（主指标，排序能力）
- 敏感度、特异度（阈值 0.5）
- F1、Brier、混淆矩阵
- 校准表（5 箱）

## 8. CLI 规范

```bash
python app.py summary
python app.py evaluate --repeats 20 --folds 5 --l2 1.0 --threshold 0.5
python app.py train --repeats 20
python app.py predict --input data/parkinsons.data --output artifacts/predictions.csv
python -m unittest discover -s tests -v
```

退出码：成功 0；数据/模型错误抛异常并由 Python 返回非 0。

## 9. 错误处理

| 场景 | 行为 |
|---|---|
| 数据文件不存在 | `FileNotFoundError`，提示路径 |
| 缺列/缺失值/标签非二值 | `ValueError`，列出问题 |
| name 无法解析 subject | `ValueError`，给出前 5 个坏样本 |
| 同一 subject 多标签 | `ValueError`，列出 subject |
| `n_splits` 大于某类 subject 数 | `ValueError`，建议减小折数 |
| 模型文件格式/特征不匹配 | `ValueError` |
| 预测输入缺特征 | `ValueError`，列出缺列 |

## 10. 扩展点（按优先级）

1. **阈值选择**：在训练折内部用 nested CV 选阈值，再固定到测试折；或预先规定“高特异度”工作点。
2. **校准**：Platt/isotonic（需要独立校准集）；当前只输出原始概率。
3. **特征选择**：用训练折内部的单变量筛选/L1，禁止用全量数据选特征。
4. **外部验证**：PC-GITA/NeuroVoz/MDVR-KCL；先做跨语料，不调参。
5. **原始音频前端**：Praat/openSMILE 提取 22 维特征，接入同一 `predict_frame` 契约。
6. **服务化**：如需 HTTP，只加一层 FastAPI 包装 `predict_frame`，不改变核心。
7. **模型对比**：随机森林/梯度提升可在同一 CV 协议下替换 `fit_on_subset`，但必须保持 subject 分组。

## 11. 验收清单

- [x] `summary` 输出 195 行、22 特征、32 subject。
- [x] `evaluate` 输出分组 CV 与随机切分对照。
- [x] `train` 生成 `model.json` 与 `model_card.json`。
- [x] `predict` 能对 195 行数据打分并输出概率/风险带。
- [x] 11 个单元测试通过。
- [x] 无 sklearn/数据库/Web 依赖。
- [x] 随机切分 AUC 明显高于分组 CV，证明泄漏检查有效。

## 12. 取舍说明

- **为什么不用 sklearn？** 环境只保证 numpy/pandas；逻辑回归+IRLS 代码不到 80 行，可审计，避免额外依赖。
- **为什么不用深度学习？** 195 条/32 人，深度模型只会过拟合；逻辑回归是更诚实的基线。
- **为什么还要跑随机切分？** 不是为了报告高分，而是为了量化“错误评估会高估多少”，帮助团队识别 GitHub 上常见的 98% 准确率。
- **为什么固定 0.5？** 先给一个透明、不可调的基线；临床阈值是另一个问题，必须单独预指定。
