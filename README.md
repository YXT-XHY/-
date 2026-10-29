# 声纹帕金森早期筛查：项目调研与架构评估

## 交付物

- `deliverables/声纹帕金森早期筛查_项目调研与架构评估报告.docx`：29 页立项建议书，含论文/数据集/GitHub 调研、参考架构、五方案评分、风险矩阵、临床与合规路径、30 个月路线图。
- `deliverables/声纹帕金森早期筛查_调研清单与测算.xlsx`：6 个工作表（说明、数据集、GitHub 项目、论文、架构评分、筛查收益测算），评分与 PPV/NPV 公式可修改。
- `assets/fig1_architecture.png`：参考架构图（可单独用于汇报）。
- `report.md`：报告 Markdown 源文；`sources.md`：来源与关键事实底稿。

## 核心结论

1. 技术路线成立，但公开数据不能支撑“早期筛查”临床声称：现有数据多为已确诊患者 vs 健康对照，mPower 为自报标签，NeuroVoz 患者为 ON 状态。
2. 语料内准确率常见 80%–90%，但真实场景会明显掉点：WavLM Base 从 82.2% 降到 68.6%，语音增强后 83.3%，WavLM+HuBERT 集成 88.3%（La Quatra et al., Interspeech 2024）。
3. GitHub 生态以 UCI 玩具项目为主，普遍存在记录级泄漏；可复用的是工具链（openSMILE、SpeechBrain、PDkit）和研究代码（SSL4PR、VoxTransPD），不是现成临床模型。
4. 推荐架构：端云协同（C）+ 院内私有化（E）；双通道（可解释声学 + SSL 表征）、质控前置、概率校准、不确定性拒识、医生最终决策。
5. 建议“有条件推进”：先做 3 个月 Phase 0（80–120 万元），锁定“辅助风险分层”定位、数据伙伴与监管路径；到注册的量级预算 1,200–1,900 万元。

## 附：UCI 最简可运行基线

`uci_pd_simple/` 是一个单机、无 sklearn、无数据库的最小程序：本地 CSV → 受试者分组 CV → 标准化逻辑回归 → JSON 模型 → CLI 打分。详见 [uci_pd_simple/README.md](uci_pd_simple/README.md)、[DESIGN.md](uci_pd_simple/DESIGN.md) 与 [TEST_REPORT.md](uci_pd_simple/TEST_REPORT.md)。

```powershell
cd uci_pd_simple
python app.py summary
python app.py evaluate --repeats 20
python app.py train --repeats 20
python app.py predict --input data/parkinsons.data --output artifacts/predictions.csv
python -m unittest discover -s tests -v
```

当前结果（默认 L2=1.0、阈值 0.5）：受试者分组 5 折 × 20 次，AUC **0.7362 ± 0.0324**，敏感度 0.8735，特异度 0.4729；随机按行切分 AUC 0.9126（泄漏对照，不可报告）。数据文件实际解析出 **32 个 subject（24 PD / 8 HC）**，与 UCI 页面文字“31 人/23 PD”存在元数据差异，程序按文件实际内容运行并在 `summary` 中打印。

## 重新生成

```powershell
& 'C:\Users\XuYang\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' src\build_arch.py
& 'C:\Users\XuYang\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' src\build_figures.py
& 'C:\Users\XuYang\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' src\build_docx.py
& 'C:\Users\XuYang\.dsh\dsh-runtimes\dsh-primary-runtime\dependencies\python\python.exe' src\build_xlsx.py
```

注意：`build_figures.py` 会把架构图覆盖为旧版密集图；如需重新生成全部图，先运行 `build_arch.py`，再运行 `build_figures.py` 的其余函数，或只运行 `build_arch.py` 覆盖架构图。

## 限制

- 快速证据扫描，不是系统综述/meta 分析；性能数字未复现，跨研究不可直接比较。
- GitHub stars/许可证为 2026-10-27 快照。
- 监管分类与合规为技术建议，不构成法律意见。
