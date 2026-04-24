# 模式推导：最大/最小点 ↔ 正交点（max_quad）

将通用框架（[switching_framework.md](../switching_framework.md)）代入本模式具体参数。

---

## 1. 切换配置

| 参数 | 值 |
|------|----|
| 状态A | 最大/最小点，$\phi_A = 0$ |
| 状态B | 正交点，$\phi_B = \pi/2$ |
| PWM幅度 | $V_\pi/2$（产生 $\pi/2$ 相位跳变） |
| PWM占空比 $A$ | 0.5（50%） |
| PWM频率 | 200 kHz |

---

## 2. 代入通用框架

$$A = 0.5 \implies \phi_0 = \arctan\!\left(\frac{1-0.5}{0.5}\right) = \arctan(1) = \frac{\pi}{4} = 45°$$

$$\kappa = \sqrt{0.5^2 + 0.5^2} = \frac{1}{\sqrt{2}} \implies \text{功率衰减} = -3\ \text{dB}$$

比值函数：

$$r(\phi_{DC}) = \frac{J_1(m_{pilot})}{J_2(m_{pilot})}\,\bigl|\tan\!\left(\phi_{DC} + \frac{\pi}{4}\right)\bigr|$$

---

## 3. 目标工作点

**目标**：第一半周期在最大点（$\phi_{DC}=0$），第二半周期在正交点（$\phi_{DC}+\pi/2$）。

对应目标偏压：$V_{DC,target} = 0$（或 $2nV_\pi$）。

目标比值（代入 $\phi_{DC}=0$）：

$$\boxed{r_{target} = \frac{J_1(m_{pilot})}{J_2(m_{pilot})} \cdot \tan\!\left(\frac{\pi}{4}\right) = \frac{J_1(m_{pilot})}{J_2(m_{pilot})}}$$

> 注：实验中 $r_{target}$ 由步骤三曲线拟合给出，自动包含系统频响差异，
> 无需代入 $J_1/J_2$ 理论值。拟合参数 $A_{fit}$ 即为 $r_{target}$。

---

## 4. $r_{target}$ 的理论数值估算

### 4.1 计算公式

由第 3 节，目标点处 $r_{target} = J_1(m_{pilot})/J_2(m_{pilot})$，调制指数为：

$$m_{pilot} = \frac{\pi V_{pilot,peak}}{V_\pi}$$

**本实验参数**：$V_{pilot,peak} = 800\,\text{mVpp}/2 = 0.400\,\text{V}$，$V_\pi \approx 5.34\,\text{V}$（实测）。

$$m_{pilot} = \frac{\pi \times 0.400}{5.34} \approx 0.235$$

### 4.2 Bessel 函数级数展开

$$J_1(x) = \frac{x}{2} - \frac{(x/2)^3}{1!\cdot 2!} + \frac{(x/2)^5}{2!\cdot 3!} - \cdots$$

$$J_2(x) = \frac{(x/2)^2}{0!\cdot 2!} - \frac{(x/2)^4}{1!\cdot 3!} + \frac{(x/2)^6}{2!\cdot 4!} - \cdots$$

代入 $m/2 = 0.1177$：

| 项 | $J_1$ 贡献 | $J_2$ 贡献 |
|----|-----------|-----------|
| 首项 | $+0.1177$ | $+0.1177^2/2 = +0.006925$ |
| 二阶修正 | $-0.1177^3/2 = -0.000816$ | $-0.1177^4/6 = -0.000032$ |
| 高阶 | $< 10^{-6}$，可忽略 | 可忽略 |
| **合计** | **0.1169** | **0.006893** |

$$r_{theory} = \frac{0.1169}{0.006893} \approx 16.96 \implies \boxed{r_{theory} \approx 17\,(24.6\,\text{dB})}$$

### 4.3 小信号近似（$m \ll 1$）

当 $m \ll 1$ 时 $J_n(m) \approx (m/2)^n / n!$，比值化简为：

$$r \approx \frac{m/2}{m^2/8} = \frac{4}{m} = \frac{4V_\pi}{\pi V_{pilot,peak}}$$

代入数值：$r \approx 4 \times 5.34\,/\,(\pi \times 0.400) \approx 17.0$，与级数结果吻合（$m=0.235$ 时近似误差 $< 0.4\%$）。

### 4.4 理论值与实验拟合值的差距

| | 值 |
|--|--|
| 理论值（纯 MZM）| $\approx 17$（24.6 dB） |
| 实验拟合值 | $\approx 10$（20 dB） |
| 差距 | 约 −4.6 dB |

差距来自**系统在 20 kHz 与 40 kHz 处的频率响应不同**。实测比值等于 MZM 理论值再乘以两频点的系统增益之比：

$$r_{meas} = \underbrace{\frac{J_1}{J_2}}_{\approx 17} \times \underbrace{\frac{H(20\,\text{kHz})}{H(40\,\text{kHz})}}_{\approx 0.59\;(-4.6\,\text{dB})}$$

即探测器 + 放大器链路在 40 kHz 处比 20 kHz 处增益高约 4.6 dB（低频段增益随频率上升而下降，属正常现象）。

> 这正是为什么不能直接使用理论值 $J_1/J_2$ 作为 $R_{target}$，
> 而要通过曲线拟合从实测数据提取经验值——拟合所得 $A_{fit}$ 自动包含了全部系统频响差异。

---

## 5. 预期扫描曲线形状

以 $V_{DC,eff} = \text{CH1 offset} - V_\pi/4$ 为横轴（在此坐标系中 $V_{DC,eff}=0$ 对应最大点）。

> **极性说明**：实验中 CH1 offset 增大会使 MZM 偏置相位 $\phi_{DC}$ **减小**（硬件极性反向），
> 因此比值曲线在 $V_{DC,eff}$ 轴上是单调**递减**的。

| 曲线 | 形状 | 目标点附近关键位置 |
|------|------|-------------------|
| $S_1$（20 kHz） | $\|\sin(\phi_{DC}+\pi/4)\|$ 包络 | 最近零点在 $V_{DC,eff} = +V_\pi/4$（右侧，P1→0） |
| $S_2$（40 kHz） | $\|\cos(\phi_{DC}+\pi/4)\|$ 包络 | 最近零点（奇点）在 $V_{DC,eff} = -V_\pi/4$（左侧，P2→0，r→∞） |
| $r = \sqrt{P_1/P_2}$ | $|\tan|$ 函数，**单调递减** | 目标 $r=A$ 在中心（$V_{DC,eff}=0$）；左侧发散，右侧趋零 |

与步骤一（无PWM，纯正弦）对比：
- 整体幅度降低 $1/\sqrt{2}$（$-3\ \text{dB}$），由占空比 $A=0.5$ 决定
- 坐标已对齐（`bias_scan` 将 offset 右移 $V_\pi/4$），目标工作点重合

拟合使用的模型（与代码一致）：

$$r(V_{DC,eff}) = A\cdot\left|\tan\!\left(\frac{\pi}{4} - \frac{\pi(V_{DC,eff}-V_0)}{V_\pi^{fit}}\right)\right|$$

---

## 6. 信号发生器设置（ARB模式）

ARB波形文件已预加载（编码 200 kHz PWM + 20 kHz导频正弦），
按测得 $V_\pi$ 恢复真实波形参数：

$$\text{幅度} = \frac{V_\pi}{2} + 0.8\ \text{Vpp}, \qquad \text{偏置} = \frac{V_\pi}{4}\ \text{V}, \qquad \text{频率} = 20\ \text{kHz}$$

示例（$V_\pi = 5.4\ \text{V}$）：幅度 = 3.5 Vpp，偏置 = 1.35 V。

闭环控制时：幅度和频率固定，仅调节 CH1 offset（即 $V_{DC}$ 控制量）。

---

## 参考

- [switching_framework.md](../switching_framework.md) — 通用推导
- [docs/experiments/modes/max_quad.md](../../experiments/modes/max_quad.md) — 实验步骤
- [mzm/modes/max_quad.py](../../../mzm/modes/max_quad.py) — 代码实现
