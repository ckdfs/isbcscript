"""
Plotting utilities.

Public API:
    save_scan_plot(path, base_offsets, vpi_data, arb_data, vpi_result, mode_name)
"""

import csv
import math

import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# Chinese font fallback
_CN_FONTS = ['STHeiti', 'Arial Unicode MS', 'PingFang SC', 'Heiti SC',
             'Microsoft YaHei', 'SimHei', 'Noto Sans CJK SC']
_avail = {f.name for f in fm.fontManager.ttflist}
for _f in _CN_FONTS:
    if _f in _avail:
        plt.rcParams['font.sans-serif'] = [_f] + plt.rcParams.get('font.sans-serif', [])
        break
plt.rcParams['axes.unicode_minus'] = False


def save_scan_plot(path: str,
                   base_offsets: list,
                   s1_sin: list, s2_sin: list,
                   actual_offsets: list,
                   s1_arb: list, s2_arb: list,
                   vpi_result,
                   mode_name: str,
                   vpi: float = None) -> None:
    """Save a three-panel scan comparison plot.

    Panel 1: 20 kHz power (sine vs ARB)
    Panel 2: 40 kHz power (sine vs ARB)
    Panel 3: ARB amplitude ratio r = sqrt(P1/P2)
    """
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 11), sharex=True)

    title = f'MZM偏压扫描 — {mode_name}'
    if vpi is not None:
        title += f'  Vpi = {vpi:.3f} V'
    fig.suptitle(title, fontsize=12)

    # Panel 1: 20 kHz
    ax1.plot(base_offsets, s1_sin, color='royalblue', lw=1.8, label='Sin 20 kHz')
    ax1.plot(base_offsets, s1_arb, color='tomato', lw=1.8, ls='--', label='ARB 20 kHz')
    if vpi_result:
        v1, v2, p1, p2 = vpi_result
        for xv in (v1, v2):
            ax1.axvline(xv, color='grey', ls=':', lw=1.0)
        pref = min(p1, p2)
        ax1.annotate('', xy=(v2, pref - 0.5), xytext=(v1, pref - 0.5),
                     arrowprops=dict(arrowstyle='<->', color='dimgrey', lw=1.5))
        if vpi is not None:
            ax1.text((v1 + v2) / 2, pref - 2.0, f'Vpi = {vpi:.3f} V',
                     ha='center', va='top', fontsize=9, color='dimgrey',
                     bbox=dict(boxstyle='round,pad=0.2', fc='white', ec='grey', alpha=0.8))
    ax1.set_ylabel('功率 (dBm)')
    ax1.set_title('20 kHz 一阶导频功率')
    ax1.legend()
    ax1.grid(alpha=0.3)

    # Panel 2: 40 kHz
    ax2.plot(base_offsets, s2_sin, color='royalblue', lw=1.8, label='Sin 40 kHz')
    ax2.plot(base_offsets, s2_arb, color='tomato', lw=1.8, ls='--', label='ARB 40 kHz')
    ax2.set_ylabel('功率 (dBm)')
    ax2.set_title('40 kHz 二阶导频功率')
    ax2.legend()
    ax2.grid(alpha=0.3)

    # Panel 3: amplitude ratio
    ratio = []
    for a, b in zip(s1_arb, s2_arb):
        if math.isnan(a) or math.isnan(b):
            ratio.append(math.nan)
        else:
            p1_lin = 10 ** (a / 10)
            p2_lin = 10 ** (b / 10)
            ratio.append((p1_lin / p2_lin) ** 0.5)

    ax3.plot(base_offsets, ratio, color='tomato', lw=1.8, label='ARB  r = √(P1/P2)')
    ax3.axhline(1.0, color='black', lw=0.6, ls=':')
    ax3.set_xlabel('CH1 offset 基准 (V)')
    ax3.set_ylabel('幅度比 r')
    ax3.set_title('ARB 一/二阶幅度比  (x轴对齐正弦扫描，ARB实际偏压右移 Vpi/4)')
    ax3.legend()
    ax3.grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(path, dpi=150)
    plt.close(fig)


def save_fit_plot(path: str,
                  actual_offsets: list,
                  s1_arb: list, s2_arb: list,
                  fit_result,
                  mode,
                  mode_name: str,
                  vpi: float) -> None:
    """Save ratio-curve fit overlay plot.

    The fit curve is drawn only within the fit window to avoid tan-asymptote
    spikes blowing up the y-axis.  All measured points are shown as scatter
    but the y-axis is clamped to a sane range.
    """
    import config as cfg

    ratio = []
    for a, b in zip(s1_arb, s2_arb):
        if math.isnan(a) or math.isnan(b):
            ratio.append(math.nan)
        else:
            p1 = 10 ** (a / 10)
            p2 = 10 ** (b / 10)
            ratio.append((p1 / p2) ** 0.5)

    # fit window in actual_offset space: centre = vpi/4, half-width = window
    window    = vpi * cfg.FIT_WINDOW_FRAC
    centre    = vpi / 4 + fit_result.V0          # V0 corrects the centre position
    x_lo      = centre - window
    x_hi      = centre + window

    # fitted curve — only inside the window to avoid asymptote spikes
    x_fine    = np.linspace(x_lo, x_hi, 400)
    vdc_fine  = x_fine - vpi / 4                 # transform to vdc_eff space
    r_fine    = mode.fit_model(vdc_fine, fit_result.A, fit_result.V0, fit_result.vpi_fit)

    # y-axis ceiling: show up to 4× R_target (keeps asymptote out of view)
    y_ceil = max(fit_result.r_target * 4.0, 2.0)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(actual_offsets, ratio, s=14, color='royalblue', alpha=0.7,
               label='测量值（全扫描范围）', zorder=3)
    ax.plot(x_fine, r_fine, color='tomato', lw=2.0,
            label=f'拟合曲线（窗口 ±{window:.2f} V）')
    ax.axhline(fit_result.r_target, color='green', ls='--', lw=1.5,
               label=f'R_target = {fit_result.r_target:.4f}')
    ax.axvline(x_lo, color='grey', ls=':', lw=1.0, label='拟合窗口边界')
    ax.axvline(x_hi, color='grey', ls=':', lw=1.0, label='_nolegend_')

    ax.set_xlabel('CH1 offset 实际值 (V)')
    ax.set_ylabel('幅度比 r = √(P1/P2)')
    ax.set_title(
        f'比值曲线拟合 — {mode_name}\n'
        f'A={fit_result.A:.4f}  V0={fit_result.V0:.4f} V  '
        f'Vpi_fit={fit_result.vpi_fit:.4f} V  (Vpi_scan={vpi:.4f} V)'
    )
    ax.set_ylim(0, y_ceil)
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


def save_control_plot(path: str, log_path: str,
                      r_target: float, mode_name: str) -> None:
    """Save three-panel control-loop result plot."""
    times, rs, errors, offsets = [], [], [], []
    with open(log_path, newline='', encoding='utf-8') as f:
        for row in csv.DictReader(f):
            times.append(float(row['timestamp_s']))
            rs.append(float(row['r']))
            errors.append(float(row['error']))
            offsets.append(float(row['offset_V']))

    if not times:
        return

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f'闭环控制过程 — {mode_name}', fontsize=12)

    ax1.plot(times, rs, color='tomato', lw=1.5, label='r = √(P1/P2)')
    ax1.axhline(r_target, color='black', ls='--', lw=1.5,
                label=f'R_target = {r_target:.4f}')
    ax1.set_ylabel('幅度比 r')
    ax1.set_title('比值随时间变化')
    ax1.legend()
    ax1.grid(alpha=0.3)

    ax2.plot(times, offsets, color='royalblue', lw=1.5, label='CH1 offset')
    ax2.set_ylabel('CH1 offset (V)')
    ax2.set_title('偏压随时间变化')
    ax2.legend()
    ax2.grid(alpha=0.3)

    ax3.plot(times, errors, color='dimgray', lw=1.2, label='误差 e = r − R_target')
    ax3.axhline(0, color='black', lw=0.8, ls=':')
    ax3.set_xlabel('时间 (s)')
    ax3.set_ylabel('误差')
    ax3.set_title('控制误差随时间变化')
    ax3.legend()
    ax3.grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(path, dpi=150)
    plt.close(fig)
