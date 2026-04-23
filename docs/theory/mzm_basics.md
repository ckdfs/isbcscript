# MZM基础模型与导频信号展开

本文档为所有控制模式的公共基础，与具体切换方式无关。

---

## 1. MZM光强传输函数

马赫-曾德调制器（MZM）的输出光强（经过光电探测器后的电流）为：

$$I_{out} = \frac{\eta P_{in} L}{2}\left[1 + \cos\!\left(\phi_{total}\right)\right]$$

| 符号 | 含义 |
|------|------|
| $\eta$ | 探测器响应度（A/W） |
| $P_{in}$ | 输入光功率（W） |
| $L$ | MZM插入损耗（线性） |
| $\phi_{total}$ | 两臂间总相位差（rad） |

总相位由各路电信号叠加决定：

$$\phi_{total} = \sum_k \frac{\pi V_k(t)}{V_\pi}$$

其中 $V_\pi$ 为MZM半波电压（使相位改变 $\pi$ 所需的电压），$V_k(t)$ 为各路输入电压。

本实验总相位为：

$$\phi_{total} = \underbrace{m_{pilot}\sin(\omega_{pilot}t)}_{\text{导频}} + \underbrace{\phi_{switching}(t)}_{\text{PWM切换}} + \underbrace{\phi_{DC}}_{\text{直流偏置}}$$

调制指数与直流相位定义：

$$m_{pilot} = \frac{\pi V_{pilot,peak}}{V_\pi}, \qquad \phi_{DC} = \frac{\pi V_{DC}}{V_\pi}$$

> 本实验无射频信号（$m_{RF}=0$，$J_0(0)=1$），所有含 $J_0(m_{RF})$ 的项均简化为 1。

---

## 2. 导频信号的 Bessel 展开

对余弦项利用 Jacobi-Anger 展开：

$$e^{jm\sin\theta} = \sum_{n=-\infty}^{\infty} J_n(m)\, e^{jn\theta}$$

展开后，输出电流中各次谐波的幅度（仅含导频正弦，忽略 $\phi_{switching}$ 后）：

$$\cos\!\bigl(m_{pilot}\sin(\omega_{pilot}t) + \phi_{DC}\bigr)
= J_0(m_{pilot})\cos\phi_{DC}
- 2J_1(m_{pilot})\sin\phi_{DC}\cdot\sin(\omega_{pilot}t)
- 2J_2(m_{pilot})\cos\phi_{DC}\cdot\cos(2\omega_{pilot}t)
+ \cdots$$

各次分量汇总：

| 频率 | 幅度（正比于） | 相位依赖 | 零点位置 |
|------|--------------|---------|---------|
| DC | $J_0(m_{pilot})\cos\phi_{DC}$ | $\cos$ | $\phi_{DC}=\pi/2+n\pi$ |
| $f_{pilot}$（一阶） | $J_1(m_{pilot})\sin\phi_{DC}$ | $\sin$ | $\phi_{DC}=n\pi$（最大/最小点） |
| $2f_{pilot}$（二阶） | $J_2(m_{pilot})\cos\phi_{DC}$ | $\cos$ | $\phi_{DC}=\pi/2+n\pi$（正交点） |

**物理含义**：
- 一阶分量在最大/最小点（$\phi_{DC}=n\pi$）处为零
- 二阶分量在正交点（$\phi_{DC}=\pi/2+n\pi$）处为零
- 两者正交关系是比值法锁定工作点的物理基础

---

## 3. 小信号近似

当 $m_{pilot} \ll 1$ 时，Bessel函数近似为：

$$J_1(m_{pilot}) \approx \frac{m_{pilot}}{2}, \qquad J_2(m_{pilot}) \approx \frac{m_{pilot}^2}{8}$$

比值 $J_1/J_2 \approx 4/m_{pilot}$，随导频幅度增大而减小。

本实验 $V_{pilot,peak}=0.4\ \text{V}$，$m_{pilot}=\pi\times0.4/V_\pi$，需步骤一测得 $V_\pi$ 后代入。

---

## 参考

- [switching_framework.md](switching_framework.md) — 切换控制通用框架
- [modes/max_quad.md](modes/max_quad.md) — 最大/最小点↔正交点切换的具体推导
