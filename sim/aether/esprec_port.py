"""BytePort adapter for tig/esprec against V-AETHER TCP.

Thin alias over :class:`AetherHostClient`, which already implements the
esprec ``BytePort`` surface (write / readline / read / reset / flush).
"""

from __future__ import annotations

from .device import AetherHostClient

# Prefer this name when wiring esprec snapshot/record tools.
AetherTcpPort = AetherHostClient

__all__ = ["AetherTcpPort", "AetherHostClient"]
