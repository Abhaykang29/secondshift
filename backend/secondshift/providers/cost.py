"""Cost guard and call ledger (spec section 11.4).

Why: real model calls cost real money and the hackathon budget is finite.
Every provider call is estimated *before* it happens and recorded after;
a hard stop raises BudgetExceeded at BUDGET_USD.
Depends on: config.PRICE_TABLE.
"""

import time
from dataclasses import dataclass, field

from secondshift.config import PRICE_TABLE


class BudgetExceeded(Exception):
    """Raised when cumulative spend reaches the configured budget."""


class ProviderUnavailable(Exception):
    """Raised when a provider cannot be reached / is not configured."""


class InvalidModelOutput(Exception):
    """Raised when a model reply fails schema validation after one retry."""


@dataclass
class CallRecord:
    """One row of the api_calls ledger."""

    at: float
    role: str
    model: str
    endpoint: str
    est_cost_usd: float
    actual_cost_usd: float
    cache_hit: bool
    latency_ms: float


@dataclass
class CostGuard:
    """Estimates, records and enforces the spend budget."""

    budget_usd: float = 100.0
    override: bool = False
    image_tokens_estimate: int = 1500
    records: list[CallRecord] = field(default_factory=list)

    @property
    def spent_usd(self) -> float:
        """Total actual spend recorded so far."""
        return sum(r.actual_cost_usd for r in self.records)

    def estimate_chat(self, model: str, n_images: int, est_output_tokens: int = 800) -> float:
        """Estimate a chat/vision call: images x image-token estimate + output."""
        prices = PRICE_TABLE[model]
        input_tokens = n_images * self.image_tokens_estimate + 500
        return (
            input_tokens / 1_000_000 * prices["input_per_m"]
            + est_output_tokens / 1_000_000 * prices["output_per_m"]
        )

    def estimate_segment(self, model: str, n_images: int) -> float:
        """Estimate a SAM call, priced per 1,000 images."""
        return n_images / 1000 * PRICE_TABLE[model]["per_1000_images"]

    def estimate_image_edit(self, model: str, n_images: int = 1) -> float:
        """Estimate a Muse Image edit, priced per image."""
        return n_images * PRICE_TABLE[model]["per_image"]

    def estimate_transcribe(self, model: str, audio_seconds: float) -> float:
        """Estimate transcription, priced per audio hour."""
        return audio_seconds / 3600 * PRICE_TABLE[model]["per_audio_hour"]

    def check_budget(self, est_cost_usd: float) -> None:
        """Raise BudgetExceeded if this call would cross the hard stop."""
        if self.override:
            return
        if self.spent_usd + est_cost_usd >= self.budget_usd:
            raise BudgetExceeded(
                f"Budget of ${self.budget_usd:.2f} reached "
                f"(spent ${self.spent_usd:.2f}, next call est. ${est_cost_usd:.2f})."
            )

    def record(
        self,
        role: str,
        model: str,
        endpoint: str,
        est_cost_usd: float,
        actual_cost_usd: float | None = None,
        cache_hit: bool = False,
        latency_ms: float = 0.0,
    ) -> CallRecord:
        """Append one call to the ledger and return the record."""
        rec = CallRecord(
            at=time.time(),
            role=role,
            model=model,
            endpoint=endpoint,
            est_cost_usd=est_cost_usd,
            actual_cost_usd=actual_cost_usd if actual_cost_usd is not None else est_cost_usd,
            cache_hit=cache_hit,
            latency_ms=latency_ms,
        )
        self.records.append(rec)
        return rec
