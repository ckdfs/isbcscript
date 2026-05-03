# 模式推导：最大点 ↔ 最小点切换（max_min）

## 1. 切换配置

| 参数 | 值 |
|------|----|
| 状态A | 最大点，$\phi_A = 0$ |
| 状态B | 最小点，$\phi_B = \pi$ |
| PWM 幅度 | $V_\pi$（全幅 π 相位跳变） |
| PWM 占空比 $A$ | 0.5 |
| 导频配置 | LOW（状态A）= cos 导频，HIGH（状态B）= sin 导频 |

## 2. 信号推导

### 2.1 MZM 输出模型

$$
P(t) \propto 1 + \cos\!\big(\phi_{DC} + \phi_{sq}(t) + m \cdot p(t)\big)
$$

其中 $\phi_{sq}(t)$ 在 0（LOW）和 $\pi$（HIGH）之间切换，$p(t)$ 为导频信号。

### 2.2 各态 Bessel 展开

**状态A**（LOW，cos 导频，$\phi = \phi_{DC}$）：

$$
\begin{aligned}
\cos(\phi_{DC} + m\cos\omega t) &= \cos\phi_{DC}\cos(m\cos\omega t) - \sin\phi_{DC}\sin(m\cos\omega t) \\
\cos(m\cos\omega t) &= J_0(m) - 2J_2(m)\cos 2\omega t + \cdots \\
\sin(m\cos\omega t) &= 2J_1(m)\cos\omega t - 2J_3(m)\cos 3\omega t + \cdots \\
\Rightarrow S_1^A &\propto -2J_1\sin\phi_{DC} \cdot \cos\omega t \\
S_2^A &\propto -2J_2\cos\phi_{DC} \cdot \cos 2\omega t
\end{aligned}
$$

**状态B**（HIGH，sin 导频，$\phi = \phi_{DC} + \pi$）：

$$
\begin{aligned}
\cos(\phi_{DC} + \pi + m\sin\omega t) &= -\cos(\phi_{DC} + m\sin\omega t) \\
&= -\cos\phi_{DC}\cos(m\sin\omega t) + \sin\phi_{DC}\sin(m\sin\omega t) \\
\Rightarrow S_1^B &\propto +2J_1\sin\phi_{DC} \cdot \sin\omega t \\
S_2^B &\propto -2J_2\cos\phi_{DC} \cdot \cos 2\omega t
\end{aligned}
$$

### 2.3 时间平均（方波切换）

以占空比 $A$ 在状态A、$1-A$ 在状态B之间切换：

$$
\begin{aligned}
S_1^{total} &= A \cdot S_1^A + (1-A) \cdot S_1^B \\
&\propto 2J_1\sin\phi_{DC}\big[{-A}\cos\omega t + (1-A)\sin\omega t\big] \\[4pt]
|S_1| &= 2J_1|\sin\phi_{DC}| \cdot \sqrt{A^2 + (1-A)^2}
\end{aligned}
$$

$$
\begin{aligned}
S_2^{total} &= A \cdot S_2^A + (1-A) \cdot S_2^B \\
&\propto -2J_2\cos\phi_{DC}\cos 2\omega t \cdot [A + (1-A)] \\[4pt]
|S_2| &= 2J_2|\cos\phi_{DC}|
\end{aligned}
$$

### 2.4 关键结论

- **$S_2$ 不依赖 $A$**：两态贡献同为 $-\cos 2\omega t$，同号叠加，不对消。这是 cos/sin 导频切换的核心优势。
- **$S_1$ 在目标处为零**：$\phi_{DC}=0 \;\Rightarrow\; |S_1| = 0$，形成 V 形谷底。
- 若两态均用相同导频（如同为 sin），则 $S_1 \propto (2A-1)$、$S_2 \propto (2A-1)$，在 $A=0.5$ 时信号完全消失。

### 2.5 $A=0.5$ 时的数值

$$
|S_1| = \sqrt{2}\,J_1|\sin\phi_{DC}| \approx 1.414\,J_1|\sin\phi_{DC}|
$$
$$
|S_2| = 2J_2|\cos\phi_{DC}|
$$
$$
r = \frac{|S_1|}{|S_2|} = \frac{1}{\sqrt{2}}\frac{J_1}{J_2}|\tan\phi_{DC}|
$$

## 3. 控制策略：$S_1$-min 梯度下降

### 3.1 为什么不用比值 PI 控制

比值 $r$ 在目标处 $r=0$，且 $\frac{dr}{d\phi_{DC}}\big|_{\phi_{DC}=0}$ 存在 cusp（左右导数符号相反但幅度相等），PI 控制器无法从恒正的误差 $e = r - 0 \ge 0$ 中判断方向。此问题与 quad_pm 的 $r$ 在 $v_{dc\_eff}=0$ 处发散同源。

### 3.2 $S_1$ 梯度下降

$|S_1| \propto |\sin\phi_{DC}|$ 在 $\phi_{DC}=0$ 处呈 V 形谷底：

- $\phi_{DC} > 0$：$S_1$ 随 $\phi_{DC}$ 增大 → 应向负方向移动
- $\phi_{DC} < 0$：$S_1$ 随 $|\phi_{DC}|$ 增大 → 应向正方向移动

梯度方向始终指向谷底，适合自适应探针梯度下降法（与 quad_pm 的 $S_2$-min 同构）。

### 3.3 自适应探针参数

| 参数 | 值 | 说明 |
|------|----|------|
| 探针范围 | 0.02–0.10 V | $\propto \max(0.02, \min(0.10, \mathrm{excess\_dB}/50))$ |
| 步长缩放 | 0.001 V/dB | $\mathrm{step} = 0.001 \times \mathrm{excess\_dB}$ |
| 死区 | 0.002 V | step < 0.002 V 时不移动 |

## 4. 信号发生器设置

| 参数 | 值 |
|------|----|
| CH1 模式 | ARB（代码上传，`load_arb_waveform`） |
| 波形 | 16,384 点，200 kHz 方波，50% 占空比 |
| 导频 | LOW = cos(20 kHz)，HIGH = sin(20 kHz)，各 ±0.4 V |
| 物理幅度 | $V_\pi + 0.8$ Vpp |
| DC 偏置 | $V_\pi/2$ V |
| 输出范围 | $[-0.4,\; V_\pi + 0.4]$ V |
| 等效状态A电压 | 0 V（最大点） |
| 等效状态B电压 | $V_\pi$（最小点） |

## 5. 与 quad_pm 的对比

| | quad_pm | max_min |
|---|---|---|
| 状态A | $-\pi/2$（负正交） | $0$（最大点） |
| 状态B | $+\pi/2$（正正交） | $\pi$（最小点） |
| 控制信号 | $S_2$（40 kHz）→ min | $S_1$（20 kHz）→ min |
| 导频配置 | cos/sin（同） | cos/sin（同） |
| 占空比 | 0.5 | 0.5 |
| ARB 振幅 | 6.2 Vpp 固定 | $V_\pi + 0.8$ Vpp |
| `vdc_ref` | $V_\pi/2$ | $V_\pi/2$ |
| `use_curve_fit` | False | False |
| $|S_2|$ 公式 | $2J_2|\cos\phi_{DC}|$ | $2J_2|\cos\phi_{DC}|$ |
| 目标处 $S_2$ | 0（谷底） | $2J_2$（峰值） |

## 参考

- [switching_framework.md](../switching_framework.md) — 通用推导（$\phi_B=\pi/2$ 标准形式，max_min 不适用）
- [quad_pm.md](quad_pm.md) — cos/sin 导频切换的同构推导
