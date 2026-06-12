# 硬件连接与校准

---

## 设备清单

| 设备 | 型号 | IP | 用途 |
|------|------|----|------|
| 信号发生器 | RIGOL DG922Pro | 192.168.99.115:5025 | 生成导频+PWM切换信号（CH1） |
| 频谱仪 | R&S FSV3000 | 192.168.99.209:5025 | 测量 PD 输出中的导频谐波功率 |
| MZM | — | — | 被控器件 |
| 光电探测器（PD） | — | — | MZM输出转电信号 |

---

## 信号链路

```
DG922Pro CH1
  (正弦导频 + DC偏置 / ARB切换波形)
       │
       ▼
  MZM 偏置端口
       │
   MZM 调制
       │
       ▼
  光电探测器（PD）
       │
       ▼
   FSV30 输入
  (测量 20 kHz, 40 kHz 功率)
```

---

## FSV30 已知校准偏差

该仪器读数约偏高 **6 dB**，所有代码中已统一减去 `POWER_OFFSET_DB = 6.0`。
若更换仪器或重新校准，修改 `config.py` 中的 `POWER_OFFSET_DB`。

相对测量（如比值 $r = \sqrt{P_1/P_2}$）不受绝对偏差影响。

---

## 低频信号注意事项

FSV30 默认 AC 耦合，对低频信号（< 100 kHz）有高通截止效应。
测量 20 kHz 和 40 kHz 信号时**必须切换为 DC 耦合**：

```python
sa.set_input_coupling('DC')
# ... 测量 ...
sa.set_input_coupling('AC')    # 测量完成后恢复，保护输入免受直流损坏
```

代码已在 `scan.setup_analyzer()` 中自动处理。

---

## 连通性验证

```bash
ping 192.168.99.115    # DG922Pro
ping 192.168.99.209    # FSV30
```

若 ping 不通：检查网线、交换机、仪器电源和局域网配置。

---

## ARB 波形约定

`main.py` 的模式流程会在步骤二调用 `mode.configure_source()`：

- 切换 CH1 到 ARB
- 设置频率、幅度和 offset
- 打开 CH1 输出

当前流程**不负责重新上传 ARB 波形**。如果仪器内的 ARB 波形被清空或切到了错误文件，
需要先用 DG922Pro 工具上传/选择对应波形：

| 模式 | ARB 波形 |
|------|----------|
| `max_quad` | 200 kHz PWM + 20 kHz 正弦导频，幅度由 $V_\pi/2+0.8$ Vpp 恢复 |
| `quad_pm` | 200 kHz 方波，HIGH=sin 导频，LOW=cos 导频，6.2 Vpp |
| `max_min` | 200 kHz 方波，LOW=cos 导频，HIGH=sin 导频，$V_\pi+0.8$ Vpp |

生成函数位于 `mzm/arb_waveforms.py`，但实验入口不会自动调用上传。

---

## Vπ 校准流程

每次实验前运行步骤一重新测量 $V_\pi$：

```bash
python main.py --mode max_quad --step scan
python main.py --mode quad_pm  --step scan
python main.py --mode max_min  --step scan
```

也可以使用旧版独立脚本 `python vpi_scan.py` 作人工排查，但正式结果目录以
`main.py` 生成的 `results/YYYYMMDD_HHMMSS_{mode}/` 为准。

MZM的 $V_\pi$ 可能随温度和时间漂移，不应复用历史数据。
