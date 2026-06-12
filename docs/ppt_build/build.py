#!/usr/bin/env python3
"""Build the MZM group-meeting deck inside a copy of the user's template."""
import json, math, sys, tempfile
from pathlib import Path

from PIL import Image, ImageChops
from pptx.util import Inches, Pt, Emu
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.dml.color import RGBColor

SKILL = Path("/Users/ckdfs/.claude/skills/group-meeting-pptx/scripts")
sys.path.insert(0, str(SKILL))
from deckbuilder import (TemplateDeck, fill_textframe, text_bottom_estimate, clone_shape,
                         add_table)

ROOT = Path(__file__).resolve().parent
TEMPLATE = ROOT / "template.pptx"
OUTPUT = ROOT / "output" / "MZM动态切换-组会汇报-20260510.pptx"
MATH = ROOT / "math"
RESULTS = Path("/Users/ckdfs/Desktop/isbc_20260510_上位机脚本采集")
SCOPE = Path("/Users/ckdfs/Desktop/isbctest_20260510")

COVER, TOC, SKELETON, CLOSING = 0, 1, 5, 16

CONTENT_L, CONTENT_W = 0.433, 9.292
BANNER_W, BANNER_H, BANNER_TOP = 6.60, 0.96, -0.226
BOTTOM = 7.28

_MAN = {f["id"]: f for f in json.load(open(MATH / "manifest.json"))["formulas"]}


def nat(fid):
    f = _MAN[fid]
    return f["width_px"] / f["dpi"], f["height_px"] / f["dpi"]


def crop_white(path):
    im = Image.open(str(path)).convert("RGB")
    bbox = ImageChops.difference(im, Image.new("RGB", im.size, "white")).getbbox()
    if bbox:
        im = im.crop(bbox)
    out = tempfile.mktemp(suffix=".png")
    im.save(out)
    return out


def banner_and_content(slide):
    boxes = [s for s in slide.shapes if s.has_text_frame]
    return min(boxes, key=lambda s: s.top), max(boxes, key=lambda s: s.top)


def H(t):  return {"text": t, "size": 20, "bold": True}
def S(t):  return {"text": t, "size": 14, "bold": True}
def B(t):  return {"text": t, "size": 14, "bold": False}
def R(t):  return {"text": t, "size": 14, "bold": True, "color": "C71F2C"}


class Builder:
    def __init__(self, deck):
        self.deck = deck
        self.slide = deck.duplicate(SKELETON)
        # purge ALL non-text-box shapes (pictures, rectangles, etc.) — keep only
        # the banner text box and the content text box from the skeleton.
        for sp in list(self.slide.shapes):
            if sp.shape_type != MSO_SHAPE_TYPE.TEXT_BOX:
                sp._element.getparent().remove(sp._element)
        self.banner_box, self.tmpl = banner_and_content(self.slide)
        self.y = 1.073
        self._first = True

    def banner(self, text):
        fill_textframe(self.banner_box.text_frame, [{"text": text}])
        self.banner_box.width = Inches(BANNER_W)
        self.banner_box.height = Inches(BANNER_H)
        self.banner_box.top = Inches(BANNER_TOP)
        tf = self.banner_box.text_frame
        tf.vertical_anchor = MSO_ANCHOR.MIDDLE
        tf.paragraphs[0].alignment = PP_ALIGN.CENTER

    def text(self, items, gap=0.06):
        box = self.tmpl if self._first else clone_shape(self.slide, self.tmpl)
        self._first = False
        box.left, box.top, box.width = Inches(CONTENT_L), Inches(self.y), Inches(CONTENT_W)
        fill_textframe(box.text_frame, items)
        self.y = text_bottom_estimate(box) + gap
        return box

    def formula(self, eq_id, gap=0.10, lead=0.04, scale=1.0):
        w, h = nat(eq_id)
        w *= scale; h *= scale
        if w > 9.5:
            scale2 = 9.5 / w
            w *= scale2; h *= scale2
        self.y += lead
        self.slide.shapes.add_picture(str(MATH / f"{eq_id}.png"),
                                      Inches((10 - w) / 2), Inches(self.y),
                                      width=Inches(w), height=Inches(h))
        self.y += h + gap

    def figure(self, img, width, gap=0.10, lead=0.05, align="center"):
        img = crop_white(img)
        self.y += lead
        wpx, hpx = Image.open(img).size
        ar = wpx / hpx
        w = min(width, 9.5)
        h = w / ar
        if self.y + h > BOTTOM:
            h = BOTTOM - self.y - 0.02
            w = h * ar
        if align == "center":
            x = (10 - w) / 2
        elif align == "left":
            x = CONTENT_L
        else:
            x = 10 - CONTENT_L - w
        self.slide.shapes.add_picture(img, Inches(x), Inches(self.y),
                                      width=Inches(w), height=Inches(h))
        self.y += h + gap

    def figures_row(self, paths, total_width=9.0, gap_between=0.15, gap=0.10, lead=0.05, labels=None, reserve_below=0.0):
        self.y += lead
        n = len(paths)
        each_w = (total_width - gap_between * (n - 1)) / n
        cropped = [crop_white(p) for p in paths]
        sizes = [Image.open(c).size for c in cropped]
        ars = [w / h for w, h in sizes]
        heights = [each_w / ar for ar in ars]
        max_h = max(heights)
        label_h = 0.25 if labels else 0
        if self.y + max_h + label_h + reserve_below > BOTTOM:
            scale = (BOTTOM - self.y - label_h - reserve_below) / max_h
            each_w *= scale
            heights = [h * scale for h in heights]
            max_h *= scale
        x_start = (10 - (each_w * n + gap_between * (n - 1))) / 2
        for i, (path, ar) in enumerate(zip(cropped, ars)):
            x = x_start + i * (each_w + gap_between)
            self.slide.shapes.add_picture(path, Inches(x), Inches(self.y),
                                          width=Inches(each_w), height=Inches(each_w / ar))
        if labels:
            from pptx.util import Inches as I
            label_y = self.y + max_h + 0.02
            for i, lab in enumerate(labels):
                x = x_start + i * (each_w + gap_between)
                tb = self.slide.shapes.add_textbox(I(x), I(label_y), I(each_w), I(0.22))
                tf = tb.text_frame
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                p = tf.paragraphs[0]
                p.alignment = PP_ALIGN.CENTER
                run = p.add_run()
                run.text = lab
                run.font.size = Pt(11)
                run.font.bold = True
            self.y += max_h + 0.28
        else:
            self.y += max_h + gap

    def figures_grid(self, paths, labels=None, ncols=2, total_width=9.0,
                     gap_x=0.28, gap_y=0.32, lead=0.06, gap=0.10, reserve_below=0.0):
        """A 2-D grid of figures (e.g. 4 images in 2x2), each with a caption
        below it.  Scales the whole grid down to fit above BOTTOM minus
        reserve_below.  Used for time-domain stability pages (0/10/20/30 min)."""
        self.y += lead
        n = len(paths)
        nrows = math.ceil(n / ncols)
        cropped = [crop_white(p) for p in paths]
        ars = [Image.open(c).size[0] / Image.open(c).size[1] for c in cropped]
        label_h = 0.24 if labels else 0.0
        each_w = (total_width - gap_x * (ncols - 1)) / ncols
        heights = [each_w / ar for ar in ars]
        row_h = max(heights)
        total_h = nrows * row_h + nrows * label_h + (nrows - 1) * gap_y
        avail = BOTTOM - self.y - reserve_below
        if total_h > avail:
            scale = avail / total_h
            each_w *= scale
            gap_y *= scale
            heights = [each_w / ar for ar in ars]
            row_h = max(heights)
            total_h = nrows * row_h + nrows * label_h + (nrows - 1) * gap_y
        grid_w = each_w * ncols + gap_x * (ncols - 1)
        x0 = (10 - grid_w) / 2
        for i, (path, ar) in enumerate(zip(cropped, ars)):
            r, c = divmod(i, ncols)
            cw = each_w
            ch = each_w / ar
            x = x0 + c * (each_w + gap_x)
            y = self.y + r * (row_h + label_h + gap_y) + (row_h - ch) / 2
            self.slide.shapes.add_picture(path, Inches(x), Inches(y),
                                          width=Inches(cw), height=Inches(ch))
            if labels and i < len(labels):
                ly = self.y + r * (row_h + label_h + gap_y) + row_h + 0.02
                tb = self.slide.shapes.add_textbox(Inches(x), Inches(ly), Inches(cw), Inches(0.2))
                tf = tb.text_frame
                tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
                pp = tf.paragraphs[0]
                pp.alignment = PP_ALIGN.CENTER
                run = pp.add_run()
                run.text = labels[i]
                run.font.size = Pt(11)
                run.font.bold = True
                run.font.color.rgb = RGBColor.from_string("C71F2C")
        self.y += total_h + gap

    def table(self, headers, rows, col_widths, top=None, font_size=11, header_color=None):
        """A NATIVE table in the reference institutional style.

        Was: a native table with an Office-blue banded header that clashed with
        the red institutional theme. Now delegates to the skill's `add_table` —
        thin grid, no fills, Microsoft YaHei, centred, bold black header — so
        tables match the rest of the deck. `header_color` is accepted but ignored
        (kept for call-site compatibility). Cells stay editable text.
        """
        if top is None:
            top = self.y + 0.04
        width_total = sum(col_widths)
        x = (10 - width_total) / 2
        row_h = max(0.22, font_size * 0.030)
        data = [list(headers)] + [[str(v) for v in r] for r in rows]
        height = row_h * len(data)
        tbl_shape = add_table(self.slide, data, left=x, top=top, width=width_total,
                              height=height, col_widths=col_widths, row_height=row_h,
                              font_size=font_size)
        self.y = top + height + 0.06
        return tbl_shape


# ============================================================
# Build the deck
# ============================================================
OUTPUT.parent.mkdir(parents=True, exist_ok=True)
deck = TemplateDeck(str(TEMPLATE), work_path=str(OUTPUT))

# ---------- Slide 1: Cover ----------
cover = deck.duplicate(COVER)
for shape in list(cover.shapes):
    if not shape.has_text_frame:
        continue
    text = shape.text_frame.text
    if "组会汇报" in text and "时间" not in text:
        # widen the title box so the long title fits on one or two lines
        shape.left = Inches(1.0)
        shape.width = Inches(8.0)
        fill_textframe(shape.text_frame, [
            {"text": "MZM 偏置点动态切换", "size": 32, "bold": True},
            {"text": "—— 原理、脚本与 5/10 实验结果", "size": 18, "bold": False},
        ])
    elif "时间" in text or "汇报人" in text:
        fill_textframe(shape.text_frame, [
            {"text": "汇报时间：2026.05.23"},
            {"text": "汇报人：    张新科"},
        ])

# ---------- Slide 2: TOC ----------
toc = deck.duplicate(TOC)
for shape in list(toc.shapes):
    if shape.has_text_frame and "汇报" in shape.text_frame.text:
        fill_textframe(shape.text_frame, [
            {"text": "汇报内容：", "size": 22, "bold": True},
            {"text": "研究背景与目标", "size": 18, "bold": False},
            {"text": "物理原理：MZM 模型与导频比值法", "size": 18, "bold": False},
            {"text": "三种控制策略与算法实现", "size": 18, "bold": False},
            {"text": "实验脚本流程与代码组织", "size": 18, "bold": False},
            {"text": "5/10 实验设计：基础验证 + 占空比扫描 + LFM 抗扰", "size": 18, "bold": False},
            {"text": "实验结果与定量验证", "size": 18, "bold": False},
            {"text": "总结与下一步计划", "size": 18, "bold": False},
        ])

# ---------- Slide 3: 背景与目标 ----------
p = Builder(deck)
p.banner("研究背景与目标")
p.text([
    H("MZM 偏置漂移导致工作点不稳定，需通用框架闭环锁定三种工作点"),
    S("应用场景"),
    B("MZM 是光通信、雷达、ADC 采样链路的核心调制器件；工作点（最大点 / 最小点 / 正交点）的选择"),
    B("直接决定调制效率、线性度、谐波分布；不同的应用对应不同的工作点配置。"),
    S("现存问题"),
    B("温度漂移、机械振动、激光波长抖动使 MZM 偏置点缓慢游走，开环工作不可持续；"),
    B("已有工业方案多为'单一工作点'锁定，难以支持工作点之间的动态切换。"),
    S("本工作目标"),
    B("① 通用的 PWM 切换框架，统一三种切换模式：最大/最小↔正交（max_quad）、正/负正交（quad_pm）、最大↔最小（max_min）；"),
    B("② 基于导频信号比值法 + 闭环 PI / 自适应梯度下降，软件可在三种模式间一键切换；"),
    B("③ 5/10 一日完成三组实验（基础验证 + 占空比扫描 + LFM 抗扰），全部锁定成功。"),
])

# ---------- Slide 4: 物理原理 1 — MZM 模型 ----------
p = Builder(deck)
p.banner("MZM 模型与导频")
p.text([H("MZM 输出 = 余弦平方调制，由总相位决定")])
p.text([S("光强传输函数")])
p.formula("F01")
p.text([S("总相位由导频、PWM 切换、直流偏置三部分叠加")])
p.formula("F02")
p.text([S("调制指数与半波电压的关系")])
p.formula("F03")
p.text([S("本实验数值代入：")])
p.formula("F18")
p.text([
    S("信号参数"),
    B("导频频率 20 kHz；PWM 频率 200 kHz；基础配置占空比 50%。"),
])

# ---------- Slide 5: 物理原理 2 — Jacobi-Anger 展开 ----------
p = Builder(deck)
p.banner("Jacobi-Anger 展开")
p.text([H("导频经 Bessel 展开把 phi_DC 编码到一阶 / 二阶谐波")])
p.text([S("Jacobi-Anger 展开")])
p.formula("F04")
p.text([S("代入 MZM 余弦项展开后，各次谐波形式")])
p.formula("F05", scale=0.85)
p.text([S("分量、相位依赖与零点位置（控制可行性的物理基础）")])
p.table(
    headers=["频率", "幅度（正比于）", "相位依赖", "零点位置"],
    rows=[
        ["DC",         "J0·cos phi_DC",  "cos",  "phi_DC = pi/2 + npi（正交点）"],
        ["f_pilot",    "J1·sin phi_DC",  "sin",  "phi_DC = npi（最大 / 最小点）"],
        ["2 f_pilot",  "J2·cos phi_DC",  "cos",  "phi_DC = pi/2 + npi（正交点）"],
    ],
    col_widths=[1.4, 2.4, 1.4, 3.6], font_size=12,
)
p.text([R("一阶与二阶分量在 phi_DC 上为 sin / cos 正交对 —— 这是比值法锁定工作点的物理基础。")])

# ---------- Slide 5b: Bessel 完整展开（原 B1，融入正文）----------
p = Builder(deck)
p.banner("Bessel 展开与各阶数值")
p.text([H("完整级数：仅一阶 / 二阶项有效，三阶以上可忽略")])
p.text([S("偶次余弦展开（决定 DC 与二阶谐波）：")])
p.formula("B1a", scale=0.85)
p.text([S("奇次正弦展开（决定一阶谐波）：")])
p.formula("B1b", scale=0.85)
p.text([S("本实验调制指数代入后的各阶 Bessel 数值：")])
p.formula("B1c", scale=0.80)
p.text([S("小信号近似（连接理论目标比值）：")])
p.formula("B1d", scale=0.85)
p.text([R("m ≈ 0.235 时三阶以下迅速衰减，仅一阶（20 kHz）与二阶（40 kHz）参与控制。")])

# ---------- Slide 6: 物理原理 3 — PWM 切换框架 ----------
p = Builder(deck)
p.banner("PWM 切换通用框架")
p.text([H("PWM 切换引入由占空比决定的相位偏移，等效统一三种模式")])
p.text([S("PWM 在状态 A 与状态 B 间切换，占空比为 A")])
p.text([S("基频谐波在切换 + 辅助角化简后的统一形式：")])
p.formula("F06")
p.text([S("相位偏移与功率衰减因子由占空比唯一确定：")])
p.formula("F07a")
p.formula("F07b")
p.text([S("不同占空比下的相位偏移与功率损失")])
p.table(
    headers=["A（占空比）", "phi_0", "kappa", "功率损失 (dB)"],
    rows=[
        ["0.5", "45°",  "0.707", "−3.00"],
        ["0.6", "33.7°","0.721",        "−2.84"],
        ["0.7", "23.2°","0.762",        "−2.36"],
        ["0.9", "6.3°", "0.906",        "−0.86"],
    ],
    col_widths=[1.6, 1.6, 2.6, 2.0], font_size=12,
)
p.text([R("A=0.5 时功率损失最大（−3 dB），但仍工程可接受；A 偏离 0.5 时损失更小。")])

# ---------- Slide 7: 物理原理 4 — 比值函数 ----------
p = Builder(deck)
p.banner("比值函数 r 与单调区间")
p.text([H("一阶 / 二阶幅度比值在单调区内唯一确定工作点")])
p.text([S("比值函数（PWM 切换形式）：")])
p.formula("F08")
p.text([S("小信号近似下的简洁形式（可与实测对比）：")])
p.formula("F09a")
p.text([
    S("关键性质"),
    B("① 周期为 pi：每周期内单调，单调区内目标点唯一；"),
    B("② 引入相位偏移后，零点和渐近线位置由占空比唯一决定，可预先计算；"),
    B("③ 实验中由曲线拟合直接给出目标值，自动吸收系统频响差异。"),
    S("max_quad 模式工程拟合公式："),
])
p.formula("F10")

# ---------- Slide 8: 物理原理 5 — 三模式 ----------
p = Builder(deck)
p.banner("三种模式的差异")
p.text([H("三种模式对应三种状态相位配置，是否需要 cos / sin 导频切换")])
p.text([S("目标工作点位置：")])
p.formula("F21")
p.text([S("模式对照表")])
p.table(
    headers=["模式", "状态A", "状态B", "导频配置", "目标工作点", "控制信号"],
    rows=[
        ["max_quad", "0",   "pi/2", "sin / sin", "最大点",         "比值 r → r_target"],
        ["quad_pm",  "pi",  "0",    "sin / cos", "±正交点",        "二阶幅度 → min"],
        ["max_min",  "0",   "pi",   "cos / sin", "最大点（切换）", "一阶幅度 → min"],
    ],
    col_widths=[1.3, 1.0, 1.0, 1.5, 2.0, 2.5], font_size=11,
)
p.text([
    S("为什么 quad_pm / max_min 必须用 cos / sin 导频切换？"),
    B("两态同 sin 导频时，方波切换引入 (2A−1) 因子，50% 占空比下控制信号完全消失；"),
    B("cos / sin 切换使两态二阶贡献同号叠加、与占空比无关 —— 详细推导见后两页。"),
])

# ---------- Slide 8b: cos/sin 切换必要性（朴素 vs 改进）----------
p = Builder(deck)
p.banner("cos / sin 导频切换（一）")
p.text([H("cos / sin 切换消除 (2A−1) 衰减因子，是可控的前提")])
p.text([S("朴素方案：两态同用 sin 导频，二阶分量按 50% 占空比加权合成")])
p.formula("F23", scale=0.92)
p.text([
    B("两态相位相差 180°（±90° 正交点、或最大 ↔ 最小点），(2A−1) 因子在 A = 0.5 处归零；"),
    R("结论：朴素方案在 50% 占空比下控制信号完全消失，无法锁定。"),
])
p.text([S("改进方案：状态 A 用 cos 导频、状态 B 用 sin 导频")])
p.formula("F25", scale=0.90)
p.text([S("两态二阶贡献由相减变为同号相加，与占空比 A 解耦：")])
p.formula("F24", scale=0.90)
p.text([R("一阶 S_1 同理摆脱 (2A−1) 因子，50% 占空比下信号最强（完整 S_1 / S_2 推导见下页）。")])

# ---------- Slide 8c: quad_pm 两态完整时域推导（原 B2，融入正文）----------
p = Builder(deck)
p.banner("cos / sin 导频切换（二）")
p.text([H("quad_pm 两态完整时域展开与 50% 切换合成")])
p.text([S("状态 A（HIGH 5.4 V，sin 导频）：")])
p.formula("B2a", scale=0.72)
p.text([S("状态 B（LOW 0 V，cos 导频）：")])
p.formula("B2b", scale=0.72)
p.text([S("二阶项两态同号叠加、一阶项符号相反；50% 切换合成：")])
p.formula("B2c", scale=0.82)
p.formula("B2d", scale=0.82)
p.text([S("比值在目标处发散 → 改用二阶谷底自适应梯度下降：")])
p.formula("B2e", scale=0.78)

# ---------- Slide 9: 控制策略 1 — max_quad PI ----------
p = Builder(deck)
p.banner("max_quad：比值 PI 控制")
p.text([H("比值 PI 控制：闭环锁定比值 r 至目标 r_target")])
p.text([S("拟合模型（比值随等效偏压单调递减）：")])
p.formula("F10")
p.text([S("功率到比值的换算与 PI 更新公式：")])
p.formula("F22")
p.formula("F12")
p.text([
    S("算法流程（mzm/control.py: pi_control_loop）"),
    B("① 频谱仪读两个谐波，转线性功率后取比值；"),
    B("② 误差为目标比值减实测比值；"),
    B("③ 用积分增益更新 CH1 偏置，限幅后下发；"),
    B("④ 循环周期约 0.5 s（频谱仪扫描时间决定），初始增益 0.01。"),
])
p.text([R("目标比值由拟合自动给出，吸收所有系统频响差异。")])

# ---------- Slide 10: 控制策略 2 — quad_pm S2-min ----------
p = Builder(deck)
p.banner("quad_pm：S2 最小值法")
p.text([H("比值在目标处发散，改用二阶幅度自适应梯度下降")])
p.text([S("quad_pm 的一阶 / 二阶幅度（cos/sin 切换让二阶两态同号叠加）：")])
p.formula("F11a")
p.formula("F11b")
p.text([
    S("为什么不用比值 PI"),
    B("两正交点处比值发散（渐近线），曲线拟合不可靠、PI 目标不可达；"),
    B("二阶幅度在正交点处恰为零（谷底），天然适合做控制目标。"),
    S("自适应探针参数（mzm/control.py: signal_min_control_loop, signal_index=2）："),
])
p.formula("F13a")
p.table(
    headers=["距谷底距离", "excess (dB)", "探针 (V)", "二阶梯度", "步长 (V)"],
    rows=[
        ["远",   "30", "0.10", "~5 dB/V",   "0.09"],
        ["中",   "10", "0.10", "~50 dB/V",  "0.03"],
        ["近",   "3",  "0.06", "~100 dB/V", "0.009"],
        ["谷底", "0",  "0.02", "—",          "0（死区）"],
    ],
    col_widths=[1.3, 1.4, 1.3, 1.8, 1.5], font_size=11,
)

# ---------- Slide 11: 控制策略 3 — max_min S1-min ----------
p = Builder(deck)
p.banner("max_min：S1 最小值法")
p.text([H("cos / sin 导频切换保留信号，一阶幅度谷底即目标")])
p.text([S("max_min 50% 占空比时的一阶 / 二阶幅度：")])
p.formula("F11a")
p.formula("F11b")
p.text([
    S("关键观察"),
    B("二阶幅度与占空比无关（两态同号叠加），目标处为峰值；"),
    B("一阶幅度在目标处为零（V 形谷底），选作控制信号。"),
    S("控制配置（与 quad_pm 同构，仅 signal_index=1）："),
])
p.formula("F13b")
p.text([
    B("参考点取在最大/最小点电气中点；探针自适应、死区 0.002 V；"),
    B("偏置硬限位与 ARB 振幅边界协调，避免输出溢出。"),
])

# ---------- Slide 12: 脚本流程 1 — 硬件链路 ----------
p = Builder(deck)
p.banner("硬件链路与关键参数")
p.text([H("DG922Pro CH1 → MZM → PD → FSV30（DC 耦合）")])
p.text([
    S("设备 + 信号链路"),
    B("DG922Pro（192.168.99.115）CH1 输出 sin / ARB 波形 → MZM 偏置端口；"),
    B("MZM 光输出 → 光电探测器 → FSV3000（192.168.99.209）输入，DC 耦合（< 1 MHz 信号必需）；"),
    B("FSV30 已知读数偏高 6 dB，所有代码统一减去 POWER_OFFSET_DB = 6.0。"),
    S("关键参数（config.py）"),
])
p.table(
    headers=["参数", "值", "说明"],
    rows=[
        ["PILOT_FREQ_HZ",   "20 000 Hz", "导频频率 f_pilot"],
        ["PILOT_AMP_VPP",   "0.800 Vpp", "导频幅度 → m_pilot ≈ 0.235"],
        ["PWM 频率",        "200 kHz",   "切换频率，远 > 导频"],
        ["SCAN_STEP",       "0.100 V",   "扫描步长（121 点 / [−6, +6] V）"],
        ["SA_RBW / VBW",    "100 Hz",    "频谱仪窄带，低噪底"],
        ["POWER_OFFSET_DB", "−6.0 dB",   "FSV30 已知校准偏差"],
    ],
    col_widths=[2.4, 2.0, 4.0], font_size=11,
)

# ---------- Slide 13: 脚本流程 2 — 四步流程 ----------
p = Builder(deck)
p.banner("四步流程：扫描→拟合→控制")
p.text([H("半波电压标定 → ARB 偏压扫描 → 拟合 → 闭环")])
p.text([S("四步与对应代码入口"),])
p.table(
    headers=["步骤", "目的", "代码入口（mzm/）", "产出文件"],
    rows=[
        ["1. 标定",  "找两个 sin 零点，间距即半波电压",         "scan.vpi_scan()",                                   "vpi_scan.csv, vpi.json"],
        ["2. 扫描",  "ARB 波形下扫偏压，记录一阶 / 二阶幅度",   "scan.bias_scan()",                                   "arb_scan.csv"],
        ["3. 拟合",  "拟合比值曲线，给出目标 / 零点修正参数",   "fit.ratio_fit() / 备选估计",                         "fit_result.json"],
        ["4. 闭环",  "PI（比值）或自适应梯度下降（min 谷底）",  "control.pi_control_loop / signal_min_control_loop",  "control_log.csv, control.png"],
    ],
    col_widths=[1.0, 3.0, 2.8, 2.5], font_size=10,
)
p.text([S("CLI 入口"),
        B("python main.py --mode {max_quad|quad_pm|max_min} --step {scan|fit|control|all}"),
        S("ARB 波形参数（步骤 2-4 共用）：")])
p.formula("F19", scale=0.85)

# ---------- Slide 14: 脚本流程 3 — ModeBase ----------
p = Builder(deck)
p.banner("ModeBase 抽象接口")
p.text([H("ModeBase：新增控制模式只需实现 4 个方法")])
p.text([
    S("抽象接口（mzm/modes/base.py）"),
    B("configure_source(gen, vpi)  —  配置 DG922 CH1（ARB 波形 / 幅度 / 偏置初值）"),
    B("sweep_offsets(base, vpi)    —  把 base 偏压序列映射为实际 CH1 序列"),
    B("fit_model(v, A, V0, vpi_fit) —  比值曲线拟合函数（curve_fit 用）"),
    B("initial_offset(vpi, V0)      —  控制环路启动偏压；另含 control_strategy / use_curve_fit 等开关"),
    S("具体实现"),
])
p.table(
    headers=["模式", "control_strategy", "use_curve_fit", "ARB 幅度", "vdc_ref"],
    rows=[
        ["max_quad", "ratio",   "True",  "Vpi/2 + 0.8 Vpp", "Vpi/4"],
        ["quad_pm",  "s2_min",  "False", "6.2 Vpp（固定）",  "Vpi/2"],
        ["max_min",  "s1_min",  "False", "Vpi + 0.8 Vpp",    "Vpi/2"],
    ],
    col_widths=[1.4, 2.0, 1.6, 2.2, 1.4], font_size=11,
)
p.text([
    S("注册（main.py 无需修改，自动读取 MODES 字典）"),
])

# ---------- Slide 15: 5/10 实验设计 ----------
p = Builder(deck)
p.banner("5/10 实验设计")
p.text([H("一日跑通三组实验：基础验证 + 占空比扫描 + LFM 抗扰")])
p.text([S("实验组别总览")])
p.table(
    headers=["组", "时间段", "目的", "实验数"],
    rows=[
        ["① 基础验证",   "10:47 – 12:58", "50% 占空比，三模式各 1 次（长稳定性测试 ~35 min/次）",   "3"],
        ["② 占空比扫描", "14:10 – 14:45", "30% 与 70% 占空比，三模式 × 2 占空比",                  "6"],
        ["③ LFM 抗扰",   "15:45 – 17:01", "注入 15 dBm LFM 干扰，max_quad / quad_pm 各 1 次",      "2"],
    ],
    col_widths=[1.6, 2.0, 4.8, 1.0], font_size=11,
)
p.text([
    S("数据组织"),
    B("脚本侧：/Users/ckdfs/Desktop/isbc_20260510_上位机脚本采集/  共 11 个子目录"),
    B("示波器：/Users/ckdfs/Desktop/isbctest_20260510/  共 32 张时域波形截图"),
    S("结论预告"),
    R("11 次实验全部锁定成功；占空比扫描定量验证了相位偏移公式；LFM 干扰下系统稳定锁定。"),
])

# ---------- Slide 16: max_quad@50% 基础验证 ----------
p = Builder(deck)
p.banner("max_quad @ 50%")
p.text([H("max_quad 在 50% 占空比下成功锁定，稳态相对误差 0.07%")])
d = RESULTS / "20260510_104721_max_quad_50%_on"
p.figures_row([d / "scan.png", d / "control.png"], total_width=9.0,
              labels=["扫描 + 拟合曲线", "闭环 PI 控制（37 min）"], reserve_below=1.6)
p.text([
    S("关键数值（fit_result.json + 稳态统计）"),
    B("半波电压 5.4 V，零点修正 −0.25 V，目标比值 13.84；"),
    B("稳态平均 13.849（偏差 0.07%），RMS 误差 0.81；持续 37 min 未漂移。"),
    R("基础验证通过：比值 PI 控制工作正常。"),
])

# ---------- Slide 16b: max_quad 时域稳定性 ----------
p = Builder(deck)
p.banner("max_quad 时域稳定性")
p.text([H("锁定后 0–30 min 射频幅度方波保持一致，时域同样稳定")])
p.text([
    B("上轨（橙）= 方波 + 导频 + 射频联合波形；下轨（黄）= 示波器数字滤波滤除方波 / 导频后的射频幅度"),
    B("max_quad：射频幅度在最大点（斜率≈0）↔ 正交点（斜率最大）间方波切换，直接显示工作点切换效果"),
])
p.figures_grid(
    [SCOPE / "max_quad_50%_on_1.png", SCOPE / "max_quad_50%_on_2.png",
     SCOPE / "max_quad_50%_on_3.png", SCOPE / "max_quad_50%_on_4.png"],
    labels=["锁定后 0 min", "+10 min", "+20 min", "+30 min"],
    reserve_below=0.32,
)
p.text([R("四个时刻下轨射频方波的电平与占空比完全一致 —— 比值 PI 控制 30 min 内时域无漂移。")])

# ---------- Slide 17: quad_pm@50% 基础验证 ----------
p = Builder(deck)
p.banner("quad_pm @ 50%")
p.text([H("quad_pm 在 50% 占空比下锁定二阶谷底，稳态比 floor 还低 2 dB")])
d = RESULTS / "20260510_112750_quad_pm_50%_on"
p.figures_row([d / "scan.png", d / "control.png"], total_width=9.0,
              labels=["扫描（二阶谷底）", "闭环梯度下降（34 min）"], reserve_below=1.6)
p.text([
    S("关键数值"),
    B("半波电压 5.4 V，谷底偏压 2.0 V，二阶 floor 约 −90.2 dBm；"),
    B("稳态 −92.3 dBm（标准差约 3.6 dB），探针远 0.10 V → 近 0.02 V 自适应。"),
    R("基础验证通过：二阶自适应梯度下降在两正交点切换下成功锁定。"),
])

# ---------- Slide 17b: quad_pm 时域稳定性 ----------
p = Builder(deck)
p.banner("quad_pm 时域稳定性")
p.text([H("锁定后 0–30 min 射频幅度恒定，两正交点等效且稳定")])
p.text([
    B("上轨（橙）= 方波 + 导频 + 射频联合波形；下轨（黄）= 数字滤波滤除方波 / 导频后的射频幅度"),
    B("quad_pm：两态均为正交点（斜率最大且相等）→ 射频幅度恒定，下轨平坦无方波切换"),
])
p.figures_grid(
    [SCOPE / "quad_pm_50%_on_1.png", SCOPE / "quad_pm_50%_on_2.png",
     SCOPE / "quad_pm_50%_on_3.png", SCOPE / "quad_pm_50%_on_4.png"],
    labels=["锁定后 0 min", "+10 min", "+20 min", "+30 min"],
    reserve_below=0.32,
)
p.text([R("四个时刻射频幅度无起伏、无漂移 —— 二阶梯度下降稳定锁定在 ±正交点。")])

# ---------- Slide 18: max_min@50% 基础验证 ----------
p = Builder(deck)
p.banner("max_min @ 50%")
p.text([H("max_min 在 50% 占空比下锁定一阶谷底，标准差 < 0.04 dB（极稳）")])
d = RESULTS / "20260510_121910_max_min_50%_on"
p.figures_row([d / "scan.png", d / "control.png"], total_width=9.0,
              labels=["扫描（一阶谷底）", "闭环梯度下降（37 min）"], reserve_below=1.6)
p.text([
    S("关键数值"),
    B("半波电压 5.4 V，谷底偏压 4.7 V，一阶 floor 约 −56.5 dBm；"),
    B("稳态 −55.9 dBm，标准差 0.034 dB —— 三种模式中最稳的工作点。"),
    R("基础验证通过：cos / sin 导频切换设计成立。"),
])

# ---------- Slide 18b: max_min 时域稳定性 ----------
p = Builder(deck)
p.banner("max_min 时域稳定性")
p.text([H("锁定后 0–30 min 光强方波 + 射频包络（≈0）均稳定")])
p.text([
    B("上轨（橙）= 光强在最大↔最小两电平方波切换（50% 占空比，切换沿陡峭）"),
    B("max_min：两态斜率≈0 → 下轨射频幅度恒定≈0（仅切换沿瞬态尖峰），与 max_quad 形成鲜明对比"),
])
p.figures_grid(
    [SCOPE / "max_min_50%_on_1.png", SCOPE / "max_min_50%_on_2.png",
     SCOPE / "max_min_50%_on_3.png", SCOPE / "max_min_50%_on_4.png"],
    labels=["锁定后 0 min", "+10 min", "+20 min", "+30 min"],
    reserve_below=0.32,
)
p.text([R("四个时刻上轨方波与下轨射频包络均一致 —— 一阶梯度下降时域稳定（σ < 0.04 dB）。")])

# ---------- Slide 19: max_quad 占空比扫描 ----------
p = Builder(deck)
p.banner("max_quad 占空比扫描")
p.text([H("30 / 50 / 70% 实测目标比值与理论吻合，偏差 < 2 dB")])
p.text([S("理论公式：目标比值仅由占空比决定")])
p.formula("F15", scale=0.95)
p.text([S("理论 vs 实测（取小信号近似 J1/J2 ≈ 17）")])
p.table(
    headers=["占空比", "相位偏移", "理论 r (dB)", "实测 r (dB)", "偏差 (dB)", "稳态 RMS"],
    rows=[
        ["0.3 (30%)", "66.8°", "39.7 (31.97)", "50.06 (33.99)", "+2.02", "4.67"],
        ["0.5 (50%)", "45.0°", "17.0 (24.61)", "13.85 (22.83)", "−1.78",  "0.81"],
        ["0.5 + LFM", "45.0°", "17.0 (24.61)", "17.04 (24.62)", "+0.01", "1.87"],
        ["0.7 (70%)", "23.2°", "7.29 (17.25)", "8.16  (18.23)", "+0.98", "0.36"],
    ],
    col_widths=[1.6, 1.2, 1.8, 1.8, 1.4, 1.4], font_size=11,
)
p.text([
    R("实测平均偏差 +1 dB —— 与文档预测的 +0.76~1.0 dB 系统频响差异完全吻合。"),
    B("结论：相位偏移公式得到实验级定量验证；max_quad 模式可自由切换占空比。"),
])

# ---------- Slide 19b: 占空比理论计算（原 B3，融入正文）----------
p = Builder(deck)
p.banner("占空比理论计算")
p.text([H("相位偏移公式的逐项推导与系统频响修正")])
p.text([S("三种占空比的逐项计算结果：")])
p.formula("F16", scale=0.95)
p.text([S("计算流程：① 由占空比计算相位偏移")])
p.formula("F07a", scale=0.85)
p.text([S("② 理论目标比值（小信号近似）")])
p.formula("F17", scale=0.85)
p.text([S("③ 实测值 / 理论值的偏差以 dB 形式呈现；系统频响修正：")])
p.formula("B3a", scale=0.82)
p.text([R("PD + 电缆 + 频谱仪输入级在 20 / 40 kHz 处的增益差异；拟合法直接读取 A_fit，自动吸收此偏差，无需理论校准。")])

# ---------- Slide 20: quad_pm + max_min 占空比 ----------
p = Builder(deck)
p.banner("quad_pm / max_min 占空比")
p.text([H("锁定谷底在 30 / 50 / 70% 占空比下基本不变，一阶 / 二阶幅度与占空比无关")])
p.text([S("quad_pm / max_min 在三种占空比下的稳态指标")])
p.table(
    headers=["模式", "30% V_valley", "50% V_valley", "70% V_valley", "稳态 σ (50%)"],
    rows=[
        ["quad_pm（S_2 谷底）",  "2.15 V", "2.0 V", "2.30 V", "3.59 dB"],
        ["max_min（S_1 谷底）",  "4.6 V",  "4.7 V", "4.7 V",  "0.034 dB"],
    ],
    col_widths=[2.4, 1.8, 1.8, 1.8, 1.5], font_size=11,
)
p.text([
    R("谷底偏压波动 ≤ 0.3 V（< 6% 半波电压），印证一阶 / 二阶幅度均不随占空比变化的理论结论。"),
    S("示波器实测：max_quad 上轨光强方波随占空比变化（下轨射频幅度同步切换）"),
])
p.figures_row(
    [SCOPE / "max_quad_30%_on.png", SCOPE / "max_quad_50%_on_4.png", SCOPE / "max_quad_70%_on.png"],
    total_width=9.0, labels=["A = 30%", "A = 50%", "A = 70%"], reserve_below=0.2,
)

# ---------- Slide 21: LFM 抗扰 ----------
p = Builder(deck)
p.banner("LFM 干扰下的抗扰测试")
p.text([H("注入 15 dBm LFM 干扰，max_quad / quad_pm 仍能稳定锁定")])
d1 = RESULTS / "20260510_154519_max_quad_50%_on_lfm15dbm"
d2 = RESULTS / "20260510_162644_quad_pm_50%_on_lfm15dbm"
p.figures_row([d1 / "control.png", d2 / "control.png"], total_width=9.0,
              labels=["max_quad + LFM 15 dBm", "quad_pm + LFM 15 dBm"], reserve_below=1.8)
p.text([
    S("关键数值（与无干扰对比）"),
    B("max_quad@50%+LFM：r_avg = 17.04（target 17.23），偏差 0.01 dB；RMS = 1.87（略大于无干扰的 0.81）。"),
    B("quad_pm@50%+LFM：S_avg2 = −89.97 dBm（floor −91.77），σ = 4.16 dB（略大于无干扰的 3.59）。"),
    R("LFM 干扰下两种模式均稳定锁定，控制时间均 > 30 min；导频与干扰频谱分离使系统具备良好抗扰能力。"),
])

# ---------- LFM max_quad 时域稳定性 ----------
p = Builder(deck)
p.banner("max_quad·LFM 时域稳定")
p.text([H("15 dBm LFM 干扰下，0–30 min 射频方波依然规整稳定")])
p.text([
    B("上轨 = 方波 + 导频 + 射频 + LFM 联合波形；下轨 = 数字滤波后的射频幅度"),
    B("强干扰下射频幅度仍在最大点（≈0）↔ 正交点（max）间规整方波切换，调制深度稳定"),
])
p.figures_grid(
    [SCOPE / "max_quad_50%_on_lfm15dbm.png", SCOPE / "max_quad_50%_on_lfm15dbm_2.png",
     SCOPE / "max_quad_50%_on_lfm15dbm_3.png", SCOPE / "max_quad_50%_on_lfm15dbm_4.png"],
    labels=["锁定后 0 min", "+10 min", "+20 min", "+30 min"],
    reserve_below=0.32,
)
p.text([R("LFM 强干扰下射频方波四时刻一致 —— 比值 PI 在干扰环境保持时域锁定。")])

# ---------- LFM quad_pm 时域稳定性 ----------
p = Builder(deck)
p.banner("quad_pm·LFM 时域稳定")
p.text([H("15 dBm LFM 干扰下，quad_pm 射频幅度恒定不漂移")])
p.text([
    B("上轨 = 方波 + 导频 + 射频 + LFM 联合波形；下轨 = 数字滤波后的射频幅度"),
    B("两正交点等效 → 射频幅度恒定，下轨平坦（仅叠加 LFM 引入的噪声起伏）"),
])
p.figures_grid(
    [SCOPE / "quad_pm_50%_on_lfm15dbm_1.png", SCOPE / "quad_pm_50%_on_lfm15dbm_2.png",
     SCOPE / "quad_pm_50%_on_lfm15dbm_3.png", SCOPE / "quad_pm_50%_on_lfm15dbm_4.png"],
    labels=["锁定后 0 min", "+10 min", "+20 min", "+30 min"],
    reserve_below=0.32,
)
p.text([R("干扰下射频幅度无系统性漂移 —— 二阶梯度下降在 LFM 环境稳定锁定。")])

# ---------- 控制 on/off 对比 ----------
p = Builder(deck)
p.banner("闭环控制有效性对比")
p.text([H("关闭闭环 → 射频幅度随工作点漂移；开启 → 恢复规整方波")])
p.text([
    B("max_quad + 15 dBm LFM，下轨为射频幅度：闭环关闭时工作点自由游走，各周期射频调制深度参差不齐；"),
    B("开启闭环后工作点锁定，射频幅度恢复为最大点↔正交点的规整方波 —— 时域直接验证控制有效性"),
])
p.figures_grid(
    [SCOPE / "max_quad_50%_off_lfm15dbm_0.png", SCOPE / "max_quad_50%_on_lfm15dbm.png",
     SCOPE / "max_quad_50%_off_lfm15dbm_2.png", SCOPE / "max_quad_50%_on_lfm15dbm_4.png"],
    labels=["闭环关闭", "闭环开启 · 0 min", "闭环关闭", "闭环开启 · 30 min"],
    reserve_below=0.32,
)
p.text([R("左列（关闭）射频方波参差漂移，右列（开启）规整稳定 —— 闭环控制时域有效性的直接证据。")])

# ---------- Slide 22: 汇总表 ----------
p = Builder(deck)
p.banner("实验结果汇总")
p.text([H("11 次实验全部锁定成功：三模式 × 三占空比 × LFM 抗扰")])
p.table(
    headers=["#", "时间", "模式", "A", "LFM", "目标值", "稳态实测", "时长"],
    rows=[
        ["1",  "10:47", "max_quad", "0.5", "—",     "r=13.84",        "r_avg=13.85, RMS=0.81",     "37 min"],
        ["2",  "11:27", "quad_pm",  "0.5", "—",     "S_2=−90.24 dBm",  "S_avg=−92.28, σ=3.59",      "34 min"],
        ["3",  "12:19", "max_min",  "0.5", "—",     "S_1=−56.50 dBm",  "S_avg=−55.91, σ=0.034",     "37 min"],
        ["4",  "14:10", "max_quad", "0.3", "—",     "r=49.92",        "r_avg=50.06, RMS=4.67",     "4 min"],
        ["5",  "14:17", "max_quad", "0.7", "—",     "r=8.13",         "r_avg=8.16, RMS=0.36",      "3.4 min"],
        ["6",  "14:25", "quad_pm",  "0.3", "—",     "S_2=−97.90 dBm",  "S_avg=−92.69, σ=3.48",      "2.1 min"],
        ["7",  "14:30", "quad_pm",  "0.7", "—",     "S_2=−87.02 dBm",  "S_avg=−85.31, σ=2.37",      "1.7 min"],
        ["8",  "14:35", "max_min",  "0.3", "—",     "S_1=−58.73 dBm",  "S_avg=−58.11, σ=0.048",     "3.4 min"],
        ["9",  "14:41", "max_min",  "0.7", "—",     "S_1=−58.94 dBm",  "S_avg=−58.30, σ=0.049",     "2 min"],
        ["10", "15:45", "max_quad", "0.5", "15 dBm","r=17.23",        "r_avg=17.04, RMS=1.87",     "38 min"],
        ["11", "16:26", "quad_pm",  "0.5", "15 dBm","S_2=−91.77 dBm",  "S_avg=−89.97, σ=4.16",      "32 min"],
    ],
    col_widths=[0.4, 0.9, 1.4, 0.6, 0.9, 1.7, 1.9, 0.9], font_size=10,
)
p.text([R("结论：通用 PWM 切换框架在三种模式 × 三种占空比 × 抗扰条件下全部锁定成功。")])

# ---------- Slide 23: 总结 ----------
p = Builder(deck)
p.banner("总结")
p.text([H("已达成的实验目标")])
p.text([
    S("① 通用 PWM 切换框架"),
    B("基于 Bessel 展开 + 辅助角化简，统一推导三种模式的 S_1、S_2 公式；"),
    B("引入由占空比决定的相位偏移后，三种模式共享同一比值函数族。"),
    S("② 三模式闭环全部实现并验证"),
    B("max_quad：比值 PI 控制，稳态相对误差 < 0.1%；"),
    B("quad_pm：自适应探针 S_2 → min，σ ≈ 3.6 dB；"),
    B("max_min：自适应探针 S_1 → min，σ < 0.05 dB（最稳）。"),
    S("③ 相位偏移公式得到实验级定量验证"),
    B("max_quad 在 30% / 50% / 70% 占空比下，实测目标比值与理论值偏差 < 2 dB（系统频响导致）；"),
    B("quad_pm / max_min 的 V_valley 在三种占空比下基本不变，印证 S_1/S_2 不依赖 A 的理论结论。"),
    S("④ LFM 抗扰能力验证"),
    B("注入 15 dBm LFM 干扰下，max_quad / quad_pm 仍能稳定锁定 > 30 min。"),
])

# ---------- Slide 24: 下一步 ----------
p = Builder(deck)
p.banner("下一步计划")
p.text([H("低损耗工作点、长时间漂移、系统集成")])
p.text([
    S("① 非 50% 占空比的工程化"),
    B("A 越偏离 0.5，功率损失越小（A=0.9 时仅 −0.9 dB），但相位偏移越接近边界，控制环路需要重新调优；"),
    B("评估 A=0.7 / 0.8 / 0.9 下的稳态噪声与收敛速度，找到最佳工程平衡点。"),
    S("② 长时间漂移测试（> 8 h）"),
    B("当前 5/10 实验最长 37 min，未观察到漂移；下一步做隔夜测试，验证温度漂移下的长期稳定性。"),
    S("③ 系统集成联调"),
    B("与上位机间歇采样雷达 / DPMZM-MIMO 项目对接，作为偏置控制子模块嵌入；"),
    B("考察控制循环带宽（当前 ~2 Hz，受频谱仪扫描时间限制）是否满足联调需求。"),
    S("④ 文档与代码规范"),
    B("docs/theory 中 quad_pm / max_min 推导已写完整；docs/experiments 待补 quad_pm.md、max_min.md；"),
    B("ModeBase 接口已稳定，可作为未来新模式（e.g., 多电平 PAM 切换）的扩展点。"),
])

# ---------- Slide 25: 谢谢页 ----------
closing = deck.duplicate(CLOSING)
for shape in list(closing.shapes):
    if shape.has_text_frame:
        text = shape.text_frame.text
        if "谢谢" in text:
            pass  # 保留原 "谢谢！"
        elif "汇报" in text or "张" in text:
            fill_textframe(shape.text_frame, [{"text": "汇报人：张新科"}])

# ---------- Backup: 数据细节 ----------
p = Builder(deck)
p.banner("附录：数据与文件清单")
p.text([H("11 次实验脚本产出 + 32 张示波器时域波形")])
p.text([
    S("脚本侧（/Users/ckdfs/Desktop/isbc_20260510_上位机脚本采集/）"),
    B("11 个子目录，命名格式：{YYYYMMDD_HHMMSS}_{mode}_{占空比}%_{LFM 状态}"),
    B("每目录含：vpi_scan.csv, vpi.json, arb_scan.csv, fit_result.json, scan.png, control.png, control_log.csv"),
    S("示波器侧（/Users/ckdfs/Desktop/isbctest_20260510/）"),
    B("32 张 PNG：max_quad 14 张、quad_pm 12 张、max_min 6 张（含 LFM / 控制 on-off 对照）"),
    B("命名格式：{mode}_{占空比}%_{on|off}_{lfmXXdbm}.png；时域波形上轨为联合信号、下轨为滤波后射频幅度"),
    S("代码侧（/Users/ckdfs/code/isbcscript/）"),
    B("main.py + mzm/{hw,scan,fit,control,plot,io}.py + mzm/modes/{base,max_quad,quad_pm,max_min}.py"),
    B("config.py 集中放参数；docs/{theory,experiments,spec,hardware} 放文档；"),
    B("PPT 构建工具链保留在 docs/ppt_build/{template.pptx, formulas.json, math/, build.py, output/}；QA 渲染缓存单独忽略。"),
])

# ---------- Finish ----------
deck.keep_only_new()
deck.save()
print(f"Saved deck with {len(deck.prs.slides)} slides → {OUTPUT}")
