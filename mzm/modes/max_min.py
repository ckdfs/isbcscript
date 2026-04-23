"""
max_min — 最大点/最小点交替切换控制模式。

Theory:  docs/theory/modes/max_min.md  (待填充)
Experiment: docs/experiments/modes/max_min.md  (待填充)

Note: 此模式两个状态的一阶导频分量均为零（sin0=0, sinπ=0），
      比值法需改用二阶分量或其他误差信号。
"""

from mzm.modes.base import ModeBase


class MaxMinMode(ModeBase):
    name        = 'max_min'
    description = '最大点 ↔ 最小点切换  (待实现)'

    def configure_source(self, gen, vpi: float) -> None:
        raise NotImplementedError(
            'max_min not yet implemented. '
            'See docs/theory/modes/max_min.md for the derivation template.'
        )

    def sweep_offsets(self, base_offsets: list, vpi: float) -> list:
        raise NotImplementedError('max_min not yet implemented.')

    def fit_model(self, v: float, A: float, V0: float, vpi_fit: float) -> float:
        raise NotImplementedError('max_min not yet implemented.')

    def initial_offset(self, vpi: float, V0_fit: float) -> float:
        raise NotImplementedError('max_min not yet implemented.')
