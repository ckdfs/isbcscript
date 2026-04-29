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
