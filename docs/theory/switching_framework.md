# 切换控制通用框架

本文档推导适用于**任意占空比 $A$ 的PWM切换控制**的通用结论，
各具体模式文档（`modes/*.md`）在此基础上代入具体参数。

**前置阅读**：[mzm_basics.md](mzm_basics.md)

---

## 1. 切换信号模型

PWM方波将MZM偏置在两个工作状态之间周期性切换：

$$\phi_{total}(t) = \begin{cases}
\phi_{DC} + \phi_A, & nT < t < nT + AT \quad (\text{状态A}) \\
\phi_{DC} + \phi_B, & nT + AT < t < (n+1)T \quad (\text{状态B})
\end{cases}$$

其中 $T = 1/f_{PWM}$ 为PWM周期，$A \in (0,1)$ 为占空比，
$\phi_A, \phi_B$ 为两状态相对于 $\phi_{DC}$ 的固定相位偏移。

**本框架的标准切换形式**（最大/最小点↔正交点类模式）：

$$\phi_A = 0, \quad \phi_B = \frac{\pi}{2}$$

即一个半周期偏置不变，另一个半周期额外加 $V_\pi/2$，使相位跳变 $\pi/2$。

---

## 2. 时域电流表达式

将Bessel展开（见 `mzm_basics.md`）与切换信号结合，得到各次谐波的时域形式。

**一阶分量（$f_{pilot}$）**，令：

$$B = -\eta P_{in}L\,J_1(m_{pilot})\sin(\phi_{DC}+\phi_A)$$
$$C = -\eta P_{in}L\,J_1(m_{pilot})\sin(\phi_{DC}+\phi_B)$$

则：

$$I_{out}(t)\big|_{f_{pilot}} = \begin{cases}
B\sin(\omega_{pilot}t), & \text{状态A} \\
C\sin(\omega_{pilot}t), & \text{状态B}
\end{cases}$$

---

## 3. 频域分析——Fourier 变换

对双值信号 $\{B\sin(\omega_c t),\,C\sin(\omega_c t)\}$ 作 Fourier 变换：

$$I_{out}(f) = \underbrace{\frac{BA + C(1-A)}{2j}\bigl[\delta(f-f_c)-\delta(f+f_c)\bigr]}_{\text{基频分量（FSV30直接测量）}}
+ \frac{B-C}{2j}\sum_{k\neq 0}\frac{\sin(\pi kA)}{\pi k}e^{-j\pi kA}
\bigl[\delta(f-kf_{PWM}-f_c)-\delta(f-kf_{PWM}+f_c)\bigr]$$

**边带位置**：$kf_{PWM} \pm f_{pilot}$，最低边带在 $f_{PWM} - f_{pilot}$。
只要 $f_{PWM} \gg f_{pilot}$（本实验：$200\ \text{kHz} \gg 20\ \text{kHz}$），
边带远离测量窗口，FSV30 Marker可直接测得基频分量。

---

## 4. 基频幅度谱

代入 $\phi_A=0$，$\phi_B=\pi/2$ 的标准形式，基频分量化简为：

$$\boxed{S_1 \propto J_1(m_{pilot})\,\bigl[A\sin(\phi_{DC})+(1-A)\cos(\phi_{DC})\bigr]}$$

$$\boxed{S_2 \propto J_2(m_{pilot})\,\bigl[A\cos(\phi_{DC})-(1-A)\sin(\phi_{DC})\bigr]}$$

其中 $S_1$ 为一阶幅度（$f_{pilot}$），$S_2$ 为二阶幅度（$2f_{pilot}$）。

---

## 5. 辅助角公式化简

利用辅助角公式（万能公式）：

$$A\sin\phi + (1-A)\cos\phi = \kappa\,\sin(\phi + \phi_0)$$
$$A\cos\phi - (1-A)\sin\phi = \kappa\,\cos(\phi + \phi_0)$$

其中：

$$\boxed{\phi_0 = \arctan\!\left(\frac{1-A}{A}\right), \quad 0 < A < 1}$$

$$\boxed{\kappa = \sqrt{A^2 + (1-A)^2}}$$

化简后：

$$S_1 \propto \kappa\,J_1(m_{pilot})\,\sin(\phi_{DC}+\phi_0)$$
$$S_2 \propto \kappa\,J_2(m_{pilot})\,\cos(\phi_{DC}+\phi_0)$$

**物理解释**：引入PWM切换后，一阶/二阶分量的相位依赖结构不变（仍为 $\sin/\cos$ 对），
等效偏置相位从 $\phi_{DC}$ 整体偏移 $\phi_0$，偏移量完全由占空比 $A$ 决定。

---

## 6. 比值函数

定义幅度比（FSV30功率转线性后取平方根）：

$$\boxed{r \equiv \sqrt{\frac{P_1}{P_2}} = \frac{J_1(m_{pilot})}{J_2(m_{pilot})}\,\bigl|\tan(\phi_{DC}+\phi_0)\bigr|}$$

关键性质：
- **周期**：$\pi$（在每个周期内严格单调）
- **控制可行性**：$r$ 与 $\phi_{DC}$ 的关系为 $|\tan|$ 函数，单调区间内可唯一确定工作点
- **与常规比值法的差异**：引入固定相移 $\phi_0$，由占空比 $A$ 唯一确定，可预先计算

---

## 7. 功率分析

切换引入的功率衰减因子为 $\kappa^2 = A^2 + (1-A)^2$。

由均值不等式：$A^2 + (1-A)^2 \geq 2A(1-A)$，等号在 $A=0.5$ 时成立，此时：

$$\kappa_{min} = \frac{1}{\sqrt{2}} \implies \text{功率衰减} = -3\ \text{dB（相对常规导频法）}$$

| $A$ | $\phi_0$ | $\kappa$ | 功率损失 |
|-----|---------|---------|---------|
| 0.5 | $45°$ | $1/\sqrt{2}$ | $-3\ \text{dB}$ |
| 0.6 | $33.7°$ | $0.721$ | $-2.8\ \text{dB}$ |
| 0.9 | $6.3°$ | $0.906$ | $-0.9\ \text{dB}$ |

> **结论**：$A=0.5$ 时功率损失最大但仍为 $-3\ \text{dB}$，工程上可接受；
> $A$ 越接近 0 或 1，功率损失越小，但 $\phi_0$ 越接近 $\pi/2$ 或 $0$。

---

## 参考

- [mzm_basics.md](mzm_basics.md) — MZM基础模型
- [modes/max_quad.md](modes/max_quad.md) — 代入 $A=0.5$ 的具体推导
- [modes/quad_pm.md](modes/quad_pm.md) — 正/负正交点切换推导（待填充）
