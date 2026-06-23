"""Billing and invoice math helpers."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import ceil, floor
from typing import Iterable, Optional


@dataclass(frozen=True)
class BillingContext:
    rate: float
    duration_hours: float
    started_at: Optional[datetime] = None
    billable: bool = True
    budget_remaining: Optional[float] = None
    retainer_remaining: Optional[float] = None


@dataclass(frozen=True)
class BillingSummary:
    raw_hours: float
    rounded_hours: float
    effective_rate: float
    subtotal: float
    retainer_applied: float
    budget_capped: bool
    total_due: float
    non_billable_reason: Optional[str] = None


class BillingService:
    """Compute charges with rounding, after-hours, budget, and retainer rules."""

    def __init__(
        self,
        rounding_minutes: int = 15,
        rounding_mode: str = "nearest",
        after_hours_start: int = 18,
        after_hours_end: int = 8,
        after_hours_multiplier: float = 1.25,
    ):
        self.rounding_minutes = rounding_minutes
        self.rounding_mode = rounding_mode
        self.after_hours_start = after_hours_start
        self.after_hours_end = after_hours_end
        self.after_hours_multiplier = after_hours_multiplier

    def round_hours(self, hours: float) -> float:
        increment = self.rounding_minutes / 60.0
        if increment <= 0:
            return max(0.0, hours)
        ratio = max(0.0, hours) / increment
        if self.rounding_mode == "up":
            rounded = ceil(ratio) * increment
        elif self.rounding_mode == "down":
            rounded = floor(ratio) * increment
        else:
            rounded = round(ratio) * increment
        return round(max(0.0, rounded), 4)

    def is_after_hours(self, started_at: Optional[datetime]) -> bool:
        if started_at is None:
            return False
        hour = started_at.hour
        return hour >= self.after_hours_start or hour < self.after_hours_end

    def compute(self, ctx: BillingContext) -> BillingSummary:
        if not ctx.billable:
            return BillingSummary(
                raw_hours=ctx.duration_hours,
                rounded_hours=0.0,
                effective_rate=0.0,
                subtotal=0.0,
                retainer_applied=0.0,
                budget_capped=False,
                total_due=0.0,
                non_billable_reason="marked_non_billable",
            )

        rounded_hours = self.round_hours(ctx.duration_hours)
        effective_rate = ctx.rate
        if self.is_after_hours(ctx.started_at):
            effective_rate = round(effective_rate * self.after_hours_multiplier, 2)

        subtotal = round(rounded_hours * effective_rate, 2)
        due = subtotal
        retainer_applied = 0.0
        budget_capped = False

        if ctx.retainer_remaining is not None and ctx.retainer_remaining > 0:
            retainer_applied = min(ctx.retainer_remaining, due)
            due = round(due - retainer_applied, 2)

        if ctx.budget_remaining is not None and due > ctx.budget_remaining:
            due = round(max(0.0, ctx.budget_remaining), 2)
            budget_capped = True

        return BillingSummary(
            raw_hours=ctx.duration_hours,
            rounded_hours=rounded_hours,
            effective_rate=effective_rate,
            subtotal=subtotal,
            retainer_applied=round(retainer_applied, 2),
            budget_capped=budget_capped,
            total_due=round(due, 2),
        )

    def summarize(self, entries: Iterable[BillingContext]) -> BillingSummary:
        total_raw = 0.0
        total_rounded = 0.0
        total_subtotal = 0.0
        total_due = 0.0
        total_retainer = 0.0
        budget_capped = False
        for entry in entries:
            summary = self.compute(entry)
            total_raw += summary.raw_hours
            total_rounded += summary.rounded_hours
            total_subtotal += summary.subtotal
            total_due += summary.total_due
            total_retainer += summary.retainer_applied
            budget_capped = budget_capped or summary.budget_capped
        return BillingSummary(
            raw_hours=round(total_raw, 4),
            rounded_hours=round(total_rounded, 4),
            effective_rate=0.0,
            subtotal=round(total_subtotal, 2),
            retainer_applied=round(total_retainer, 2),
            budget_capped=budget_capped,
            total_due=round(total_due, 2),
        )
