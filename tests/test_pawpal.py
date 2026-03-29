"""
tests/test_pawpal.py — pytest suite for PawPal+ core logic
Run: python -m pytest
"""

from datetime import time
from pawpal_system import Owner, Pet, Task, Scheduler


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_task(**kwargs) -> Task:
    defaults = dict(title="Test task", category="walk", duration_minutes=20, priority="medium")
    defaults.update(kwargs)
    return Task(**defaults)


def make_pet_with_tasks() -> Pet:
    pet = Pet(name="Buddy", species="dog")
    pet.add_task(make_task(title="Walk", priority="high", duration_minutes=30))
    pet.add_task(make_task(title="Feed", priority="medium", duration_minutes=10))
    return pet


# ---------------------------------------------------------------------------
# Task tests
# ---------------------------------------------------------------------------

class TestTaskCompletion:
    def test_mark_complete_sets_flag(self):
        task = make_task()
        assert task.completed is False
        task.mark_complete()
        assert task.completed is True

    def test_mark_complete_idempotent(self):
        """Calling mark_complete twice should not raise and stays True."""
        task = make_task()
        task.mark_complete()
        task.mark_complete()
        assert task.completed is True

    def test_completed_task_not_due_today_unless_recurring(self):
        task = make_task(recurring=False)
        task.mark_complete()
        assert task.is_due_today() is False

    def test_recurring_task_still_due_after_completion(self):
        task = make_task(recurring=True)
        task.mark_complete()
        assert task.is_due_today() is True


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

class TestPetTaskManagement:
    def test_add_task_increases_count(self):
        pet = Pet(name="Luna", species="cat")
        initial_count = len(pet.tasks)
        pet.add_task(make_task())
        assert len(pet.tasks) == initial_count + 1

    def test_add_multiple_tasks(self):
        pet = Pet(name="Luna", species="cat")
        pet.add_task(make_task(title="Feed"))
        pet.add_task(make_task(title="Groom"))
        pet.add_task(make_task(title="Play"))
        assert len(pet.tasks) == 3

    def test_remove_task_decreases_count(self):
        pet = make_pet_with_tasks()
        initial_count = len(pet.tasks)
        pet.remove_task("Walk")
        assert len(pet.tasks) == initial_count - 1

    def test_remove_nonexistent_task_is_safe(self):
        pet = make_pet_with_tasks()
        count_before = len(pet.tasks)
        pet.remove_task("Does not exist")
        assert len(pet.tasks) == count_before

    def test_get_tasks_for_today_excludes_completed(self):
        pet = Pet(name="Max", species="dog")
        t_done = make_task(title="Done task", recurring=False)
        t_done.mark_complete()
        t_pending = make_task(title="Pending task")
        pet.add_task(t_done)
        pet.add_task(t_pending)
        today = pet.get_tasks_for_today()
        assert t_pending in today
        assert t_done not in today


# ---------------------------------------------------------------------------
# Owner tests
# ---------------------------------------------------------------------------

class TestOwner:
    def test_add_pet_increases_count(self):
        owner = Owner(name="Jordan")
        owner.add_pet(Pet(name="Mochi", species="dog"))
        assert len(owner.pets) == 1

    def test_get_all_tasks_aggregates_across_pets(self):
        owner = Owner(name="Jordan")
        owner.add_pet(make_pet_with_tasks())      # 2 tasks
        owner.add_pet(make_pet_with_tasks())      # 2 tasks
        assert len(owner.get_all_tasks()) == 4

    def test_remove_pet(self):
        owner = Owner(name="Jordan")
        owner.add_pet(Pet(name="Mochi", species="dog"))
        owner.add_pet(Pet(name="Luna", species="cat"))
        owner.remove_pet("Mochi")
        names = [p.name for p in owner.pets]
        assert "Mochi" not in names
        assert "Luna" in names


# ---------------------------------------------------------------------------
# Scheduler tests
# ---------------------------------------------------------------------------

class TestScheduler:
    def _make_owner(self) -> Owner:
        owner = Owner(name="Alex", available_minutes_per_day=60)
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="High priority task", priority="high", duration_minutes=20))
        pet.add_task(make_task(title="Medium task", priority="medium", duration_minutes=20))
        pet.add_task(make_task(title="Low priority task", priority="low", duration_minutes=20))
        owner.add_pet(pet)
        return owner

    def test_generate_schedule_returns_tasks(self):
        scheduler = Scheduler(self._make_owner())
        result = scheduler.generate_schedule()
        assert len(result) > 0

    def test_high_priority_always_scheduled(self):
        """High-priority tasks should be scheduled even if over time budget."""
        owner = Owner(name="Alex", available_minutes_per_day=5)  # very tight budget
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="Critical med", priority="high", duration_minutes=30))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        titles = [t.title for t in scheduler.schedule]
        assert "Critical med" in titles

    def test_sort_by_priority_order(self):
        owner = Owner(name="Alex")
        scheduler = Scheduler(owner)
        tasks = [
            make_task(title="L", priority="low"),
            make_task(title="H", priority="high"),
            make_task(title="M", priority="medium"),
        ]
        sorted_tasks = scheduler.sort_by_priority(tasks)
        priorities = [t.priority for t in sorted_tasks]
        assert priorities == ["high", "medium", "low"]

    def test_detect_conflicts_finds_overlap(self):
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        # Two tasks at 08:00 that overlap (30 min each → conflict)
        pet.add_task(make_task(title="A", duration_minutes=30, due_time=time(8, 0), priority="high"))
        pet.add_task(make_task(title="B", duration_minutes=30, due_time=time(8, 15), priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        conflicts = scheduler.detect_conflicts()
        assert len(conflicts) == 1

    def test_detect_conflicts_no_overlap(self):
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="A", duration_minutes=30, due_time=time(8, 0), priority="high"))
        pet.add_task(make_task(title="B", duration_minutes=30, due_time=time(9, 0), priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        conflicts = scheduler.detect_conflicts()
        assert len(conflicts) == 0
