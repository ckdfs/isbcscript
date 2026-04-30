"""
ModeBase — abstract interface for all control modes.

See docs/spec/modebase.md for the full contract description.
"""

from abc import ABC, abstractmethod


class ModeBase(ABC):
    name: str         # key in MODES dict; used for logging and result dir names
    description: str  # human-readable, shown in --help

    # ── abstract ────────────────────────────────────────────────────────────────

    @abstractmethod
    def configure_source(self, gen, vpi: float) -> None:
        """Configure DG922Pro CH1 for this mode (CH1 output ON on return)."""

    @abstractmethod
    def sweep_offsets(self, base_offsets: list, vpi: float) -> list:
        """Map base offset sequence to actual CH1 offset sequence."""

    @abstractmethod
    def fit_model(self, v: float, A: float, V0: float, vpi_fit: float) -> float:
        """Fitting function r(v) for scipy.curve_fit.

        v       — Vdc_eff = actual_offset - vdc_ref(vpi) (V)
        A       — amplitude parameter (= R_target at target point)
        V0      — zero-point correction (V)
        vpi_fit — fitted Vpi (V)
        returns — amplitude ratio r (dimensionless)
        """

    @abstractmethod
    def initial_offset(self, vpi: float, V0_fit: float) -> float:
        """Starting CH1 offset for the control loop (V)."""

    # ── control strategy ────────────────────────────────────────────────────────

    control_strategy: str = 'ratio'   # 'ratio' (PI on r) or 's2_min' (gradient descent on S₂)

    # ── concrete (override when needed) ─────────────────────────────────────────

    def vdc_ref(self, vpi: float) -> float:
        """DC reference point for the Vdc_eff coordinate.

        Vdc_eff = actual_offset - vdc_ref(vpi).  The target operating point
        is at Vdc_eff ≈ 0 (after V0 correction from the fit).
        """
        return vpi / 4

    def offset_limits(self, vpi: float) -> tuple[float, float]:
        """Return (min, max) safe CH1 offset range for the control loop.

        Default: ±Vpi around the operating point, clipped to instrument limits.
        Override when the ARB waveform amplitude imposes tighter hardware bounds.
        """
        import config as cfg
        center = self.vdc_ref(vpi)
        return (center - vpi, center + vpi)
