"""Orchestrate software ECU + software Aether for bench and CI scenarios."""

from .bench import SimBench, burn_soak
from .runner import main

__all__ = ["SimBench", "burn_soak", "main"]
