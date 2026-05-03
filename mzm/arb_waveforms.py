"""
ARB waveform generation for MZM bias control modes.

All functions return normalized [-1.0, +1.0] float samples suitable for
DG922Pro.load_arb_waveform().
"""

import math


def quad_pm_waveform(
    num_points: int = 16384,
    square_high_v: float = 5.4,
    square_low_v: float = 0.0,
    pilot_amp_v: float = 0.4,
    pilot_freq_hz: float = 20e3,
    square_freq_hz: float = 200e3,
    sample_rate: float = 327.68e6,
) -> list:
    """Generate quad_pm ARB waveform samples.

    Encodes a 200 kHz square wave switching between two pilot-modulated states:
      - HIGH (5.4 V): sin(2π × 20kHz × t) pilot, ±0.4 V
      - LOW  (0.0 V): cos(2π × 20kHz × t) pilot, ±0.4 V

    Returns samples normalized to [-1.0, +1.0] range.
    Total voltage range: −0.4 V ~ 5.8 V (6.2 Vpp, centered at 2.7 V).

    Parameters
    ----------
    num_points      : Total sample points (default 16384 → 50 µs at 327.68 MHz)
    square_high_v   : HIGH-level DC voltage (default 5.4 V)
    square_low_v    : LOW-level DC voltage (default 0.0 V)
    pilot_amp_v     : Pilot amplitude, zero-to-peak (default 0.4 V)
    pilot_freq_hz   : Pilot frequency (default 20 kHz)
    square_freq_hz  : Square-wave frequency (default 200 kHz)
    sample_rate     : ARB DAC sample rate (default 327.68 MHz)
    """
    dt = 1.0 / sample_rate
    omega = 2.0 * math.pi * pilot_freq_hz
    square_period = 1.0 / square_freq_hz
    half_square = square_period / 2.0

    samples = []
    for i in range(num_points):
        t = i * dt
        if (t % square_period) < half_square:
            # HIGH state: sin pilot on 5.4 V DC
            samples.append(square_high_v + pilot_amp_v * math.sin(omega * t))
        else:
            # LOW state: cos pilot on 0 V DC
            samples.append(square_low_v + pilot_amp_v * math.cos(omega * t))

    # Normalize to [-1, +1]
    v_min = min(samples)
    v_max = max(samples)
    center = (v_max + v_min) / 2.0
    half_range = (v_max - v_min) / 2.0
    normalized = [(v - center) / half_range for v in samples]

    return normalized


def max_min_waveform(
    vpi: float = 4.0,
    num_points: int = 16384,
    pilot_amp_v: float = 0.4,
    pilot_freq_hz: float = 20e3,
    square_freq_hz: float = 200e3,
    sample_rate: float = 327.68e6,
    duty_a: float = 0.5,
) -> list:
    """Generate max_min ARB waveform samples (sin/cos switching, Vpi-aware).

    50%-duty square wave switching between two pilot-modulated states:

      - LOW  (state A, max point, φ=0):  cos(2π·20kHz·t) pilot
      - HIGH (state B, min point, φ=π):  sin(2π·20kHz·t) pilot

    The sin/cos assignment is essential — it makes S₂ contributions from
    the two states add constructively instead of cancelling.  Without it,
    both S₁ and S₂ are attenuated by |2A−1| and vanish at A=0.5.

    With sin/cos switching (derived from Bessel expansion):
      |S₁| ∝ 2J₁·|sin(φ_DC)|·√(A²+(1−A)²)   → valley at target (φ_DC=0)
      |S₂| ∝ 2J₂·|cos(φ_DC)|                → peak at target, A-independent

    Designed for DG922Pro amplitude = Vpi + 2·pilot_amp_v Vpp
    and offset = Vpi/2.

    Parameters
    ----------
    vpi             : Vpi in volts (controls DC level positions)
    num_points      : Total sample points (default 16384)
    pilot_amp_v     : Pilot amplitude, zero-to-peak (default 0.4 V)
    pilot_freq_hz   : Pilot frequency (default 20 kHz)
    square_freq_hz  : Square-wave frequency (default 200 kHz)
    sample_rate     : ARB DAC sample rate (default 327.68 MHz)
    duty_a          : Duty cycle for state A (LOW); any value works
    """
    total_vpp = vpi + 2.0 * pilot_amp_v

    dc_low_norm  = -vpi / total_vpp
    dc_high_norm =  vpi / total_vpp
    pilot_norm   = pilot_amp_v / (total_vpp / 2)

    dt = 1.0 / sample_rate
    omega = 2.0 * math.pi * pilot_freq_hz
    square_period = 1.0 / square_freq_hz
    low_duration = square_period * duty_a

    samples = []
    for i in range(num_points):
        t = i * dt
        pilot_cos = pilot_norm * math.cos(omega * t)
        pilot_sin = pilot_norm * math.sin(omega * t)
        if (t % square_period) < low_duration:
            samples.append(dc_low_norm + pilot_cos)    # cos on LOW
        else:
            samples.append(dc_high_norm + pilot_sin)   # sin on HIGH

    return samples
