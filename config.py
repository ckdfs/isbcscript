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
OFFSET_STEP     =  0.050   # V   (50 mV)
SETTLE_S        =  0.15    # s   settle time after each offset step

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

# ── Fitting ───────────────────────────────────────────────────────────────────
FIT_WINDOW_FRAC = 1 / 3    # fraction of Vpi used as monotonic window around V0

# ── Control loop ─────────────────────────────────────────────────────────────
K_I             = 0.01     # integral gain (tune from small value)
OFFSET_MIN      = -9.0     # V  CH1 offset hard limit
OFFSET_MAX      =  9.0     # V
