"""
quad_pm — 正/负正交点切换控制模式。

Theory:  docs/theory/modes/quad_pm.md
Experiment: docs/experiments/modes/quad_pm.md

Signal: CH1 ARB (pre-loaded waveform encodes 200 kHz square wave + sin/cos pilot)
  amp    = 6.2        (Vpp, fixed — waveform range −0.4 ~ 5.8 V)
  offset = Vpi/2      (V, centre of control range)
  freq   = 20 kHz

Square-wave amplitude ≈ Vpi  →  phase step ≈ π between states.
Target: State B at +π/2 (pos quadrature), State A at −π/2 (neg quadrature).
vdc_ref = Vpi/2 (centre of two quadrature points).

Duty cycle A = 0.5  →  phi_0 = 45° in the framework, but the sin-on-HIGH /
cos-on-LOW assignment yields r = κ·(J₁/J₂)·|tan(φ_DC)| with κ = 1/√2.
After mapping φ_DC = π/4 − π·v/Vpi, the fit model has the same |tan(…)|
form as max_quad; only the empirical A_fit (≈ κ·J₁/J₂) differs.
"""

import numpy as np

from mzm.modes.base import ModeBase


class QuadPMMode(ModeBase):
    name             = 'quad_pm'
    description      = '正/负正交点切换  (A=0.5, sin/cos导频, κ=1/√2)'
    control_strategy = 's2_min'   # gradient descent on S₂ → lock to quadrature points
    use_curve_fit    = False      # vdc_eff=0 is asymptote → curve_fit unreliable

    def vdc_ref(self, vpi: float) -> float:
        return vpi / 2

    def offset_limits(self, vpi: float) -> tuple[float, float]:
        # ARB amp = 6.2 Vpp → output swing ±3.1 V from offset
        # DG922Pro output range: −10 ~ +10 V (high-Z)
        #   → offset ∈ [−10+3.1, 10−3.1] = [−6.9, 6.9]
        hw_hi =  6.9
        hw_lo = -6.9
        center = self.vdc_ref(vpi)
        return (max(hw_lo, center - vpi), min(hw_hi, center + vpi))

    def configure_source(self, gen, vpi: float) -> None:
        gen.send(':SOURce1:FUNCtion ARB')
        gen.set_frequency(1, 20e3)
        gen.set_amplitude(1, 6.2)
        gen.set_offset(1, vpi / 2)
        gen.output_on(1)

    def sweep_offsets(self, base_offsets: list, vpi: float) -> list:
        shift = vpi / 2
        return [round(v + shift, 6) for v in base_offsets]

    def fit_model(self, v: float, A: float, V0: float, vpi_fit: float) -> float:
        return A * np.abs(np.tan(np.pi / 4 - np.pi * (v - V0) / vpi_fit))

    def initial_offset(self, vpi: float, V0_fit: float) -> float:
        return vpi / 2 + V0_fit
