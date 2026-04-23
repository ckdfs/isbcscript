"""
Results directory management and file I/O.

Public API:
    make_result_dir(mode_name) → str
    save_csv(path, headers, rows)
    save_json(path, data)
"""

import csv
import json
import os
from datetime import datetime


def make_result_dir(mode_name: str, base: str = 'results') -> str:
    """Create and return a timestamped result directory."""
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    path = os.path.join(base, f'{ts}_{mode_name}')
    os.makedirs(path, exist_ok=True)
    return path


def save_csv(path: str, headers: list, rows) -> None:
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.writer(f)
        w.writerow(headers)
        for row in rows:
            w.writerow([f'{v:.6g}' if isinstance(v, float) else v for v in row])


def save_json(path: str, data: dict) -> None:
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)
