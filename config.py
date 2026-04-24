"""
Default parameters for all modes and hardware.
Change values here; do not scatter magic numbers in module code.
"""

# ── Hardware ─────────────────────────────────────────────────────────────────
DG922PRO_IP     = '192.168.99.115'
DG922PRO_PORT   = 5025
FSV30_IP        = '192.168.99.209'
FSV30_PORT      = 5025

# ── Pilot signal ─────────────────────────────────────────────────────────────
PILOT_FREQ_HZ   = 20e3     # Hz
PILOT_AMP_VPP   = 0.800    # Vpp

# ── Bias scan ────────────────────────────────────────────────────────────────
OFFSET_START    = -6.000   # V
OFFSET_STOP     =  6.000   # V
OFFSET_STEP     =  0.050   # V   fine step (用于后处理，不直接驱动扫描)
SETTLE_S        =  0.15    # s   control-loop settle time

# ── Scan phase — 快速扫描专用参数 ─────────────────────────────────────────────
# 扫描只需找零点位置和曲线形状，无需与控制环路相同的精度。
# 修改此处即可调节扫描速度，不影响控制环路设置。
SCAN_STEP       =  0.100   # V   扫描步长（→ 121 点，是 0.05V 的一半）
SCAN_SETTLE_S   =  0.050   # s   MZM 响应 << 1 ms，50 ms 已十分保守
SCAN_RBW_HZ     =  1000    # Hz  宽 RBW → 扫描速度约快 3×（噪底升 ~10 dB，可接受）
SCAN_VBW_HZ     =  1000    # Hz

# ── FSV30 measurement window ─────────────────────────────────────────────────
SA_CENTER_HZ    = 30e3     # Hz  covers 10–50 kHz
SA_SPAN_HZ      = 40e3     # Hz
SA_RBW_HZ       = 300      # Hz
SA_VBW_HZ       = 300      # Hz
SA_REF_LEV      = 0        # dBm
FREQ_F1_HZ      = 20e3     # Hz  marker 1: 1st harmonic of pilot
FREQ_F2_HZ      = 40e3     # Hz  marker 2: 2nd harmonic of pilot
POWER_OFFSET_DB = 6.0      # dB  FSV30 known calibration offset (reads ~6 dB high)
SWEEP_TIMEOUT_S = 120      # s
MEAS_AVG_N      = 1        # number of sweeps averaged per point (linear-power avg)

# ── Fitting ───────────────────────────────────────────────────────────────────
FIT_WINDOW_FRAC = 0.20     # fraction of Vpi; must be < 0.25 for max_quad (asymptote at Vpi/4)

# ── Control loop ─────────────────────────────────────────────────────────────
K_I             = 0.01     # integral gain (tune from small value)
OFFSET_MIN      = -9.0     # V  CH1 offset hard limit
OFFSET_MAX      =  9.0     # V
