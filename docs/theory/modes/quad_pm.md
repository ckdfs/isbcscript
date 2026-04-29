# 模式推导：正/负正交点切换（quad_pm）

## 1. 切换配置

ARB 信号由 200 kHz 方波在 0 V 和 5.4 V 之间切换（50% 占空比），
高电平时叠加 20 kHz 正弦导频，低电平时叠加 20 kHz 余弦导频。
$V_\pi \approx 5.34$ V，5.4 V 近似产生 $\pi$ 相位差。

| 参数 | 值 |
|------|----|
| 状态A（HIGH, 5.4 V） | $\phi_A = \pi$（$V_{DC}=V_\pi$），导频 = $\sin(\omega t)$ |
| 状态B（LOW, 0 V） | $\phi_B = 0$，导频 = $\cos(\omega t)$ |
| PWM 频率 | 200 kHz |
| PWM 占空比 $A$ | 0.5 |
| 导频频率 | 20 kHz |
| 导频幅度 | ±0.4 V（800 mVpp） |

## 2. 代入通用框架

### 2.1 Bessel 展开

**状态A（HIGH, $\phi_A=\pi$, sin 导频）**：

$$
\begin{aligned}
P_A &\propto 1 + \cos(\phi_{DC} + \pi + m\sin\omega t) \\
    &= 1 + \cos(\phi_{DC}+\pi)\cos(m\sin\omega t) - \sin(\phi_{DC}+\pi)\sin(m\sin\omega t) \\
    &= 1 + (-\cos\phi_{DC})\cos(m\sin\omega t) - (-\sin\phi_{DC})\sin(m\sin\omega t)
\end{aligned}
$$

代入 Jacobi-Anger：

$$
\begin{aligned}
\cos(m\sin\omega t) &= J_0(m) + 2J_2(m)\cos 2\omega t + \cdots \\
\sin(m\sin\omega t) &= 2J_1(m)\sin\omega t + \cdots
\end{aligned}
$$

$$
\boxed{P_A \propto 1 - J_0\cos\phi_{DC} \;\underline{-\;2J_2\cos\phi_{DC}\cos 2\omega t} \;+\; 2J_1\sin\phi_{DC}\sin\omega t + \cdots}
$$

**状态B（LOW, $\phi_B=0$, cos 导频）**：

$$
\begin{aligned}
P_B &\propto 1 + \cos(\phi_{DC} + m\cos\omega t) \\
    &= 1 + \cos\phi_{DC}\cos(m\cos\omega t) - \sin\phi_{DC}\sin(m\cos\omega t)
\end{aligned}
$$

代入 Jacobi-Anger（注意 cos 导频的展开符号）：

$$
\begin{aligned}
\cos(m\cos\omega t) &= J_0(m) - 2J_2(m)\cos 2\omega t + 2J_4(m)\cos 4\omega t - \cdots \\
\sin(m\cos\omega t) &= 2J_1(m)\cos\omega t - 2J_3(m)\cos 3\omega t + \cdots
\end{aligned}
$$

$$
\boxed{P_B \propto 1 + J_0\cos\phi_{DC} \;\underline{-\;2J_2\cos\phi_{DC}\cos 2\omega t} \;-\; 2J_1\sin\phi_{DC}\cos\omega t + \cdots}
$$

### 2.2 关键观察

两态的 **f₂ 项符号相同**（均为 $-2J_2\cos\phi_{DC}\cos 2\omega t$），
f₁ 项符号相反（$+2J_1\sin\phi_{DC}\sin\omega t$ vs $-2J_1\sin\phi_{DC}\cos\omega t$）。

### 2.3 切换合成

50% 占空比方波（$A=0.5$），总信号为两态加权叠加：

**一阶分量（$f_1 = 20$ kHz）**：

$$
\begin{aligned}
I_1(t) &= A \cdot \big[+2J_1\sin\phi_{DC}\sin\omega t\big]
       + (1-A) \cdot \big[-2J_1\sin\phi_{DC}\cos\omega t\big] \\[4pt]
       &= J_1\sin\phi_{DC}\big[\sin\omega t - \cos\omega t\big] \\[4pt]
       &= \sqrt{2}\,J_1(m)\sin\phi_{DC} \cdot \sin(\omega t - \pi/4)
\end{aligned}
$$

$$
\boxed{S_1 \propto \sqrt{2}\,J_1(m)\,|\sin\phi_{DC}|}
$$

**二阶分量（$f_2 = 40$ kHz）**：

两态 f₂ 项**同号相加**，不受占空比影响：

$$
\begin{aligned}
I_2(t) &= A \cdot \big[-2J_2\cos\phi_{DC}\cos 2\omega t\big]
       + (1-A) \cdot \big[-2J_2\cos\phi_{DC}\cos 2\omega t\big] \\[4pt]
       &= -2J_2(m)\cos\phi_{DC}\cos 2\omega t
\end{aligned}
$$

$$
\boxed{S_2 \propto 2J_2(m)\,|\cos\phi_{DC}|}
$$

### 2.4 比值函数

$$
r = \frac{S_1}{S_2}
   = \frac{\sqrt{2}\,J_1(m)\,|\sin\phi_{DC}|}{2J_2(m)\,|\cos\phi_{DC}|}
   = \frac{1}{\sqrt{2}} \cdot \frac{J_1(m)}{J_2(m)} \cdot |\tan\phi_{DC}|
$$

定义 $\kappa = 1/\sqrt{2}$（−3 dB 导频衰减因子）：

$$
\boxed{r = \kappa \cdot \frac{J_1}{J_2} \cdot |\tan\phi_{DC}|}
$$

### 2.5 与 max_quad 对比

| 项目 | max_quad | quad_pm |
|------|----------|---------|
| $\phi_A$ | $0$ | $\pi$ |
| $\phi_B$ | $\pi/2$ | $0$ |
| 导频 A / B | sin / sin | sin / cos |
| f₂ 两态符号 | 相反（部分抵消） | **相同（叠加保持）** |
| $S_1$ | $\sqrt{2}J_1\vert\sin(\phi_{DC}+\pi/4)\vert$ | $\sqrt{2}J_1\vert\sin\phi_{DC}\vert$ |
| $S_2$ | $\sqrt{2}J_2\vert\cos(\phi_{DC}+\pi/4)\vert$ | $2J_2\vert\cos\phi_{DC}\vert$ |
| 比值 $r$ | $\frac{J_1}{J_2}\vert\tan(\phi_{DC}+\pi/4)\vert$ | $\frac{1}{\sqrt{2}}\frac{J_1}{J_2}\vert\tan\phi_{DC}\vert$ |

## 3. 拟合模型

映射到硬件坐标 $\phi_{DC} = \pi/4 - \pi v / V_\pi$（$v = V_{DC,eff}$）：

$$
r = \kappa\frac{J_1}{J_2} \cdot \left|\tan\!\left(\frac{\pi}{4} - \frac{\pi v}{V_\pi}\right)\right|
$$

记 $A = \kappa\frac{J_1}{J_2}$，加入零点修正 $V_0$：

$$
\boxed{r = A \cdot \left|\tan\!\left(\frac{\pi}{4} - \frac{\pi(v-V_0)}{V_\pi^{fit}}\right)\right|}
$$

**与 max_quad 拟合形式完全相同**，仅 $A$ 物理值不同：
- max_quad：$A \approx J_1/J_2 \approx 17$（~24.6 dB）
- quad_pm：$A \approx \kappa J_1/J_2 \approx 12$（~21.6 dB，低约 3 dB）

## 4. 目标工作点

$\phi_{DC} = \pi/4$（$v=0$），$r = A = R_{target}$。

- 左侧奇点（$P_2 \to 0$）：$v = V_0 - V_\pi/4$
- 目标点（$r = A$）：$v = V_0$
- 右侧零点（$P_1 \to 0$）：$v = V_0 + V_\pi/4$
- 拟合窗口 $|v| < 0.20V_\pi$，需 $< 0.25V_\pi$ 以避开奇点

## 参考

- [switching_framework.md](../switching_framework.md) — 通用推导
- [max_quad.md](max_quad.md) — 已实现模式（对比参考）
