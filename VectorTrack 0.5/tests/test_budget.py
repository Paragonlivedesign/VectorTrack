"""Tests for project budget settings."""

from __future__ import annotations

from vectortrack.budget import (
    BudgetType,
    ProjectBudget,
    budget_progress_percent,
    budget_usage,
    format_budget_display,
    load_project_budget,
    migrate_project_budget,
    save_project_budget,
)


class _MemorySettings:
    def __init__(self) -> None:
        self._values: dict[str, str] = {}

    def get_setting(self, key: str, default: str = "") -> str:
        return self._values.get(key, default)

    def set_setting(self, key: str, value: str) -> None:
        self._values[key] = value


def test_load_hours_budget_from_legacy_setting():
    repo = _MemorySettings()
    repo.set_setting("budget_hours:ABC", "12.50")
    budget = load_project_budget(repo, "ABC")
    assert budget == ProjectBudget(BudgetType.HOURS, 12.5)


def test_save_and_load_money_budget():
    repo = _MemorySettings()
    save_project_budget(repo, "JOB1", ProjectBudget(BudgetType.MONEY, 5000.0))
    budget = load_project_budget(repo, "JOB1")
    assert budget == ProjectBudget(BudgetType.MONEY, 5000.0)
    assert repo.get_setting("budget_hours:JOB1") == "0"


def test_save_hours_clears_money():
    repo = _MemorySettings()
    save_project_budget(repo, "JOB1", ProjectBudget(BudgetType.MONEY, 100.0))
    save_project_budget(repo, "JOB1", ProjectBudget(BudgetType.HOURS, 8.0))
    budget = load_project_budget(repo, "JOB1")
    assert budget == ProjectBudget(BudgetType.HOURS, 8.0)
    assert repo.get_setting("budget_money:JOB1") == "0"


def test_budget_usage_and_display():
    hours_budget = ProjectBudget(BudgetType.HOURS, 10.0)
    assert budget_usage(hours_budget, tracked_hours=5.0, billable=400.0) == (5.0, 10.0)
    assert budget_progress_percent(hours_budget, tracked_hours=8.0, billable=0.0) == 80
    assert format_budget_display(hours_budget) == "10.00h"

    money_budget = ProjectBudget(BudgetType.MONEY, 2500.0)
    assert budget_usage(money_budget, tracked_hours=20.0, billable=2000.0) == (2000.0, 2500.0)
    assert format_budget_display(money_budget) == "$2500.00"


def test_migrate_project_budget():
    repo = _MemorySettings()
    save_project_budget(repo, "OLD", ProjectBudget(BudgetType.MONEY, 900.0))
    migrate_project_budget(repo, "OLD", "NEW")
    assert load_project_budget(repo, "NEW") == ProjectBudget(BudgetType.MONEY, 900.0)
    assert load_project_budget(repo, "OLD") == ProjectBudget(BudgetType.NONE, 0.0)
