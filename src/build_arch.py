# -*- coding: utf-8 -*-
"""Readable portrait reference-architecture figure (replaces the dense 2400px version)."""
from pathlib import Path
from PIL import Image, ImageDraw
from build_figures import font, text_block, arrow, BG, INK, MUTED, LINE, NAVY, BLUE, TEAL, ORANGE, WHITE

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "assets"
ASSETS.mkdir(exist_ok=True)

LIGHT_BLUE = "#E8F1FA"
LIGHT_TEAL = "#E6F4F1"
LIGHT_ORANGE = "#FBE9E3"
LIGHT_GRAY = "#EEF2F7"


def architecture_v2():
    W, H = 1600, 1400
    img = Image.new("RGB", (W, H), BG)
    d = ImageDraw.Draw(img)

    d.text((50, 34), "参考架构：九层 + 双通道 + 临床闭环", font=font(44, True), fill=NAVY)
    d.text((50, 96), "端云协同 · 质控前置 · 可解释与 SSL 融合 · 医生最终决策", font=font(23), fill=MUTED)

    x0, label_w, content_x, content_w = 40, 245, 310, 1240
    y = 150
    bands = [
        ("①", "场景层", NAVY, "#E9EDF4", 70,
         "社区筛查 · 基层门诊 · 专科随访 · 科研队列"),
        ("②", "采集层", BLUE, LIGHT_BLUE, 98,
         "小程序 / App / 平板 · 任务引导（/a/、DDK、朗读）· 设备校准 · 6 维质控 · 重录反馈"),
        ("③", "接入与安全", BLUE, LIGHT_BLUE, 82,
         "API 网关 · OIDC/SAML · 同意管理 · RBAC/ABAC · 审计与加密"),
        ("④", "数据平台", BLUE, LIGHT_BLUE, 92,
         "原始音频（WORM）· 元数据/标签库 · 特征库（训练=推理）· 数据版本 · 去标识化"),
    ]

    def simple_band(num, label, color, fill, h, text):
        nonlocal y
        d.rounded_rectangle((x0 + 4, y + 4, x0 + label_w + 4, y + h - 8 + 4), radius=12, fill="#E1E6EE")
        d.rounded_rectangle((x0, y, x0 + label_w, y + h - 8), radius=12, fill=color)
        d.text((x0 + 18, y + (h - 8 - 34) / 2), f"{num} {label}", font=font(29, True), fill=WHITE)
        d.rounded_rectangle((content_x, y, content_x + content_w, y + h - 8), radius=12, fill=fill, outline=LINE, width=2)
        # vertically center one/two lines
        fs = font(27)
        lines = text_block(d, content_x + 22, y + 10, content_w - 44, text, fs, fill=INK, leading=34)
        y += h

    for b in bands:
        simple_band(*b)

    # AI core band
    ai_h = 300
    d.rounded_rectangle((x0 + 4, y + 4, x0 + label_w + 4, y + ai_h - 8 + 4), radius=12, fill="#D9EDE9")
    d.rounded_rectangle((x0, y, x0 + label_w, y + ai_h - 8), radius=12, fill=TEAL)
    d.text((x0 + 18, y + 18), "⑤ AI 核心", font=font(29, True), fill=WHITE)
    d.text((x0 + 18, y + 62), "双通道", font=font(22), fill="#D7F0EB")
    d.text((x0 + 18, y + 92), "融合/校准", font=font(22), fill="#D7F0EB")
    d.rounded_rectangle((content_x, y, content_x + content_w, y + ai_h - 8), radius=12, fill=WHITE, outline=LINE, width=2)

    d.text((content_x + 22, y + 14), "预处理与质控", font=font(23, True), fill=NAVY)
    d.text((content_x + 190, y + 17), "VAD · 去混响 · 降噪 · 响度归一化 · 质量门控", font=font(21), fill=INK)

    a = (content_x + 22, y + 58, content_x + 608, y + 188)
    b = (content_x + 632, y + 58, content_x + 1218, y + 188)
    d.rounded_rectangle(a, radius=10, fill=LIGHT_BLUE, outline="#B7D2EC", width=2)
    d.rounded_rectangle(b, radius=10, fill=LIGHT_TEAL, outline="#B7DED8", width=2)
    d.text((a[0] + 14, a[1] + 10), "通道 A｜可解释声学", font=font(22, True), fill=NAVY)
    d.text((b[0] + 14, b[1] + 10), "通道 B｜SSL 表征", font=font(22, True), fill=TEAL)
    text_block(d, a[0] + 14, a[1] + 44, 550,
               "eGeMAPS / Praat · F0/jitter/shimmer\nHNR/CPP · DFA/RPDE · GBDT/LR + SHAP",
               font(21), fill=INK, leading=28)
    text_block(d, b[0] + 14, b[1] + 44, 550,
               "Wav2Vec2 / HuBERT / WavLM\n层加权/注意力池化 · 冻结/微调",
               font(21), fill=INK, leading=28)

    fus = (content_x + 22, y + 202, content_x + 1218, y + 282)
    d.rounded_rectangle(fus, radius=10, fill=LIGHT_ORANGE, outline="#E8C2B3", width=2)
    d.text((fus[0] + 14, fus[1] + 8), "融合 · 校准 · 拒识", font=font(22, True), fill=ORANGE)
    d.text((fus[0] + 230, fus[1] + 11), "晚期融合 / 堆叠 · Platt/isotonic · 置信度/OOD · 风险分层（低/中/高）",
           font=font(20), fill=INK)
    arrow(d, [(a[0] + 290, a[3]), (a[0] + 290, fus[1])], color=ORANGE, width=3)
    arrow(d, [(b[0] + 290, b[3]), (b[0] + 290, fus[1])], color=ORANGE, width=3)
    y += ai_h

    for b in [
        ("⑥", "服务与集成", BLUE, LIGHT_BLUE, 90,
         "在线推理 · 批处理 · FHIR/HL7 · 模型注册/版本 · 端云 / 院内私有化"),
        ("⑦", "临床工作流", ORANGE, LIGHT_ORANGE, 90,
         "风险分层 · 医生复核（最终决策）· 转诊建议 · 纵向趋势 · 患者报告"),
        ("⑧", "治理与运营", NAVY, "#E9EDF4", 80,
         "MLOps · 漂移监控 · 安全/等保 · QMS/NMPA · 不良事件"),
        ("⑨", "评估与证据", TEAL, LIGHT_TEAL, 92,
         "分析效度 → 临床效度 → 临床效用 → 监管/卫生经济 · TRIPOD+AI / PROBAST / DECIDE-AI"),
    ]:
        simple_band(*b)

    # bottom note
    note = (x0, 1185, 1560, 1248)
    d.rounded_rectangle(note, radius=28, fill=NAVY)
    d.text((x0 + 28, 1202), "设计原则：原始音频默认不出端 · 医生最终决策 · 不提供诊断 · 全版本可追溯",
           font=font(23, True), fill=WHITE)

    d.text((50, 1320), "来源：项目组架构评估（2026-10-27）。图为概念架构，不表示具体部署拓扑。",
           font=font(16), fill=MUTED)

    img.save(ASSETS / "fig1_architecture.png", quality=95)
    print("wrote", ASSETS / "fig1_architecture.png")


if __name__ == "__main__":
    architecture_v2()
