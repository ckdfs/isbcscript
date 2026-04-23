# ModeBase 接口契约

新增控制模式时**必读**本文档。每个模式必须继承 `ModeBase` 并实现以下四个方法。

**代码位置**：`mzm/modes/base.py`

---

## 接口定义

```python
class ModeBase(ABC):

    name: str           # 与 MODES 字典键名一致，用于日志和结果目录命名
    description: str    # 人类可读描述，显示在 --help 中

    def configure_source(self, gen: DG922Pro, vpi: float) -> None: ...
    def sweep_offsets(self, base_offsets: list[float], vpi: float) -> list[float]: ...
    def fit_model(self, v: float, A: float, V0: float, vpi_fit: float) -> float: ...
    def initial_offset(self, vpi: float, V0_fit: float) -> float: ...
```

---

## 方法说明

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
    gen.set_offset(1, vpi / 4)      # 初始偏置，闭环时会被覆盖
    gen.output_on(1)
```

---

### `sweep_offsets(base_offsets, vpi)`

将 `config.py` 中定义的基础 offset 序列（$[-6, +6]$ V，步进 50 mV）
转换为实际发送给 CH1 的 offset 序列。

**约定**：
- 返回列表长度与 `base_offsets` 相同
- 坐标变换由此处统一处理，`scan.bias_scan` 不做额外偏移

**max_quad 示例**（右移 $V_\pi/4$ 使扫描中心在最大点）：
```python
def sweep_offsets(self, base_offsets, vpi):
    return [round(v + vpi / 4, 6) for v in base_offsets]
```

---

### `fit_model(v, A, V0, vpi_fit)`

供 `scipy.optimize.curve_fit` 使用的拟合函数。

- `v`：有效偏置偏差（`actual_offset - vpi/4`，V）
- `A`：幅度参数（= $R_{target}$）
- `V0`：零点修正（V）
- `vpi_fit`：拟合半波电压（V）
- 返回值：幅度比 $r$（无量纲）

**约定**：
- 函数在拟合窗口（$|v - V_0| < V_\pi/3$）内必须单调
- 使用 `abs()` 处理 `tan` 的符号问题

**max_quad 示例**：
```python
def fit_model(self, v, A, V0, vpi_fit):
    return A * abs(math.tan(math.pi * (v - V0) / vpi_fit + math.pi / 4))
```

---

### `initial_offset(vpi, V0_fit)`

控制循环的初始 CH1 offset 值（V）。通常为目标工作点的理论偏压加上拟合零点修正。

**max_quad 示例**（目标工作点：$V_{DC}=0$，CH1 offset = $V_\pi/4$）：
```python
def initial_offset(self, vpi, V0_fit):
    return vpi / 4 + V0_fit
```

---

## 注册新模式

实现完成后，在 `mzm/modes/__init__.py` 的 `MODES` 字典中注册：

```python
from mzm.modes.your_mode import YourMode

MODES = {
    'max_quad': MaxQuadMode,
    'your_mode': YourMode,   # 新增
}
```

`main.py` 无需修改，自动从 `MODES` 读取。
