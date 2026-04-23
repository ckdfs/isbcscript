# MZM Bias Control — Project Guide

MZM 偏置点闭环控制脚本库。通过导频信号比值法将 MZM 工作点锁定在
指定位置（最大点/正交点及其切换），支持多种切换控制模式。

## Commands

```bash
# 完整流程（Vpi标定 → 切换扫描 → 曲线拟合 → 闭环控制）
python main.py --mode max_quad --step all

# 分步运行
python main.py --mode max_quad --step scan     # 步骤一+二（扫描，存CSV）
python main.py --mode max_quad --step fit      # 步骤三（从CSV拟合，存JSON）
python main.py --mode max_quad --step control  # 步骤四（闭环，需先有拟合结果）

# 独立Vpi标定脚本（不依赖包结构，可单独运行）
python vpi_scan.py
```

## Architecture

```
config.py           — 所有可调参数（扫描范围、RBW、IP等），改参数只改这里
main.py             — CLI入口，--mode / --step 参数

mzm/hw.py           — DG922Pro / FSV30 驱动封装（仅此处引用skill路径和硬件IP）
mzm/scan.py         — 通用偏压扫描：vpi_scan() + bias_scan()
mzm/fit.py          — 比值曲线拟合：ratio_fit() → FitResult
mzm/control.py      — 通用PI控制循环：pi_control_loop()
mzm/plot.py         — 绘图工具：save_scan_plot()
mzm/io.py           — 结果目录管理、CSV/JSON读写
mzm/modes/base.py   — ModeBase抽象基类（接口契约）
mzm/modes/*.py      — 各控制模式实现

results/            — 输出目录，按 YYYYMMDD_HHMMSS_mode 子目录组织（已gitignore）
docs/               — 文档（见下方文档地图）
```

## Hardware

| 仪器 | IP | 端口 | 备注 |
|------|----|------|------|
| RIGOL DG922Pro | 192.168.99.115 | 5025 | 仅用 CH1 |
| R&S FSV30 | 192.168.99.209 | 5025 | 必须 DC 耦合（信号 < 1 MHz） |

## Critical Conventions

- **功率单位**：dBm（FSV30读数需 `-6 dB` 校正，`POWER_OFFSET_DB = 6.0`）
- **幅度比**：`r = sqrt(P1_linear / P2_linear)`，不是 dBm 差值
- **频率单位**：代码内统一用 Hz（不写 kHz/MHz 字面量）
- **ARB模式参数公式**：`amp = Vpi/2 + 0.8`（Vpp），`offset = Vpi/4`（V）
- **结果目录**：`io.make_result_dir(mode_name)` 创建，路径写入 `fit_result.json`

## Adding a New Mode（新增控制模式流程）

1. `docs/theory/modes/{name}.md` — 代入通用框架（`switching_framework.md`），推导该模式的 φ₀ 和 R_target
2. `docs/experiments/modes/{name}.md` — 填写硬件配置和实验步骤
3. `docs/spec/modes.md` — 补充该模式的数学规格摘要
4. `mzm/modes/{name}.py` — 继承 `ModeBase`，实现四个抽象方法（见 `docs/spec/modebase.md`）
5. `mzm/modes/__init__.py` — 在 `MODES` 字典中注册
6. `main.py` 无需修改（自动从 `MODES` 读取）

## Document Map

```
docs/theory/
  mzm_basics.md           — MZM模型 + Bessel展开（与模式无关的基础）
  switching_framework.md  — 切换信号傅里叶分析 + 比值函数（通用框架，A为参数）
  modes/max_quad.md       — 最大/最小点↔正交点的具体推导（A=0.5）
  modes/quad_pm.md        — 正/负正交点切换推导（待填充）
  modes/max_min.md        — 最大/最小点切换推导（待填充）

docs/experiments/modes/
  max_quad.md             — 四步实验计划（硬件配置、步骤、代码对应）

docs/spec/
  modebase.md             — ModeBase接口契约（新增模式必读）
  modes.md                — 各模式数学规格摘要
  data_formats.md         — CSV/JSON输出格式定义

docs/hardware/
  setup.md                — 硬件连接、信号链路图、校准流程
```
