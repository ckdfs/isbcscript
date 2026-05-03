# 输出数据格式定义

所有结果保存在 `results/YYYYMMDD_HHMMSS_{mode}/` 子目录下。

---

## vpi_scan.csv

步骤一扫描数据。

| 列名 | 单位 | 说明 |
|------|------|------|
| `offset_V` | V | CH1 DC offset（实际施加电压） |
| `s1_dbm` | dBm | 20 kHz 功率（已校正 −6 dB） |
| `s2_dbm` | dBm | 40 kHz 功率（已校正 −6 dB） |

---

## arb_scan.csv

步骤二扫描数据。

| 列名 | 单位 | 说明 |
|------|------|------|
| `actual_offset_V` | V | CH1 实际 offset（= base + 模式偏移） |
| `s1_dbm` | dBm | 20 kHz 功率（已校正） |
| `s2_dbm` | dBm | 40 kHz 功率（已校正） |

---

## vpi.json

```json
{
  "vpi":    5.412,    // Vpi（V），由谷值法从 vpi_scan.csv 提取
  "v_null": -0.050    // S1 零点 offset（V），对应最大点
}
```

---

## fit_result.json

### ratio 策略（max_quad）

```json
{
  "strategy":  "ratio",
  "r_target": 1.234,   // 控制目标比值（= A_fit）
  "A":        1.234,   // 拟合幅度参数
  "V0":       0.012,   // 零点修正（V）
  "vpi_fit":  5.398,   // 拟合 Vpi（V），用于交叉验证
  "vpi_scan": 5.412    // 谷值法 Vpi（V），参考
}
```

### s1_min / s2_min 策略（quad_pm / max_min）

```json
{
  "strategy":       "s1_min",
  "s1_valley_dbm":  -45.2,   // S₁ 谷底功率（dBm）
  "V_valley":        1.98,   // 谷底 CH1 offset（V）
  "vpi_scan":        5.412
}
```

`s2_min` 同理，键名为 `s2_valley_dbm`。

---

## control_log.csv

步骤四控制循环实时记录。根据控制策略不同，CSV 格式分为两种：

### ratio 策略（`'r'` 列存在）

| 列名 | 单位 | 说明 |
|------|------|------|
| `timestamp_s` | s | 从控制开始的相对时间 |
| `s1_dbm` | dBm | 当前 20 kHz 功率（已校正） |
| `s2_dbm` | dBm | 当前 40 kHz 功率（已校正） |
| `r` | — | 当前幅度比 $\sqrt{P_1/P_2}$ |
| `error` | — | $r - R_{target}$ |
| `offset_V` | V | 本次更新后的 CH1 offset |

### s1_min / s2_min 策略（`'dir'` 列存在）

| 列名 | 单位 | 说明 |
|------|------|------|
| `timestamp_s` | s | 从控制开始的相对时间 |
| `s1_dbm` | dBm | 当前 20 kHz 功率（已校正） |
| `s2_dbm` | dBm | 当前 40 kHz 功率（已校正） |
| `dir` | — | 梯度方向：`→`（正方向）或 `←`（反方向） |
| `probe_V` | V | 本次探针步长 |
| `step_V` | V | 本次控制步长 |
| `offset_V` | V | 本次更新后的 CH1 offset |
