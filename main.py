#!/usr/bin/env python3
"""MZM bias control — unified entry point.

Usage:
    python main.py --mode max_quad --step all
    python main.py --mode max_quad --step scan
    python main.py --mode max_quad --step fit
    python main.py --mode max_quad --step control
    python main.py --mode max_quad --step scan-control  # skip fit
"""

import argparse
import logging
import math
import os
import time

from mzm.modes import MODES
from mzm.hw import DG922Pro, FSV30
from mzm import scan, fit, control, io, plot

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s  %(levelname)-7s  %(message)s',
    datefmt='%H:%M:%S',
)
log = logging.getLogger(__name__)


def cmd_scan(mode, result_dir):
    """Steps 1 + 2: Vpi scan then ARB bias scan."""
    import config as cfg
    base_offsets = scan.make_offsets()
    n_pts = len(base_offsets)
    log.info('=' * 50)
    log.info('SCAN phase  mode=%s  %d points  %.3f→%.3f V  step=%.3f V',
             mode.name, n_pts, base_offsets[0], base_offsets[-1],
             abs(base_offsets[1] - base_offsets[0]) if n_pts > 1 else 0)
    log.info('=' * 50)
    t_start = time.time()

    with DG922Pro() as gen, FSV30() as sa:
        offsets1, s1_sin, s2_sin, vpi_result = scan.vpi_scan(gen, sa, base_offsets)

        if vpi_result is None:
            log.error('Vpi scan: could not find two valleys — aborting')
            return None

        v_null1, v_null2, _, _ = vpi_result
        vpi = abs(v_null2 - v_null1)
        v_null = v_null1
        log.info('Vpi = %.3f V  (valleys at %.3f, %.3f V)  V_null = %.3f V',
                 vpi, v_null1, v_null2, v_null)

        io.save_csv(
            os.path.join(result_dir, 'vpi_scan.csv'),
            headers=['offset_V', 's1_dbm', 's2_dbm'],
            rows=zip(offsets1, s1_sin, s2_sin),
        )
        io.save_json(os.path.join(result_dir, 'vpi.json'),
                     {'vpi': vpi, 'v_null': v_null})

        actual_offsets, s1_arb, s2_arb = scan.bias_scan(gen, sa, mode, vpi, base_offsets)
        sa.set_input_coupling('AC')

    io.save_csv(
        os.path.join(result_dir, 'arb_scan.csv'),
        headers=['actual_offset_V', 's1_dbm', 's2_dbm'],
        rows=zip(actual_offsets, s1_arb, s2_arb),
    )
    log.info('Scan data saved → %s', result_dir)

    plot.save_scan_plot(
        os.path.join(result_dir, 'scan.png'),
        offsets1, s1_sin, s2_sin,
        actual_offsets, s1_arb, s2_arb,
        vpi_result, mode.name, vpi,
    )
    log.info('Scan plot saved → scan.png')
    log.info('SCAN phase done — elapsed %.0f s', time.time() - t_start)
    return vpi


def cmd_fit(mode, result_dir):
    """Step 3: fit ratio curve from arb_scan.csv.

    For s2_min modes (quad_pm) the ratio curve has an asymptote inside
    the fit window, making curve_fit unreliable.  Falls back to the
    quick-estimate method automatically.
    """
    import csv, json

    if not mode.use_curve_fit:
        log.info('Curve fit disabled for this mode — using quick estimate instead')
        return cmd_quick_estimate(mode, result_dir)

    vpi_path = os.path.join(result_dir, 'vpi.json')
    scan_path = os.path.join(result_dir, 'arb_scan.csv')
    if not os.path.exists(vpi_path) or not os.path.exists(scan_path):
        log.error('Run --step scan first to generate input files')
        return None

    log.info('=' * 50)
    log.info('FIT phase  mode=%s', mode.name)
    log.info('=' * 50)

    with open(vpi_path) as f:
        vpi_data = json.load(f)
    vpi = vpi_data['vpi']

    actual_offsets, s1_list, s2_list = [], [], []
    with open(scan_path) as f:
        for row in csv.DictReader(f):
            actual_offsets.append(float(row['actual_offset_V']))
            s1_list.append(float(row['s1_dbm']))
            s2_list.append(float(row['s2_dbm']))

    log.info('Loaded %d data points from %s', len(actual_offsets), scan_path)
    result = fit.ratio_fit(actual_offsets, s1_list, s2_list, vpi, mode)
    r_db = 20 * math.log10(result.r_target) if result.r_target > 0 else float('-inf')
    log.info('Fit result: R_target=%.4f (%.1f dB)  V0=%.4f V  Vpi_fit=%.4f V  (Vpi_scan=%.4f V)',
             result.r_target, r_db, result.V0, result.vpi_fit, vpi)

    io.save_json(os.path.join(result_dir, 'fit_result.json'), {
        'r_target': result.r_target,
        'A':        result.A,
        'V0':       result.V0,
        'vpi_fit':  result.vpi_fit,
        'vpi_scan': vpi,
    })

    plot.save_fit_plot(
        os.path.join(result_dir, 'fit.png'),
        actual_offsets, s1_list, s2_list,
        result, mode, mode.name, vpi,
    )
    log.info('Fit plot saved → fit.png')
    return result


def cmd_quick_estimate(mode, result_dir):
    """Estimate control target from scan CSV — skip curve_fit.

    'ratio' strategy (max_quad): finds s2 valley, walks Vpi/4 into the
        monotonic region, reads r as R_target and computes V0.
    's2_min' strategy (quad_pm): finds the deepest s2 valley and uses
        its offset / s2 value directly for gradient-descent control.
    """
    import csv, json, math

    vpi_path = os.path.join(result_dir, 'vpi.json')
    scan_path = os.path.join(result_dir, 'arb_scan.csv')
    if not os.path.exists(vpi_path) or not os.path.exists(scan_path):
        log.error('Run --step scan first to generate input files')
        return None

    with open(vpi_path) as f:
        vpi = json.load(f)['vpi']

    actual_offsets, s1_list, s2_list = [], [], []
    with open(scan_path) as f:
        for row in csv.DictReader(f):
            actual_offsets.append(float(row['actual_offset_V']))
            s1_list.append(float(row['s1_dbm']))
            s2_list.append(float(row['s2_dbm']))

    # find deepest s2 valley
    valley_idx = min(range(len(s2_list)), key=lambda i: s2_list[i])
    v_valley = actual_offsets[valley_idx]
    s2_valley = s2_list[valley_idx]

    if mode.control_strategy == 's2_min':
        # S₂-min mode: lock directly to the S₂ valley
        log.info('Quick estimate (s2_min): valley @ offset=%.3f V  s2=%.1f dBm',
                 v_valley, s2_valley)
        io.save_json(os.path.join(result_dir, 'fit_result.json'), {
            'strategy':      's2_min',
            's2_valley_dbm': s2_valley,
            'V_valley':      v_valley,
            'vpi_scan':      vpi,
        })
        log.info('Quick-estimate fit_result.json saved')
        return {'s2_valley_dbm': s2_valley, 'V_valley': v_valley, 'vpi': vpi}

    # ratio mode
    ref = mode.vdc_ref(vpi)
    p1 = [10 ** (s / 10) for s in s1_list]
    p2 = [10 ** (s / 10) for s in s2_list]

    v_valley_eff = v_valley - ref
    V0_est = v_valley_eff + vpi / 4
    target_off = ref + V0_est
    best_idx = min(range(len(actual_offsets)),
                   key=lambda i: abs(actual_offsets[i] - target_off))
    r_est = (p1[best_idx] / p2[best_idx]) ** 0.5

    log.info('Quick estimate: s2 valley @ %.3f V  →  target @ %.3f V  (Vpi/4 away)',
             v_valley, target_off)
    log.info('  v_valley=%.3f V  V0=%.3f V  R_target=%.4f',
             v_valley_eff, V0_est, r_est)

    result = fit.FitResult(A=float(r_est), V0=float(V0_est), vpi_fit=vpi)
    io.save_json(os.path.join(result_dir, 'fit_result.json'), {
        'strategy':  'ratio',
        'r_target':  result.r_target,
        'A':         result.A,
        'V0':        result.V0,
        'vpi_fit':   result.vpi_fit,
        'vpi_scan':  vpi,
    })
    log.info('Quick-estimate fit_result.json saved')
    return result


def cmd_control(mode, result_dir):
    """Step 4: closed-loop control (ratio PI or S₂-min gradient descent)."""
    import json

    fit_path = os.path.join(result_dir, 'fit_result.json')
    vpi_path = os.path.join(result_dir, 'vpi.json')
    if not os.path.exists(fit_path):
        log.error('Run --step fit first to generate fit_result.json')
        return

    with open(fit_path) as f:
        fd = json.load(f)
    with open(vpi_path) as f:
        vpi = json.load(f)['vpi']

    log_path = os.path.join(result_dir, 'control_log.csv')
    strategy = fd.get('strategy', 'ratio')

    if strategy == 's2_min':
        # ── S₂ gradient-descent control (quad_pm) ──────────────────────────
        s2_valley_dbm = fd['s2_valley_dbm']
        V_valley = fd['V_valley']

        import config as cfg
        log.info('=' * 50)
        log.info('CONTROL phase  mode=%s  strategy=S₂-min  V_start=%.4f V  '
                 'S₂_floor≈%.1f dBm  K=%.1f',
                 mode.name, V_valley, s2_valley_dbm, 0.5)
        log.info('Press Ctrl+C to stop and save the control plot')
        log.info('=' * 50)
        with DG922Pro() as gen, FSV30() as sa:
            mode.configure_source(gen, vpi)
            scan.setup_analyzer(sa)
            try:
                control.s2_min_control_loop(gen, sa, mode, vpi,
                                            s2_valley_dbm,
                                            measure_fn=scan.measure_markers,
                                            log_path=log_path,
                                            V_start=V_valley)
            except KeyboardInterrupt:
                log.info('Control loop stopped by user')
            finally:
                gen.output_off(1)
                sa.set_input_coupling('AC')

    else:
        # ── ratio PI control (max_quad) ────────────────────────────────────
        fit_result = fit.FitResult(A=fd['A'], V0=fd['V0'], vpi_fit=fd['vpi_fit'])

        import config as cfg
        v_start = mode.initial_offset(vpi, fit_result.V0)
        log.info('=' * 50)
        log.info('CONTROL phase  mode=%s  R_target=%.4f  V_start=%.4f V  Ki=%.4f',
                 mode.name, fit_result.r_target, v_start, cfg.K_I)
        log.info('Press Ctrl+C to stop and save the control plot')
        log.info('=' * 50)
        with DG922Pro() as gen, FSV30() as sa:
            mode.configure_source(gen, vpi)
            scan.setup_analyzer(sa)
            try:
                control.pi_control_loop(gen, sa, mode, fit_result, vpi,
                                        measure_fn=scan.measure_markers,
                                        log_path=log_path)
            except KeyboardInterrupt:
                log.info('Control loop stopped by user')
            finally:
                gen.output_off(1)
                sa.set_input_coupling('AC')

    if os.path.exists(log_path):
        plot.save_control_plot(
            os.path.join(result_dir, 'control.png'),
            log_path, fd.get('r_target', 0), mode.name,
        )
        log.info('Control plot saved → control.png')


def main():
    parser = argparse.ArgumentParser(description='MZM bias point controller')
    parser.add_argument('--mode', choices=list(MODES), default='max_quad',
                        help='Control mode')
    parser.add_argument('--step',
                        choices=['all', 'scan', 'fit', 'control', 'scan-control'],
                        default='all',
                        help='Which step(s) to run')
    parser.add_argument('--results-dir', default=None,
                        help='Reuse existing result dir (for fit/control steps)')
    args = parser.parse_args()

    mode_cls = MODES[args.mode]
    mode = mode_cls()

    if args.results_dir:
        result_dir = args.results_dir
    else:
        result_dir = io.make_result_dir(args.mode)
    log.info(f'Result dir: {result_dir}')

    if args.step in ('scan', 'all', 'scan-control'):
        vpi = cmd_scan(mode, result_dir)
        if vpi is None:
            return

    if args.step in ('fit', 'all'):
        cmd_fit(mode, result_dir)

    if args.step == 'scan-control':
        cmd_quick_estimate(mode, result_dir)

    if args.step in ('control', 'all', 'scan-control'):
        cmd_control(mode, result_dir)


if __name__ == '__main__':
    main()
