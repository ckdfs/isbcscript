"""
Plotting utilities.

Public API:
    save_scan_plot(path, base_offsets, vpi_data, arb_data, vpi_result, mode_name)
"""

import math

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
    ax3.set_title('ARB 一/二阶幅度比')
    ax3.legend()
    ax3.grid(alpha=0.3)
    ax3.set_xlim(base_offsets[0], base_offsets[-1])

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(path, dpi=150)
    plt.close(fig)
