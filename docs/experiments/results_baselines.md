# 实验结果判读与参考 run

本页用于快速判断一次实验是否“看起来正常”。原始数据仍以
`results/YYYYMMDD_HHMMSS_{mode}/` 中的 CSV、JSON 和 PNG 为准。

---

## 推荐先看的文件

| 文件 | 用途 |
|------|------|
| `vpi.json` | 确认本次测得的 $V_\pi$ 和最大点零点 |
| `scan.png` | 检查 Vπ 扫描和 ARB 扫描曲线形状 |
| `fit_result.json` | 确认控制目标或谷底 floor |
| `control_log.csv` | 检查控制过程是否撞限、振荡或进入死区 |
| `control.png` | 快速查看闭环稳定性 |

---

## 当前参考 run

| 模式 | 参考目录 | 关键结果 | 控制判读 |
|------|----------|----------|----------|
| `max_quad` | `results/20260510_154519_max_quad/` | `vpi=5.4 V`，`r_target=17.23`，`V0=-0.45 V` | 比值在目标附近波动，需关注是否长期撞限或振荡 |
| `quad_pm` | `results/20260510_162644_quad_pm/` | `vpi=5.4 V`，`s2_valley=-91.77 dBm`，`V_valley=2.10 V` | `S2` 能回到谷底附近，谷底处 `step_V` 多次进入 0 |
| `max_min` | `results/20260510_144113_max_min/` | `vpi=5.4 V`，`s1_valley=-58.94 dBm`，`V_valley=4.70 V` | `S1` 靠近谷底，控制约 2 分钟内稳定到死区附近 |

这些目录是“参考样例”，不是永久标定值。MZM 的 $V_\pi$ 和零点会随温度、光路、
器件状态漂移，每次正式实验仍应重新运行 `--step scan`。

---

## 按模式判读

### max_quad

正常现象：

- `vpi_scan.csv` 中 $S_1$ 有两个清晰谷底，间距约为 $V_\pi$
- `arb_scan.csv` 中比值曲线在目标附近单调递减
- `fit_result.json` 中 `vpi_fit` 与 `vpi_scan` 差异小于约 10%
- `control_log.csv` 中 `r` 围绕 `r_target` 波动，`offset_V` 不长期停在限幅边界

异常信号：

- `r_target` 远离理论量级（默认 50% 占空比时约 17）
- `V0` 过大，说明扫描参考点或 ARB 波形可能不对
- `offset_V` 一直贴上下限，说明初值、极性或 ARB 幅度需要检查

### quad_pm

正常现象：

- `fit_result.json` 的 `strategy` 为 `s2_min`
- `arb_scan.csv` 中 $S_2$ 在目标附近出现明显谷底
- `control_log.csv` 中 `probe_V` 远离谷底时较大，靠近谷底时接近 0.02 V
- `step_V` 在谷底附近多次为 0，表示进入死区

异常信号：

- $S_2$ 没有谷底：优先检查 ARB 是否为 HIGH=sin、LOW=cos
- 谷底离 $V_\pi/2$ 太远：检查 `vpi.json` 和 ARB 幅度
- 比值拟合发散：这是预期风险，quad_pm 应使用 quick estimate 而不是 curve_fit

### max_min

正常现象：

- `fit_result.json` 的 `strategy` 为 `s1_min`
- `arb_scan.csv` 中 $S_1$ 在目标附近形成 V 形谷底
- $S_2$ 在目标附近为峰值或较高值，不作为控制目标
- `control_log.csv` 中 `s1_dbm` 靠近 `s1_valley_dbm`，且 `step_V` 进入死区

异常信号：

- $S_1$ 和 $S_2$ 同时很弱：常见原因是两态使用了相同导频，50% 占空比抵消
- $S_1$ 没有清晰谷底：检查 ARB 是否为 LOW=cos、HIGH=sin
- 控制振荡：先看 `scan.png` 的谷底是否可信，再考虑调小 `step_scale`

---

## 快速命令

```bash
# 生成完整结果目录
python main.py --mode max_quad --step all
python main.py --mode quad_pm  --step all
python main.py --mode max_min  --step all

# 复用已有扫描结果重新估计/控制
python main.py --mode quad_pm --step fit --results-dir results/YYYYMMDD_HHMMSS_quad_pm
python main.py --mode quad_pm --step control --results-dir results/YYYYMMDD_HHMMSS_quad_pm
```
