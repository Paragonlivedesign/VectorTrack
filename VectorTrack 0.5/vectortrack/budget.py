"""Project budget settings (hours or money, not both)."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Protocol


class BudgetType(str, Enum):
    NONE = "none"
    HOURS = "hours"
    MONEY = "money"


@dataclass(frozen=True)
class ProjectBudget:
    budget_type: BudgetType
    amount: float

    @property
    def has_budget(self) -> bool:
        return self.budget_type != BudgetType.NONE and self.amount > 0


class SettingsReader(Protocol):
    def get_setting(self, key: str, default: str = "") -> str: ...


class SettingsWriter(SettingsReader, Protocol):
    def set_setting(self, key: str, value: str) -> None: ...


def budget_hours_key(project_code: str) -> str:
    return f"budget_hours:{project_code}"


def budget_money_key(project_code: str) -> str:
    return f"budget_money:{project_code}"


def budget_type_key(project_code: str) -> str:
    return f"budget_type:{project_code}"


def budget_setting_keys(project_code: str) -> tuple[str, str, str]:
    return budget_hours_key(project_code), budget_money_key(project_code), budget_type_key(project_code)


def _parse_float(raw: str | None, default: float = 0.0) -> float:
    try:
        return max(0.0, float(raw or default))
    except (TypeError, ValueError):
        return default


def load_project_budget(repository: SettingsReader, project_code: str) -> ProjectBudget:
    hours = _parse_float(repository.get_setting(budget_hours_key(project_code), "0"))
    money = _parse_float(repository.get_setting(budget_money_key(project_code), "0"))
    raw_type = (repository.get_setting(budget_type_key(project_code), "") or "").strip().lower()

    if raw_type == BudgetType.MONEY.value and money > 0:
        return ProjectBudget(BudgetType.MONEY, money)
    if raw_type == BudgetType.HOURS.value and hours > 0:
        return ProjectBudget(BudgetType.HOURS, hours)
    if money > 0 and hours <= 0:
        return ProjectBudget(BudgetType.MONEY, money)
    if hours > 0:
        return ProjectBudget(BudgetType.HOURS, hours)
    return ProjectBudget(BudgetType.NONE, 0.0)


def save_project_budget(repository: SettingsWriter, project_code: str, budget: ProjectBudget) -> None:
    if budget.budget_type == BudgetType.HOURS and budget.amount > 0:
        repository.set_setting(budget_type_key(project_code), BudgetType.HOURS.value)
        repository.set_setting(budget_hours_key(project_code), f"{budget.amount:.2f}")
        repository.set_setting(budget_money_key(project_code), "0")
        return
    if budget.budget_type == BudgetType.MONEY and budget.amount > 0:
        repository.set_setting(budget_type_key(project_code), BudgetType.MONEY.value)
        repository.set_setting(budget_money_key(project_code), f"{budget.amount:.2f}")
        repository.set_setting(budget_hours_key(project_code), "0")
        return
    repository.set_setting(budget_type_key(project_code), BudgetType.NONE.value)
    repository.set_setting(budget_hours_key(project_code), "0")
    repository.set_setting(budget_money_key(project_code), "0")


def migrate_project_budget(repository: SettingsWriter, old_code: str, new_code: str) -> None:
    if not old_code or old_code == new_code:
        return
    budget = load_project_budget(repository, old_code)
    if budget.has_budget:
        save_project_budget(repository, new_code, budget)
    for key in budget_setting_keys(old_code):
        repository.set_setting(key, "0" if key != budget_type_key(old_code) else BudgetType.NONE.value)


def budget_usage(
    budget: ProjectBudget,
    *,
    tracked_hours: float,
    billable: float,
) -> tuple[float, float]:
    """Return (used, limit) for progress and warnings."""
    if not budget.has_budget:
        return 0.0, 0.0
    if budget.budget_type == BudgetType.MONEY:
        return max(0.0, billable), budget.amount
    return max(0.0, tracked_hours), budget.amount


def budget_progress_percent(budget: ProjectBudget, *, tracked_hours: float, billable: float) -> int:
    used, limit = budget_usage(budget, tracked_hours=tracked_hours, billable=billable)
    if limit <= 0:
        return 0
    return max(0, min(100, int((used / limit) * 100)))


def format_budget_display(budget: ProjectBudget) -> str:
    if not budget.has_budget:
        return "N/A"
    if budget.budget_type == BudgetType.MONEY:
        return f"${budget.amount:.2f}"
    return f"{budget.amount:.2f}h"
