from datetime import datetime

import pytest

from vectortrack.services.billing_service import BillingContext, BillingService


def test_billing_rounding_nearest_quarter_hour():
    service = BillingService(rounding_minutes=15, rounding_mode="nearest")
    summary = service.compute(BillingContext(rate=100.0, duration_hours=1.12))
    assert summary.rounded_hours == pytest.approx(1.0, abs=0.0001)
    assert summary.total_due == pytest.approx(100.0, abs=0.01)


def test_billing_after_hours_multiplier():
    service = BillingService(after_hours_multiplier=1.5)
    summary = service.compute(
        BillingContext(
            rate=100.0,
            duration_hours=1.0,
            started_at=datetime(2026, 6, 21, 20, 0, 0),
        )
    )
    assert summary.effective_rate == pytest.approx(150.0, abs=0.01)
    assert summary.total_due == pytest.approx(150.0, abs=0.01)


def test_billing_non_billable():
    service = BillingService()
    summary = service.compute(BillingContext(rate=100.0, duration_hours=2.0, billable=False))
    assert summary.total_due == 0.0
    assert summary.non_billable_reason == "marked_non_billable"


def test_billing_budget_and_retainer():
    service = BillingService(rounding_mode="up")
    summary = service.compute(
        BillingContext(
            rate=100.0,
            duration_hours=1.0,
            retainer_remaining=60.0,
            budget_remaining=30.0,
        )
    )
    assert summary.subtotal == pytest.approx(100.0, abs=0.01)
    assert summary.retainer_applied == pytest.approx(60.0, abs=0.01)
    assert summary.total_due == pytest.approx(30.0, abs=0.01)
