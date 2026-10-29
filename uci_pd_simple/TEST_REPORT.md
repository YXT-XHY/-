# 测试报告：UCI 最简基线

**测试日期：** 2026-10-27  
**测试环境：** Windows，Python 3.12.14，numpy 2.3.5，pandas 3.0.1  
**被测版本：** `uci_pd_simple`（v1.0，最简架构）  
**结论：** **通过（PASS）** —— 作为研究与教学基线可用；不具备临床有效性。

---

## 1. 测试范围

| 类别 | 内容 |
|---|---|
| 单元测试 | 数据形状、一人一标签、分组折、模型概率、AUC 边界、持久化、异常输入、折数越界、CV 可复现 |
| CLI 正常路径 | `summary`、`evaluate`、`train`、`predict`（含/不含 `status`） |
| CLI 异常路径 | 数据/模型文件不存在、缺特征、特征 NaN、同一 subject 多标签、`--folds` 越界 |
| 一致性 | `model.json` 特征/系数长度、`model_card.json` 与 `cv_metrics.csv` 的 AUC 一致、概率范围 |
| 可复现性 | 相同参数重复运行 CV，AUC 逐次完全一致 |
| 打包验证 | 从 zip 解压到全新目录，运行测试与 `summary`、`train`、`predict` |

---

## 2. 单元测试

命令：

```powershell
python -m unittest discover -s tests -v
```

结果：

```text
Ran 11 tests in 0.141s
OK
```

覆盖：

1. `test_shape_and_labels`：195 行、22 特征、32 subject、二分类标签。
2. `test_one_label_per_subject`：每个 subject 只有一个标签。
3. `test_no_missing_features`：22 维特征无缺失。
4. `test_inconsistent_subject_labels_raise`：人为制造同一 subject 两个标签，`load_data` 抛出 `ValueError`。
5. `test_folds_are_disjoint_and_complete`：5 折互不重叠、并集覆盖全部 subject。
6. `test_too_many_folds_raises`：`n_splits=9` 超过 8 例对照，抛出 `ValueError`。
7. `test_cv_is_deterministic`：重复运行 3 次 CV，AUC 完全一致。
8. `test_model_probabilities`：概率在 [0,1]，系数长度 22。
9. `test_metrics_perfect_and_reversed`：完美预测 AUC=1、反向 AUC=0，混淆矩阵正确。
10. `test_save_load_predict`：保存/加载 JSON 后预测一致。
11. `test_predict_rejects_missing_and_nan`：缺特征/NaN 输入被拒绝。

---

## 3. CLI 正常路径

| 命令 | 退出码 | 结果 |
|---|---:|---|
| `app.py summary` | 0 | 195 行、32 subject（24 PD / 8 HC）、22 特征 |
| `app.py evaluate --repeats 20` | 0 | AUC 0.7362 ± 0.0324；敏感度 0.8735；特异度 0.4729 |
| `app.py train --repeats 20` | 0 | 生成 `model.json`、`model_card.json`、`cv_metrics.csv`、`oof_predictions.csv` |
| `app.py predict --input data/parkinsons.data` | 0 | 195 行概率/预测/风险带；附 in-sample 指标与警告 |
| `app.py predict --input artifacts/sample_input.csv` | 0 | 3 行无标签输入，正常输出概率，不打印指标 |

**关键指标：**

| 指标 | 值 |
|---|---:|
| 受试者分组 AUC | 0.7362 ± 0.0324 |
| 准确率 | 0.7749 |
| 敏感度 | 0.8735 |
| 特异度 | 0.4729 |
| F1 | 0.8539 |
| Brier | 0.1791 |
| 随机按行切分 AUC（错误对照） | 0.9126 ± 0.0333 |

说明：随机切分把同一受试者的其他录音放进训练集，AUC 被高估；**只能报告分组结果**。

---

## 4. CLI 异常路径

| 场景 | 退出码 | 输出 | 结果 |
|---|---:|---|---|
| 数据文件不存在 | 2 | `ERROR: Dataset not found: ...` | 通过 |
| 模型文件不存在 | 2 | `ERROR: [Errno 2] No such file or directory: ...` | 通过 |
| 输入缺 `MDVP:Fo(Hz)` | 2 | `ERROR: Input is missing features: [...]` | 通过 |
| 输入含 NaN | 2 | `ERROR: Input contains missing values: {'MDVP:Fo(Hz)': 1}` | 通过（修复后） |
| 同一 subject 多标签 | 2 | `ERROR: Subjects with inconsistent labels: ['S01']` | 通过 |
| `--folds 9`（只有 8 例对照） | 2 | `ERROR: Class 0 has only 8 subjects; reduce n_splits.` | 通过 |

异常路径不会写半成品模型或预测文件。

---

## 5. 测试中发现并修复的问题

| 问题 | 现象 | 修复 |
|---|---|---|
| `predict_frame` 未校验 NaN | NaN 输入会输出 NaN 概率，CLI 仍返回 0 | 增加缺失值/非数值校验，改为 `ValueError`，CLI 返回 2 |
| CLI 异常直接抛 traceback | 用户看到长堆栈，不像命令行工具 | `main()` 捕获 `FileNotFoundError/ValueError/KeyError`，打印 `ERROR:` 并返回 2 |
| 测试用系统临时目录被沙箱拒绝 | `PermissionError`，测试误报 | 测试改用项目内 `artifacts/_test_model*.json`，用完删除 |
| 早期 zip 无顶层目录、含 `__pycache__` | 解压后文件散落 | 重新打包为 `uci_pd_simple/...`，排除缓存 |

---

## 6. 一致性与可复现性

- `model.json`：`coef`、`mean`、`std` 均为 22 维。
- `model_card.json` 的 `cv.repeats = 20`，与 `cv_metrics.csv` 的 20 行一致。
- `card.cv.summary.auc.mean` 与 `cv_metrics.csv` 的 `auc.mean()` 完全相等（差值 < 1e-9）。
- `predictions.csv`：195 行，概率范围 0.0291–0.9999999。
- 相同参数重复 CV，AUC 逐次完全一致（固定 seed）。
- 手工按 `(x-mean)/std @ coef + intercept` 计算首条样本概率 0.9953689653，与 `predict_frame` 完全一致。

---

## 7. 打包验证

将 `deliverables/uci_pd_simple.zip` 解压到全新目录，执行：

```text
python -m unittest discover -s tests -v   -> 11 tests OK
python app.py summary                     -> 195 rows / 32 subjects
python app.py train --repeats 2           -> 0
python app.py predict ...                 -> 0
```

结果：**通过**。说明代码、数据、测试、依赖说明自包含。

---

## 8. 未测试 / 不能测试的内容

- **外部验证**：未使用 PC-GITA/NeuroVoz/MDVR-KCL；当前数据不允许声称泛化。
- **原始音频前端**：UCI 只有特征表，未测试录音质控、降噪、设备差异。
- **概率校准**：未做 Platt/isotonic，Brier 0.179 只是基线。
- **临床阈值**：未做阈值选择/决策曲线；0.5 不是临床工作点。
- **并发/服务化**：无 Web 服务、无并发、无数据库。
- **安全/合规**：无身份认证、审计、PII 处理；不适用于真实患者数据。

---

## 9. 最终判定

| 维度 | 结论 |
|---|---|
| 可运行性 | PASS |
| 数据契约 | PASS |
| 评估无泄漏 | PASS（受试者分组） |
| 异常处理 | PASS（退出码 2 + 明确信息） |
| 可复现性 | PASS |
| 打包完整性 | PASS |
| 临床有效性 | **不适用 / 未验证** |

**一句话：** 这是一个**测试通过、评估诚实、可复现**的 UCI 最小基线；它可以作为后续数据和模型工作的起点，但不能作为临床产品。
