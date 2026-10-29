# -*- coding: utf-8 -*-
"""Generate report figures with Pillow (no matplotlib dependency)."""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

FONT_REG = "C:/Windows/Fonts/msyh.ttc"
FONT_BOLD = "C:/Windows/Fonts/msyhbd.ttc"

# palette
BG = "#F6F8FB"
INK = "#172033"
MUTED = "#5B677A"
LINE = "#CBD5E1"
NAVY = "#1F3A5F"
BLUE = "#2F5D8A"
TEAL = "#177E73"
ORANGE = "#C45B3C"
LIGHT_BLUE = "#E8F1FA"
LIGHT_TEAL = "#E6F4F1"
LIGHT_ORANGE = "#FBE9E3"
LIGHT_GRAY = "#EEF2F7"
WHITE = "#FFFFFF"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REG, size)


def wrap(draw, text, fnt, max_w):
    lines = []
    for para in text.split("\n"):
        cur = ""
        for ch in para:
            if draw.textlength(cur + ch, font=fnt) <= max_w:
                cur += ch
            else:
                if cur:
                    lines.append(cur)
                cur = ch
        if cur:
            lines.append(cur)
    return lines


def text_block(draw, x, y, w, text, fnt, fill=INK, leading=None, bullet=False, max_lines=None):
    leading = leading or int(fnt.size * 1.55)
    lines = wrap(draw, text, fnt, w)
    if max_lines:
        lines = lines[:max_lines]
    for i, line in enumerate(lines):
        yy = y + i * leading
        if bullet:
            draw.ellipse((x, yy + fnt.size * 0.42, x + 7, yy + fnt.size * 0.42 + 7), fill=fill)
            draw.text((x + 20, yy), line, font=fnt, fill=fill)
        else:
            draw.text((x, yy), line, font=fnt, fill=fill)
    return y + len(lines) * leading


def header(draw, box, num, title, color=NAVY, h=58):
    x1, y1, x2, _ = box
    draw.rounded_rectangle((x1, y1, x2, y1 + h), radius=14, fill=color)
    draw.text((x1 + 18, y1 + 12), num, font=font(24, True), fill=WHITE)
    draw.text((x1 + 62, y1 + 12), title, font=font(25, True), fill=WHITE)


def arrow(draw, pts, color=BLUE, width=5, dashed=False, head=14):
    if dashed:
        # draw dashed polyline
        for i in range(len(pts) - 1):
            (x1, y1), (x2, y2) = pts[i], pts[i + 1]
            dx, dy = x2 - x1, y2 - y1
            dist = max((dx * dx + dy * dy) ** 0.5, 1)
            seg = 16
            t = 0
            while t < dist:
                t2 = min(t + 10, dist)
                a = (x1 + dx * t / dist, y1 + dy * t / dist)
                b = (x1 + dx * t2 / dist, y1 + dy * t2 / dist)
                draw.line([a, b], fill=color, width=width)
                t += seg
    else:
        draw.line(pts, fill=color, width=width, joint="curve")
    # arrowhead at final segment
    (x1, y1), (x2, y2) = pts[-2], pts[-1]
    dx, dy = x2 - x1, y2 - y1
    dist = max((dx * dx + dy * dy) ** 0.5, 1)
    ux, uy = dx / dist, dy / dist
    px, py = -uy, ux
    tip = (x2, y2)
    base = (x2 - ux * head, y2 - uy * head)
    left = (base[0] + px * head * 0.55, base[1] + py * head * 0.55)
    right = (base[0] - px * head * 0.55, base[1] - py * head * 0.55)
    draw.polygon([tip, left, right], fill=color)


def architecture():
    W, H = 2400, 1560
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    # title
    d.text((80, 42), "声纹帕金森早期筛查：参考架构", font=font(46, True), fill=NAVY)
    d.text((80, 106), "端云协同 · 双通道模型 · 质控前置 · 临床闭环", font=font(24), fill=MUTED)

    # scenario pills
    scenarios = ["社区 / 体检筛查", "基层门诊分诊", "专科随访监测", "科研多中心队列"]
    pills = []
    x = 80
    for s in scenarios:
        box = (x, 158, x + 530, 218)
        pills.append(box)
        d.rounded_rectangle(box, radius=30, fill=WHITE, outline=LINE, width=2)
        d.text((x + 28, 172), s, font=font(24, True), fill=BLUE)
        x += 560

    # scenario bus down to acquisition
    bus_y = 240
    d.line((230, 218, 230, 262), fill=BLUE, width=5)
    d.line((230, bus_y, 2040, bus_y), fill=BLUE, width=4)
    for i, box in enumerate(pills):
        cx = (box[0] + box[2]) // 2
        d.line((cx, 218, cx, bus_y), fill=LINE, width=2)
    arrow(d, [(230, bus_y), (230, 270)], color=BLUE, width=5)

    # main columns
    y1, y2 = 270, 1060
    c1 = (80, y1, 380, y2)
    c2 = (410, y1, 670, y2)
    c3 = (700, y1, 1030, y2)
    c4 = (1060, y1, 1710, y2)
    c5 = (1740, y1, 2040, y2)
    c6 = (2070, y1, 2320, y2)

    for box in (c1, c2, c3, c4, c5, c6):
        d.rounded_rectangle((box[0] + 5, box[1] + 6, box[2] + 5, box[3] + 6), radius=18, fill="#E3E8F0")
        d.rounded_rectangle(box, radius=18, fill=WHITE, outline=LINE, width=2)

    header(d, c1, "①", "采集层")
    header(d, c2, "②", "接入与安全")
    header(d, c3, "③", "数据平台")
    header(d, c4, "④", "AI 核心", color=TEAL)
    header(d, c5, "⑤", "服务与集成")
    header(d, c6, "⑥", "临床工作流", color=ORANGE)

    # column 1
    f = font(21)
    yy = 350
    for t in ["小程序 / App / 诊所平板", "任务：/a/、DDK、朗读", "设备校准与环境噪声检测", "6 维质控：时长/SNR/削波", "实时反馈与重录引导", "采集协议 / 设备版本化", "受试者 ID / 时间 / 设备", "无障碍 / 方言提示"]:
        yy = text_block(d, 100, yy, 258, t, f, bullet=True) + 6

    # column 2
    yy = 350
    for t in ["API 网关 / WAF", "OIDC / SAML 身份", "同意与授权管理", "RBAC / ABAC 权限", "审计日志 / 加密传输", "数据分类分级", "密钥 / 证书管理"]:
        yy = text_block(d, 430, yy, 220, t, f, bullet=True) + 6

    # column 3
    yy = 350
    for t in ["原始音频对象存储（WORM）", "元数据 / 标签库", "特征库：训练=推理同源", "数据版本 / 快照 / 回溯", "去标识化 / 权限隔离", "数据血缘 / 审计", "保留期限 / 删除"]:
        yy = text_block(d, 720, yy, 290, t, f, bullet=True) + 8

    # column 4 subpanels
    pre = (1080, 345, 1690, 455)
    d.rounded_rectangle(pre, radius=12, fill=LIGHT_GRAY, outline=LINE, width=2)
    d.text((1098, 356), "预处理与质控", font=font(22, True), fill=NAVY)
    d.text((1098, 392), "VAD · 去混响 · 降噪 · 响度归一化 · 质量门控", font=font(19), fill=INK)
    d.text((1098, 422), "保留增强前/后两路特征，避免“增强即失真”", font=font(18), fill=MUTED)

    a = (1080, 480, 1375, 790)
    b = (1395, 480, 1690, 790)
    d.rounded_rectangle(a, radius=12, fill=LIGHT_BLUE, outline="#B7D2EC", width=2)
    d.rounded_rectangle(b, radius=12, fill=LIGHT_TEAL, outline="#B7DED8", width=2)
    d.text((1098, 492), "通道 A｜可解释声学", font=font(21, True), fill=NAVY)
    d.text((1413, 492), "通道 B｜SSL 表征", font=font(21, True), fill=TEAL)

    aa = ["eGeMAPS / Praat 特征", "F0 / jitter / shimmer", "HNR / CPP", "DFA / RPDE / PPE", "DDK 速率与规律性", "GBDT / LR + SHAP"]
    yy = 532
    for t in aa:
        yy = text_block(d, 1098, yy, 255, t, font(19), bullet=True) + 4
    bb = ["Wav2Vec2 / HuBERT", "WavLM", "层加权 + 注意力池化", "冻结线性探针 / 端到端微调", "噪声/设备/语料域增强", "输出表征与置信度"]
    yy = 532
    for t in bb:
        yy = text_block(d, 1413, yy, 255, t, font(19), bullet=True) + 4

    # arrows pre -> A/B
    arrow(d, [(1230, 455), (1230, 480)], color=TEAL, width=4)
    arrow(d, [(1540, 455), (1540, 480)], color=TEAL, width=4)
    # arrows A/B -> fusion
    fusion = (1080, 815, 1690, 1015)
    d.rounded_rectangle(fusion, radius=12, fill=LIGHT_ORANGE, outline="#E8C2B3", width=2)
    d.text((1098, 827), "融合 · 校准 · 拒识", font=font(22, True), fill=ORANGE)
    d.text((1098, 864), "晚期融合 / 堆叠；Platt / isotonic / 温度缩放", font=font(18), fill=INK)
    d.text((1098, 894), "集成方差 / conformal / OOD 检测", font=font(18), fill=INK)
    d.text((1098, 924), "低置信度 → 建议复测 / 转诊，不硬判", font=font(18), fill=INK)
    d.text((1098, 954), "输出：校准概率 + 风险分层（低/中/高）", font=font(18, True), fill=ORANGE)
    arrow(d, [(1230, 790), (1230, 815)], color=ORANGE, width=4)
    arrow(d, [(1540, 790), (1540, 815)], color=ORANGE, width=4)

    # column 5
    yy = 350
    for t in ["在线推理 API", "异步批处理 / 队列", "FHIR / HL7 / LOINC", "模型注册 / 版本 / 回滚", "模型卡 / 数据卡", "灰度 / 影子模式", "云端 / 院内私有化"]:
        yy = text_block(d, 1760, yy, 255, t, f, bullet=True) + 8

    # column 6
    yy = 350
    for t in ["风险分层：低 / 中 / 高", "医生复核（最终决策）", "转诊建议 / 4 周内", "纵向趋势 / 个体基线", "报告：风险 + 解释", "患者报告 / 随访", "随访结局回流"]:
        yy = text_block(d, 2090, yy, 210, t, f, bullet=True) + 8

    # main flow arrows
    mid = 650
    arrow(d, [(380, mid), (410, mid)], color=BLUE, width=5)
    arrow(d, [(670, mid), (700, mid)], color=BLUE, width=5)
    arrow(d, [(1030, 405), (1060, 405)], color=TEAL, width=5)
    arrow(d, [(1710, 915), (1740, 915)], color=ORANGE, width=5)
    arrow(d, [(2040, mid), (2070, mid)], color=ORANGE, width=5)

    # bottom governance / evaluation
    gov = (80, 1110, 1180, 1265)
    ev = (1210, 1110, 2320, 1265)
    for box, color, title, body in [
        (gov, NAVY, "⑦ 治理与运营", "MLOps · 数据/模型/阈值版本 · 漂移监控 · 安全/等保 · QMS/NMPA · 不良事件"),
        (ev, TEAL, "⑧ 评估与证据", "分析效度 → 临床效度 → 临床效用 → 监管/卫生经济；TRIPOD+AI / PROBAST / DECIDE-AI"),
    ]:
        d.rounded_rectangle(box, radius=16, fill=LIGHT_GRAY, outline=LINE, width=2)
        d.rounded_rectangle((box[0], box[1], box[0] + 8, box[3]), radius=4, fill=color)
        d.text((box[0] + 28, box[1] + 18), title, font=font(23, True), fill=color)
        text_block(d, box[0] + 28, box[1] + 58, box[2] - box[0] - 56, body, font(19), fill=INK)

    # clinical -> evidence
    arrow(d, [(2195, 1060), (2195, 1110)], color=TEAL, width=5)
    # evidence -> AI feedback
    arrow(d, [(1260, 1110), (1260, 1082), (1360, 1082), (1360, 1015)], color=TEAL, width=4, dashed=True)
    d.text((1372, 1062), "再校准 / 再训练", font=font(17), fill=TEAL)

    # bottom note
    note = (80, 1305, 2320, 1375)
    d.rounded_rectangle(note, radius=30, fill=NAVY)
    d.text((110, 1323), "设计原则：原始音频默认不出端 · 医生最终决策 · 不提供诊断 · 全版本可追溯", font=font(23, True), fill=WHITE)

    d.text((80, 1468), "来源：项目组架构评估（2026-10-27）。图为概念架构，不表示具体部署拓扑。", font=font(17), fill=MUTED)
    img.save(ASSETS / "fig1_architecture.png", quality=95)
    print("wrote", ASSETS / "fig1_architecture.png")


def evidence_ladder():
    W, H = 2000, 1150
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((80, 50), "证据阶梯：从“能测”到“值得用”", font=font(44, True), fill=NAVY)
    d.text((80, 112), "每一级都需要不同的研究设计；跳级是临床 AI 最常见的失败原因", font=font(23), fill=MUTED)

    base_y = 920
    steps = [
        dict(x=100, h=330, color=BLUE, fill=LIGHT_BLUE, num="①", title="分析效度",
             q="测出来的东西稳定吗？",
             items=["重测信度 / ICC", "设备与操作者一致性", "特征定义与质控"]),
        dict(x=530, h=430, color=TEAL, fill=LIGHT_TEAL, num="②", title="临床效度",
             q="能否区分目标人群？",
             items=["受试者级外部验证", "敏感度/特异度/校准", "疾病对照与亚组"]),
        dict(x=960, h=530, color=ORANGE, fill=LIGHT_ORANGE, num="③", title="临床效用",
             q="是否改变临床决策？",
             items=["转诊率 / 诊断时间", "医生依从性 / 患者结局", "决策曲线 / 成本"]),
        dict(x=1390, h=630, color=NAVY, fill="#E9EDF4", num="④", title="监管与卫生经济",
             q="能否上市、支付、持续？",
             items=["QMS / 临床评价 / 注册", "上市后监测 / 变更控制", "预算影响 / 成本效果"]),
    ]
    for s in steps:
        x, h = s["x"], s["h"]
        box = (x, base_y - h, x + 380, base_y)
        d.rounded_rectangle((x + 6, box[1] + 6, x + 386, base_y + 6), radius=16, fill="#E3E8F0")
        d.rounded_rectangle(box, radius=16, fill=s["fill"], outline=s["color"], width=3)
        d.rounded_rectangle((x, box[1], x + 380, box[1] + 64), radius=16, fill=s["color"])
        d.text((x + 18, box[1] + 14), s["num"], font=font(24, True), fill=WHITE)
        d.text((x + 62, box[1] + 14), s["title"], font=font(25, True), fill=WHITE)
        d.text((x + 24, box[1] + 84), s["q"], font=font(21, True), fill=s["color"])
        yy = box[1] + 128
        for it in s["items"]:
            yy = text_block(d, x + 24, yy, 330, it, font(19), bullet=True) + 8

    # arrows between steps
    for i in range(3):
        x1 = steps[i]["x"] + 380
        x2 = steps[i + 1]["x"]
        y = base_y - 80 - i * 40
        arrow(d, [(x1 + 8, y), (x2 - 8, y)], color=MUTED, width=4)

    # gates
    gates = [("G0", 290, 990), ("G1", 720, 990), ("G2", 1150, 990), ("G3", 1580, 990)]
    for label, x, y in gates:
        d.ellipse((x - 34, y - 34, x + 34, y + 34), fill=WHITE, outline=NAVY, width=3)
        d.text((x - 20, y - 17), label, font=font(19, True), fill=NAVY)

    # current position
    d.rounded_rectangle((100, 1020, 1080, 1088), radius=18, fill="#FFF4D6", outline="#E0B84C", width=2)
    d.text((122, 1038), "当前项目位置：① 与 ② 之间；尚无 ③/④ 证据", font=font(23, True), fill="#8A5A00")

    d.text((80, 1110), "来源：项目组根据 TRIPOD+AI、PROBAST、DECIDE-AI 与临床评价实践整理。", font=font(16), fill=MUTED)
    img.save(ASSETS / "fig2_evidence.png", quality=95)
    print("wrote", ASSETS / "fig2_evidence.png")


def roadmap():
    W, H = 2200, 1100
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((80, 45), "实施路线图：18 个月见分晓，30 个月看注册", font=font(42, True), fill=NAVY)
    d.text((80, 105), "先证据、后规模；每个阶段门都可以触发转向", font=font(23), fill=MUTED)

    left = 330
    right = 2100
    top = 210
    row_h = 120
    months = 36

    def x_of(m):
        return left + (right - left) * m / months

    # grid and month labels
    for m in range(0, 37, 3):
        x = x_of(m)
        d.line((x, top - 20, x, top + 5 * row_h + 30), fill="#E2E8F0", width=2)
        d.text((x - 18, top - 52), f"{m}", font=font(18), fill=MUTED)
    d.text((right - 80, top - 88), "月", font=font(18), fill=MUTED)

    rows = [
        ("临床与数据", ["P0 方案/伦理", "P1 回顾 600–800", "P2 前瞻 silent 1,000+", "P3 临床效用", "P4 上市后"]),
        ("算法与模型", ["基线复现", "双通道 v1", "外部验证/校准", "锁定/变更控制", "漂移再验证"]),
        ("工程与平台", ["MVP", "数据平台/质控", "EMR/FHIR 集成", "试点部署", "规模化"]),
        ("合规与注册", ["分类预沟通", "QMS 起步", "临床评价", "注册申报", "PMS/年度报告"]),
    ]
    phases = [
        (0, 3, "#8FB3D9"), (3, 9, "#5E93C7"), (9, 18, "#2F6FA8"), (18, 30, "#1F4E79"), (30, 36, "#163A5A")
    ]
    for i, (name, labels) in enumerate(rows):
        y = top + i * row_h
        d.text((80, y + 36), name, font=font(22, True), fill=NAVY)
        # phase bands
        for j, (a, b, color) in enumerate(phases):
            x1, x2 = x_of(a), x_of(b)
            d.rounded_rectangle((x1 + 3, y + 12, x2 - 3, y + row_h - 24), radius=10, fill=color)
            label = labels[j]
            # fit text
            fnt = font(18, True)
            while d.textlength(label, font=fnt) > (x2 - x1 - 20) and fnt.size > 12:
                fnt = font(fnt.size - 1, True)
            d.text((x1 + 10, y + 28), label, font=fnt, fill=WHITE)

    # milestones
    gates = [(3, "G0"), (9, "G1"), (18, "G2"), (30, "G3")]
    for m, label in gates:
        x = x_of(m)
        y = top + 4 * row_h + 34
        d.polygon([(x, y - 16), (x + 16, y), (x, y + 16), (x - 16, y)], fill=ORANGE)
        d.text((x - 18, y + 24), label, font=font(19, True), fill=ORANGE)

    # phase legend
    legend_y = 1000
    d.text((80, legend_y), "阶段：", font=font(18, True), fill=MUTED)
    xx = 160
    for label, color in [("P0 立项", "#8FB3D9"), ("P1 平台", "#5E93C7"), ("P2 多中心", "#2F6FA8"), ("P3 注册", "#1F4E79"), ("P4 上市后", "#163A5A")]:
        d.rounded_rectangle((xx, legend_y - 2, xx + 26, legend_y + 22), radius=5, fill=color)
        d.text((xx + 34, legend_y - 2), label, font=font(17), fill=INK)
        xx += 190

    d.text((80, 1060), "注：时间为建议排期，实际取决于伦理、入组速度、监管沟通与数据伙伴。", font=font(16), fill=MUTED)
    img.save(ASSETS / "fig3_roadmap.png", quality=95)
    print("wrote", ASSETS / "fig3_roadmap.png")


def performance():
    W, H = 1800, 920
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)
    d.text((80, 45), "真实世界条件让性能显著掉点，语音增强与集成可恢复", font=font(38, True), fill=NAVY)
    d.text((80, 105), "WavLM Base / HuBERT+WavLM 集成，PC-GITA → e-PC-GITA；准确率（%）", font=font(21), fill=MUTED)

    data = [
        ("干净 PC-GITA", 82.2, "#8FB3D9"),
        ("真实场景\n原始录音", 68.6, "#D98C72"),
        ("+ 语音增强", 83.3, "#5E93C7"),
        ("+ 双模型集成", 88.3, "#177E73"),
    ]
    left, right = 160, 1680
    top, bottom = 230, 760
    # y grid
    for v in range(0, 101, 20):
        y = bottom - (bottom - top) * v / 100
        d.line((left, y, right, y), fill="#E2E8F0", width=2)
        d.text((100, y - 12), str(v), font=font(18), fill=MUTED)
    d.line((left, top, left, bottom), fill=LINE, width=2)

    n = len(data)
    slot = (right - left) / n
    bar_w = 170
    for i, (label, value, color) in enumerate(data):
        cx = left + slot * (i + 0.5)
        x1, x2 = cx - bar_w / 2, cx + bar_w / 2
        y = bottom - (bottom - top) * value / 100
        d.rounded_rectangle((x1, y, x2, bottom), radius=8, fill=color)
        d.text((cx - 30, y - 42), f"{value:.1f}", font=font(30, True), fill=color)
        # label
        lines = label.split("\n")
        for j, line in enumerate(lines):
            tw = d.textlength(line, font=font(19))
            d.text((cx - tw / 2, bottom + 22 + j * 28), line, font=font(19), fill=INK)

    # annotation for drop
    x1 = left + slot * 0.5 + bar_w / 2
    x2 = left + slot * 1.5 - bar_w / 2
    y1 = bottom - (bottom - top) * 82.2 / 100
    y2 = bottom - (bottom - top) * 68.6 / 100
    d.line((x1 + 8, y1 + 10, x2 - 8, y2 - 10), fill=ORANGE, width=3)
    d.rectangle((x1 + 14, y1 + 10, x1 + 162, y1 + 46), fill=BG)
    d.text((x1 + 18, y1 + 18), "−13.6 pts", font=font(20, True), fill=ORANGE)

    d.text((80, 860), "来源：La Quatra et al., Interspeech 2024（arXiv:2406.16128）。仅用于说明域偏移，不代表所有模型/语料的平均效应。", font=font(16), fill=MUTED)
    img.save(ASSETS / "fig4_performance.png", quality=95)
    print("wrote", ASSETS / "fig4_performance.png")


if __name__ == "__main__":
    architecture()
    evidence_ladder()
    roadmap()
    performance()
