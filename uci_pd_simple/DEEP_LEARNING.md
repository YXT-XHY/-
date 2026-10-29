# 语音 → CNN + Transformer → 帕金森组 / 健康对照组研究分类

本工程已实现真实音频推理，前端不再生成模拟疾病分数。它仍是小样本研究原型：可预测语音更接近哪个训练组，不能据此确认或排除帕金森病。

中文数据进展（2026-10-28）：已核实三项可申请的临床语音来源，尚未取得原始中文录音或使用授权。候选规模、获取条件与接入方案见 [CHINESE_DATA_SOURCES.md](CHINESE_DATA_SOURCES.md)，本地申请草稿见 [DATA_ACCESS_REQUEST.md](DATA_ACCESS_REQUEST.md)。当前中文输入仍返回“不确定”。

## 启动

在 `uci_pd_simple` 目录：

```powershell
& '.\.venv-dl\Scripts\python.exe' recording_server.py --port 8768 --model-dir artifacts/audio_transformer_v1
```

打开 http://127.0.0.1:8768/ 。已训练权重在 `artifacts/audio_transformer_v1`，完整依赖在项目内 `.venv-dl`。旧的 8766 静态服务和之前启动的 8767 服务不具备本次更新后的后端代码，请以新服务为准。

操作：选择英文朗读 → 确认同意 → 录音或导入音频 → 回放 → Transformer 分析 → 查看结果 / 导出报告。录音最多 30 秒，导入最多 120 秒，推荐 15–25 秒自然朗读。点击保存才在本机持久存储原始音频，推理请求本身不保存音频。

普通话可采集，但因无中文训练验证，返回“不确定”，不输出 PD/HC 分类结论；下拉框是操作者声明的语种，不是自动语种识别。持续元音和 DDK 可用于采集，当前模型仅支持朗读分类。

## 实际完成的模型

原始单声道音频 → 16 kHz 重采样 → 最多 20 个 6 秒片段 → 64 维 log-Mel 声谱图 → 两层卷积声学编码 → 位置编码 → 两层、四头 Transformer Encoder → 学习式时间注意力汇聚 → 二分类。

- 84,946 个参数，PyTorch 2.9.1 CUDA 12.8；已在 RTX 5060 Laptop GPU 上实际训练。
- 训练与推理共享 `deep_learning/audio.py`，每片段做去直流和声谱图标准化，不从测试集拟合统计量。
- 每位受试者在训练采样中等权，正负组等权；仅训练集使用小幅噪声和频率/时间遮挡增强。
- 保存 5 个 `safetensors` 权重文件，无外部 pickle 模型执行；推理前验证 SHA-256。
- 网页 CPU 推理，避免常驻占用 GPU；多段 logits 先在每个模型内平均，再对五个模型的分数取平均。
- 返回时间关注权重，但这些权重不是因果解释或病灶定位。

## 数据与可追溯性

MDVR-KCL 的 ReadText 子集：37 人（16 PD / 21 HC）、37 条原始朗读录音、666 个有效训练/验证片段。官方来源：https://zenodo.org/records/2867216 ，DOI 10.5281/zenodo.2867216，许可 CC BY 4.0。

引用：Jaeger H, Trivedi D, Stadtschnitzer M. Mobile Device Voice Recordings at King's College London (MDVR-KCL) from both early and advanced Parkinson's disease patients and healthy controls. Zenodo, 2019.

数据通过官方 ZIP 字节范围下载，验证了每个文件的 ZIP CRC32 与解压大小，并记录 SHA-256。完整 ZIP 因下载不稳定未完成，因此没有声称验证完整压缩包 MD5。来源、逐文件哈希和标签记录于 `data/mdvr-kcl/provenance.json`，副本也包含在模型卡内。

未使用自发对话目录，减少采访者声音混入的问题；没有把合成测试音、用户采集的无标签录音或 UCI 特征表冒充原始音频训练数据。

## 实测评估

外层 5 折按受试者分组，每位受试者只进入一次外层测试。每折其余受试者再分训练和内部验证，依据内部验证损失早停。没有在外层测试上选最佳轮次或阈值。

以下按 **37 位受试者** 聚合计算，阈值固定 0.5：

| 指标 | 实测结果 |
|---|---:|
| 折外 ROC-AUC | 0.7589 |
| 准确率 | 0.7297 |
| 平衡准确率 | 0.7173 |
| 敏感度 | 0.6250（10 / 16）|
| 特异度 | 0.8095（17 / 21）|
| Brier | 0.1962 |
| 分层受试者 bootstrap AUC 95% 区间 | 0.5774–0.9107 |

区间很宽，各折不稳定：不能用单折高分宣传。以上是留出折单模型的 OOF 结果，不是部署五模型集成在独立外部人群上的性能。训练数据含已确诊病例，不证明前驱期或社区早筛效果。

页面低于 0.35 / 高于 0.65 时才可能给出训练组分类，中间区间、跨语种或模型分歧较大时输出不确定；这些是工程性拒识规则，未验证其临床工作点或覆盖率。内部开放分类门槛 AUC≥0.65 且平衡准确率≥0.60 也是工程规则，不能理解为医疗合格认证。

## 验证证据

`audit.json` 已记录：5 折训练/验证/测试人员无重叠、37 人恰好各测试一次、权重和 manifest 哈希一致，并用保存权重在 CPU 重算所有留出人员结果。CPU 与训练 GPU 的最大分数差约 1.65e-5，主要分类指标一致。

40 项 Python 测试通过，覆盖 CNN/Transformer 梯度、重采样、静音/恒定测试音拒识、权重缺失拒绝、真实 API 与直接推理一致、跨语种不确定、任务拒绝及本机采集。新增清单测试拒绝语言/来源与诊断完全混淆、单类队列、空身份、未知标签与同一人标签冲突；现有37人真实数据清单也通过新校验。这些检查不能替代临床标注核验或排除所有混杂因素。浏览器已验证公开录音导入、真实推理和结果展示。实际个人麦克风硬件与录音权限仍需操作者试录确认。

`integration_pd.json` / `integration_hc.json` 是公开训练语料窗口上的功能测试报告，不是新的外部测试证据，不能据此报告临床准确率。

## 重新训练与审计

新环境安装（GPU CUDA 示例，CPU 可改 PyTorch 官方 CPU 源）：

```powershell
python -m venv .venv-dl
& '.\.venv-dl\Scripts\python.exe' -m pip install torch==2.9.1 --index-url https://download.pytorch.org/whl/cu128
& '.\.venv-dl\Scripts\python.exe' -m pip install --no-cache-dir -r requirements-dl.txt
& '.\.venv-dl\Scripts\python.exe' -m deep_learning.fetch_mdvr
& '.\.venv-dl\Scripts\python.exe' -m deep_learning.train --device cuda --output artifacts/audio_transformer_new
```

训练命令禁止覆盖已有完整模型卡。切换到新模型时必须运行对应 audit 并修改服务的 `--model-dir`。预处理改变后要更新缓存版本及模型版本，不能用旧权重声称是新处理流程的验证结果。

```powershell
& '.\.venv-dl\Scripts\python.exe' -m deep_learning.audit
& '.\.venv-dl\Scripts\python.exe' -m unittest discover -s tests -v
& '.\.venv-dl\Scripts\python.exe' -m deep_learning.predict --audio your-reading.wav --task reading --language en
```

## 主要文件与接口

- `deep_learning/model.py`：CNN + Transformer。
- `deep_learning/audio.py`：统一预处理与分段。
- `deep_learning/train.py`：受试者级训练、验证、权重与模型卡导出。
- `deep_learning/runtime.py`：权重校验、真实分类、质量与语种拒识。
- `deep_learning/audit.py`：保存权重重算 OOF 与泄漏审计。
- `recording_server.py`：GET `/api/model` 查看真实模型状态；POST `/api/predict?task=reading&language=en&consent=yes` 发送二进制 `audio/wav` 获取真实结果。
- `frontend/capture.js`：录音、导入、本机推理、结果和报告展示。

缺权重或内部验证不合格返回 503，音频不合格或不支持任务返回 422，输入参数/同意缺失返回 400。没有随机权重回退或固定分数回退。

## 仍需完成的临床工作

扩大有确诊标签且匹配年龄、性别的中文临床语料；加入其他嗓音疾病和帕金森综合征对照；在不同机构、设备、语种和新文本上做外部验证；校准工作点并验证敏感度、特异度、覆盖率和人群预测值。当前功能完成的是比赛用研究分类系统，不是已证明可判断个人是否患病的临床工具。
