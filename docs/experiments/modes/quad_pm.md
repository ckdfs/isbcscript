# 实验计划：正/负正交点切换（quad_pm）

**理论背景**：[docs/theory/modes/quad_pm.md](../../theory/modes/quad_pm.md)
**代码入口**：`python main.py --mode quad_pm --step all`

---

## 实验目标

验证 MZM 在 200 kHz 方波切换下交替工作于正、负正交点：

- LOW 态：等效相位 $\phi_{DC}$，导频为 cos(20 kHz)
- HIGH 态：等效相位 $\phi_{DC}+\pi$，导频为 sin(20 kHz)
- 目标点：$\phi_{DC}=\pi/2$，两态分别位于正/负正交点

quad_pm 不使用比值 PI 控制。目标点处
$S_2 \propto |\cos\phi_{DC}| = 0$，因此闭环控制直接最小化 $S_2$（40 kHz）。

---

## 硬件配置

### 信号发生器（RIGOL DG922Pro，IP: 192.168.99.115）

仅使用 **CH1**：

| 实验阶段 | 模式 | 频率 | 幅度 | 偏置（offset） |
|----------|------|------|------|----------------|
| 步骤一（Vπ扫描） | SINusoid | 20 kHz | 800 mVpp | 扫描变量（-6 V → +6 V） |
| 步骤二～四 | ARB（预加载/已选中） | 20 kHz | 6.2 Vpp | 扫描/控制变量 |

ARB 波形为 16,384 点，编码 200 kHz 方波切换 + sin/cos 导频：

- 方波 HIGH（约 5.4 V）：sin(20 kHz) 导频，±0.4 V
- 方波 LOW（0 V）：cos(20 kHz) 导频，±0.4 V
- 归一化范围 -1.0 到 +1.0，对应物理输出约 -0.4 V 到 5.8 V

当前 `configure_source()` 只切换到仪器上已有 ARB 并设置 6.2 Vpp 幅度，
不会在实验流程中重新上传波形。若仪器 ARB 波形被清空，需要先用
`mzm/arb_waveforms.py:quad_pm_waveform()` 生成并通过 DG922Pro 工具上传。

### 频谱仪（R&S FSV30，IP: 192.168.99.209）

| 参数 | 值 | 原因 |
|------|-----|------|
| 输入耦合 | **DC**（必须） | 信号 < 1 MHz，AC耦合引入高通截止 |
| 中心频率 | 30 kHz | 覆盖 10-50 kHz |
| 跨度 | 40 kHz | 同时测量 20 kHz 与 40 kHz |
| 扫描 RBW / VBW | 100 Hz / 100 Hz | 与 `config.SCAN_RBW_HZ` / `SCAN_VBW_HZ` 一致 |
| 控制 RBW / VBW | 100 Hz / 100 Hz | 与 `config.SA_RBW_HZ` / `SA_VBW_HZ` 一致 |
| Marker 1 | 20 kHz | 读取 $S_1$ |
| Marker 2 | 40 kHz | 读取 $S_2$ |
| 功率校正 | -6 dB | 仪器已知读数偏高约 6 dB |

---

## 步骤一：正弦波模式 — 大范围偏压扫描，测量 $V_\pi$

**目的**：确定 $V_\pi$，为 ARB 扫描中心和控制限幅提供参考。

**操作**：

1. CH1 设为正弦波，20 kHz，800 mVpp
2. FSV30 设为 DC 耦合，Marker1@20kHz，Marker2@40kHz
3. CH1 offset 从 -6 V 扫至 +6 V，步进 100 mV（`SCAN_STEP = 0.100 V`）
4. 每步记录 $S_1$ 和 $S_2$
5. 从 $S_1$ 曲线寻找两个相邻谷底，间距即 $V_\pi$

**输出文件**：`results/{run}/vpi_scan.csv`，`results/{run}/vpi.json`

---

## 步骤二：ARB 模式 — 偏压扫描，寻找 $S_2$ 谷底

**目的**：验证 sin/cos 导频切换使 $S_2$ 在正交点形成可控制谷底。

**ARB 参数设置**：

```
幅度 = 6.2       Vpp
偏置 = Vpi / 2   V
频率 = 20 kHz
```

**操作**：

1. 切换 CH1 到 ARB 模式，设置频率、幅度和初始 offset
2. CH1 offset 扫描范围：`base_offsets + Vpi/2`
3. 每步记录 $S_1$（20 kHz）和 $S_2$（40 kHz）
4. 从扫描数据中选择最靠近 `vdc_ref = Vpi/2` 的 $S_2$ 谷底

**预期结果**：

- $S_2$ 在目标附近出现明显谷底
- $S_1$ 在目标附近通常较高，不作为控制目标
- 比值 $r=\sqrt{P_1/P_2}$ 在 $S_2$ 谷底附近发散，因此不用于闭环

**输出文件**：`results/{run}/arb_scan.csv`，`results/{run}/scan.png`

---

## 步骤三：快速估计 — 生成控制初值

**目的**：从步骤二扫描数据中直接提取 $S_2$ 谷底，不做曲线拟合。

quad_pm 设置了：

```python
control_strategy = 's2_min'
use_curve_fit = False
```

因此运行 `python main.py --mode quad_pm --step fit --results-dir results/{run}`
时，`cmd_fit()` 会自动跳过 `ratio_fit()`，改用 `cmd_quick_estimate()`。

**估计方法**：

1. 读取 `arb_scan.csv`
2. 在 $S_2$ 曲线中寻找局部极小值
3. 优先选择比中值低 10 dB 以上、且最靠近 `vdc_ref = Vpi/2` 的谷底
4. 将该谷底 offset 作为闭环起点，将谷底功率作为控制 floor

**输出文件**：`results/{run}/fit_result.json`

```json
{
  "strategy": "s2_min",
  "s2_valley_dbm": -48.5,
  "V_valley": 2.70,
  "vpi_scan": 5.412
}
```

---

## 步骤四：闭环偏压控制 — 最小化 $S_2$

**目的**：保持 ARB 输出不变，只调节 CH1 offset，使 $S_2$ 维持在谷底。

控制算法为自适应探针梯度下降：

```
初始值：V_offset = V_valley
循环：
  1. 测当前 s1_dbm, s2_dbm
  2. signal = s2_dbm
  3. excess_dB = max(0, signal - s2_floor)
  4. probe = max(0.02, min(0.10, excess_dB / 50))
  5. 向正方向探测 probe，比较 S2 是否下降
  6. step = 0.001 * excess_dB；若 step < 0.002 V 则不动
  7. 沿下降方向更新 offset，并限制在 mode.offset_limits(vpi)
```

`offset_limits()` 同时考虑 DG922Pro 输出范围和模式工作范围：

$$
\left[
\max(-6.9,\; V_\pi/2 - 2V_\pi),
\min(6.9,\; V_\pi/2 + V_\pi)
\right]
$$

**输出文件**：`results/{run}/control_log.csv`，`results/{run}/control.png`

**通过标准**：

- `control_log.csv` 中 `s2_dbm` 长时间靠近 `s2_valley_dbm`
- `offset_V` 不持续撞到上下限
- `probe_V` 在远离谷底时接近 0.10 V，靠近谷底时逐渐减小
- `step_V` 在谷底附近进入死区

---

## 常见异常

| 现象 | 可能原因 | 处理 |
|------|----------|------|
| $S_2$ 没有清晰谷底 | ARB 波形不是 HIGH=sin、LOW=cos | 重新确认/上传 quad_pm ARB |
| `fit_result.json` 里谷底离 $V_\pi/2$ 很远 | 扫描中心或波形幅度不对 | 重新运行 `--step scan` 并检查 `scan.png` |
| 使用比值拟合发散 | 目标点处 $P_2 \to 0$，$r$ 发散 | 使用默认 `use_curve_fit = False` |
| 控制 offset 撞到 6.9 V | ARB 幅度 6.2 Vpp 下触及 DG922Pro 输出范围 | 检查初始谷底和 `vpi.json` |
| 谷底功率明显偏高 | FSV30 未用 DC 耦合或 RBW/VBW 设置不对 | 检查 `scan.setup_analyzer()` 输出 |

---

## 与代码的对应关系

| 步骤 | 代码位置 |
|------|----------|
| 步骤一 | `mzm/scan.py: vpi_scan()` |
| 步骤二 | `mzm/scan.py: bias_scan()` + `mzm/modes/quad_pm.py: configure_source(), sweep_offsets()` |
| 步骤三 | `main.py: cmd_quick_estimate()`（`strategy == 's2_min'`） |
| 步骤四 | `mzm/control.py: s2_min_control_loop()` → `signal_min_control_loop(signal_index=2)` |
| 波形生成 | `mzm/arb_waveforms.py: quad_pm_waveform()` |
| 全流程 | `python main.py --mode quad_pm --step all` |
