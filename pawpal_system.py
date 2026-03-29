"""
PawPal+ — backend logic layer
Phase 4: Algorithmic enhancements — sort by time, filter tasks,
         date-aware recurring tasks, and enriched conflict detection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import Optional

# Priority order used for sorting (lower index = higher urgency)
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}


# ---------------------------------------------------------------------------
# Task — a single care item (feeding, walk, medication, appointment, etc.)
# ---------------------------------------------------------------------------

@dataclass
class Task:
    title: str
    category: str                        # "feeding"|"walk"|"medication"|"appointment"|"grooming"|"enrichment"
    duration_minutes: int
    priority: str                        # "high" | "medium" | "low"
    due_time: Optional[time] = None      # e.g. time(8, 0) → 08:00
    recurring: bool = False
    completed: bool = False
    notes: str = ""
    pet_name: str = ""                   # set automatically by Pet.add_task()
    next_due_date: Optional[date] = None # for recurring tasks: date of next occurrence

    def is_due_today(self) -> bool:
        """Return True if the task should appear on today's schedule.

        - Non-recurring: due if not yet completed.
        - Recurring: due if it has never been completed, or its next_due_date
          has arrived (today >= next_due_date).
        """
        if self.recurring:
            if self.next_due_date is None:
                return True                          # never completed → due today
            return date.today() >= self.next_due_date
        return not self.completed

    def mark_complete(self) -> None:
        """Mark the task completed.

        For recurring tasks, automatically schedule the next occurrence
        using timedelta(days=1) so the task reappears tomorrow.
        """
        self.completed = True
        if self.recurring:
            self.next_due_date = date.today() + timedelta(days=1)

    def __str__(self) -> str:
        time_str = self.due_time.strftime("%I:%M %p") if self.due_time else "anytime"
        status = "✓" if self.completed else "○"
        pet_tag = f" [{self.pet_name}]" if self.pet_name else ""
        return (
            f"[{status}]{pet_tag} {self.title} ({self.category}) | "
            f"{self.duration_minutes} min | priority: {self.priority} | at: {time_str}"
        )


# ---------------------------------------------------------------------------
# Pet — one animal belonging to an owner
# ---------------------------------------------------------------------------

@dataclass
class Pet:
    name: str
    species: str                         # "dog" | "cat" | "other"
    breed: str = ""
    age: int = 0
    tasks: list[Task] = field(default_factory=list)

    def add_task(self, task: Task) -> None:
        """Append a care task and tag it with this pet's name."""
        task.pet_name = self.name
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
    available_minutes_per_day: int = 480  # default: 8 hours
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

    # ------------------------------------------------------------------
    # Core scheduling
    # ------------------------------------------------------------------

    def generate_schedule(self) -> list[Task]:
        """Build a priority-then-time-sorted daily task list within the owner's budget.

        Tasks are collected from all pets, filtered to those due today,
        sorted high → medium → low (then by due_time), and accepted until
        the time budget is exhausted. High-priority tasks always make the cut.
        """
        today_tasks: list[Task] = []
        for pet in self.owner.pets:
            today_tasks.extend(pet.get_tasks_for_today())

        sorted_tasks = self.sort_by_priority(today_tasks)

        scheduled: list[Task] = []
        minutes_used = 0

        for task in sorted_tasks:
            fits = (minutes_used + task.duration_minutes) <= self.owner.available_minutes_per_day
            if task.priority == "high" or fits:
                scheduled.append(task)
                minutes_used += task.duration_minutes

        # Within the final list, order by time so the output reads chronologically
        self.schedule = self.sort_by_time(scheduled)
        return self.schedule

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low, then by due_time (nulls last).

        Uses a tuple key so Python's stable sort preserves insertion order
        for tasks that share the same priority and time.
        """
        return sorted(
            tasks,
            key=lambda t: (
                _PRIORITY_ORDER.get(t.priority, 99),
                (t.due_time.hour * 60 + t.due_time.minute) if t.due_time else 1440,
            ),
        )

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted chronologically by due_time; tasks with no time go last.

        Useful for rendering the final schedule in reading order.
        Pure time sort — ignores priority so call after priority selection.
        """
        return sorted(
            tasks,
            key=lambda t: (t.due_time.hour * 60 + t.due_time.minute) if t.due_time else 1440,
        )

    # ------------------------------------------------------------------
    # Filtering
    # ------------------------------------------------------------------

    def filter_tasks(
        self,
        tasks: list[Task],
        *,
        pet_name: Optional[str] = None,
        completed: Optional[bool] = None,
        category: Optional[str] = None,
    ) -> list[Task]:
        """Return a filtered subset of *tasks* based on the supplied criteria.

        Any combination of keyword filters can be applied simultaneously:
        - pet_name: keep only tasks belonging to that pet (case-insensitive)
        - completed: True → completed only, False → pending only
        - category: keep only tasks of that category (case-insensitive)
        """
        result = tasks
        if pet_name is not None:
            result = [t for t in result if t.pet_name.lower() == pet_name.lower()]
        if completed is not None:
            result = [t for t in result if t.completed == completed]
        if category is not None:
            result = [t for t in result if t.category.lower() == category.lower()]
        return result

    # ------------------------------------------------------------------
    # Conflict detection
    # ------------------------------------------------------------------

    def detect_conflicts(self) -> list[tuple[Task, Task]]:
        """Return pairs of scheduled tasks whose time windows overlap.

        A conflict exists when both tasks carry a due_time and their intervals
        [start, start + duration) intersect. Returns warning-ready tuples
        rather than raising an exception so the caller decides how to surface them.
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

    def conflict_warnings(self) -> list[str]:
        """Return human-readable warning strings for every detected conflict."""
        warnings = []
        for a, b in self.detect_conflicts():
            a_time = a.due_time.strftime("%I:%M %p")
            b_time = b.due_time.strftime("%I:%M %p")
            warnings.append(
                f"⚠ CONFLICT: '{a.title}' ({a_time}, {a.duration_minutes} min) "
                f"overlaps with '{b.title}' ({b_time}, {b.duration_minutes} min)"
            )
        return warnings

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------

    def get_summary(self) -> str:
        """Return a formatted, human-readable daily schedule for the terminal."""
        if not self.schedule:
            return "No tasks scheduled for today."

        total_minutes = sum(t.duration_minutes for t in self.schedule)
        lines = [
            "=" * 58,
            "  PawPal+ — Today's Care Schedule",
            "=" * 58,
        ]

        for i, task in enumerate(self.schedule, start=1):
            lines.append(f"  {i}. {task}")

        lines.append("-" * 58)
        lines.append(f"  Total time: {total_minutes} min  |  Tasks: {len(self.schedule)}")

        for warning in self.conflict_warnings():
            lines.append(f"  {warning}")

        lines.append("=" * 58)
        return "\n".join(lines)
