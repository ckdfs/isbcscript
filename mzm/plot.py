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

    # Panel 3: P1_dBm - P2_dBm  (dBm subtraction, no linear conversion needed)
    diff_sin = [a - b if not (math.isnan(a) or math.isnan(b)) else math.nan
                for a, b in zip(s1_sin, s2_sin)]
    diff_arb = [a - b if not (math.isnan(a) or math.isnan(b)) else math.nan
                for a, b in zip(s1_arb, s2_arb)]

    ax3.plot(base_offsets, diff_sin, color='royalblue', lw=1.8, label='Sin P1−P2')
    ax3.plot(base_offsets, diff_arb, color='tomato',    lw=1.8, ls='--', label='ARB P1−P2')
    ax3.axhline(0, color='black', lw=0.6, ls=':', label='0 dB (P1=P2)')
    ax3.set_xlabel('CH1 offset 基准 (V)')
    ax3.set_ylabel('P1 − P2 (dBm)')
    ax3.set_title('一阶功率 − 二阶功率  (dBm差值，ARB实际偏压右移 Vpi/4)')
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

    Y axis: P1_dBm − P2_dBm  =  20·log10(r).
    X axis: zoomed to fit window ±50% buffer so the monotonic region fills
    the plot and asymptote spikes stay off screen.
    The fit curve is 20·log10(A·|tan(...)|) — same model, dB scale.
    """
    import config as cfg

    # measured dB difference: no linear conversion needed
    diff_meas = [a - b if not (math.isnan(a) or math.isnan(b)) else math.nan
                 for a, b in zip(s1_arb, s2_arb)]
    r_target_db = 20 * math.log10(fit_result.r_target)

    # fit window + 50% buffer for x-axis zoom
    # For max_quad: asymptote (P2→0) at actual_offset = V0_fit,
    #               zero (P1→0) at actual_offset = V0_fit + Vpi/2.
    # centre is the target max point (actual_offset = Vpi/4 + V0_fit).
    window   = vpi * cfg.FIT_WINDOW_FRAC
    centre   = vpi / 4 + fit_result.V0
    buf      = window * 0.5
    x_lo     = centre - window - buf
    x_hi     = centre + window + buf

    # select measured points inside the zoomed range
    xs_zoom = [x for x in actual_offsets if x_lo <= x <= x_hi]
    ys_zoom = [d for x, d in zip(actual_offsets, diff_meas) if x_lo <= x <= x_hi]

    # fitted curve in dB, only inside the fit window (no asymptote)
    x_fine   = np.linspace(centre - window, centre + window, 400)
    vdc_fine = x_fine - vpi / 4
    r_fine   = mode.fit_model(vdc_fine, fit_result.A, fit_result.V0, fit_result.vpi_fit)
    # guard against log(0) at window edges
    r_fine   = np.clip(r_fine, 1e-9, None)
    db_fine  = 20 * np.log10(r_fine)

    fig, ax = plt.subplots(figsize=(10, 5))
    ax.scatter(xs_zoom, ys_zoom, s=18, color='royalblue', zorder=3,
               label='测量值  P1−P2 (dBm)')
    ax.plot(x_fine, db_fine, color='tomato', lw=2.0,
            label='拟合曲线')
    ax.axhline(r_target_db, color='green', ls='--', lw=1.5,
               label=f'R_target = {fit_result.r_target:.4f}  ({r_target_db:.2f} dB)')
    ax.axvline(centre - window, color='grey', ls=':', lw=1.0, label='拟合窗口边界')
    ax.axvline(centre + window, color='grey', ls=':', lw=1.0, label='_nolegend_')

    ax.set_xlim(x_lo, x_hi)
    ax.set_xlabel('CH1 offset 实际值 (V)')
    ax.set_ylabel('P1 − P2 (dBm)')
    ax.set_title(
        f'比值曲线拟合 — {mode_name}\n'
        f'A={fit_result.A:.4f}  V0={fit_result.V0:.4f} V  '
        f'Vpi_fit={fit_result.vpi_fit:.4f} V  (Vpi_scan={vpi:.4f} V)'
    )
    ax.legend()
    ax.grid(alpha=0.3)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close(fig)


def save_control_plot(path: str, log_path: str,
                      r_target: float, mode_name: str) -> None:
    """Save three-panel control-loop result plot.

    Auto-detects CSV format: ratio (r, error columns) or s2_min (dir, probe_V columns).
    """
    times, offsets = [], []
    with open(log_path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        columns = reader.fieldnames or []
        for row in reader:
            times.append(float(row['timestamp_s']))
            offsets.append(float(row['offset_V']))

    if not times:
        return

    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f'闭环控制过程 — {mode_name}', fontsize=12)

    if 'r' in columns:
        # ── ratio-mode plot ──────────────────────────────────────────────────
        with open(log_path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        rs = [float(r['r']) for r in rows]
        errors = [float(r['error']) for r in rows]

        ax1.plot(times, rs, color='tomato', lw=1.5, label='r = √(P1/P2)')
        ax1.axhline(r_target, color='black', ls='--', lw=1.5,
                    label=f'R_target = {r_target:.4f}')
        ax1.set_ylabel('r')
        ax1.set_title('比值随时间变化')
        ax1.legend()
        ax1.grid(alpha=0.3)

        ax2.plot(times, offsets, color='royalblue', lw=1.5, label='CH1 offset')
        ax2.set_ylabel('CH1 offset (V)')
        ax2.set_title('偏压随时间变化')
        ax2.legend()
        ax2.grid(alpha=0.3)

        ax3.plot(times, errors, color='dimgray', lw=1.2, label='e = r − R_target')
        ax3.axhline(0, color='black', lw=0.8, ls=':')
        ax3.set_ylabel('误差')
        ax3.set_title('控制误差随时间变化')
        ax3.legend()
        ax3.grid(alpha=0.3)
    else:
        # ── s2-min plot ──────────────────────────────────────────────────────
        with open(log_path, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        s2s = [float(r['s2_dbm']) for r in rows]
        steps = [float(r['step_V']) for r in rows]
        probes = [float(r.get('probe_V', 0)) for r in rows]

        ax1.plot(times, s2s, color='steelblue', lw=1.2, label='S2 (40 kHz)')
        ax1.set_ylabel('S2 (dBm)')
        ax1.set_title('S2 功率随时间变化')
        ax1.legend()
        ax1.grid(alpha=0.3)

        ax2.plot(times, offsets, color='royalblue', lw=1.5, label='CH1 offset')
        ax2.set_ylabel('CH1 offset (V)')
        ax2.set_title('偏压随时间变化')
        ax2.legend()
        ax2.grid(alpha=0.3)

        ax3.plot(times, steps, color='dimgray', lw=1.2, label='步长')
        ax3.set_ylabel('步长 (V)')
        ax3.set_xlabel('时间 (s)')
        ax3.set_title('控制步长随时间变化')
        ax3.legend()
        ax3.grid(alpha=0.3)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    plt.savefig(path, dpi=150)
    plt.close(fig)
