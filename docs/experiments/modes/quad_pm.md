# 实验计划：正/负正交点切换（quad_pm）

**理论背景**：[docs/theory/modes/quad_pm.md](../../theory/modes/quad_pm.md)
**代码入口**：`python main.py --mode quad_pm --step all`

---

## 硬件配置

### 信号发生器（RIGOL DG922Pro，IP: 192.168.99.115）

仅使用 **CH1**，分两种工作模式：

| 实验阶段 | 模式 | 频率 | 幅度 | 偏置（offset） |
|----------|------|------|------|----------------|
| 步骤一（Vπ扫描） | SINusoid | 20 kHz | 800 mVpp | 扫描变量（−6 V → +6 V） |
| 步骤二～四 | **ARB**（上传波形） | 20 kHz | 6.2 Vpp | 扫描/控制变量 |

ARB 波形由代码生成并上传，编码 200 kHz 方波切换 + sin/cos 导频：
- 方波 HIGH（5.4 V）：sin(2π × 20kHz × t) 导频，±0.4 V
- 方波 LOW（0 V）：cos(2π × 20kHz × t) 导频，±0.4 V
- 归一化范围 −1.0 ~ 1.0，对应输出电压 −0.4 V ~ 5.8 V

### 频谱仪（R&S FSV30，IP: 192.168.99.209）

| 参数 | 值 | 原因 |
|------|-----|------|
| 输入耦合 | **DC**（必须） | 信号 < 1 MHz，AC耦合引入高通截止 |
| 中心频率 | 30 kHz | 覆盖 10–50 kHz |
| 跨度 | 40 kHz | |
| RBW / VBW | 300 Hz / 300 Hz | 窄带抑制噪底 |
| Marker 1 | 20 kHz | 读取 $P_1$（一阶功率） |
| Marker 2 | 40 kHz | 读取 $P_2$（二阶功率） |
| 功率校正 | −6 dB | 仪器已知读数偏高约 6 dB |

---

## 步骤一：正弦波模式 — 大范围偏压扫描，测量 $V_\pi$

**目的**：确定 $V_\pi$，为后续 ARB 参数提供参考。

与 max_quad 步骤一完全一致：
1. CH1 设为正弦波，20 kHz，800 mVpp
2. FSV30 DC耦合，Marker1@20kHz，Marker2@40kHz
3. CH1 offset 从 −6 V 扫至 +6 V，步进 100 mV
4. 每步记录 $S_1$（20 kHz dBm）和 $S_2$（40 kHz dBm）

**输出文件**：`results/{run}/vpi_scan.csv`，`results/{run}/vpi.json`

---

## 步骤二：ARB模式 — 偏压扫描，验证切换效果

**目的**：验证 sin/cos 导频切换效果；获取比值曲线拟合数据。

**ARB参数设置**（固定值，不依赖 $V_\pi$）：

```
幅度 = 6.2   Vpp（波形范围 −0.4V ~ 5.8V）
偏置 = 2.7   V（波形 DC 中心，扫描时会被覆盖）
频率 = 20 kHz
```

**操作**：
1. 代码调用 `quad_pm_waveform()` 生成 16,384 点波形 → `gen.load_arb_waveform()` 上传并激活
2. CH1 offset 扫描范围：`base_offsets + Vpi/4`（同 max_quad）
3. 记录 $S_1$，$S_2$

**预期结果**：
- 曲线形状与 max_quad 类似（$r \propto |\tan|$），但整体幅度低约 3 dB
- 二阶分量 $S_2$ 不为零（f₂ 两态同号叠加保持），可正常计算比值

**输出文件**：`results/{run}/arb_scan.csv`

---

## 步骤三：曲线拟合 — 获取经验 $R_{target}$

**目的**：从步骤二数据拟合，获取系统频响差异修正的 $R_{target}$。

**拟合模型**（与 max_quad 相同形式）：

$$r(V_{DC,eff}) = A\cdot\left|\tan\!\left(\frac{\pi}{4} - \frac{\pi(V_{DC,eff}-V_0)}{V_\pi^{fit}}\right)\right|$$

- $V_{DC,eff} = \text{actual\_offset} - V_\pi/4$
- $A = R_{target}$（拟合所得）
- 理论预期 $A \approx 12$（~21.6 dB），比 max_quad 的 ~17 低约 3 dB

**验证**：$V_\pi^{fit}$ 与步骤一差异 < 10%；$|V_0| < 0.5$ V。

**输出文件**：`results/{run}/fit_result.json`

```json
{
  "r_target": 12.0,
  "A":        12.0,
  "V0":       0.012,
  "vpi_fit":  5.398,
  "vpi_scan": 5.412
}
```

---

## 步骤四：闭环偏压控制 — 锁定正交点

**目的**：保持 ARB 输出不变，持续调节 CH1 offset，维持 $r = R_{target}$。

控制算法与 max_quad 完全相同：

```
初始值：V_offset = Vpi/4 + V0_fit
循环：
  1. FSV30 单次扫频，读取 s1_dbm, s2_dbm
  2. r = sqrt(P1_linear / P2_linear)
  3. e = r - R_target
  4. V_offset -= K_I * e
  5. 限幅：V_offset ∈ [OFFSET_MIN, OFFSET_MAX]
  6. gen.set_offset(1, V_offset)
```

**输出文件**：`results/{run}/control_log.csv`（timestamp, r, e, V_offset）

---

## 与代码的对应关系

| 步骤 | 代码位置 |
|------|----------|
| 步骤一 | `mzm/scan.py: vpi_scan()` |
| 步骤二 | `mzm/scan.py: bias_scan()` + `mzm/modes/quad_pm.py: configure_source(), sweep_offsets()` |
| 步骤三 | `mzm/fit.py: ratio_fit()` + `mzm/modes/quad_pm.py: fit_model()` |
| 步骤四 | `mzm/control.py: pi_control_loop()` + `mzm/modes/quad_pm.py: initial_offset()` |
| 波形生成 | `mzm/arb_waveforms.py: quad_pm_waveform()` |
| 全流程 | `python main.py --mode quad_pm --step all` |
