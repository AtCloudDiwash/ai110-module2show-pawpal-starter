"""
PawPal+ — backend logic layer
Phase 1: Class skeletons derived from UML design.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import Optional


# ---------------------------------------------------------------------------
# Task — a single care item (feeding, walk, medication, appointment, etc.)
# ---------------------------------------------------------------------------

@dataclass
class Task:
    title: str
    category: str                       # "feeding" | "walk" | "medication" | "appointment" | "grooming" | "enrichment"
    duration_minutes: int
    priority: str                       # "high" | "medium" | "low"
    due_time: Optional[time] = None     # e.g. time(8, 0) → 08:00
    recurring: bool = False
    completed: bool = False
    notes: str = ""

    def is_due_today(self) -> bool:
        """Return True if this task should appear on today's schedule."""
        pass  # TODO: implement recurrence logic

    def mark_complete(self) -> None:
        """Mark the task as completed."""
        pass  # TODO: set completed = True, record timestamp


# ---------------------------------------------------------------------------
# Pet — one animal belonging to an owner
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    species: str                        # "dog" | "cat" | "other"
    breed: str = ""
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Attach a care task to this pet."""
        pass  # TODO

    def remove_task(self, task_title: str) -> None:
        """Remove a task by title."""
        pass  # TODO

    def get_tasks_for_today(self) -> list[Task]:
        """Return tasks that are due today and not yet completed."""
        pass  # TODO


# ---------------------------------------------------------------------------
# Owner — the human managing one or more pets
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    name: str
    email: str = ""
    available_minutes_per_day: int = 480   # default: 8 hours
    pets: list[Pet] = field(default_factory=list)

    def add_pet(self, pet: Pet) -> None:
        """Register a pet under this owner."""
        pass  # TODO

    def remove_pet(self, pet_name: str) -> None:
        """Unregister a pet by name."""
        pass  # TODO

    def get_all_tasks(self) -> list[Task]:
        """Aggregate tasks across all pets."""
        pass  # TODO


# ---------------------------------------------------------------------------
# Scheduler — generates and organises the daily care plan
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        self.owner = owner
        self.schedule: list[Task] = []

    def generate_schedule(self) -> list[Task]:
        """Build an ordered daily task list respecting priority and time budget."""
        pass  # TODO

    def detect_conflicts(self) -> list[tuple[Task, Task]]:
        """Return pairs of tasks whose time windows overlap."""
        pass  # TODO

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low priority."""
        pass  # TODO

    def get_summary(self) -> str:
        """Return a human-readable summary of the generated schedule."""
        pass  # TODO
