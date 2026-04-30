"""
PI / gradient control loops — Step 4.

Public API:
    pi_control_loop(gen, sa, mode, fit_result, vpi, measure_fn, log_path)
    s2_min_control_loop(gen, sa, mode, vpi, s2_min_dbm, measure_fn, log_path)
"""

import csv
import logging
import math
import time

import config as cfg
from mzm.fit import FitResult

log = logging.getLogger(__name__)


def pi_control_loop(gen, sa, mode, fit_result: FitResult, vpi: float,
                    measure_fn, log_path: str = None,
                    k_i: float = cfg.K_I) -> None:
    """Run PI control loop (ratio method) until KeyboardInterrupt."""
    offset_min, offset_max = mode.offset_limits(vpi)
    V_offset  = mode.initial_offset(vpi, fit_result.V0)
    R_target  = fit_result.r_target
    t0        = time.time()

    log.info(f'Control loop started  R_target={R_target:.4f}'
             f'  V_init={V_offset:.4f} V  K_I={k_i}'
             f'  limits=[{offset_min:.1f}, {offset_max:.1f}] V')

    _csv_file = open(log_path, 'w', newline='', encoding='utf-8') if log_path else None
    _writer = None
    if _csv_file:
        _writer = csv.writer(_csv_file)
        _writer.writerow(['timestamp_s', 's1_dbm', 's2_dbm', 'r', 'error', 'offset_V'])

    try:
        while True:
            s1, s2 = measure_fn(sa)

            if math.isnan(s1) or math.isnan(s2):
                log.warning('NaN measurement — skipping update')
                continue

            p1 = 10 ** (s1 / 10)
            p2 = 10 ** (s2 / 10)
            r  = (p1 / p2) ** 0.5
            e  = r - R_target

            V_offset = max(offset_min, min(offset_max, V_offset - k_i * e))
            gen.set_offset(1, V_offset)

            t = time.time() - t0
            log.info(f't={t:7.1f}s  s1={s1:7.2f}  s2={s2:7.2f}  r={r:.4f}  e={e:+.4f}  Vdc={V_offset:.4f} V')

            if _writer:
                _writer.writerow([f'{t:.3f}', f'{s1:.3f}', f'{s2:.3f}',
                                  f'{r:.5f}', f'{e:.5f}', f'{V_offset:.5f}'])
                _csv_file.flush()
    finally:
        if _csv_file:
            _csv_file.close()


def s2_min_control_loop(gen, sa, mode, vpi: float, s2_min_dbm: float,
                        measure_fn, log_path: str = None,
                        V_start: float = None,
                        probe_v: float = 0.02,
                        step_scale: float = 0.003) -> None:
    """Gradient-descent control: minimise S₂ (40 kHz power).

    Probes +probe_v V to determine gradient direction, then steps toward
    lower S₂.  Step size scales with how far S₂ is above the valley floor.
    Designed for quad_pm where the S₂ valley = target operating point.

    gen          — DG922Pro instance
    sa           — FSV30 instance
    mode         — ModeBase instance
    vpi          — Vpi from vpi_scan (V)
    s2_min_dbm   — S₂ floor estimate from scan (dBm), for reference only
    measure_fn   — callable(sa) → (s1_dbm, s2_dbm)
    log_path     — path for control_log.csv
    V_start      — initial CH1 offset (default: mode.initial_offset)
    probe_v      — voltage probe step for direction sensing (V)
    step_scale   — step scaling (V / dB); larger → more aggressive
    """
    offset_min, offset_max = mode.offset_limits(vpi)
    V_offset = V_start if V_start is not None else mode.initial_offset(vpi, 0.0)
    t0 = time.time()

    log.info(f'S₂-min control  V_start={V_offset:.4f} V  S₂_floor≈{s2_min_dbm:.1f} dBm'
             f'  probe={probe_v:.3f} V  limits=[{offset_min:.1f}, {offset_max:.1f}] V')

    _csv_file = open(log_path, 'w', newline='', encoding='utf-8') if log_path else None
    _writer = None
    if _csv_file:
        _writer = csv.writer(_csv_file)
        _writer.writerow(['timestamp_s', 's1_dbm', 's2_dbm', 'dir',
                          'step_V', 'offset_V'])

    try:
        while True:
            # measure at current offset
            s1, s2 = measure_fn(sa)
            if math.isnan(s1) or math.isnan(s2):
                log.warning('NaN measurement — skipping update')
                continue

            # probe: step positive, measure again
            V_probe = min(offset_max, V_offset + probe_v)
            gen.set_offset(1, V_probe)
            _, s2_probe = measure_fn(sa)
            gen.set_offset(1, V_offset)  # restore

            # direction: did S₂ decrease (toward valley) or increase?
            going_down = (s2_probe < s2)

            # step size proportional to how far above the valley floor we are
            excess_db = max(0.0, s2 - s2_min_dbm)
            step = step_scale * excess_db
            if step < 0.002:
                step = 0.0   # dead-band: close enough to the floor

            if going_down:
                V_offset += step          # keep going positive → lower S₂
            else:
                V_offset -= step          # reverse: go negative → lower S₂

            V_offset = max(offset_min, min(offset_max, V_offset))
            gen.set_offset(1, V_offset)

            t = time.time() - t0
            direction = '→' if going_down else '←'
            log.info(f't={t:7.1f}s  s1={s1:7.2f}  s2={s2:7.2f}  '
                     f'dir={direction}  step={step:+.4f} V  Vdc={V_offset:.4f} V')

            if _writer:
                _writer.writerow([f'{t:.3f}', f'{s1:.3f}', f'{s2:.3f}',
                                  direction, f'{step:.5f}', f'{V_offset:.5f}'])
                _csv_file.flush()
    finally:
        if _csv_file:
            _csv_file.close()
