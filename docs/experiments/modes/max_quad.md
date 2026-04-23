# 实验计划：最大/最小点 ↔ 正交点（max_quad）

**理论背景**：[docs/theory/modes/max_quad.md](../../theory/modes/max_quad.md)
**代码入口**：`python main.py --mode max_quad --step all`

---

## 硬件配置

### 信号发生器（RIGOL DG922Pro，IP: 192.168.99.115）

仅使用 **CH1**，分两种工作模式：

| 实验阶段 | 模式 | 频率 | 幅度 | 偏置（offset） |
|----------|------|------|------|----------------|
| 步骤一（Vπ扫描） | SINusoid | 20 kHz | 800 mVpp | 扫描变量（−6 V → +6 V） |
| 步骤二～四 | **ARB**（预加载） | 20 kHz | $V_\pi/2 + 0.8$ Vpp | 扫描/控制变量 |

ARB波形文件已预加载于仪器，编码 200 kHz PWM切换 + 20 kHz导频正弦。

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

**目的**：确定 $V_\pi$ 和最大点偏压，为后续ARB参数提供依据。

**操作**：
1. CH1 设为正弦波，20 kHz，800 mVpp
2. FSV30 DC耦合，Marker1@20kHz，Marker2@40kHz
3. CH1 offset 从 −6 V 扫至 +6 V，步进 50 mV
4. 每步记录 $S_1$（20 kHz dBm）和 $S_2$（40 kHz dBm）

**Vπ 提取**（代码：`scan.find_two_valleys`）：
- $S_1(V_{offset}) \propto |\sin\phi_{DC}|$，相邻零点间距 = $V_\pi$
- 同时记录零点 $V_{null}$（最大点对应的 CH1 offset）

**输出文件**：`results/{run}/vpi_scan.csv`，`results/{run}/vpi.json`

---

## 步骤二：ARB模式 — 偏压扫描，验证切换效果

**目的**：验证 $\phi_0=45°$ 偏移和 −3 dB功率损失；获取拟合数据。

**ARB参数设置**（由测得 $V_\pi$ 计算）：

```
幅度 = Vpi / 2 + 0.8   (Vpp)
偏置 = Vpi / 4          (V)    ← 扫描起点，之后在此基础上扫描
频率 = 20 kHz
```

**操作**：
1. 切换 CH1 到 ARB 模式，按上述公式设置幅度和频率
2. CH1 offset 扫描范围：`base_offsets + Vpi/4`（实际范围 $[-6+V_\pi/4,\, +6+V_\pi/4]$ V）
3. 记录 $S_1$，$S_2$

**预期结果**（与步骤一叠图，以 $V_{DC,eff}=\text{offset}-V_\pi/4$ 为横轴）：
- 曲线形状不变，幅度整体低 3 dB
- 零点位置相同（坐标已对齐）

**输出文件**：`results/{run}/arb_scan.csv`

---

## 步骤三：曲线拟合 — 获取经验 $R_{target}$

**目的**：从步骤二数据拟合，获取包含系统频响差异的精确 $R_{target}$。

> 为什么不用理论值？理论 $J_1/J_2$ 假设两频点系统增益完全对称，
> 实际探测器和电缆在 20 kHz 与 40 kHz 处响应不同。
> 拟合法直接从实测数据提取，自动吸收所有系统效应。

**拟合模型**（以 $V_{DC,eff} = \text{offset} - V_\pi/4$ 为自变量）：

$$r(V_{DC,eff}) = A\cdot\left|\tan\!\left(\frac{\pi(V_{DC,eff}-V_0)}{V_\pi^{fit}} + \frac{\pi}{4}\right)\right|$$

拟合参数：$A$（= $R_{target}$）、$V_0$（零点修正）、$V_\pi^{fit}$（交叉验证）

**验证**：$V_\pi^{fit}$ 与步骤一谷值法差异应 < 2%；$V_0$ 应 < 0.1 V。

**输出文件**：`results/{run}/fit_result.json`

```json
{
  "r_target": 1.234,
  "A":        1.234,
  "V0":       0.012,
  "vpi_fit":  5.398,
  "vpi_scan": 5.412
}
```

---

## 步骤四：闭环偏压控制 — 锁定最大点

**目的**：保持 ARB 输出不变，持续调节 CH1 offset，维持 $r = R_{target}$。

**控制目标**：

$$e = r - R_{target} = \sqrt{P_1/P_2} - R_{target} = 0$$

**积分控制算法**：

```
初始值：V_offset = Vpi/4 + V0_fit
循环：
  1. FSV30 单次扫频，读取 s1_dbm, s2_dbm
  2. r = sqrt(P1_linear / P2_linear)
  3. e = r - R_target
  4. V_offset -= K_I * e   (K_I 从 0.005 开始调)
  5. 限幅：V_offset ∈ [OFFSET_MIN, OFFSET_MAX]
  6. gen.set_offset(1, V_offset)
```

**K_I 调参**：从 0.005 开始；稳定后逐步增大；振荡则减半。
控制周期由 FSV30 扫频时间决定（约 0.2–1 s）。

**输出文件**：`results/{run}/control_log.csv`（timestamp, r, e, V_offset）

---

## 与代码的对应关系

| 步骤 | 代码位置 |
|------|----------|
| 步骤一 | `mzm/scan.py: vpi_scan()` |
| 步骤二 | `mzm/scan.py: bias_scan()` + `mzm/modes/max_quad.py: configure_source(), sweep_offsets()` |
| 步骤三 | `mzm/fit.py: ratio_fit()` + `mzm/modes/max_quad.py: fit_model()` |
| 步骤四 | `mzm/control.py: pi_control_loop()` + `mzm/modes/max_quad.py: initial_offset()` |
| 全流程 | `python main.py --mode max_quad --step all` |
