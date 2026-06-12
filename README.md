# isbcscript — MZM Bias Control

通过导频谐波信号对马赫-曾德调制器（MZM）进行偏置点闭环控制，
支持最大/最小点 ↔ 正交点、正/负正交点、最大点 ↔ 最小点等切换模式。

## Quick Start

```bash
# 依赖
pip install matplotlib scipy numpy

# 完整流程：Vπ扫描 → ARB扫描 → 拟合/快速估计 → 闭环控制
python main.py --mode max_quad --step all
python main.py --mode quad_pm  --step all
python main.py --mode max_min  --step all

# 分步运行并复用结果目录
python main.py --mode max_quad --step scan
python main.py --mode max_quad --step fit --results-dir results/YYYYMMDD_HHMMSS_max_quad
python main.py --mode max_quad --step control --results-dir results/YYYYMMDD_HHMMSS_max_quad

# 跳过 curve_fit，直接从扫描曲线估计控制目标后进入控制
python main.py --mode max_quad --step scan-control

# 旧版独立 Vπ/ARB 扫描脚本（保留作人工排查）
python vpi_scan.py
```

## 模式

| 模式 | 控制策略 | 目标 |
|------|----------|------|
| `max_quad` | 比值 PI 控制 | 最大/最小点 ↔ 正交点 |
| `quad_pm` | `S2-min` 自适应探针控制 | 正/负正交点 |
| `max_min` | `S1-min` 自适应探针控制 | 最大点 ↔ 最小点 |

结果保存在 `results/YYYYMMDD_HHMMSS_{mode}/`，通常包含：
`vpi_scan.csv`、`arb_scan.csv`、`fit_result.json`、`control_log.csv`
以及对应的 `scan.png`、`fit.png`、`control.png`。

## 文档

- 理论推导：`docs/theory/`
- 实验计划：`docs/experiments/modes/`
- 结果判读与参考 run：`docs/experiments/results_baselines.md`
- 接口规格：`docs/spec/`
- 硬件配置：`docs/hardware/setup.md`
- AI维护指南：`CLAUDE.md`
