# ModeBase 接口契约

新增控制模式时**必读**本文档。每个模式必须继承 `ModeBase` 并实现以下方法。

**代码位置**：`mzm/modes/base.py`

---

## 接口定义

```python
class ModeBase(ABC):

    name: str              # 与 MODES 字典键名一致，用于日志和结果目录命名
    description: str       # 人类可读描述，显示在 --help 中
    control_strategy: str  # 'ratio' (比值 PI 控制) 或 's2_min' (S₂ 梯度下降)

    # 必须实现的抽象方法
    def configure_source(self, gen: DG922Pro, vpi: float) -> None: ...
    def sweep_offsets(self, base_offsets: list[float], vpi: float) -> list[float]: ...
    def fit_model(self, v: float, A: float, V0: float, vpi_fit: float) -> float: ...
    def initial_offset(self, vpi: float, V0_fit: float) -> float: ...

    # 可选重写的具体方法
    def vdc_ref(self, vpi: float) -> float: ...
    def offset_limits(self, vpi: float) -> tuple[float, float]: ...
```

---

## 抽象方法说明

### `configure_source(gen, vpi)`

在步骤二开始时（步骤一已测得 `vpi`）调用，配置 DG922Pro CH1 为该模式所需的波形。

**约定**：
- 函数返回前 CH1 输出应处于**打开**状态
- 频率单位：Hz；幅度单位：Vpp；偏置单位：V
- 若使用 ARB 模式，先发 `:SOURce1:FUNCtion ARB` 保留预加载波形

**max_quad 示例**：
```python
def configure_source(self, gen, vpi):
    gen.send(':SOURce1:FUNCtion ARB')
    gen.set_frequency(1, 20e3)
    gen.set_amplitude(1, vpi / 2 + 0.8)
    gen.set_offset(1, vpi / 4)
    gen.output_on(1)
```

**quad_pm 示例**（固定幅度，因波形预加载）：
```python
def configure_source(self, gen, vpi):
    gen.send(':SOURce1:FUNCtion ARB')
    gen.set_frequency(1, 20e3)
    gen.set_amplitude(1, 6.2)        # 固定值，波形范围 −0.4~5.8 V
    gen.set_offset(1, vpi / 2)
    gen.output_on(1)
```

---

### `sweep_offsets(base_offsets, vpi)`

将 `config.py` 中定义的基础 offset 序列（$[-6, +6]$ V）转换为实际发送给 CH1 的 offset 序列。

**约定**：
- 返回列表长度与 `base_offsets` 相同
- 坐标变换由此处统一处理，`scan.bias_scan` 不做额外偏移
- 偏移量使扫描中心在目标工作点附近

**max_quad 示例**（右移 $V_\pi/4$）：
```python
return [round(v + vpi / 4, 6) for v in base_offsets]
```

**quad_pm 示例**（右移 $V_\pi/2$，因方波幅度 = Vπ）：
```python
return [round(v + vpi / 2, 6) for v in base_offsets]
```

---

### `fit_model(v, A, V0, vpi_fit)`

供 `scipy.optimize.curve_fit` 使用的拟合函数（仅 'ratio' 策略使用）。

- `v`：有效偏置偏差 = `actual_offset - vdc_ref(vpi)`（V）
- `A`：幅度参数（= $R_{target}$）
- `V0`：零点修正（V）
- `vpi_fit`：拟合半波电压（V）
- 返回值：幅度比 $r$（无量纲）

**约定**：
- 函数在拟合窗口（$|v| < 0.20\,V_\pi$）内必须单调
- 使用 `numpy.abs` / `numpy.tan`
- max_quad 模式中 $r$ 随 $v$ 单调**递减**

**通用形式**（max_quad 和 quad_pm 共用）：
```python
import numpy as np

def fit_model(self, v, A, V0, vpi_fit):
    # r = A·|tan(π/4 − π(v−V0)/Vpi)|
    #   左侧奇点（P2→0）：v = V0 − Vpi/4
    #   目标点（r = A）：  v = V0
    #   右侧零点（P1→0）：v = V0 + Vpi/4
    return A * np.abs(np.tan(np.pi / 4 - np.pi * (v - V0) / vpi_fit))
```

> **注意**：quad_pm 的 `vdc_ref = Vpi/2` 使其 `v=0` 在 S₂ 渐近线附近，
> curve_fit 在此模式下不可靠。's2_min' 策略自动跳过拟合，改用扫描数据直接估算。

---

### `initial_offset(vpi, V0_fit)`

控制循环的初始 CH1 offset 值（V）。通常为 `vdc_ref(vpi) + V0_fit`。

---

## 具体方法（可选重写）

### `vdc_ref(vpi) → float`

Vdc_eff 坐标参考点。默认 `vpi/4`（对应 max_quad 的目标点）。

quad_pm 重写为 `vpi/2`（两正交点之间，S₂ 谷底位置）。

---

### `offset_limits(vpi) → (float, float)`

控制回路中 CH1 offset 的安全范围。默认 `[vdc_ref − Vpi, vdc_ref + Vpi]`。

quad_pm 重写以考虑 ARB 振幅 6.2 Vpp 带来的硬件上限 6.9 V：
```python
def offset_limits(self, vpi):
    hw_hi, hw_lo = 6.9, -6.9   # ARB 输出摆幅 ±3.1 V
    center = self.vdc_ref(vpi)
    return (max(hw_lo, center - vpi), min(hw_hi, center + vpi))
```

---

### `control_strategy: str`

控制回路策略选择（类属性，非方法）：

| 值 | 控制方式 | 适用模式 |
|----|---------|---------|
| `'ratio'` | PI 积分控制，追 $r = R_{target}$ | max_quad |
| `'s2_min'` | 梯度下降，最小化 $S_2$ (40kHz) | quad_pm |

对应 `control.py` 中两个不同的控制回路函数：
- `'ratio'` → `pi_control_loop()`
- `'s2_min'` → `s2_min_control_loop()`

---

## 注册新模式

在 `mzm/modes/__init__.py` 的 `MODES` 字典中注册，`main.py` 自动读取。
