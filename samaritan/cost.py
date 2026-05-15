"""Per-session token accounting.

Tracks cumulative input / output / cache-read / cache-write tokens across
all API responses in the current session, plus an estimated USD figure
based on the Opus 4.7 list price.
"""

from __future__ import annotations

from dataclasses import dataclass

# Opus 4.7 list pricing per 1M tokens (input / output)
_PRICE_IN = 5.00
_PRICE_OUT = 25.00
_PRICE_CACHE_WRITE = _PRICE_IN * 1.25
_PRICE_CACHE_READ = _PRICE_IN * 0.10


@dataclass
class Usage:
    input_tokens: int = 0
    output_tokens: int = 0
    cache_creation_input_tokens: int = 0
    cache_read_input_tokens: int = 0

    def add(self, usage_obj) -> None:
        """Accumulate from a Message.usage object (SDK Pydantic model)."""
        if usage_obj is None:
            return
        self.input_tokens += getattr(usage_obj, "input_tokens", 0) or 0
        self.output_tokens += getattr(usage_obj, "output_tokens", 0) or 0
        self.cache_creation_input_tokens += (
            getattr(usage_obj, "cache_creation_input_tokens", 0) or 0
        )
        self.cache_read_input_tokens += (
            getattr(usage_obj, "cache_read_input_tokens", 0) or 0
        )

    def cost_usd(self) -> float:
        return (
            self.input_tokens / 1_000_000 * _PRICE_IN
            + self.output_tokens / 1_000_000 * _PRICE_OUT
            + self.cache_creation_input_tokens / 1_000_000 * _PRICE_CACHE_WRITE
            + self.cache_read_input_tokens / 1_000_000 * _PRICE_CACHE_READ
        )

    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_creation_input_tokens
            + self.cache_read_input_tokens
        )

    def summary(self) -> str:
        return (
            f"in={self.input_tokens:,}  "
            f"out={self.output_tokens:,}  "
            f"cache_w={self.cache_creation_input_tokens:,}  "
            f"cache_r={self.cache_read_input_tokens:,}  "
            f"≈ ${self.cost_usd():.4f}"
        )
