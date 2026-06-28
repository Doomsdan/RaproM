"""Shared test setup for optional scientific dependencies."""

from __future__ import annotations

import sys
import types


if "miepython" not in sys.modules:
    miepython = types.ModuleType("miepython")

    def mie(_m, _x):
        return 1.0, 1.0, 1.0, 1.0

    miepython.mie = mie
    sys.modules["miepython"] = miepython

