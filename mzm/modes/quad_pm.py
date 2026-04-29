"""
quad_pm — 正/负正交点切换控制模式。

Theory:  docs/theory/modes/quad_pm.md
Experiment: docs/experiments/modes/quad_pm.md

Signal: CH1 ARB (uploaded waveform encodes 200 kHz square wave + sin/cos pilot)
  amp    = 6.2        (Vpp, fixed — waveform range −0.4 ~ 5.8 V)
  offset = 2.7        (V, fixed — waveform DC centre)
  freq   = 20 kHz

Duty cycle A = 0.5  →  phi_0 = 45° in the framework, but the sin-on-HIGH /
cos-on-LOW assignment yields r = κ·(J₁/J₂)·|tan(φ_DC)| with κ = 1/√2.
After mapping φ_DC = π/4 − π·v/Vpi, the fit model has the same |tan(…)|
form as max_quad; only the empirical A_fit (≈ κ·J₁/J₂) differs.
"""

import math

import numpy as np

from mzm.arb_waveforms import quad_pm_waveform
from mzm.modes.base import ModeBase


class QuadPMMode(ModeBase):
    name        = 'quad_pm'
    description = '正/负正交点切换  (A=0.5, sin/cos导频, κ=1/√2)'

    def configure_source(self, gen, vpi: float) -> None:
        samples = quad_pm_waveform()
        gen.load_arb_waveform(1, samples, freq=20e3, amp=6.2, offset=2.7)
        gen.output_on(1)

    def sweep_offsets(self, base_offsets: list, vpi: float) -> list:
        shift = vpi / 4
        return [round(v + shift, 6) for v in base_offsets]

    def fit_model(self, v: float, A: float, V0: float, vpi_fit: float) -> float:
        return A * np.abs(np.tan(np.pi / 4 - np.pi * (v - V0) / vpi_fit))

    def initial_offset(self, vpi: float, V0_fit: float) -> float:
        return vpi / 4 + V0_fit
