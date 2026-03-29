"""
PawPal+ — backend logic layer
Challenges: JSON persistence, weighted urgency scoring, next-available-slot finder.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, time, timedelta
from typing import Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Priority order for tier-based sorting (lower = higher urgency)
_PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Per-category urgency bonus used by the weighted scheduler
_CATEGORY_URGENCY: dict[str, int] = {
    "medication":   5,
    "appointment":  4,
    "feeding":      3,
    "walk":         2,
    "grooming":     1,
    "enrichment":   1,
}


# ---------------------------------------------------------------------------
# Task
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

    # ------------------------------------------------------------------
    # Scheduling helpers
    # ------------------------------------------------------------------

    def is_due_today(self) -> bool:
        """Return True if the task should appear on today's schedule.

        - Non-recurring: due if not yet completed.
        - Recurring: due if never completed (next_due_date is None)
          or today >= next_due_date.
        """
        if self.recurring:
            if self.next_due_date is None:
                return True
            return date.today() >= self.next_due_date
        return not self.completed

    def mark_complete(self) -> None:
        """Mark the task completed.

        For recurring tasks, set next_due_date to tomorrow via timedelta(days=1)
        so the task reappears automatically the following day.
        """
        self.completed = True
        if self.recurring:
            self.next_due_date = date.today() + timedelta(days=1)

    # ------------------------------------------------------------------
    # Serialisation (Challenge 2)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "title":            self.title,
            "category":         self.category,
            "duration_minutes": self.duration_minutes,
            "priority":         self.priority,
            "due_time":         self.due_time.strftime("%H:%M") if self.due_time else None,
            "recurring":        self.recurring,
            "completed":        self.completed,
            "notes":            self.notes,
            "pet_name":         self.pet_name,
            "next_due_date":    self.next_due_date.isoformat() if self.next_due_date else None,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Task:
        """Reconstruct a Task from a serialised dictionary."""
        due_time = None
        if data.get("due_time"):
            h, m = data["due_time"].split(":")
            due_time = time(int(h), int(m))
        next_due_date = None
        if data.get("next_due_date"):
            next_due_date = date.fromisoformat(data["next_due_date"])
        return cls(
            title=data["title"],
            category=data["category"],
            duration_minutes=data["duration_minutes"],
            priority=data["priority"],
            due_time=due_time,
            recurring=data.get("recurring", False),
            completed=data.get("completed", False),
            notes=data.get("notes", ""),
            pet_name=data.get("pet_name", ""),
            next_due_date=next_due_date,
        )

    def __str__(self) -> str:
        time_str = self.due_time.strftime("%I:%M %p") if self.due_time else "anytime"
        status   = "✓" if self.completed else "○"
        pet_tag  = f" [{self.pet_name}]" if self.pet_name else ""
        return (
            f"[{status}]{pet_tag} {self.title} ({self.category}) | "
            f"{self.duration_minutes} min | priority: {self.priority} | at: {time_str}"
        )


# ---------------------------------------------------------------------------
# Pet
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

    # ------------------------------------------------------------------
    # Serialisation (Challenge 2)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise to a JSON-compatible dictionary."""
        return {
            "name":    self.name,
            "species": self.species,
            "breed":   self.breed,
            "age":     self.age,
            "tasks":   [t.to_dict() for t in self.tasks],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Pet:
        """Reconstruct a Pet (and its tasks) from a serialised dictionary."""
        pet = cls(
            name=data["name"],
            species=data["species"],
            breed=data.get("breed", ""),
            age=data.get("age", 0),
        )
        for t_data in data.get("tasks", []):
            pet.tasks.append(Task.from_dict(t_data))
        return pet

    def __str__(self) -> str:
        breed_str = f" ({self.breed})" if self.breed else ""
        return f"{self.name}{breed_str} — {self.species}, age {self.age}"


# ---------------------------------------------------------------------------
# Owner
# ---------------------------------------------------------------------------

@dataclass
class Owner:
    name: str
    email: str = ""
    available_minutes_per_day: int = 480
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

    # ------------------------------------------------------------------
    # Serialisation (Challenge 2)
    # ------------------------------------------------------------------

    def to_dict(self) -> dict:
        """Serialise the full owner graph to a JSON-compatible dictionary."""
        return {
            "name":                    self.name,
            "email":                   self.email,
            "available_minutes_per_day": self.available_minutes_per_day,
            "pets":                    [p.to_dict() for p in self.pets],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Owner:
        """Reconstruct an Owner (with all pets and tasks) from a dictionary."""
        owner = cls(
            name=data["name"],
            email=data.get("email", ""),
            available_minutes_per_day=data.get("available_minutes_per_day", 480),
        )
        for p_data in data.get("pets", []):
            owner.pets.append(Pet.from_dict(p_data))
        return owner

    def save_to_json(self, path: str = "data.json") -> None:
        """Persist the owner graph to a JSON file at *path*."""
        with open(path, "w") as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def load_from_json(cls, path: str = "data.json") -> Owner:
        """Load and reconstruct an Owner graph from a JSON file at *path*."""
        with open(path) as f:
            return cls.from_dict(json.load(f))


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class Scheduler:
    def __init__(self, owner: Owner) -> None:
        """Initialise the scheduler with the owner whose pets will be scheduled."""
        self.owner = owner
        self.schedule: list[Task] = []

    # ------------------------------------------------------------------
    # Core scheduling — tier-based
    # ------------------------------------------------------------------

    def generate_schedule(self) -> list[Task]:
        """Build a priority-tier-sorted daily task list within the owner's budget.

        Collects tasks due today, sorts high → medium → low (then by time),
        accepts tasks until the budget is exhausted, and reorders the
        accepted set chronologically for display.
        High-priority tasks always make the cut regardless of budget.
        """
        today_tasks: list[Task] = []
        for pet in self.owner.pets:
            today_tasks.extend(pet.get_tasks_for_today())

        scheduled, minutes_used = [], 0
        for task in self.sort_by_priority(today_tasks):
            fits = (minutes_used + task.duration_minutes) <= self.owner.available_minutes_per_day
            if task.priority == "high" or fits:
                scheduled.append(task)
                minutes_used += task.duration_minutes

        self.schedule = self.sort_by_time(scheduled)
        return self.schedule

    # ------------------------------------------------------------------
    # Challenge 1a — weighted urgency scheduling
    # ------------------------------------------------------------------

    def score_task(self, task: Task) -> float:
        """Compute a composite urgency score for a single task.

        Score = priority_weight + category_urgency + time_bonus

        This produces finer-grained ordering than simple tier sorting:
        a high-priority medication (score 18) always outranks a
        high-priority walk (score 14), even though both are "high".

        Priority weights  : high=10, medium=5, low=1
        Category urgency  : medication=5, appointment=4, feeding=3,
                            walk=2, grooming=1, enrichment=1
        Time bonus        : +2 if a due_time is set (time-sensitive)
        """
        priority_weight = {"high": 10, "medium": 5, "low": 1}.get(task.priority, 1)
        category_urgency = _CATEGORY_URGENCY.get(task.category, 1)
        time_bonus = 2 if task.due_time is not None else 0
        return priority_weight + category_urgency + time_bonus

    def generate_weighted_schedule(self) -> list[Task]:
        """Build a schedule using composite urgency scores instead of simple tiers.

        Tasks with equal priority are further differentiated by category:
        medications come before walks, even if both are "high" priority.
        The time budget and high-priority bypass rules still apply.
        Returns tasks in chronological order for display.
        """
        today_tasks = [
            t for pet in self.owner.pets for t in pet.get_tasks_for_today()
        ]
        scored = sorted(today_tasks, key=self.score_task, reverse=True)

        scheduled, minutes_used = [], 0
        for task in scored:
            fits = (minutes_used + task.duration_minutes) <= self.owner.available_minutes_per_day
            if task.priority == "high" or fits:
                scheduled.append(task)
                minutes_used += task.duration_minutes

        self.schedule = self.sort_by_time(scheduled)
        return self.schedule

    # ------------------------------------------------------------------
    # Challenge 1b — next available slot finder
    # ------------------------------------------------------------------

    def find_next_available_slot(
        self,
        duration_minutes: int,
        earliest: time = time(6, 0),
    ) -> Optional[time]:
        """Find the earliest free time slot that fits *duration_minutes*.

        Scans forward from *earliest* in 15-minute increments.
        When a timed task in the current schedule would cause a conflict,
        the scan jumps past the end of that task instead of checking
        every slot one by one (O(n) in the number of scheduled tasks).
        Returns None if no slot is found before midnight.
        """
        timed = sorted(
            [t for t in self.schedule if t.due_time is not None],
            key=lambda t: t.due_time.hour * 60 + t.due_time.minute,
        )

        candidate = earliest.hour * 60 + earliest.minute

        while candidate + duration_minutes <= 24 * 60:
            cand_end = candidate + duration_minutes
            conflict_found = False

            for t in timed:
                t_start = t.due_time.hour * 60 + t.due_time.minute
                t_end   = t_start + t.duration_minutes
                if candidate < t_end and t_start < cand_end:
                    candidate = t_end          # jump past this task
                    conflict_found = True
                    break

            if not conflict_found:
                return time(candidate // 60, candidate % 60)

        return None  # no slot before midnight

    # ------------------------------------------------------------------
    # Sorting
    # ------------------------------------------------------------------

    def sort_by_priority(self, tasks: list[Task]) -> list[Task]:
        """Return tasks sorted high → medium → low, then by due_time (nulls last)."""
        return sorted(
            tasks,
            key=lambda t: (
                _PRIORITY_ORDER.get(t.priority, 99),
                (t.due_time.hour * 60 + t.due_time.minute) if t.due_time else 1440,
            ),
        )

    def sort_by_time(self, tasks: list[Task]) -> list[Task]:
        """Return tasks in chronological order; tasks with no due_time go last."""
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
        """Return a filtered subset of *tasks*.

        Combine any of: pet_name (case-insensitive), completed (bool),
        category (case-insensitive). All supplied filters are ANDed.
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
        """Return pairs of scheduled tasks whose time windows overlap."""
        timed = [t for t in self.schedule if t.due_time is not None]
        conflicts: list[tuple[Task, Task]] = []

        for i, a in enumerate(timed):
            a_start = a.due_time.hour * 60 + a.due_time.minute
            a_end   = a_start + a.duration_minutes
            for b in timed[i + 1:]:
                b_start = b.due_time.hour * 60 + b.due_time.minute
                b_end   = b_start + b.duration_minutes
                if a_start < b_end and b_start < a_end:
                    conflicts.append((a, b))

        return conflicts

    def conflict_warnings(self) -> list[str]:
        """Return human-readable warning strings for every detected conflict."""
        warnings = []
        for a, b in self.detect_conflicts():
            warnings.append(
                f"⚠ CONFLICT: '{a.title}' ({a.due_time.strftime('%I:%M %p')}, "
                f"{a.duration_minutes} min) overlaps with '{b.title}' "
                f"({b.due_time.strftime('%I:%M %p')}, {b.duration_minutes} min)"
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
