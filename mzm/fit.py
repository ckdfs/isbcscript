"""
Ratio curve fitting — Step 3.

Public API:
    ratio_fit(actual_offsets, s1_dbm, s2_dbm, vpi, mode) → FitResult
"""

import dataclasses
import logging
import math

import numpy as np
from scipy.optimize import curve_fit

import config as cfg

log = logging.getLogger(__name__)


@dataclasses.dataclass
class FitResult:
    A:       float    # empirical amplitude = R_target
    V0:      float    # zero-point correction (V)
    vpi_fit: float    # cross-check Vpi from fit (V)

    @property
    def r_target(self) -> float:
        return self.A


def ratio_fit(actual_offsets: list, s1_dbm: list, s2_dbm: list,
              vpi: float, mode) -> FitResult:
    """Fit r(Vdc_eff) = mode.fit_model(v, A, V0, Vpi_fit) to scan data.

    actual_offsets  — CH1 offset values from bias_scan() (V)
    s1_dbm, s2_dbm  — power measurements (dBm, already corrected)
    vpi             — Vpi from vpi_scan (V), used as initial guess
    mode            — ModeBase instance providing fit_model()

    Returns FitResult with A (= R_target), V0, vpi_fit.
    """
    p1 = np.array([10 ** (s / 10) for s in s1_dbm])
    p2 = np.array([10 ** (s / 10) for s in s2_dbm])
    r_meas = np.sqrt(p1 / p2)

    vdc_eff = np.array(actual_offsets) - mode.vdc_ref(vpi)

    window = vpi * cfg.FIT_WINDOW_FRAC
    mask = (np.abs(vdc_eff) < window) & np.isfinite(r_meas)
    n_total = len(r_meas)
    n_fit = int(mask.sum())
    log.info('Fit window: |Vdc_eff| < %.3f V  →  %d/%d points in window',
             window, n_fit, n_total)
    if n_fit < 5:
        raise RuntimeError(
            f'Too few valid points in fit window (|Vdc_eff| < {window:.3f} V): '
            f'{n_fit} points'
        )

    vdc_fit = vdc_eff[mask]
    r_fit   = r_meas[mask]

    # Initial guess: A ≈ r at vdc_eff closest to 0 (= R_target by definition),
    # V0 = 0 (no DC offset correction), vpi_fit = vpi_scan.
    idx_centre = int(np.argmin(np.abs(vdc_fit)))
    A0 = float(r_fit[idx_centre])
    p0 = [A0, 0.0, vpi]
    log.info('Initial guess: A0=%.3f  V0=0  vpi_fit=%.3f V', A0, vpi)

    # Bounds prevent degenerate solutions (V0 within ±Vpi/2, vpi_fit within 50–200% of vpi_scan).
    bounds = (
        [0.0,       -vpi / 2,   vpi * 0.5],
        [np.inf,     vpi / 2,   vpi * 2.0],
    )
    popt, pcov = curve_fit(
        lambda v, A, V0, Vpi: mode.fit_model(v, A, V0, Vpi),
        vdc_fit, r_fit, p0=p0, bounds=bounds, maxfev=10000,
    )
    A_fit, V0_fit, Vpi_fit = popt

    # Per-point residuals for quality check
    r_pred = np.array([mode.fit_model(v, A_fit, V0_fit, Vpi_fit) for v in vdc_fit])
    residuals = r_fit - r_pred
    rmse = float(np.sqrt(np.mean(residuals ** 2)))
    log.info('Fit converged: R² ≈ %.4f  RMSE=%.4f', 1 - rmse / np.std(r_fit), rmse)

    return FitResult(A=float(A_fit), V0=float(V0_fit), vpi_fit=float(Vpi_fit))
