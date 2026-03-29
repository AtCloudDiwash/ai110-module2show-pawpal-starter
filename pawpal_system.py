"""
PawPal+ — backend logic layer
Phase 2: Full implementation of Owner, Pet, Task, and Scheduler.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import time
from typing import Optional

# Priority order used for sorting (lower index = higher urgency)
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


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
        """Return True if the task recurs daily or has not been completed yet."""
        return self.recurring or not self.completed

    def mark_complete(self) -> None:
        """Set the task status to completed."""
        self.completed = True

    def __str__(self) -> str:
        time_str = self.due_time.strftime("%I:%M %p") if self.due_time else "anytime"
        status = "✓" if self.completed else "○"
        return (
            f"[{status}] {self.title} ({self.category}) | "
            f"{self.duration_minutes} min | priority: {self.priority} | at: {time_str}"
        )


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
        """Append a care task to this pet's task list."""
        self.tasks.append(task)

    def remove_task(self, task_title: str) -> None:
        """Remove the first task whose title matches (case-insensitive)."""
        self.tasks = [t for t in self.tasks if t.title.lower() != task_title.lower()]

    def get_tasks_for_today(self) -> list[Task]:
        """Return all tasks that are due today and not yet completed."""
        return [t for t in self.tasks if t.is_due_today() and not t.completed]

    def __str__(self) -> str:
        breed_str = f" ({self.breed})" if self.breed else ""
        return f"{self.name}{breed_str} — {self.species}, age {self.age}"


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
        """Register a new pet under this owner."""
        self.pets.append(pet)

    def remove_pet(self, pet_name: str) -> None:
        """Remove a pet by name (case-insensitive)."""
        self.pets = [p for p in self.pets if p.name.lower() != pet_name.lower()]

    def get_all_tasks(self) -> list[Task]:
        """Aggregate and return every task across all pets."""
        all_tasks: list[Task] = []
        for pet in self.pets:
            all_tasks.extend(pet.tasks)
        return all_tasks


# ---------------------------------------------------------------------------
# Scheduler — generates and organises the daily care plan
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        """Initialise the scheduler with the owner whose pets will be scheduled."""
        self.owner = owner
        self.schedule: list[Task] = []

    def generate_schedule(self) -> list[Task]:
        """Build a priority-sorted daily task list that fits within the owner's time budget.

        Tasks are collected from all pets, filtered to those due today,
        sorted high → medium → low, then accepted until the time budget runs out.
        High-priority tasks are always included regardless of budget.
        """
        today_tasks: list[Task] = []
        for pet in self.owner.pets:
            today_tasks.extend(pet.get_tasks_for_today())

        sorted_tasks = self.sort_by_priority(today_tasks)

        scheduled: list[Task] = []
        minutes_used = 0

        for task in sorted_tasks:
            fits_in_budget = (minutes_used + task.duration_minutes) <= self.owner.available_minutes_per_day
            if task.priority == "high" or fits_in_budget:
                scheduled.append(task)
                minutes_used += task.duration_minutes

        self.schedule = scheduled
        return self.schedule

    def detect_conflicts(self) -> list[tuple[Task, Task]]:
        """Return pairs of tasks in the current schedule whose time windows overlap.

        A conflict exists when both tasks have a due_time and their windows
        [due_time, due_time + duration] overlap.
        """
        timed = [t for t in self.schedule if t.due_time is not None]
        conflicts: list[tuple[Task, Task]] = []

        for i, a in enumerate(timed):
            a_start = a.due_time.hour * 60 + a.due_time.minute
            a_end = a_start + a.duration_minutes
            for b in timed[i + 1:]:
                b_start = b.due_time.hour * 60 + b.due_time.minute
                b_end = b_start + b.duration_minutes
                if a_start < b_end and b_start < a_end:
                    conflicts.append((a, b))

        return conflicts

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return a new list sorted high → medium → low, then by due_time (nulls last)."""
        def sort_key(t: Task):
            priority_rank = _PRIORITY_ORDER.get(t.priority, 99)
            if t.due_time is None:
                time_rank = 1440  # treat "anytime" as end of day
            else:
                time_rank = t.due_time.hour * 60 + t.due_time.minute
            return (priority_rank, time_rank)

        return sorted(tasks, key=sort_key)

    def get_summary(self) -> str:
        """Return a formatted, human-readable daily schedule for the terminal."""
        if not self.schedule:
            return "No tasks scheduled for today."

        total_minutes = sum(t.duration_minutes for t in self.schedule)
        lines = [
            "=" * 52,
            "  PawPal+ — Today's Care Schedule",
            "=" * 52,
        ]

        for i, task in enumerate(self.schedule, start=1):
            lines.append(f"  {i}. {task}")

        conflicts = self.detect_conflicts()
        lines.append("-" * 52)
        lines.append(f"  Total time: {total_minutes} min  |  Tasks: {len(self.schedule)}")

        if conflicts:
            lines.append(f"  ⚠ {len(conflicts)} time conflict(s) detected:")
            for a, b in conflicts:
                lines.append(f"    • '{a.title}' overlaps with '{b.title}'")

        lines.append("=" * 52)
        return "\n".join(lines)
