#!/usr/bin/env python3
"""MZM bias control — unified entry point.

Usage:
    python main.py --mode max_quad --step all
    python main.py --mode max_quad --step scan
    python main.py --mode max_quad --step fit
    python main.py --mode max_quad --step control
"""

import argparse
import logging
import os

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

    with DG922Pro() as gen, FSV30() as sa:
        log.info('Step 1: Vpi scan (sine mode)')
        offsets1, s1_sin, s2_sin, vpi_result = scan.vpi_scan(gen, sa, base_offsets)

        if vpi_result is None:
            log.error('Vpi scan: could not find two valleys — aborting')
            return None

        v_null1, v_null2, _, _ = vpi_result
        vpi = abs(v_null2 - v_null1)
        v_null = v_null1
        log.info(f'Vpi = {vpi:.3f} V,  V_null = {v_null:.3f} V')

        io.save_csv(
            os.path.join(result_dir, 'vpi_scan.csv'),
            headers=['offset_V', 's1_dbm', 's2_dbm'],
            rows=zip(offsets1, s1_sin, s2_sin),
        )
        io.save_json(os.path.join(result_dir, 'vpi.json'),
                     {'vpi': vpi, 'v_null': v_null})

        log.info(f'Step 2: ARB bias scan ({mode.name})')
        actual_offsets, s1_arb, s2_arb = scan.bias_scan(gen, sa, mode, vpi, base_offsets)
        sa.set_input_coupling('AC')

    io.save_csv(
        os.path.join(result_dir, 'arb_scan.csv'),
        headers=['actual_offset_V', 's1_dbm', 's2_dbm'],
        rows=zip(actual_offsets, s1_arb, s2_arb),
    )
    log.info(f'Scan data saved to {result_dir}')

    plot.save_scan_plot(
        os.path.join(result_dir, 'scan.png'),
        offsets1, s1_sin, s2_sin,
        actual_offsets, s1_arb, s2_arb,
        vpi_result, mode.name, vpi,
    )
    log.info('Scan plot saved → scan.png')
    return vpi


def cmd_fit(mode, result_dir):
    """Step 3: fit ratio curve from arb_scan.csv."""
    import csv, json

    vpi_path = os.path.join(result_dir, 'vpi.json')
    scan_path = os.path.join(result_dir, 'arb_scan.csv')
    if not os.path.exists(vpi_path) or not os.path.exists(scan_path):
        log.error('Run --step scan first to generate input files')
        return None

    with open(vpi_path) as f:
        vpi_data = json.load(f)
    vpi = vpi_data['vpi']

    actual_offsets, s1_list, s2_list = [], [], []
    with open(scan_path) as f:
        for row in csv.DictReader(f):
            actual_offsets.append(float(row['actual_offset_V']))
            s1_list.append(float(row['s1_dbm']))
            s2_list.append(float(row['s2_dbm']))

    result = fit.ratio_fit(actual_offsets, s1_list, s2_list, vpi, mode)
    log.info(f'Fit result: R_target={result.r_target:.4f}  V0={result.V0:.4f} V'
             f'  Vpi_fit={result.vpi_fit:.4f} V  (Vpi_scan={vpi:.4f} V)')

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


def cmd_control(mode, result_dir):
    """Step 4: closed-loop PI control."""
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

    fit_result = fit.FitResult(A=fd['A'], V0=fd['V0'], vpi_fit=fd['vpi_fit'])
    log_path = os.path.join(result_dir, 'control_log.csv')

    log.info(f'Starting control loop  mode={mode.name}  R_target={fit_result.r_target:.4f}')
    log.info('Press Ctrl+C to stop and save the control plot')
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
            log_path, fit_result.r_target, mode.name,
        )
        log.info('Control plot saved → control.png')


def main():
    parser = argparse.ArgumentParser(description='MZM bias point controller')
    parser.add_argument('--mode', choices=list(MODES), default='max_quad',
                        help='Control mode')
    parser.add_argument('--step',
                        choices=['all', 'scan', 'fit', 'control'],
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

    if args.step in ('scan', 'all'):
        cmd_scan(mode, result_dir)

    if args.step in ('fit', 'all'):
        cmd_fit(mode, result_dir)

    if args.step in ('control', 'all'):
        cmd_control(mode, result_dir)


if __name__ == '__main__':
    main()
