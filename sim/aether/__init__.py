"""Software-only Aether device: identity, ECU client, synthetic framebuffer."""

from .device import AetherDevice, AetherServer
from .framebuffer import SyntheticFramebuffer

__all__ = ["AetherDevice", "AetherServer", "SyntheticFramebuffer"]
