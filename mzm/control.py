"""
PI control loop — Step 4.

Public API:
    pi_control_loop(gen, sa, mode, fit_result, vpi, measure_fn, log_path)
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
                    k_i: float = cfg.K_I,
                    offset_min: float = cfg.OFFSET_MIN,
                    offset_max: float = cfg.OFFSET_MAX) -> None:
    """Run PI control loop until KeyboardInterrupt.

    gen         — DG922Pro instance (CH1 must already be in ARB mode)
    sa          — FSV30 instance (must be set up via setup_analyzer)
    mode        — ModeBase instance
    fit_result  — FitResult from ratio_fit()
    vpi         — Vpi from vpi_scan (V)
    measure_fn  — callable(sa) → (s1_dbm, s2_dbm), e.g. scan.measure_markers
    log_path    — path for control_log.csv (None to skip logging)
    k_i         — integral gain
    offset_min/max — CH1 offset hard limits (V)
    """
    V_offset  = mode.initial_offset(vpi, fit_result.V0)
    R_target  = fit_result.r_target
    t0        = time.time()

    log.info(f'Control loop started  R_target={R_target:.4f}'
             f'  V_init={V_offset:.4f} V  K_I={k_i}')

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
            log.info(f't={t:7.1f}s  r={r:.4f}  e={e:+.4f}  Vdc={V_offset:.4f} V')

            if _writer:
                _writer.writerow([f'{t:.3f}', f'{s1:.3f}', f'{s2:.3f}',
                                  f'{r:.5f}', f'{e:.5f}', f'{V_offset:.5f}'])
                _csv_file.flush()
    finally:
        if _csv_file:
            _csv_file.close()
