# 调研来源与关键事实（工作底稿）

> 检索日期：2026-10-27。以下数字均来自对应来源；未做二次实验验证。
> 报告中的引用编号与此处一致。

## 一、论文与指南

[1] Little MA, McSharry PE, Roberts SJ, Costello DAE, Moroz IM. Exploiting nonlinear recurrence and fractal scaling properties for voice disorder detection. *BioMedical Engineering OnLine*. 2007;6:23. DOI: 10.1186/1475-925X-6-23.
- 牛津帕金森语音数据集的来源论文；31 人、195 条录音、22 维声学特征；用于区分 PD 与健康对照。
- 该数据集是“特征表”，不是原始音频；每人大约 6 条持续元音 /a/ 录音。

[2] Little MA, McSharry PE, Hunter EJ, Ramig LO. Suitability of dysphonia measurements for telemonitoring of Parkinson's disease. *IEEE Transactions on Biomedical Engineering*. 2009;56(4):1015-1022. DOI: 10.1109/TBME.2008.2005954.
- 强调语音用于“远程监测/随访”的可行性，而非独立诊断。

[3] Tsanas A, Little MA, McSharry PE, Ramig LO. Accurate telemonitoring of Parkinson's disease progression by noninvasive speech tests. *IEEE Transactions on Biomedical Engineering*. 2010;57(4):884-893. DOI: 10.1109/TBME.2009.2036000.
- 用语音特征估计 UPDRS 进展；属于纵向监测，不是早期筛查。

[4] Orozco-Arroyave JR, Arias-Londoño JD, Vargas-Bonilla JF, González-Rátiva MC, Nöth E. New Spanish speech corpus database for the analysis of people suffering from Parkinson's disease. *LREC 2014*:342-347. https://aclanthology.org/L14-1549/
- PC-GITA：50 例 PD + 50 例健康对照，西班牙语（哥伦比亚），男女各半，年龄 31-86 岁；任务包括持续元音、DDK、45 个词、10 个句子、朗读和独白。
- 摘要指出 PD 在 65 岁以上人群患病率约 1%，约 89% 的 PD 患者出现言语障碍。

[5] Bot BM, Suver C, Neto EC, et al. The mPower study, Parkinson disease mobile data collected using ResearchKit. *Scientific Data*. 2016;3:160011. DOI: 10.1038/sdata.2016.11.
- 9,520 人同意参与；6,805 人完成入组问卷；1,087 人自报 PD，5,581 人自报非 PD；5,826 人贡献语音，65,022 条语音任务。
- 语音任务仅为约 10 秒持续元音 /a/；诊断标签为自报，非临床确诊。

[6] Mendes-Laureano J, Gómez-García JA, Guerrero-López A, et al. NeuroVoz: a Castillian Spanish corpus of parkinsonian speech. *Scientific Data*. 2024;11:1367. DOI: 10.1038/s41597-024-04186-z.
- 112 人：54 例 PD + 58 例健康对照；均为西班牙语；PD 患者在 ON 状态录制。
- 任务：持续元音、DDK、16 个听重复句子、自由独白；含 GRBAS、UPDRS、H-Y 等标注。
- 该文称 PD 确诊平均延迟约 2.75 年；言语障碍约见于 89% 患者；数据集内基准准确率约 89%，跨语料约 83%。
- 该文还给出其他数据集规模：意大利数据集 831 个音频、28 例 PD + 50 例 HC；MDVR-KCL 21 例 HC + 16 例 PD；mPower 5,826 人、65,022 条录音。

[7] Jaeger H, Trivedi D, Stadtschnitzer M. Mobile Device Voice Recordings at King's College London (MDVR-KCL) from both early and advanced Parkinson's disease patients and healthy controls. *Zenodo*. 2019. DOI: 10.5281/zenodo.2867216.
- 37 人（21 HC + 16 PD）；朗读段落 + 电话场景自发对话；44.1 kHz/16 bit；CC BY 4.0。
- 含 H&Y、UPDRS II-5、UPDRS III-18 标注；包含早期与进展期患者。

[8] Dimauro G, Girardi F. Italian Parkinson's Voice and Speech. *IEEE DataPort*. 2019. DOI: 10.21227/aw6b-tg17.
- 831 个音频文件；28 例 PD + 50 例 HC；意大利语；任务含朗读、/pa/、/ta/ 重复、持续元音。
- 开放获取但需 IEEE 账号登录；许可条款以数据集页面为准。

[9] La Quatra M, Turco MF, Svendsen T, Salvi G, Orozco-Arroyave JR, Siniscalchi SM. Exploiting Foundation Models and Speech Enhancement for Parkinson's Disease Detection from Speech in Real-World Operative Conditions. *Interspeech 2024*:1405-1409. arXiv:2406.16128.
- 在干净 PC-GITA（100 人）上微调 Wav2Vec2/HuBERT/WavLM/Whisper；在真实场景 e-PC-GITA（20 PD + 20 HC）外部测试。
- 干净条件最佳 WavLM Base：准确率 82.21%，F1 81.99%，AUC 82.22%。
- 真实场景原始录音：WavLM Base 准确率降至 68.58%；HuBERT 67.33%；Whisper Small 74.83%。
- 经 VAD、去混响、降噪后：HuBERT 82.75%，WavLM 83.33%；两模型集成准确率 88.33%，敏感度 85.00%，特异度 91.67%。
- 结论：从理想条件到真实条件性能显著下降；语音增强对基础模型有效；跨场景泛化是核心问题。

[10] Sedigh Malekroodi H, Lee BI, Yi M. Voice-Based Detection of Parkinson's Disease Using Machine and Deep Learning Approaches: A Systematic Review. *Bioengineering*. 2025;12(11):1279. DOI: 10.3390/bioengineering12111279.
- 检索 2020-2025.9，纳入 69 项研究。
- 经典 ML（SVM、RF）在小样本同质数据上准确率高；DL（CNN、RNN、Transformer/基础模型）在跨语言、跨录音条件上更稳健、更可扩展。
- 主要问题：数据异质、类别不平衡、验证不规范、可复现性差、临床转化不足。
- 建议：大规模多语言开放数据、标准化评价协议、可解释 AI。

[11] Xavier D, Felizardo V, Ferreira B, et al. Voice analysis in Parkinson's disease - a systematic literature review. *Artificial Intelligence in Medicine*. 2025;163:103109. DOI: 10.1016/j.artmed.2025.103109.
- 2019-2023 年 106 项研究；94.34% 聚焦诊断，11.32% 聚焦预后（原文比例有重叠/表述问题，报告中只引用“绝大多数聚焦诊断”）。
- 总体认为语音分析用于诊断/预后“性能令人满意”，但研究异质性大。

[12] Hossain MA, Amenta F. Machine Learning-Based Classification of Parkinson's Disease Patients Using Speech Biomarkers. *Journal of Parkinson's Disease*. 2024;14(1):95-109. DOI: 10.3233/JPD-230002.
- 252 人、756 个实例、754 维特征；10 折交叉验证。
- 最佳 pipeline：准确率 85.09%，精确率 92%，敏感度 91%，F1 89%，AUC 90%。
- 仅为内部交叉验证，不能代表外部泛化。

[13] Iyer A, Kemp A, Rahmatallah Y, et al. A machine learning method to process voice samples for identification of Parkinson's disease. *Scientific Reports*. 2023;13:20615. DOI: 10.1038/s41598-023-47568-w.
- 50 例专科确诊 PD + 50 例健康对照；个人电话采集的持续元音 /a/；自然环境。
- 使用 Inception V3 迁移学习分析频谱图；深度模型优于手工特征。
- 说明“电话/手机采集”在真实场景可行，但样本仍为病例对照。

[14] Costantini G, Cesarini V, Di Leo P, et al. Artificial Intelligence-Based Voice Assessment of Patients with Parkinson's Disease Off and On Treatment: Machine vs. Deep-Learning Comparison. *Sensors*. 2023;23(4):2293. DOI: 10.3390/s23042293.
- 自建意大利语数据，含早期未用药 PD、中晚期 L-Dopa 治疗 PD 和健康对照；比较 ML 与 CNN。
- 特征选择（CFS）影响显著；ML 与 DL 性能可比，KNN/SVM/Naive Bayes 略优。
- 提示“早期 PD”与“进展期 PD”的声学表现不同，需分层建模。

[15] Di Cesare MG, Perpetuini D, Cardone D, Merla A. Machine Learning-Assisted Speech Analysis for Early Detection of Parkinson's Disease: A Study on Speaker Diarization and Classification Techniques. *Sensors*. 2024;24(5):1499. DOI: 10.3390/s24051499.
- MDVR-KCL；MFCC + GTCC；电话自发对话做说话人日志；测试准确率 92.3%。
- 说明真实电话场景可行，但样本小（37 人）。

[16] Tougui I, Zakroum M, Karrakchou O, Ghogho M. Transformer-based transfer learning on self-reported voice recordings for Parkinson's disease diagnosis. *Scientific Reports*. 2024;14:30131. DOI: 10.1038/s41598-024-81824-x.
- mPower 自报语音数据；CNN/Transformer 迁移学习；Transformer 预训练于语音数据表现最佳。
- 标签为自报，存在标签噪声；不能等同于临床诊断。

[17] Sedigh Malekroodi H, Madusanka N, Lee BI, Yi M. Speech-Based Parkinson's Detection Using Pre-Trained Self-Supervised Automatic Speech Recognition (ASR) Models and Supervised Contrastive Learning. *Bioengineering*. 2025;12(7):728. DOI: 10.3390/bioengineering12070728.
- NeuroVoz；Wav2Vec 2.0 / HuBERT + 监督对比学习；与 MFCC、eGeMAPS 基线比较。
- Wav2Vec 2.0 + SupCon 最佳 F1 90.0%，HuBERT + SupCon 88.99%；CE 模型 AUC 0.84-0.89。
- 说明 SSL 特征在单语料内很强，但跨语料仍是开放问题。

[18] Berg D, Postuma RB, Adler CH, et al. MDS research criteria for prodromal Parkinson's disease. *Movement Disorders*. 2015;30(12):1600-1611. DOI: 10.1002/mds.26431.
- 前驱期 PD 研究标准；基于贝叶斯风险计算；标志物需有前瞻性证据；语音未列入正式标志物。
- 仅用于研究，不用于临床诊断。

[19] Postuma RB, Berg D, Stern M, et al. MDS clinical diagnostic criteria for Parkinson's disease. *Movement Disorders*. 2015;30(12):1591-1601. DOI: 10.1002/mds.26424.
- 临床诊断核心：运动迟缓 + 静止性震颤或肌强直；结合绝对排除、红旗征、支持征；分“临床确诊”“很可能”。
- 语音不是诊断标准的一部分。

[20] UCI Machine Learning Repository. Parkinsons [Dataset]. 2007. DOI: 10.24432/C59C74. https://archive.ics.uci.edu/dataset/174/parkinsons
- 31 人（23 PD）、195 条录音、22 维特征；CC BY 4.0。
- 注意：记录级数据，每人有约 6 条录音；随机切分会导致受试者泄漏。

[21] pdkit/pdkit. https://github.com/pdkit/pdkit
- MIT；43 stars（2026-10-27 快照）；PD 数字评估数据科学工具包；语音不是唯一模态。
- 可复用数据处理、特征、评估框架；不提供临床级语音模型。

[22] K-STMLab/SSL4PR. https://github.com/K-STMLab/SSL4PR
- Interspeech 2024 论文代码；12 stars；GitHub 未声明许可证。
- 基础模型 + 语音增强 + 注意力池化；研究参考价值高；商用复用需作者授权。

[23] cuiluofu/VoxTransPD. https://github.com/cuiluofu/VoxTransPD
- MIT；MSR 2026 Data and Tool Showcase；多尺度卷积、跨模态注意力、自适应权重；模块化 PyTorch。
- 0 stars；新项目，尚无临床验证。

[24] Aadithyaar22/Parkinson-s_voice_detection. https://github.com/Aadithyaar22/Parkinson-s_voice_detection
- README 声称 MIT，但 GitHub API 未识别许可证；2 stars。
- wav2vec2-XLS-R 冻结特征 + 逻辑回归；5 折受试者分组交叉验证；意大利数据 61 人/831 条。
- README 自报 CV AUC 0.972，但跨语料：意大利→UCI AUC 0.31，UCI→意大利 0.55；说明模型学到的可能是语言/语料特征。
- 工程实现（质控、SHAP、纵向跟踪、部署）有参考价值；不能作为临床证据。

[25] audEERING/openSMILE. https://github.com/audeering/opensmile
- 854 stars；eGeMAPS 等声学特征标准工具；许可证为 audEERING 自有条款（研究免费，商用需授权）。
- 商用前必须做许可审查，不能默认 Apache/MIT。

[26] Aastha2104/Parkinson-Disease-Prediction. https://github.com/Aastha2104/Parkinson-Disease-Prediction
- 197 stars；无许可证；UCI 195 条记录；随机训练/测试切分；声称 98% 准确率。
- 典型“高准确率、低临床价值”项目；记录级泄漏，不能复用于临床。

[27] imadtoubal/Parkinson-s-Disease-Classification-from-Speech-Data. https://github.com/imadtoubal/Parkinson-s-Disease-Classification-from-Speech-Data
- MIT；14 stars；UCI 数据 + 多种 sklearn 分类器；教学/基线价值。

[28] Zaozzz/SM-CBNet. https://github.com/Zaozzz/SM-CBNet
- ICIC 2025；SMOTE-ENN + CNN+BiLSTM；13 stars；无许可证；研究代码。

[29] SpeechBrain. https://github.com/speechbrain/speechbrain
- Apache 2.0；语音工具链；可用于 SSL 特征、微调、推理；不是 PD 专用。

[30] 国家药监局. 人工智能医用软件产品分类界定指导原则（2021 年第 47 号）. https://www.nmpa.gov.cn/xxgk/ggtg/ylqxggtg/ylqxqtggtg/20210708111147171.html
- 按预期用途、数据处理、算法成熟度、风险分级；辅助诊断/治疗决策的 AI 医用软件通常按第三类管理；仅健康管理、不提供诊断结论的可能不作为医疗器械。最终以药监部门界定为准。

[31] 中华医学会神经病学分会. 中国帕金森病的诊断标准（2016 版）. *中华神经科杂志*. 2016;49(4):268-271.
- 临床诊断标准；以运动迟缓、静止性震颤、肌强直等为核心；语音不是诊断依据。

[32] 中华医学会神经病学分会帕金森病及运动障碍学组. 中国帕金森病治疗指南（第四版）. *中华神经科杂志*. 2020;53(12):973-986.
- 强调早期识别、综合治疗、全程管理；未推荐语音作为独立筛查工具。

[33] Collins GS, Moons KGM, Dhiman P, et al. TRIPOD+AI statement: updated guidance for reporting clinical prediction models that use regression or machine learning methods. *BMJ*. 2024;385:e078378. DOI: 10.1136/bmj-2023-078378.
- 预测模型报告规范；要求明确人群、结局、预测因子、样本量、缺失数据、模型性能、校准、公平性等。

[34] Wolff RF, Moons KGM, Riley RD, et al. PROBAST: A Tool to Assess the Risk of Bias and Applicability of Prediction Model Studies. *Annals of Internal Medicine*. 2019;170(1):51-58. DOI: 10.7326/M18-1376.
- 偏倚风险与应用性评估工具； Participants、Predictors、Outcome、Analysis 四个域。

[35] Vasey B, Nagendran M, Campbell B, et al. Reporting guideline for the early-stage clinical evaluation of decision support systems driven by artificial intelligence: DECIDE-AI. *Nature Medicine*. 2022;28(5):924-933. DOI: 10.1038/s41591-022-01887-7.
- AI 决策支持系统早期临床评价报告规范；强调人机交互、临床工作流、安全性、失败模式。

[36] 《中华人民共和国个人信息保护法》. http://www.npc.gov.cn/npc/c30834/202108/a8c4e3672c74491a80b53a172bb753fe.shtml
- 医疗健康、生物识别信息属于敏感个人信息；需特定目的、充分必要性、严格保护措施和单独同意；跨境传输需满足法定条件。

## 二、关键数字速查

- UCI：31 人（23 PD）、195 条、22 特征、CC BY 4.0。
- mPower：9,520 同意；6,805 入组问卷；1,087 自报 PD；5,826 语音参与者；65,022 条语音；仅持续 /a/；自报标签。
- PC-GITA：100 人（50 PD/50 HC）；西班牙语；多任务；申请获取。
- NeuroVoz：112 人（54 PD/58 HC）；西班牙语；ON 状态；多任务；公开；89% 内部基准、83% 跨语料。
- MDVR-KCL：37 人（16 PD/21 HC）；英语；朗读+对话；CC BY 4.0。
- Italian：78 人（28 PD/50 HC）；831 条；意大利语；IEEE DataPort 登录获取。
- 真实场景性能：WavLM 82.21% → 68.58%（原始）→ 83.33%（增强）；HuBERT+WavLM 集成 88.33%。
- 系统综述：69 项（2020-2025.9）；验证不规范、数据异质是主要问题。
- 诊断延迟：平均约 2.75 年（NeuroVoz 引用）。
- 言语障碍比例：约 89%（PC-GITA/NeuroVoz 引用）。

## 三、使用说明

- 报告是“快速证据扫描 + 架构评估”，不是系统综述或 meta 分析。
- 所有性能数字均为原文报告，未复现；跨研究不可直接比较。
- GitHub stars、许可证为 2026-10-27 快照，可能变化。
- 监管分类为技术建议，不构成法律意见；正式路径需与药监部门沟通。
