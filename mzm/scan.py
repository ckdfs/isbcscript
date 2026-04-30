"""
Bias scan functions — instrument-agnostic logic refactored from vpi_scan.py.

Public API:
    make_offsets()      → list[float]
    setup_analyzer(sa)
    measure_markers(sa) → (s1_dbm, s2_dbm)
    vpi_scan(gen, sa)   → (offsets, s1, s2, vpi_result)
    bias_scan(gen, sa, mode, vpi) → (actual_offsets, s1, s2)
    find_two_valleys(xs, ys) → (v1, v2, p1, p2) | None
"""

import logging
import math
import time

import config as cfg

log = logging.getLogger(__name__)


# ── Utilities ────────────────────────────────────────────────────────────────

def make_offsets(start=cfg.OFFSET_START, stop=cfg.OFFSET_STOP,
                 step=cfg.SCAN_STEP) -> list:
    n = round((stop - start) / step) + 1
    return [round(start + i * step, 6) for i in range(n)]


def _smooth(ys, w=5):
    half = w // 2
    out = []
    for i in range(len(ys)):
        chunk = [v for v in ys[max(0, i - half):min(len(ys), i + half + 1)]
                 if not math.isnan(v)]
        out.append(sum(chunk) / len(chunk) if chunk else math.nan)
    return out


def find_two_valleys(xs, ys, min_sep_v=0.8):
    """Find two deepest local minima separated by at least min_sep_v V.

    Returns (v1, v2, p1, p2) sorted by voltage, or None if not found.
    """
    sy = _smooth(ys)
    candidates = [
        (xs[i], sy[i], i)
        for i in range(1, len(sy) - 1)
        if not math.isnan(sy[i]) and sy[i] < sy[i - 1] and sy[i] < sy[i + 1]
    ]
    candidates.sort(key=lambda c: c[1])
    if len(candidates) < 2:
        return None
    v1_x, _, v1_i = candidates[0]
    for c in candidates[1:]:
        if abs(c[0] - v1_x) >= min_sep_v:
            v2_x, _, v2_i = c
            pair = sorted([(v1_x, ys[v1_i]), (v2_x, ys[v2_i])], key=lambda p: p[0])
            return pair[0][0], pair[1][0], pair[0][1], pair[1][1]
    return None


# ── FSV30 helpers ─────────────────────────────────────────────────────────────

def setup_analyzer(sa, rbw: float = None, vbw: float = None) -> None:
    """Apply FSV30 config for low-frequency pilot measurement.

    rbw / vbw — override bandwidth (Hz).  Defaults to cfg.SA_RBW_HZ / SA_VBW_HZ.
    Pass cfg.SCAN_RBW_HZ for fast survey scans, omit for the control loop.
    """
    sa.set_input_coupling('DC')
    sa.setup_frequency(cfg.SA_CENTER_HZ, cfg.SA_SPAN_HZ)
    sa.setup_bandwidth(rbw=rbw or cfg.SA_RBW_HZ, vbw=vbw or cfg.SA_VBW_HZ)
    sa.set_ref_level(cfg.SA_REF_LEV)
    sa.set_attenuation(auto=True)
    sa.set_sweep_time(auto=True)
    sa.marker_on(1)
    sa.marker_set_freq(cfg.FREQ_F1_HZ, marker=1)
    sa.marker_on(2)
    sa.marker_set_freq(cfg.FREQ_F2_HZ, marker=2)


def measure_markers(sa, n_avg: int = None) -> tuple:
    """Averaged sweep + read both markers. Returns (s1_dbm, s2_dbm), NaN on timeout.

    n_avg sweeps are performed and the marker readings are averaged in linear
    power (mW) before converting back to dBm.  Defaults to cfg.MEAS_AVG_N.
    """
    if n_avg is None:
        n_avg = cfg.MEAS_AVG_N

    p1_sum = p2_sum = 0.0
    for _ in range(n_avg):
        sa.single_sweep()
        ok = sa.wait_for_sweep(timeout_s=cfg.SWEEP_TIMEOUT_S)
        if not ok:
            return math.nan, math.nan
        _, r1 = sa.marker_read(1)
        _, r2 = sa.marker_read(2)
        p1_sum += 10 ** ((r1 - cfg.POWER_OFFSET_DB) / 10)   # dBm → mW
        p2_sum += 10 ** ((r2 - cfg.POWER_OFFSET_DB) / 10)

    return (10 * math.log10(p1_sum / n_avg),    # mW → dBm
            10 * math.log10(p2_sum / n_avg))


# ── Scans ─────────────────────────────────────────────────────────────────────

def vpi_scan(gen, sa, base_offsets=None) -> tuple:
    """Step 1: sine wave bias scan.

    Returns:
        offsets      — list of CH1 offset values (V)
        s1_list      — 20 kHz power (dBm, corrected)
        s2_list      — 40 kHz power (dBm, corrected)
        vpi_result   — (v_null1, v_null2, p1, p2) or None
    """
    if base_offsets is None:
        base_offsets = make_offsets()

    n_pts = len(base_offsets)
    step_v = abs(base_offsets[1] - base_offsets[0]) if n_pts > 1 else 0
    log.info('Vpi scan: %d pts  %.3f→%.3f V  step=%.3f V  settle=%.0f ms  RBW=%d Hz',
             n_pts, base_offsets[0], base_offsets[-1], step_v,
             cfg.SCAN_SETTLE_S * 1000, cfg.SCAN_RBW_HZ)

    gen.send(f':SOURce1:APPLy:SINusoid '
             f'{cfg.PILOT_FREQ_HZ:.6g},{cfg.PILOT_AMP_VPP:.6g},0,0')
    gen.output_on(1)
    setup_analyzer(sa, rbw=cfg.SCAN_RBW_HZ, vbw=cfg.SCAN_VBW_HZ)

    sa.single_sweep()
    sa.wait_for_sweep(timeout_s=cfg.SWEEP_TIMEOUT_S)   # warmup sweep

    t0 = time.time()
    report_every = max(1, n_pts // 10)
    s1, s2 = [], []
    for i, offset in enumerate(base_offsets):
        gen.set_offset(1, offset)
        time.sleep(cfg.SCAN_SETTLE_S)
        p1, p2 = measure_markers(sa)
        s1.append(p1)
        s2.append(p2)
        if (i + 1) % report_every == 0 or i == n_pts - 1:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (n_pts - i - 1)
            log.info('  [%3d/%d]  offset=%+7.3f V  s1=%7.2f  s2=%7.2f dBm  elapsed=%.0fs  eta=%.0fs',
                     i + 1, n_pts, offset, p1, p2, elapsed, eta)

    gen.output_off(1)
    log.info('Vpi scan done: %d pts in %.0f s', n_pts, time.time() - t0)
    return base_offsets, s1, s2, find_two_valleys(base_offsets, s1)


def bias_scan(gen, sa, mode, vpi: float, base_offsets=None) -> tuple:
    """Step 2: mode-configured bias scan.

    Returns:
        actual_offsets — actual CH1 offset values sent to instrument (V)
        s1_list        — 20 kHz power (dBm, corrected)
        s2_list        — 40 kHz power (dBm, corrected)
    """
    if base_offsets is None:
        base_offsets = make_offsets()

    mode.configure_source(gen, vpi)
    actual_offsets = mode.sweep_offsets(base_offsets, vpi)
    setup_analyzer(sa, rbw=cfg.SCAN_RBW_HZ, vbw=cfg.SCAN_VBW_HZ)

    n_pts = len(actual_offsets)
    log.info('ARB scan: %d pts  %.3f→%.3f V  settle=%.0f ms  RBW=%d Hz',
             n_pts, actual_offsets[0], actual_offsets[-1],
             cfg.SCAN_SETTLE_S * 1000, cfg.SCAN_RBW_HZ)

    sa.single_sweep()
    sa.wait_for_sweep(timeout_s=cfg.SWEEP_TIMEOUT_S)   # warmup sweep

    t0 = time.time()
    report_every = max(1, n_pts // 10)
    s1, s2 = [], []
    for i, offset in enumerate(actual_offsets):
        gen.set_offset(1, offset)
        time.sleep(cfg.SCAN_SETTLE_S)
        p1, p2 = measure_markers(sa)
        s1.append(p1)
        s2.append(p2)
        if (i + 1) % report_every == 0 or i == n_pts - 1:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (n_pts - i - 1)
            log.info('  [%3d/%d]  offset=%+7.3f V  s1=%7.2f  s2=%7.2f dBm  elapsed=%.0fs  eta=%.0fs',
                     i + 1, n_pts, offset, p1, p2, elapsed, eta)

    gen.output_off(1)
    log.info('ARB scan done: %d pts in %.0f s', n_pts, time.time() - t0)
    return actual_offsets, s1, s2
