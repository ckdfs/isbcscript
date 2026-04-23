"""
quad_pm — 正/负正交点切换控制模式。

Theory:  docs/theory/modes/quad_pm.md  (待填充)
Experiment: docs/experiments/modes/quad_pm.md  (待填充)
"""

from mzm.modes.base import ModeBase


class QuadPMMode(ModeBase):
    name        = 'quad_pm'
    description = '正/负正交点切换  (待实现)'

    def configure_source(self, gen, vpi: float) -> None:
        raise NotImplementedError(
            'quad_pm not yet implemented. '
            'See docs/theory/modes/quad_pm.md for the derivation template.'
        )

    def sweep_offsets(self, base_offsets: list, vpi: float) -> list:
        raise NotImplementedError('quad_pm not yet implemented.')

    def fit_model(self, v: float, A: float, V0: float, vpi_fit: float) -> float:
        raise NotImplementedError('quad_pm not yet implemented.')

    def initial_offset(self, vpi: float, V0_fit: float) -> float:
        raise NotImplementedError('quad_pm not yet implemented.')
