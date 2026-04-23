"""
Ratio curve fitting — Step 3.

Public API:
    ratio_fit(actual_offsets, s1_dbm, s2_dbm, vpi, mode) → FitResult
"""

import dataclasses
import math

import numpy as np
from scipy.optimize import curve_fit

import config as cfg


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

    vdc_eff = np.array(actual_offsets) - vpi / 4

    window = vpi * cfg.FIT_WINDOW_FRAC
    mask = (np.abs(vdc_eff) < window) & np.isfinite(r_meas)
    if mask.sum() < 5:
        raise RuntimeError(
            f'Too few valid points in fit window (|Vdc_eff| < {window:.3f} V): '
            f'{mask.sum()} points'
        )

    vdc_fit = vdc_eff[mask]
    r_fit   = r_meas[mask]

    p0 = [1.0, 0.0, vpi]
    popt, _ = curve_fit(
        lambda v, A, V0, Vpi: mode.fit_model(v, A, V0, Vpi),
        vdc_fit, r_fit, p0=p0, maxfev=5000,
    )
    A_fit, V0_fit, Vpi_fit = popt
    return FitResult(A=float(A_fit), V0=float(V0_fit), vpi_fit=float(Vpi_fit))
