"""
tests/test_pawpal.py — pytest suite for PawPal+ core logic
Run: python -m pytest
"""

from datetime import date, time, timedelta
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

    def test_recurring_task_not_due_today_after_completion(self):
        """After completion, a recurring task should be due TOMORROW, not today."""
        task = make_task(recurring=True)
        task.mark_complete()
        # next_due_date is set to tomorrow, so it should NOT be due today
        assert task.is_due_today() is False

    def test_recurring_task_due_again_when_next_due_date_arrives(self):
        """A recurring task whose next_due_date is today or in the past is due."""
        task = make_task(recurring=True)
        task.mark_complete()
        # Simulate next day by back-dating next_due_date to today
        task.next_due_date = date.today()
        assert task.is_due_today() is True

    def test_recurring_task_sets_next_due_date_on_complete(self):
        """mark_complete on a recurring task sets next_due_date to tomorrow."""
        task = make_task(recurring=True)
        task.mark_complete()
        assert task.next_due_date == date.today() + timedelta(days=1)

    def test_non_recurring_task_has_no_next_due_date(self):
        task = make_task(recurring=False)
        task.mark_complete()
        assert task.next_due_date is None


# ---------------------------------------------------------------------------
# Pet tests
# ---------------------------------------------------------------------------

class TestPetTaskManagement:
    def test_add_task_increases_count(self):
        pet = Pet(name="Luna", species="cat")
        initial_count = len(pet.tasks)
        pet.add_task(make_task())
        assert len(pet.tasks) == initial_count + 1

    def test_add_task_sets_pet_name(self):
        """Pet.add_task should tag the task with the pet's name."""
        pet = Pet(name="Luna", species="cat")
        task = make_task()
        pet.add_task(task)
        assert task.pet_name == "Luna"

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
        owner = Owner(name="Alex", available_minutes_per_day=5)
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="Critical med", priority="high", duration_minutes=30))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        titles = [t.title for t in scheduler.schedule]
        assert "Critical med" in titles

    def test_sort_by_priority_order(self):
        scheduler = Scheduler(Owner(name="Alex"))
        tasks = [
            make_task(title="L", priority="low"),
            make_task(title="H", priority="high"),
            make_task(title="M", priority="medium"),
        ]
        sorted_tasks = scheduler.sort_by_priority(tasks)
        assert [t.priority for t in sorted_tasks] == ["high", "medium", "low"]

    def test_sort_by_time_chronological(self):
        """sort_by_time should order tasks earliest due_time first."""
        scheduler = Scheduler(Owner(name="Alex"))
        tasks = [
            make_task(title="Late",  due_time=time(18, 0)),
            make_task(title="Early", due_time=time(7,  0)),
            make_task(title="Mid",   due_time=time(12, 0)),
        ]
        result = scheduler.sort_by_time(tasks)
        assert [t.title for t in result] == ["Early", "Mid", "Late"]

    def test_sort_by_time_nulls_last(self):
        """Tasks with no due_time should appear at the end after sort_by_time."""
        scheduler = Scheduler(Owner(name="Alex"))
        tasks = [
            make_task(title="No time"),
            make_task(title="Has time", due_time=time(9, 0)),
        ]
        result = scheduler.sort_by_time(tasks)
        assert result[0].title == "Has time"
        assert result[-1].title == "No time"

    def test_filter_by_pet_name(self):
        owner = Owner(name="Alex")
        mochi = Pet(name="Mochi", species="dog")
        luna  = Pet(name="Luna",  species="cat")
        mochi.add_task(make_task(title="Mochi task"))
        luna.add_task(make_task(title="Luna task"))
        owner.add_pet(mochi)
        owner.add_pet(luna)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        result = scheduler.filter_tasks(scheduler.schedule, pet_name="Mochi")
        assert all(t.pet_name == "Mochi" for t in result)
        assert len(result) == 1

    def test_filter_by_category(self):
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="Walk",    category="walk"))
        pet.add_task(make_task(title="Feed",    category="feeding"))
        pet.add_task(make_task(title="Walk 2",  category="walk"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        walks = scheduler.filter_tasks(scheduler.schedule, category="walk")
        assert len(walks) == 2
        assert all(t.category == "walk" for t in walks)

    def test_filter_by_completed_status(self):
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        t1 = make_task(title="Done",    recurring=False)
        t2 = make_task(title="Pending")
        pet.add_task(t1)
        pet.add_task(t2)
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        # manually put both in schedule to test filter independent of generate
        scheduler.schedule = [t1, t2]
        t1.mark_complete()
        pending = scheduler.filter_tasks(scheduler.schedule, completed=False)
        done    = scheduler.filter_tasks(scheduler.schedule, completed=True)
        assert len(pending) == 1 and pending[0].title == "Pending"
        assert len(done)    == 1 and done[0].title    == "Done"

    def test_detect_conflicts_finds_overlap(self):
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="A", duration_minutes=30, due_time=time(8,  0), priority="high"))
        pet.add_task(make_task(title="B", duration_minutes=30, due_time=time(8, 15), priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert len(scheduler.detect_conflicts()) == 1

    def test_detect_conflicts_no_overlap(self):
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="A", duration_minutes=30, due_time=time(8, 0), priority="high"))
        pet.add_task(make_task(title="B", duration_minutes=30, due_time=time(9, 0), priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert len(scheduler.detect_conflicts()) == 0

    def test_conflict_warnings_returns_strings(self):
        """conflict_warnings() should return non-empty strings for each conflict."""
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="A", duration_minutes=60, due_time=time(8, 0), priority="high"))
        pet.add_task(make_task(title="B", duration_minutes=60, due_time=time(8, 0), priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        warnings = scheduler.conflict_warnings()
        assert len(warnings) == 1
        assert "CONFLICT" in warnings[0]


# ---------------------------------------------------------------------------
# Edge-case tests
# ---------------------------------------------------------------------------

class TestEdgeCases:
    """Boundary conditions and unusual-but-valid inputs."""

    # -- Empty / zero-item cases ---------------------------------------------

    def test_owner_with_no_pets_produces_empty_schedule(self):
        scheduler = Scheduler(Owner(name="Alex"))
        result = scheduler.generate_schedule()
        assert result == []

    def test_pet_with_no_tasks_returns_empty_today(self):
        pet = Pet(name="Ghost", species="cat")
        assert pet.get_tasks_for_today() == []

    def test_owner_with_no_pets_get_all_tasks_is_empty(self):
        owner = Owner(name="Alex")
        assert owner.get_all_tasks() == []

    def test_all_tasks_completed_produces_empty_schedule(self):
        """If every task is already done, nothing should be scheduled."""
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        t = make_task(recurring=False)
        t.mark_complete()
        pet.add_task(t)
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        assert scheduler.generate_schedule() == []

    def test_get_summary_empty_schedule(self):
        """get_summary() on an empty schedule returns a safe fallback string."""
        scheduler = Scheduler(Owner(name="Alex"))
        scheduler.generate_schedule()
        summary = scheduler.get_summary()
        assert "No tasks" in summary

    def test_sort_by_priority_empty_list(self):
        scheduler = Scheduler(Owner(name="Alex"))
        assert scheduler.sort_by_priority([]) == []

    def test_sort_by_time_empty_list(self):
        scheduler = Scheduler(Owner(name="Alex"))
        assert scheduler.sort_by_time([]) == []

    def test_filter_tasks_no_match_returns_empty(self):
        scheduler = Scheduler(Owner(name="Alex"))
        tasks = [make_task(title="Walk", category="walk")]
        result = scheduler.filter_tasks(tasks, category="medication")
        assert result == []

    # -- Conflict edge cases -------------------------------------------------

    def test_tasks_without_due_time_never_conflict(self):
        """Untimed tasks should never be flagged as conflicting."""
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="A", due_time=None, priority="high"))
        pet.add_task(make_task(title="B", due_time=None, priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert scheduler.detect_conflicts() == []

    def test_tasks_touching_but_not_overlapping_are_not_conflicts(self):
        """Task A ending exactly when task B starts should NOT be a conflict."""
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        # A: 08:00–08:30, B: 08:30–09:00 — they touch but don't overlap
        pet.add_task(make_task(title="A", duration_minutes=30, due_time=time(8, 0),  priority="high"))
        pet.add_task(make_task(title="B", duration_minutes=30, due_time=time(8, 30), priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert scheduler.detect_conflicts() == []

    def test_multiple_conflicts_detected(self):
        """Three mutually overlapping tasks should produce three conflict pairs."""
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        # All three start at 08:00 and run 60 min — every pair overlaps
        for title in ("A", "B", "C"):
            pet.add_task(make_task(title=title, duration_minutes=60,
                                   due_time=time(8, 0), priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert len(scheduler.detect_conflicts()) == 3

    def test_exact_same_start_time_is_a_conflict(self):
        """Two tasks starting at the identical minute must be flagged."""
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="A", duration_minutes=15, due_time=time(9, 0), priority="high"))
        pet.add_task(make_task(title="B", duration_minutes=15, due_time=time(9, 0), priority="high"))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert len(scheduler.detect_conflicts()) == 1

    # -- Budget edge cases ---------------------------------------------------

    def test_zero_budget_still_schedules_high_priority(self):
        """Even with 0 available minutes, high-priority tasks must be included."""
        owner = Owner(name="Alex", available_minutes_per_day=0)
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="Meds", priority="high", duration_minutes=5))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        assert any(t.title == "Meds" for t in scheduler.schedule)

    def test_low_priority_dropped_when_budget_exceeded(self):
        """Low-priority task should be skipped if budget is used up by higher ones."""
        owner = Owner(name="Alex", available_minutes_per_day=30)
        pet = Pet(name="Rex", species="dog")
        pet.add_task(make_task(title="Big medium", priority="medium", duration_minutes=30))
        pet.add_task(make_task(title="Small low",  priority="low",    duration_minutes=10))
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        titles = [t.title for t in scheduler.schedule]
        assert "Big medium" in titles
        assert "Small low" not in titles

    # -- Filter combined criteria --------------------------------------------

    def test_filter_combined_pet_and_category(self):
        """Applying pet_name and category together should AND the conditions."""
        owner = Owner(name="Alex")
        mochi = Pet(name="Mochi", species="dog")
        luna  = Pet(name="Luna",  species="cat")
        mochi.add_task(make_task(title="Mochi walk", category="walk"))
        mochi.add_task(make_task(title="Mochi feed", category="feeding"))
        luna.add_task(make_task(title="Luna walk",  category="walk"))
        owner.add_pet(mochi)
        owner.add_pet(luna)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        result = scheduler.filter_tasks(scheduler.schedule, pet_name="Mochi", category="walk")
        assert len(result) == 1
        assert result[0].title == "Mochi walk"

    # -- Recurrence integration ----------------------------------------------

    def test_recurring_task_reappears_next_day(self):
        """Simulate completing a recurring task today and checking it's due tomorrow."""
        task = make_task(recurring=True)
        task.mark_complete()
        tomorrow = date.today() + timedelta(days=1)
        assert task.next_due_date == tomorrow
        # Back-date to simulate tomorrow arriving
        task.next_due_date = date.today()
        assert task.is_due_today() is True

    def test_non_recurring_completed_task_excluded_from_schedule(self):
        """A completed non-recurring task must not appear in generate_schedule."""
        owner = Owner(name="Alex")
        pet = Pet(name="Rex", species="dog")
        done = make_task(title="Already done", recurring=False)
        done.mark_complete()
        pending = make_task(title="Still pending")
        pet.add_task(done)
        pet.add_task(pending)
        owner.add_pet(pet)
        scheduler = Scheduler(owner)
        scheduler.generate_schedule()
        titles = [t.title for t in scheduler.schedule]
        assert "Already done" not in titles
        assert "Still pending" in titles
