"""Test configuration and compatibility fixes."""

from __future__ import annotations

import bcrypt

if not hasattr(bcrypt, "__about__"):
    import types

    _about = types.ModuleType("bcrypt.__about__")
    _about.__version__ = getattr(bcrypt, "__version__", "5.0.0")
    bcrypt.__about__ = _about
