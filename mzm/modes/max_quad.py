"""
max_quad — 最大/最小点 ↔ 正交点切换控制模式。

Theory:  docs/theory/modes/max_quad.md
Experiment: docs/experiments/modes/max_quad.md

Signal: CH1 ARB (pre-loaded waveform encodes 200 kHz PWM + 20 kHz pilot)
  amp    = Vpi/2 + 0.8  (Vpp)
  offset = Vpi/4        (V)   ← center of control range
  freq   = 20 kHz

Duty cycle A = 0.5  →  phi_0 = 45°,  kappa = 1/sqrt(2)  (-3 dB)
R_target = A_fit  (empirical, from ratio_fit)
"""

import math

import numpy as np

from mzm.modes.base import ModeBase


class MaxQuadMode(ModeBase):
    name        = 'max_quad'
    description = '最大/最小点 ↔ 正交点切换  (A=0.5, φ₀=45°, −3 dB)'

    def configure_source(self, gen, vpi: float) -> None:
        amp    = vpi / 2 + 0.8
        offset = vpi / 4
        gen.send(':SOURce1:FUNCtion ARB')
        gen.set_frequency(1, 20e3)
        gen.set_amplitude(1, amp)
        gen.set_offset(1, offset)
        gen.output_on(1)

    def sweep_offsets(self, base_offsets: list, vpi: float) -> list:
        shift = vpi / 4
        return [round(v + shift, 6) for v in base_offsets]

    def fit_model(self, v, A: float, V0: float, vpi_fit: float):
        return A * np.abs(np.tan(np.pi * (v - V0) / vpi_fit + np.pi / 4))

    def initial_offset(self, vpi: float, V0_fit: float) -> float:
        return vpi / 4 + V0_fit
