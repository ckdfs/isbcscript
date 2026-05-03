"""
max_min — 最大点/最小点交替切换控制模式。

Theory:  docs/theory/modes/max_min.md
Experiment: docs/experiments/modes/max_min.md

Signal: CH1 ARB (sin/cos switching, same structure as quad_pm)
  amp    = Vpi + 0.8  (Vpp, full π phase swing + pilot margin)
  offset = Vpi/2      (V, centre of max (0V) / min (Vpi) states)
  freq   = 20 kHz

States (50% duty cycle):
  State A (LOW):  cos pilot, V_equiv = 0 V   → φ_A = 0   (max transmission)
  State B (HIGH): sin pilot, V_equiv = Vpi   → φ_B = π   (min transmission)

The sin/cos assignment is ESSENTIAL — it prevents S₂ cancellation between
states.  With same-sin pilot, both states contribute out-of-phase and the
signal is attenuated by |2A−1|, vanishing at A=0.5.  With sin/cos:
  |S₁| ∝ 2J₁·|sin(φ_DC)|·√(A²+(1−A)²)   → V-shaped valley at target
  |S₂| ∝ 2J₂·|cos(φ_DC)|                 → peak, A-independent
Control minimises S₁ via adaptive-probe gradient descent.
"""

import numpy as np

from mzm.modes.base import ModeBase


class MaxMinMode(ModeBase):
    name             = 'max_min'
    description      = '最大点 ↔ 最小点切换  (A=0.5, sin/cos导频, S₁-min梯度下降)'
    control_strategy = 's1_min'    # gradient descent on S₁ → lock to max point
    use_curve_fit    = False       # r=0 at target is a cusp → curve_fit unreliable

    def vdc_ref(self, vpi: float) -> float:
        return vpi / 2

    def offset_limits(self, vpi: float) -> tuple[float, float]:
        # ARB amp = Vpi + 0.8 Vpp → output swing ±(Vpi/2 + 0.4) from offset
        # DG922Pro output range: −10 ~ +10 V (high-Z)
        hw_hi = 10.0 - (vpi + 0.8) / 2
        hw_lo = -10.0 + (vpi + 0.8) / 2
        center = self.vdc_ref(vpi)
        return (max(hw_lo, center - 2 * vpi), min(hw_hi, center + vpi))

    def configure_source(self, gen, vpi: float) -> None:
        gen.send(':SOURce1:FUNCtion ARB')
        gen.set_frequency(1, 20e3)
        gen.set_amplitude(1, vpi + 0.8)
        gen.set_offset(1, vpi / 2)
        gen.output_on(1)

    def sweep_offsets(self, base_offsets: list, vpi: float) -> list:
        shift = vpi / 2
        return [round(v + shift, 6) for v in base_offsets]

    def fit_model(self, v: float, A: float, V0: float, vpi_fit: float) -> float:
        # r = A · |tan(π · (v − V0) / vpi_fit)|
        # Not used in control (use_curve_fit=False), but required by interface.
        return A * np.abs(np.tan(np.pi * (v - V0) / vpi_fit))

    def initial_offset(self, vpi: float, V0_fit: float) -> float:
        return vpi / 2 + V0_fit
