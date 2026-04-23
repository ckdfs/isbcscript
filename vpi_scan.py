#!/usr/bin/env python3
"""
vpi_scan.py
扫描 1 — DG922Pro CH1 正弦波: 20 kHz, 200 mVpp, 偏移 -6 V → +6 V (步进 0.05 V)
          FSV30 采集 20 kHz & 40 kHz 功率，自动寻找 20 kHz 曲线两个谷值 → Vpi
扫描 2 — DG922Pro CH1 默认 ARB 波形: 20 kHz, 3.5 Vpp, 同样偏移范围
          FSV30 采集 20 kHz & 40 kHz 功率
两次扫描结果画在同一张图内，文件名含时间戳。

运行: python3 vpi_scan.py
依赖: matplotlib  (pip install matplotlib)
"""

import sys, time, csv, os, math
from datetime import datetime

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 中文字体配置：从 fontManager 的已注册字体名中匹配，支持 macOS/Windows/Linux
_cn_fonts = ['STHeiti', 'Arial Unicode MS', 'PingFang SC', 'Heiti SC',
             'Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC', 'WenQuanYi Micro Hei']
_avail_names = {f.name for f in fm.fontManager.ttflist}
for _f in _cn_fonts:
    if _f in _avail_names:
        plt.rcParams['font.sans-serif'] = [_f] + plt.rcParams.get('font.sans-serif', [])
        break
plt.rcParams['axes.unicode_minus'] = False   # 防止负号显示为方块

sys.path.insert(0, '/Users/ckdfs/.claude/skills/dg922pro/scripts')
sys.path.insert(0, '/Users/ckdfs/.claude/skills/fsv30/scripts')
from dg922pro import DG922Pro
from fsv30 import FSV30

# ════════════════════════════════════════════════════════════════
# 用户参数
# ════════════════════════════════════════════════════════════════

# 偏移扫描范围
OFFSET_START = -6.000   # V
OFFSET_STOP  =  6.000   # V
OFFSET_STEP  =  0.050   # V

# 扫描 1：正弦波
SIN_FREQ_HZ = 20e3
SIN_AMP_VPP = 0.800     # 800 mVpp

# 扫描 2：默认 ARB 波形
ARB_FREQ_HZ = 20e3
ARB_AMP_VPP = 3.5       # 3.5 Vpp（Vpi 未知时的回退值）
ARB_SHIFT_ENABLE = True # True: 扫描范围右移 Vpi/4 并在图上归一化回 -6~6 V
                         # False: 直接在 -6~6 V 扫描，不做坐标变换

# 测量频点
FREQ_F1 = 20e3           # 20 kHz
FREQ_F2 = 40e3           # 40 kHz

# 频谱仪配置
SA_CENTER  = 30e3        # 中心频率，覆盖 10–50 kHz
SA_SPAN    = 40e3        # 跨度
SA_RBW     = 300         # Hz
SA_VBW     = 300         # Hz
SA_REF_LEV = 0           # dBm

POWER_OFFSET_DB = 6.0    # FSV30 已知读数偏高校正
SETTLE_S        = 0.15   # 换挡稳定时间 s
SWEEP_TIMEOUT   = 120    # s

# 输出目录
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TIMESTAMP  = datetime.now().strftime('%Y%m%d_%H%M%S')

# ════════════════════════════════════════════════════════════════
# 辅助函数
# ════════════════════════════════════════════════════════════════

def make_offsets(start, stop, step):
    n = round((stop - start) / step) + 1
    return [round(start + i * step, 6) for i in range(n)]


def smooth(ys, w=3):
    """简单滑动平均平滑，用于谷值检测。"""
    half = w // 2
    out = []
    for i in range(len(ys)):
        lo = max(0, i - half)
        hi = min(len(ys), i + half + 1)
        chunk = [v for v in ys[lo:hi] if not math.isnan(v)]
        out.append(sum(chunk) / len(chunk) if chunk else math.nan)
    return out


def find_two_valleys(xs, ys, min_sep_v=0.8):
    """
    在曲线上寻找两个最深的局部极小值，两者间距 ≥ min_sep_v V。
    返回 (v_valley1, v_valley2, pwr_valley1, pwr_valley2)，按电压升序排列。
    若找不到满足条件的两个谷，返回 None。
    """
    sy = smooth(ys, w=5)
    candidates = []
    for i in range(1, len(sy) - 1):
        if math.isnan(sy[i]):
            continue
        if sy[i] < sy[i - 1] and sy[i] < sy[i + 1]:
            candidates.append((xs[i], sy[i], i))

    if len(candidates) < 2:
        return None

    # 按功率升序（最深在前）
    candidates.sort(key=lambda c: c[1])

    v1_x, v1_y, v1_i = candidates[0]
    for c in candidates[1:]:
        if abs(c[0] - v1_x) >= min_sep_v:
            v2_x, v2_y, v2_i = c
            # 按电压排序后返回
            pair = sorted([(v1_x, ys[v1_i]), (v2_x, ys[v2_i])], key=lambda p: p[0])
            return pair[0][0], pair[1][0], pair[0][1], pair[1][1]
    return None


def run_scan(gen, sa, label, waveform, freq, amp, offsets):
    """
    执行一次偏移扫描，返回 (power_f1, power_f2) 列表。
    waveform='SINusoid' 使用正弦波；waveform='ARB' 保留当前 ARB 文件。
    """
    n = len(offsets)
    print(f"\n{'═'*55}")
    print(f"  扫描: {label}")
    print(f"  波形: {waveform}  频率: {freq/1e3:.0f} kHz  幅度: {amp} Vpp")
    print(f"  偏移: {offsets[0]:.3f} V → {offsets[-1]:.3f} V  ({n} 步)")
    print(f"{'═'*55}")

    # ── 配置信号发生器 ──────────────────────────────────────────
    if waveform == 'ARB':
        gen.send(':SOURce1:FUNCtion ARB')   # 保留当前已加载波形文件
    else:
        gen.send(f':SOURce1:APPLy:{waveform} {freq:.6g},{amp:.6g},0,0')

    gen.set_frequency(1, freq)
    gen.set_amplitude(1, amp)
    gen.set_offset(1, offsets[0])
    gen.output_on(1)

    # ── 配置频谱仪（每次扫描重新确认） ────────────────────────
    sa.set_input_coupling('DC')
    sa.setup_frequency(SA_CENTER, SA_SPAN)
    sa.setup_bandwidth(rbw=SA_RBW, vbw=SA_VBW)
    sa.set_ref_level(SA_REF_LEV)
    sa.set_attenuation(auto=True)
    sa.set_sweep_time(auto=True)
    sa.marker_on(1)
    sa.marker_on(2)
    sa.marker_set_freq(FREQ_F1, marker=1)
    sa.marker_set_freq(FREQ_F2, marker=2)

    # 预热扫频
    print("  预热扫频...")
    sa.single_sweep()
    sa.wait_for_sweep(timeout_s=SWEEP_TIMEOUT)
    print("  预热完成，开始扫描...\n")
    print(f"  {'步':>4}  {'偏移(V)':>9}  {'P@20kHz':>10}  {'P@40kHz':>10}")
    print(f"  {'─'*40}")

    pwr_f1, pwr_f2 = [], []

    for i, offset in enumerate(offsets):
        gen.set_offset(1, offset)
        time.sleep(SETTLE_S)

        sa.single_sweep()
        ok = sa.wait_for_sweep(timeout_s=SWEEP_TIMEOUT)
        if not ok:
            print(f"  [警告] 步骤 {i+1}: 扫频超时，记 NaN")
            pwr_f1.append(math.nan)
            pwr_f2.append(math.nan)
            continue

        _, r1 = sa.marker_read(1)
        _, r2 = sa.marker_read(2)
        p1 = r1 - POWER_OFFSET_DB
        p2 = r2 - POWER_OFFSET_DB
        pwr_f1.append(p1)
        pwr_f2.append(p2)

        if i % 10 == 0 or i == n - 1:
            print(f"  {i+1:4d}   {offset:8.3f} V   {p1:+7.2f} dBm   {p2:+7.2f} dBm")

    gen.output_off(1)
    valid = sum(1 for p in pwr_f1 if not math.isnan(p))
    print(f"\n  完成: {valid}/{n} 个有效点")
    return pwr_f1, pwr_f2


# ════════════════════════════════════════════════════════════════
# 主程序
# ════════════════════════════════════════════════════════════════

offsets = make_offsets(OFFSET_START, OFFSET_STOP, OFFSET_STEP)
print(f"偏移序列: {len(offsets)} 步  ({OFFSET_START:.3f} V → {OFFSET_STOP:.3f} V, 步进 {OFFSET_STEP*1000:.0f} mV)")
print(f"时间戳  : {TIMESTAMP}")

with DG922Pro() as gen, FSV30() as sa:
    print(f"\nDG922Pro : {gen.identify()}")
    print(f"FSV30    : {sa.identify()}")

    # ── 扫描 1：正弦波 ──────────────────────────────────────────
    sin_f1, sin_f2 = run_scan(
        gen, sa,
        label='正弦波 (Sine)',
        waveform='SINusoid',
        freq=SIN_FREQ_HZ,
        amp=SIN_AMP_VPP,
        offsets=offsets,
    )

    # ── 扫描 1 结束后立即计算 Vpi，用于确定扫描 2 的幅度和偏移 ────
    vpi_result = find_two_valleys(offsets, sin_f1, min_sep_v=0.8)
    if vpi_result:
        v_null1, v_null2, p_null1, p_null2 = vpi_result
        vpi = abs(v_null2 - v_null1)
        arb_amp          = vpi / 2 + 0.8
        arb_offset_shift = (vpi / 4) if ARB_SHIFT_ENABLE else 0.0
        print(f"\nVpi 分析（正弦 20 kHz）:")
        print(f"  谷值 1: V = {v_null1:.3f} V,  P = {p_null1:.2f} dBm")
        print(f"  谷值 2: V = {v_null2:.3f} V,  P = {p_null2:.2f} dBm")
        print(f"  Vpi        = {vpi:.3f} V")
        print(f"  ARB 幅度   = Vpi/2 + 0.8 = {arb_amp:.3f} Vpp")
        if ARB_SHIFT_ENABLE:
            print(f"  ARB 偏移量 = Vpi/4 = {arb_offset_shift:.3f} V  "
                  f"（实际范围 {OFFSET_START+arb_offset_shift:.3f}"
                  f"~{OFFSET_STOP+arb_offset_shift:.3f} V，图上归一化到 {OFFSET_START:.0f}~{OFFSET_STOP:.0f} V）")
        else:
            print(f"  ARB 偏移量 = 0 V（不平移，直接在 {OFFSET_START:.0f}~{OFFSET_STOP:.0f} V 扫描）")
    else:
        vpi = None
        arb_amp          = ARB_AMP_VPP
        arb_offset_shift = 0.0
        print(f"\n[警告] 未能找到两个谷值，Vpi 无法计算，"
              f"ARB 幅度使用默认值 {arb_amp} Vpp，偏移不做平移")

    # 生成扫描 2 的实际电压序列
    arb_offsets = [round(v + arb_offset_shift, 6) for v in offsets]

    # ── 扫描 2：默认 ARB 波形（幅度 = Vpi/2+0.8 V，范围右移 Vpi/4）─
    arb_f1, arb_f2 = run_scan(
        gen, sa,
        label=(f'默认 ARB 波形  ({arb_amp:.3f} Vpp, '
               f'实际范围 {arb_offsets[0]:.3f}~{arb_offsets[-1]:.3f} V)'),
        waveform='ARB',
        freq=ARB_FREQ_HZ,
        amp=arb_amp,
        offsets=arb_offsets,       # 传入右移后的真实电压
    )

    # 还原频谱仪耦合
    sa.set_input_coupling('AC')

print("\n所有扫描完成。")

# ════════════════════════════════════════════════════════════════
# 保存 CSV
# ════════════════════════════════════════════════════════════════

csv_path = os.path.join(SCRIPT_DIR, f'vpi_scan_{TIMESTAMP}.csv')
with open(csv_path, 'w', newline='', encoding='utf-8') as f:
    w = csv.writer(f)
    w.writerow([
        'offset_V',               # 坐标轴电压（-6~6 V）
        'sin_20kHz_dBm', 'sin_40kHz_dBm',
        'arb_actual_V',           # ARB 扫描实际施加电压（右移 Vpi/2）
        'arb_20kHz_dBm', 'arb_40kHz_dBm',
    ])
    for row in zip(offsets, sin_f1, sin_f2, arb_offsets, arb_f1, arb_f2):
        w.writerow([f'{v:.4f}' for v in row])
print(f"CSV 已保存: {csv_path}")

# ════════════════════════════════════════════════════════════════
# 绘图
# ════════════════════════════════════════════════════════════════

fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 11), sharex=True)
_shift_info = (f'    坐标平移 = Vpi/4 = {arb_offset_shift:.3f} V'
               if ARB_SHIFT_ENABLE else '    无坐标平移')
_vpi_str = (f'\nVpi = {vpi:.3f} V    ARB 幅度 = Vpi/2+0.8 = {arb_amp:.3f} Vpp'
            + _shift_info) if vpi else ''
fig.suptitle(
    f'MZM 偏压扫描  —  {TIMESTAMP}    步进 {OFFSET_STEP*1000:.0f} mV' + _vpi_str,
    fontsize=12, y=0.99,
)

_arb_shift_note = (f' [实际+{arb_offset_shift:.3f} V]'
                   if arb_offset_shift != 0 else '')

# ── 子图 1：20 kHz 基波功率 ───────────────────────────────────
ax1.plot(offsets, sin_f1, color='royalblue', linewidth=1.8,
         label=f'Sin  20 kHz  ({SIN_AMP_VPP*1000:.0f} mVpp)')
ax1.plot(offsets, arb_f1, color='tomato', linewidth=1.8, linestyle='--',
         label=f'ARB  20 kHz  ({arb_amp:.3f} Vpp){_arb_shift_note}')

if vpi_result:
    for xv in (v_null1, v_null2):
        ax1.axvline(xv, color='grey', linestyle=':', linewidth=1.0)
    pref = min(p_null1, p_null2)
    ax1.annotate('', xy=(v_null2, pref - 0.5), xytext=(v_null1, pref - 0.5),
                 arrowprops=dict(arrowstyle='<->', color='dimgrey', lw=1.5))
    ax1.text((v_null1 + v_null2) / 2, pref - 2.0,
             f'Vpi = {vpi:.3f} V',
             ha='center', va='top', fontsize=9, color='dimgrey',
             bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='grey', alpha=0.8))
    ax1.plot([v_null1, v_null2], [p_null1, p_null2],
             'o', color='dimgrey', markersize=5, zorder=5)

ax1.set_ylabel('功率 (dBm)', fontsize=11)
ax1.set_title('20 kHz 基波功率', fontsize=11)
ax1.legend(fontsize=10)
ax1.grid(True, alpha=0.3)

# ── 子图 2：40 kHz 二次谐波功率 ──────────────────────────────
ax2.plot(offsets, sin_f2, color='royalblue', linewidth=1.8,
         label=f'Sin  40 kHz  ({SIN_AMP_VPP*1000:.0f} mVpp)')
ax2.plot(offsets, arb_f2, color='tomato', linewidth=1.8, linestyle='--',
         label=f'ARB  40 kHz  ({arb_amp:.3f} Vpp){_arb_shift_note}')
ax2.set_ylabel('功率 (dBm)', fontsize=11)
ax2.set_title('40 kHz 二次谐波功率', fontsize=11)
ax2.legend(fontsize=10)
ax2.grid(True, alpha=0.3)

# ── 子图 3：ARB 一阶/二阶功率比（P_20kHz − P_40kHz，单位 dB）─
arb_ratio = [a - b if not (math.isnan(a) or math.isnan(b)) else math.nan
             for a, b in zip(arb_f1, arb_f2)]

ax3.plot(offsets, arb_ratio, color='tomato', linewidth=1.8,
         label=f'ARB  ({arb_amp:.3f} Vpp){_arb_shift_note}')
ax3.axhline(0, color='black', linewidth=0.6, linestyle=':')
ax3.set_xlabel('DC 偏移 (V)', fontsize=11)
ax3.set_ylabel('P1/P2 (dB)', fontsize=11)
ax3.set_title('ARB 一阶/二阶功率比  (P_20kHz - P_40kHz)', fontsize=11)
ax3.legend(fontsize=10)
ax3.grid(True, alpha=0.3)
ax3.set_xlim(OFFSET_START, OFFSET_STOP)

plt.tight_layout(rect=[0, 0, 1, 0.97])
png_path = os.path.join(SCRIPT_DIR, f'vpi_scan_{TIMESTAMP}.png')
plt.savefig(png_path, dpi=150)
print(f"图表已保存: {png_path}")

if vpi:
    print(f"\n{'─'*40}")
    print(f"  Vpi = {vpi:.3f} V")
    print(f"{'─'*40}")
