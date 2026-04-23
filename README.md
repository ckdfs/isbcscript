# isbcscript — MZM Bias Control

通过导频信号比值法对马赫-曾德调制器（MZM）进行偏置点闭环控制，
支持多种切换控制模式（最大/最小点↔正交点、正/负正交点等）。

## Quick Start

```bash
# 依赖
pip install matplotlib scipy numpy

# 运行（完整流程）
python main.py --mode max_quad --step all

# 仅Vpi标定
python vpi_scan.py
```

## 文档

- 理论推导：`docs/theory/`
- 实验计划：`docs/experiments/`
- 接口规格：`docs/spec/`
- 硬件配置：`docs/hardware/setup.md`
- AI维护指南：`CLAUDE.md`
