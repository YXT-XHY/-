# -*- coding: utf-8 -*-
"""Build the research inventory workbook."""
from pathlib import Path
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "deliverables" / "声纹帕金森早期筛查_调研清单与测算.xlsx"
OUT.parent.mkdir(exist_ok=True)

NAVY = "1F3A5F"
TEAL = "177E73"
LIGHT = "F2F5F9"
WHITE = "FFFFFF"
GRAY = "5B677A"

thin = Side(style="thin", color="CBD5E1")
border = Border(left=thin, right=thin, top=thin, bottom=thin)
header_fill = PatternFill("solid", fgColor=NAVY)
header_font = Font(name="微软雅黑", size=10, bold=True, color=WHITE)
body_font = Font(name="微软雅黑", size=9, color="172033")
muted_font = Font(name="微软雅黑", size=8, color=GRAY)
link_font = Font(name="微软雅黑", size=9, color="0563C1", underline="single")


def setup_sheet(ws, title, headers, widths, notes=None):
    ws.sheet_view.showGridLines = False
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
    c = ws.cell(1, 1, title)
    c.font = Font(name="微软雅黑", size=14, bold=True, color=NAVY)
    c.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 28
    if notes:
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
        c = ws.cell(2, 1, notes)
        c.font = muted_font
        c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.row_dimensions[2].height = 22
        header_row = 3
    else:
        header_row = 2
    for i, h in enumerate(headers, 1):
        c = ws.cell(header_row, i, h)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
        c.border = border
        ws.column_dimensions[get_column_letter(i)].width = widths[i - 1]
    ws.row_dimensions[header_row].height = 30
    ws.freeze_panes = ws.cell(header_row + 1, 1)
    return header_row


def add_rows(ws, header_row, rows, link_col=None):
    for r_idx, row in enumerate(rows, header_row + 1):
        for c_idx, val in enumerate(row, 1):
            c = ws.cell(r_idx, c_idx, val)
            c.font = body_font
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.border = border
            if r_idx % 2 == 0:
                c.fill = PatternFill("solid", fgColor=LIGHT)
        if link_col:
            c = ws.cell(r_idx, link_col)
            if c.value:
                url = str(c.value)
                if url.startswith("https://doi.org"):
                    label = "DOI"
                elif "github.com" in url:
                    label = "GitHub"
                elif "arxiv.org" in url:
                    label = "arXiv"
                else:
                    label = "链接"
                c.value = label
                c.hyperlink = url
                c.font = link_font
                c.alignment = Alignment(horizontal="center", vertical="center")
        ws.row_dimensions[r_idx].height = 70


wb = Workbook()
wb.calculation.fullCalcOnLoad = True

# ---------------------------------------------------------------- cover / notes
ws = wb.active
ws.title = "说明"
ws.sheet_view.showGridLines = False
ws.merge_cells("A1:F1")
c = ws["A1"]
c.value = "声纹帕金森早期筛查：调研清单与测算"
c.font = Font(name="微软雅黑", size=18, bold=True, color=NAVY)
c.alignment = Alignment(vertical="center")
ws.row_dimensions[1].height = 36

lines = [
    ("编制日期", "2026-10-27"),
    ("版本", "v1.0"),
    ("用途", "配合《声纹帕金森早期筛查_项目调研与架构评估报告.docx》使用"),
    ("数据口径", "所有性能数字来自原文；未复现；跨研究不可直接比较。"),
    ("GitHub 快照", "Stars 与许可证为 2026-10-27 的 GitHub API 快照，可能变化。"),
    ("监管声明", "分类与合规为技术建议，不构成法律意见；正式路径需与药监部门沟通。"),
    ("免责声明", "本工作簿用于内部立项讨论，不构成医疗、法律或投资建议。"),
]
r = 3
for k, v in lines:
    ws.cell(r, 1, k).font = Font(name="微软雅黑", size=9, bold=True, color=GRAY)
    ws.cell(r, 2, v).font = Font(name="微软雅黑", size=9, color="172033")
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
    ws.cell(r, 2).alignment = Alignment(wrap_text=True, vertical="top")
    ws.row_dimensions[r].height = 30
    r += 1

ws.cell(r + 1, 1, "工作表").font = Font(name="微软雅黑", size=11, bold=True, color=NAVY)
sheet_desc = [
    ("数据集", "公开语音数据集的规模、标签、许可与适用性"),
    ("GitHub项目", "开源项目的类型、方法、Stars、许可与可复用性"),
    ("论文", "关键论文的数据、方法、结果与局限"),
    ("架构评分", "五方案七维度加权评分（可修改权重）"),
    ("筛查收益", "不同患病率/特异度下的 PPV/NPV 测算（公式可改）"),
]
r += 2
for name, desc in sheet_desc:
    ws.cell(r, 1, name).font = Font(name="微软雅黑", size=9, bold=True, color=NAVY)
    ws.cell(r, 2, desc).font = Font(name="微软雅黑", size=9, color="172033")
    ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=6)
    r += 1
for col, w in zip("ABCDEF", [16, 22, 22, 22, 22, 22]):
    ws.column_dimensions[col].width = w

# ---------------------------------------------------------------- datasets
ws = wb.create_sheet("数据集")
headers = ["数据集", "规模", "语言/任务", "标签/状态", "获取与许可", "适用性", "主要风险", "链接"]
widths = [18, 30, 34, 26, 30, 28, 34, 10]
hr = setup_sheet(ws, "公开数据集对比", headers, widths,
                 "注：公开数据以已确诊患者 vs 健康对照为主，不能单独支撑“早期筛查”临床声称。")
rows = [
    ["UCI PD", "31 人（23 PD）、195 条", "英语；持续元音 /a/；22 维特征表", "临床 PD/健康", "CC BY 4.0；公开下载", "基线、教学、特征验证", "样本极小；仅特征表；记录级数据易泄漏", "https://doi.org/10.24432/C59C74"],
    ["mPower", "9,520 人同意；5,826 人贡献语音；65,022 条", "美式英语；10 秒持续 /a/", "自报 PD/非 PD", "Synapse 受控访问；需数据使用协议", "大规模预训练、真实设备鲁棒性", "标签自报；单任务；人群偏 iPhone 用户", "https://doi.org/10.1038/sdata.2016.11"],
    ["PC-GITA", "100 人（50 PD/50 HC）", "哥伦比亚西班牙语；元音、DDK、词、句、朗读、独白", "神经科医生诊断", "申请获取；研究用途", "多任务基准、跨语言验证", "获取受限；病例对照；录音条件干净", "https://aclanthology.org/L14-1549/"],
    ["NeuroVoz", "112 人（54 PD/58 HC）", "卡斯蒂利亚西班牙语；元音、DDK、16 句听重复、独白", "临床诊断；ON 状态；GRBAS/UPDRS/H-Y", "公开数据集；许可以数据页为准", "当前最好的公开多任务基准", "ON 状态；单语种；无前瞻；54 例 PD 仍偏小", "https://doi.org/10.1038/s41597-024-04186-z"],
    ["MDVR-KCL", "37 人（16 PD/21 HC）", "英语；朗读段落、电话自发对话", "早期与进展期；H&Y/UPDRS", "CC BY 4.0", "真实电话场景、跨语料", "样本小；对话内容不可控", "https://doi.org/10.5281/zenodo.2867216"],
    ["Italian", "78 人（28 PD/50 HC）、831 条", "意大利语；朗读、/pa/、/ta/、元音", "临床诊断", "IEEE DataPort 开放获取（需登录）", "跨语言验证", "样本小；任务偏少；许可需核对", "https://doi.org/10.21227/aw6b-tg17"],
    ["UCI 远程监测", "42 人、约 5,875 条（文献常用）", "英语；持续 /a/；UPDRS", "纵向 UPDRS", "CC BY 4.0", "进展监测、纵向建模", "不是诊断/早筛；标签为 UPDRS", "https://doi.org/10.24432/C59C74"],
]
add_rows(ws, hr, rows, link_col=8)
ws.auto_filter.ref = f"A{hr}:H{hr + len(rows)}"

# ---------------------------------------------------------------- github
ws = wb.create_sheet("GitHub项目")
headers = ["项目", "类型", "方法/数据", "Stars", "许可", "可复用性", "评价", "链接"]
widths = [18, 14, 34, 8, 18, 10, 38, 10]
hr = setup_sheet(ws, "GitHub 项目对比", headers, widths,
                 "注：Stars/许可证为 2026-10-27 快照；许可证以仓库 LICENSE 为准。")
rows = [
    ["PDkit", "工具包", "PD 数字评估数据科学；多模态", 43, "MIT", "高", "数据管理、特征、评估框架可借鉴；不是语音专用", "https://github.com/pdkit/pdkit"],
    ["SSL4PR", "研究代码", "Wav2Vec2/HuBERT/WavLM/Whisper + 语音增强", 12, "未声明", "中", "Interspeech 2024，方法参考价值高；商用需作者授权", "https://github.com/K-STMLab/SSL4PR"],
    ["VoxTransPD", "研究工具", "多尺度卷积、跨模态注意力、自适应权重", 0, "MIT", "中", "MSR 2026 工具论文；模块化好，但很新、无临床验证", "https://github.com/cuiluofu/VoxTransPD"],
    ["Aadithya 原型", "工程原型", "wav2vec2-XLS-R 冻结特征 + 逻辑回归", 2, "未识别（README 称 MIT）", "中", "质控、SHAP、纵向跟踪、部署有参考价值；跨语料失败，不能当证据", "https://github.com/Aadithyaar22/Parkinson-s_voice_detection"],
    ["openSMILE", "特征工具", "eGeMAPS 等", 854, "自有条款", "高", "事实标准；研究免费、商用需授权，不能默认开源", "https://github.com/audeering/opensmile"],
    ["Aastha 教学", "教学项目", "UCI 195 条 + sklearn", 197, "无", "低", "随机切分 + 98% 准确率，典型泄漏案例", "https://github.com/Aastha2104/Parkinson-Disease-Prediction"],
    ["imadtoubal", "教学项目", "UCI + 多分类器", 14, "MIT", "低–中", "适合做基线复现，不适合临床", "https://github.com/imadtoubal/Parkinson-s-Disease-Classification-from-Speech-Data"],
    ["SM-CBNet", "研究代码", "SMOTE-ENN + CNN+BiLSTM", 13, "无", "低–中", "类别不平衡处理可参考；无外部验证", "https://github.com/Zaozzz/SM-CBNet"],
    ["SpeechBrain", "工具包", "语音/SSL 训练与推理", "高", "Apache 2.0", "高", "可作为 SSL 微调与部署底座；不是 PD 专用", "https://github.com/speechbrain/speechbrain"],
]
add_rows(ws, hr, rows, link_col=8)
ws.auto_filter.ref = f"A{hr}:H{hr + len(rows)}"

# ---------------------------------------------------------------- papers
ws = wb.create_sheet("论文")
headers = ["编号", "作者/年份", "标题", "期刊/会议", "数据/方法", "关键结果", "主要局限", "DOI/URL"]
widths = [6, 20, 46, 22, 32, 34, 30, 10]
hr = setup_sheet(ws, "关键论文与证据", headers, widths,
                 "注：性能数字均为原文报告，未复现；跨研究不可直接比较。")
rows = [
    [1, "Little 2007", "Exploiting nonlinear recurrence and fractal scaling properties for voice disorder detection", "BioMedical Engineering OnLine", "UCI：31 人、195 条；非线性特征", "奠定语音特征路线", "样本极小；特征表非原始音频", "https://doi.org/10.1186/1475-925X-6-23"],
    [2, "Little 2009", "Suitability of dysphonia measurements for telemonitoring of Parkinson's disease", "IEEE TBME", "远程监测队列", "证明远程监测可行", "不是诊断/早筛", "https://doi.org/10.1109/TBME.2008.2005954"],
    [3, "Tsanas 2010", "Accurate telemonitoring of Parkinson's disease progression by noninvasive speech tests", "IEEE TBME", "42 人、数千条；回归 UPDRS", "进展监测误差约 2 分", "纵向监测，非早筛", "https://doi.org/10.1109/TBME.2009.2036000"],
    [4, "Orozco-Arroyave 2014", "New Spanish speech corpus database for the analysis of people suffering from Parkinson's disease", "LREC 2014", "PC-GITA：50 PD/50 HC；多任务", "建立西语基准", "申请获取；病例对照", "https://aclanthology.org/L14-1549/"],
    [5, "Bot 2016", "The mPower study, Parkinson disease mobile data collected using ResearchKit", "Scientific Data", "9,520 人同意；手机 App", "大规模真实世界语音", "自报标签；仅持续 /a/", "https://doi.org/10.1038/sdata.2016.11"],
    [6, "Mendes-Laureano 2024", "NeuroVoz: a Castillian Spanish corpus of parkinsonian speech", "Scientific Data", "54 PD/58 HC；多任务、多标注", "公开基准 89%；跨语料 83%", "ON 状态；单语种；无前瞻", "https://doi.org/10.1038/s41597-024-04186-z"],
    [9, "La Quatra 2024", "Exploiting Foundation Models and Speech Enhancement for Parkinson's Disease Detection from Speech in Real-World Operative Conditions", "Interspeech 2024", "PC-GITA 100 人 + e-PC-GITA 40 人；SSL+增强", "82.2% → 68.6% → 83.3%；集成 88.3%", "外部集仅 40 人；同语料", "https://arxiv.org/abs/2406.16128"],
    [10, "Sedigh 2025 (review)", "Voice-Based Detection of Parkinson's Disease Using Machine and Deep Learning Approaches: A Systematic Review", "Bioengineering", "69 项研究（2020–2025.9）", "经典 ML 小样本强；DL 更稳健；验证不规范", "研究异质；不能合并", "https://doi.org/10.3390/bioengineering12111279"],
    [11, "Xavier 2025 (review)", "Voice analysis in Parkinson's disease - a systematic literature review", "Artificial Intelligence in Medicine", "106 项研究（2019–2023）", "绝大多数聚焦诊断；性能满意但异质性大", "预后研究少", "https://doi.org/10.1016/j.artmed.2025.103109"],
    [12, "Hossain 2024", "Machine Learning-Based Classification of Parkinson's Disease Patients Using Speech Biomarkers", "Journal of Parkinson's Disease", "252 人、756 实例；10 折 CV", "准确率 85.1%，AUC 0.90", "无外部验证", "https://doi.org/10.3233/JPD-230002"],
    [13, "Iyer 2023", "A machine learning method to process voice samples for identification of Parkinson's disease", "Scientific Reports", "50 PD/50 HC 电话 /a/；Inception V3", "深度模型优于手工特征", "病例对照；电话场景", "https://doi.org/10.1038/s41598-023-47568-w"],
    [14, "Costantini 2023", "Artificial Intelligence-Based Voice Assessment of Patients with Parkinson's Disease Off and On Treatment: Machine vs. Deep-Learning Comparison", "Sensors", "早期/进展期 PD + HC；ML vs CNN", "ML 与 DL 可比；CFS 有效", "自建数据；样本有限", "https://doi.org/10.3390/s23042293"],
    [15, "Di Cesare 2024", "Machine Learning-Assisted Speech Analysis for Early Detection of Parkinson's Disease: A Study on Speaker Diarization and Classification Techniques", "Sensors", "MDVR-KCL 37 人；MFCC+GTCC", "测试准确率 92.3%", "样本小；电话对话", "https://doi.org/10.3390/s24051499"],
    [16, "Tougui 2024", "Transformer-based transfer learning on self-reported voice recordings for Parkinson's disease diagnosis", "Scientific Reports", "mPower 自报语音；Transformer 迁移", "优于从头训练", "自报标签；单任务", "https://doi.org/10.1038/s41598-024-81824-x"],
    [17, "Sedigh 2025 (SSL)", "Speech-Based Parkinson's Detection Using Pre-Trained Self-Supervised Automatic Speech Recognition (ASR) Models and Supervised Contrastive Learning", "Bioengineering", "NeuroVoz；Wav2Vec2/HuBERT + SupCon", "F1 90.0%/88.99%", "单语料；ON 状态", "https://doi.org/10.3390/bioengineering12070728"],
    [18, "Berg 2015", "MDS research criteria for prodromal Parkinson's disease", "Movement Disorders", "前驱期研究标准", "语音未列入正式标志物", "仅研究用途", "https://doi.org/10.1002/mds.26431"],
    [19, "Postuma 2015", "MDS clinical diagnostic criteria for Parkinson's disease", "Movement Disorders", "临床诊断标准", "运动迟缓 + 震颤/强直为核心", "语音不是诊断标准", "https://doi.org/10.1002/mds.26424"],
]
add_rows(ws, hr, rows, link_col=8)
ws.auto_filter.ref = f"A{hr}:H{hr + len(rows)}"

# ---------------------------------------------------------------- scoring
ws = wb.create_sheet("架构评分")
headers = ["方案", "临床证据", "泛化鲁棒", "隐私合规", "工程可行", "成本扩展", "临床工作流", "可解释维护", "加权分"]
widths = [28, 12, 12, 12, 12, 12, 12, 12, 12]
hr = setup_sheet(ws, "架构方案加权评分（1–5 分；可修改权重与评分）", headers, widths,
                 "加权分 = SUMPRODUCT(评分, 权重) / 5，满分 100。权重为专家判断，建议立项会校准。")
# weights row
ws.cell(hr + 1, 1, "权重").font = Font(name="微软雅黑", size=9, bold=True, color=WHITE)
ws.cell(hr + 1, 1).fill = PatternFill("solid", fgColor=TEAL)
ws.cell(hr + 1, 1).border = border
weights = [25, 20, 15, 15, 10, 10, 5]
for i, w in enumerate(weights, 2):
    c = ws.cell(hr + 1, i, w)
    c.font = Font(name="微软雅黑", size=9, bold=True, color=WHITE)
    c.fill = PatternFill("solid", fgColor=TEAL)
    c.alignment = Alignment(horizontal="center")
    c.border = border
c = ws.cell(hr + 1, 9, "=SUM(B%d:H%d)" % (hr + 1, hr + 1))
c.font = Font(name="微软雅黑", size=9, bold=True, color=WHITE)
c.fill = PatternFill("solid", fgColor=TEAL)
c.alignment = Alignment(horizontal="center")
c.border = border

scores = [
    ("A 轻量特征 + 云 API", [4, 2, 2, 5, 5, 3, 5]),
    ("B SSL 微调 + 云推理", [4, 4, 2, 3, 2, 3, 2]),
    ("C 端云协同 + 双通道", [4, 4, 4, 3, 3, 4, 4]),
    ("D 全端侧", [3, 3, 5, 2, 4, 3, 3]),
    ("E 院内私有化 + 双通道", [4, 4, 5, 4, 2, 5, 3]),
]
for r_idx, (name, vals) in enumerate(scores, hr + 2):
    c = ws.cell(r_idx, 1, name)
    c.font = body_font
    c.border = border
    for i, v in enumerate(vals, 2):
        c = ws.cell(r_idx, i, v)
        c.font = body_font
        c.alignment = Alignment(horizontal="center")
        c.border = border
    c = ws.cell(r_idx, 9, f"=SUMPRODUCT(B{r_idx}:H{r_idx},$B${hr+1}:$H${hr+1})/5")
    c.font = Font(name="微软雅黑", size=9, bold=True, color=NAVY)
    c.alignment = Alignment(horizontal="center")
    c.border = border
    c.number_format = "0.0"
    if r_idx % 2 == 0:
        for i in range(1, 10):
            ws.cell(r_idx, i).fill = PatternFill("solid", fgColor=LIGHT)

note_r = hr + 8
ws.merge_cells(start_row=note_r, start_column=1, end_row=note_r, end_column=9)
c = ws.cell(note_r, 1, "说明：E 分最高，适合首个临床验证站点；C 是最平衡的产品形态；A 适合 MVP/降级；B 是研究主力；D 适合隐私极敏感/无网场景。")
c.font = muted_font
c.alignment = Alignment(wrap_text=True, vertical="top")
ws.row_dimensions[note_r].height = 36

# ---------------------------------------------------------------- PPV calculator
ws = wb.create_sheet("筛查收益")
headers = ["患病率", "敏感度", "特异度", "PPV", "NPV", "每 10 万人阳性数", "每 10 万人真阳性数"]
widths = [14, 12, 12, 12, 12, 20, 20]
hr = setup_sheet(ws, "筛查收益测算（可修改蓝色单元格）", headers, widths,
                 "公式：PPV = Sens×P / [Sens×P + (1−Spec)×(1−P)]；NPV = Spec×(1−P) / [Spec×(1−P) + (1−Sens)×P]。")
rows = [
    [0.003, 0.85, 0.90],
    [0.01, 0.85, 0.90],
    [0.05, 0.85, 0.90],
    [0.10, 0.85, 0.90],
    [0.003, 0.85, 0.95],
    [0.01, 0.85, 0.95],
    [0.05, 0.85, 0.95],
    [0.10, 0.85, 0.95],
]
for r_idx, row in enumerate(rows, hr + 1):
    for i, v in enumerate(row, 1):
        c = ws.cell(r_idx, i, v)
        c.font = body_font
        c.border = border
        c.alignment = Alignment(horizontal="center")
        if i == 1:
            c.number_format = "0.0%"
        else:
            c.number_format = "0%"
        if i <= 3:
            c.fill = PatternFill("solid", fgColor="E8F1FA")
    p = f"A{r_idx}"; sens = f"B{r_idx}"; spec = f"C{r_idx}"
    ws.cell(r_idx, 4, f"={sens}*{p}/({sens}*{p}+(1-{spec})*(1-{p}))").number_format = "0.0%"
    ws.cell(r_idx, 5, f"={spec}*(1-{p})/({spec}*(1-{p})+(1-{sens})*{p})").number_format = "0.0%"
    ws.cell(r_idx, 6, f"=100000*({sens}*{p}+(1-{spec})*(1-{p}))").number_format = "#,##0"
    ws.cell(r_idx, 7, f"=100000*{sens}*{p}").number_format = "#,##0"
    for i in range(4, 8):
        c = ws.cell(r_idx, i)
        c.font = Font(name="微软雅黑", size=9, bold=(i == 4), color=NAVY if i == 4 else "172033")
        c.border = border
        c.alignment = Alignment(horizontal="center")
        if r_idx % 2 == 0:
            c.fill = PatternFill("solid", fgColor=LIGHT)

note_r = hr + len(rows) + 2
ws.merge_cells(start_row=note_r, start_column=1, end_row=note_r, end_column=7)
c = ws.cell(note_r, 1, "解读：全人群（0.3%）即使敏感度 85%、特异度 90%，PPV 也只有约 2.5%；因此必须做高危富集或定位为转诊优先级，而不是“筛出所有病人”。")
c.font = muted_font
c.alignment = Alignment(wrap_text=True, vertical="top")
ws.row_dimensions[note_r].height = 40

# print settings
for ws in wb.worksheets:
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.sheet_properties.pageSetUpPr.fitToPage = True

wb.save(OUT)
print("saved", OUT)
