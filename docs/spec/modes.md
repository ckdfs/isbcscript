# 各控制模式数学规格摘要

代码实现时的快速参考。详细推导见 `docs/theory/modes/`。

---

## max_quad — 最大/最小点 ↔ 正交点

| 字段 | 值 |
|------|----|
| `name` | `'max_quad'` |
| `control_strategy` | `'ratio'`（比值 PI 控制） |
| 状态A | $\phi_{DC}$（最大点，PWM低电平） |
| 状态B | $\phi_{DC} + \pi/2$（正交点，PWM高电平） |
| 占空比 $A$ | 0.5 |
| $\phi_0$ | $\pi/4 = 45°$ |
| $\kappa$ | $1/\sqrt{2}$（$-3\ \text{dB}$） |
| 拟合模型 | $r = A\cdot\|\tan(\pi/4 - \pi(v-V_0)/V_\pi^{fit})\|$（随 $v$ 单调递减） |
| $R_{target}$ | $A_{fit}$（拟合所得，理论值 $J_1/J_2$） |
| CH1 模式 | ARB（预加载波形） |
| ARB 幅度 | $V_\pi/2 + 0.8$ Vpp |
| `vdc_ref` | $V_\pi/4$ V |
| `initial_offset` | $V_\pi/4 + V_0$ |
| `sweep_offsets` | base + $V_\pi/4$ |
| `offset_limits` | $[V_\pi/4 - V_\pi,\; V_\pi/4 + V_\pi]$ |

---

## quad_pm — 正/负正交点切换

| 字段 | 值 |
|------|----|
| `name` | `'quad_pm'` |
| `control_strategy` | **`'s2_min'`**（自适应探针梯度下降） |
| `use_curve_fit` | **`False`**（渐近线在拟合窗口内，curve_fit 不可靠） |
| 状态A | $\phi_{DC} + \pi$（负正交点，方波HIGH，sin导频） |
| 状态B | $\phi_{DC}$（正正交点，方波LOW，cos导频） |
| 占空比 $A$ | 0.5 |
| $\kappa$ | $1/\sqrt{2}$（−3 dB，仅作用于 $S_1$） |
| f₂ 两态 | **同号叠加**（不抵消），$S_2 \propto 2J_2\vert\cos\phi_{DC}\vert$ |
| 控制信号 | **$S_2$（40 kHz）→ min**，$S_2\propto\vert\cos\phi_{DC}\vert$，谷底即目标 |
| 探针步长 | **自适应** 0.02–0.10 V（$= \max(0.02, \min(0.10, \mathrm{excess\_dB}/50))$） |
| 步长缩放 | 0.003 V/dB（$\mathrm{step} = 0.003 \times \mathrm{excess\_dB}$） |
| CH1 模式 | ARB（预加载波形） |
| ARB 波形 | 16,384 点，200kHz 方波（0V↔5.4V）+ sin/cos 导频 |
| ARB 幅度 | **6.2 Vpp**（固定，波形范围 −0.4 ~ 5.8 V） |
| `vdc_ref` | **$V_\pi/2$** V（S₂ 谷底位置，两正交点电气中点） |
| `initial_offset` | 谷底 offset（由 quick_estimate 从扫描数据确定） |
| `sweep_offsets` | base + $V_\pi/2$ |
| `offset_limits` | $[\max(-6.9, -V_\pi/2),\; \min(6.9, 3V_\pi/2)]$ |

> **控制策略说明**：quad_pm 的目标是两态分别在正/负正交点（$\phi=\pm\pi/2$），
> 此时 $S_2\propto\vert\cos\phi\vert=0$。控制回路用自适应探针判断 $S_2$ 梯度方向，
> 步长与 $S_2$ 距谷底的距离成正比。远离谷底时探针自动放大（0.10 V），
> 靠近时缩小（0.02 V），兼顾收敛速度和精度。
> 
> `vdc_ref = Vpi/2` 恰好位于 $S_2$ 渐近线，比值 $r$ 在此发散，因此
> `use_curve_fit = False`，`--step fit` 自动跳过 curve_fit 改用 quick_estimate。

---

## max_min — 最大点 ↔ 最小点切换

| 字段 | 值 |
|------|----|
| `name` | `'max_min'` |
| `control_strategy` | **`'s1_min'`**（自适应探针梯度下降） |
| `use_curve_fit` | **`False`**（r=0 处为 cusp，curve_fit 不可靠） |
| 状态A | $\phi_{DC}=0$（最大点，方波LOW，cos导频） |
| 状态B | $\phi_{DC}=\pi$（最小点，方波HIGH，sin导频） |
| 占空比 $A$ | 0.5 |
| $|S_1|$ | $2J_1|\sin\phi_{DC}|\sqrt{A^2+(1-A)^2} = \sqrt{2}J_1|\sin\phi_{DC}|$ |
| $|S_2|$ | $2J_2|\cos\phi_{DC}|$（与 $A$ 无关，两态同号叠加） |
| 控制信号 | **$S_1$（20 kHz）→ min**，$S_1\propto|\sin\phi_{DC}|$，谷底即目标 |
| 探针步长 | **自适应** 0.02–0.10 V（$= \max(0.02, \min(0.10, \mathrm{excess\_dB}/50))$） |
| 步长缩放 | 0.001 V/dB（$\mathrm{step} = 0.001 \times \mathrm{excess\_dB}$） |
| CH1 模式 | ARB（`load_arb_waveform` 上传） |
| ARB 波形 | 16,384 点，200 kHz 方波（50%），cos(LOW)/sin(HIGH) 导频 |
| ARB 幅度 | **$V_\pi + 0.8$ Vpp**（Vpi 感知） |
| `vdc_ref` | **$V_\pi/2$** V（最大点/最小点电气中点） |
| `initial_offset` | 谷底 offset（由 quick_estimate 从扫描数据确定） |
| `sweep_offsets` | base + $V_\pi/2$ |
| `offset_limits` | $[\max(-10+\tfrac{V_\pi+0.8}{2},\; -\tfrac{V_\pi}{2}),\; \min(10-\tfrac{V_\pi+0.8}{2},\; \tfrac{3V_\pi}{2})]$ |
| 拟合模型 | $r = A \cdot |\tan(\pi(v-V_0)/V_\pi^{fit})|$（仅供参考，控制不使用） |

> **控制策略说明**：max_min 的目标是锁定在最大点（$\phi_{DC}=0$）。
> 此时 $S_1\propto|\sin 0|=0$ 形成 V 形谷底。控制回路用自适应探针判断 $S_1$
> 梯度方向，步长与 $S_1$ 距谷底的距离成正比。
> 
> **导频选择**：必须使用 cos(LOW)/sin(HIGH) 切换。若两态同用 sin 导频，
> 则 $S_1, S_2 \propto (2A-1)$，在 $A=0.5$ 时信号完全消失。
> cos/sin 切换使 $S_2$ 两态贡献同号叠加（均为 $-\cos 2\omega t$），
> 消除 $(2A-1)$ 衰减因子。
> 
> $|S_2| \propto |\cos\phi_{DC}|$ 在目标处为**峰值**而非谷底，
> 因此控制信号选 $S_1$ 而非 $S_2$（与 quad_pm 相反）。
