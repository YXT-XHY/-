# UCI 帕金森语音基线：最简易项目架构

## 当前入口：真实音频深度学习分类

公开数据检索、元数据核查与批量下载：`python -m data_tools catalog`，使用说明见 [PUBLIC_DATA_TOOL.md](PUBLIC_DATA_TOOL.md)。中文候选来源及申请条件见 [CHINESE_DATA_SOURCES.md](CHINESE_DATA_SOURCES.md)。

运行 `& '.\.venv-dl\Scripts\python.exe' recording_server.py --port 8768`，打开 http://127.0.0.1:8768/ 。已接入基于真实 MDVR-KCL 英文朗读语料训练的 CNN + Transformer 模型，支持录音/音频导入 → 实际推理 → 研究分类/不确定 → 报告导出。模型训练、按人验证和限制详见 [DEEP_LEARNING.md](DEEP_LEARNING.md)。下文 UCI CSV 逻辑回归是保留的独立历史基线。

## 新增：麦克风与音频采集

运行 `python recording_server.py`，打开 http://127.0.0.1:8767/ 。支持麦克风录音、音频导入、回放、质量提示、WAV 下载、本机保存及录音档案。详见 [VOICE_CAPTURE.md](VOICE_CAPTURE.md)。原始音频尚未提取为 UCI 22 维特征，采集后不会直接给出疾病分数。

一个**单机、单模型、无数据库、无 Web 服务**的最小可运行项目，用于 UCI 帕金森语音数据（195 条录音、22 维声学特征）的二分类实验。

> 这是教学/研究基线，不是临床诊断系统。UCI 数据是“已确诊患者 vs 健康对照”的病例对照数据，不能用于宣称“早期筛查”。

---

## 1. 数据集

| 项目 | 值 |
|---|---|
| 文件 | `data/parkinsons.data` |
| 样本 | 195 条录音 |
| 特征 | 22 维声学特征 |
| 标签 | `status`：1 = PD，0 = 健康对照 |
| 受试者 | 文件解析出 **32 个 subject ID（24 PD / 8 HC）** |
| 录音/人 | 6–7 条 |

**注意一个元数据不一致：** UCI 官网文字写“31 人、23 例 PD”，但公开分发的 `parkinsons.data` 实际解析出 32 个 subject ID、24 例 PD、8 例 HC。本项目**按文件实际内容运行**，并在 `summary` 中打印真实数量；不做手工删除受试者。

数据来源：UCI Machine Learning Repository, Parkinsons（CC BY 4.0），文件镜像来自公开 GitHub 仓库；引用请以 UCI 页面为准。

---

## 2. 最简架构

```text
┌─────────────────────────────────────────────────────────────┐
│  1. 数据层   data/parkinsons.data（195 × 24）                │
│       ↓                                                     │
│  2. 校验层   core.load_data()                               │
│       - 必需列 / 缺失值 / 标签二值化                         │
│       - 从 name 解析 subject（phon_R01_S01_1 → S01）        │
│       - 校验“一人一个标签”                                   │
│       ↓                                                     │
│  3. 评估层   core.cross_validate()                          │
│       - 按 subject 分 5 折（同一人不同时进训练/测试）         │
│       - 重复 20 次，统计均值/标准差/2.5–97.5 分位            │
│       - 另跑“随机按行切分”作为泄漏对照（仅警告，不报告）      │
│       ↓                                                     │
│  4. 模型层   Standardizer + L2 Logistic Regression（IRLS）  │
│       - 只用 numpy，无 sklearn                              │
│       - 22 个标准化系数 + 截距，可解释                       │
│       ↓                                                     │
│  5. 产物层   artifacts/model.json                           │
│       - 特征顺序、均值/标准差、系数、阈值、元数据             │
│       - CLI 可直接加载并对新 CSV 打分                        │
└─────────────────────────────────────────────────────────────┘
```

**设计原则：** 先保证“评估不泄漏”，再谈模型复杂度。对 195 条、32 人的数据，逻辑回归比深度模型更合适：小样本、可解释、几秒跑完、没有额外依赖。

---

## 3. 文件结构

```text
uci_pd_simple/
├─ app.py                 # CLI：summary / evaluate / train / predict
├─ core.py                # 数据、模型、指标、分组 CV、持久化
├─ data/
│  └─ parkinsons.data     # UCI 数据（195 × 24）
├─ artifacts/             # 运行后生成
│  ├─ model.json
│  ├─ model_card.json
│  ├─ cv_summary.json
│  ├─ cv_metrics.csv
│  ├─ oof_predictions.csv
│  └─ predictions.csv
├─ tests/
│  └─ test_core.py        # 11 个冒烟测试
├─ TEST_REPORT.md         # 完整测试报告（单元/CLI/异常/打包）
├─ requirements.txt
└─ README.md
```

---

## 4. 运行

在 `uci_pd_simple/` 目录下：

```powershell
# 1) 看数据
python app.py summary

# 2) 受试者分组交叉验证（推荐先跑这个）
python app.py evaluate --repeats 20

# 3) 训练最终模型并保存 artifacts/model.json
python app.py train --repeats 20

# 4) 对新 CSV 打分（输入需含 22 个特征列；status/name 可选）
python app.py predict --input data/parkinsons.data --output artifacts/predictions.csv

# 5) 测试
python -m unittest discover -s tests -v
```

本机若 `python` 不在 PATH，可使用：

```powershell
& 'C:\Users\XuYang\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' app.py train --repeats 20
```

### 已测试

- **11 个单元测试全部通过**：数据形状、一人一标签、分组不重叠、模型概率范围、AUC 边界、持久化、缺失/NaN 拒识、折数越界、CV 可复现。
- **CLI 正常路径**：`summary / evaluate / train / predict` 均返回 0；`predict` 在含/不含 `status` 的输入上都能输出概率与风险带。
- **CLI 异常路径**：数据文件不存在、模型文件不存在、缺特征、特征含 NaN、同一 subject 多标签、`--folds` 大于对照人数，均返回 2 并给出 `ERROR:` 信息，不写半成品结果。
- **泄漏对照**：随机按行切分 AUC 0.9126，受试者分组 AUC 0.7362；证明评估协议有效。

---

## 5. 当前结果（默认 L2=1.0，阈值 0.5）

**受试者分组 5 折 × 20 次重复：**

| 指标 | 均值 | 标准差 | 2.5% | 97.5% |
|---|---:|---:|---:|---:|
| AUC | 0.7362 | 0.0324 | 0.6680 | 0.7827 |
| 准确率 | 0.7749 | 0.0168 | 0.7433 | 0.8000 |
| 敏感度 | 0.8735 | 0.0230 | 0.8296 | 0.9015 |
| 特异度 | 0.4729 | 0.0245 | 0.4266 | 0.5109 |
| F1 | 0.8539 | 0.0125 | 0.8297 | 0.8713 |
| Brier | 0.1791 | 0.0123 | 0.1559 | 0.1964 |

**泄漏对照（错误做法，仅用于说明问题）：**

- 随机按行 80/20 切分：AUC **0.9126 ± 0.0333**
- 受试者分组 CV：AUC **0.7362 ± 0.0324**

随机切分把同一个人的其他录音放进训练集，AUC 被显著高估。**任何报告都应使用受试者分组结果。**

**训练集内打分（仅演示，不是性能）：** AUC 0.9290。`predict` 命令会提示这是 in-sample。

**如何解读：** 在 32 人、8 例对照的条件下，0.74 的 AUC 说明“有信号，但远不够临床可用”；特异度只有 0.47，说明阈值 0.5 不适合筛查场景。下一步应做：
1. 用训练折内部选择阈值（或预先规定高特异度工作点），而不是在测试折上调阈值；
2. 增加外部数据/跨语料验证；
3. 加入疾病对照（特发性震颤、非典型帕金森综合征等），而不是只对健康人。

---

## 6. 关键设计选择

| 选择 | 理由 |
|---|---|
| 逻辑回归，而不是深度学习 | 195 条/32 人；小模型更稳、可解释、无过拟合风险 |
| 只用 numpy + pandas | 不依赖 sklearn，安装简单，代码可审计 |
| 标准化 + L2 | 22 维特征量纲差异大；L2 抑制小样本过拟合 |
| 受试者分组 CV | 同一人的 6–7 条录音不能跨训练/测试 |
| 重复 20 次 | 32 人划分一次不稳定；重复降低划分偶然性 |
| 固定阈值 0.5 | 先给一个透明基线；临床阈值应单独预指定 |
| JSON 模型 | 无 pickle 版本问题；特征顺序、均值、系数全部显式 |

---

## 7. 限制

- 数据是病例对照，不是前瞻性筛查队列；不能证明“早期”或“筛查有效”。
- 32 人（8 例对照）非常小；AUC 的置信区间很宽，换一批人可能明显变化。
- 只做内部受试者分组 CV，没有外部验证。
- 阈值 0.5 未针对临床场景优化；特异度偏低。
- 特征来自 UCI 特征表，不是原始音频；不能评估录音质量、设备、噪声的影响。
- 不构成医疗、法律或投资建议。

---

## 8. 一页结论

**最简架构 = 本地 CSV + 受试者分组评估 + 标准化逻辑回归 + JSON 模型 + CLI。**  
它不能做出临床产品，但能在一小时内建立一个**不泄漏、可复现、可解释**的基线，并明确告诉你：UCI 上的“98% 准确率”大多来自随机切分，而不是模型本身。
