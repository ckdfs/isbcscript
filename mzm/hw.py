"""
Hardware driver wrappers.

Single source of truth for instrument paths and IPs.
If skill paths change, only update _DG_PATH / _FS_PATH here.
"""

import sys

_DG_PATH = '/Users/ckdfs/.claude/skills/dg922pro/scripts'
_FS_PATH = '/Users/ckdfs/.claude/skills/fsv30/scripts'

for _p in (_DG_PATH, _FS_PATH):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from dg922pro import DG922Pro  # noqa: E402
from fsv30 import FSV30        # noqa: E402

__all__ = ['DG922Pro', 'FSV30']
