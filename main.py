"""
main.py — CLI demo for PawPal+
Phase 4: demonstrates sorting, filtering, recurring task scheduling,
         and conflict detection.

Run: python main.py
"""

from datetime import time
from pawpal_system import Owner, Pet, Task, Scheduler


def section(title: str) -> None:
    print(f"\n{'─' * 58}")
    print(f"  {title}")
    print(f"{'─' * 58}")


def main():
    # ----------------------------------------------------------------
    # Setup
    # ----------------------------------------------------------------
    owner = Owner(name="Jordan", email="jordan@example.com", available_minutes_per_day=180)

    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)
    luna  = Pet(name="Luna",  species="cat", breed="Tabby",     age=5)
    owner.add_pet(mochi)
    owner.add_pet(luna)

    # Tasks added intentionally OUT OF TIME ORDER to show sort_by_time works
    mochi.add_task(Task("Evening walk",    "walk",        40, "high",   due_time=time(18, 0),  recurring=True))
    mochi.add_task(Task("Flea medication", "medication",   5, "medium", due_time=time(8,  0)))
    mochi.add_task(Task("Morning walk",    "walk",        30, "high",   due_time=time(7,  0),  recurring=True))
    mochi.add_task(Task("Breakfast",       "feeding",     10, "high",   due_time=time(7, 30),  recurring=True))

    luna.add_task(Task("Breakfast",        "feeding",      5, "high",   due_time=time(7, 15),  recurring=True))
    luna.add_task(Task("Vet appointment",  "appointment", 60, "high",   due_time=time(10, 0),
                       notes="Annual check-up"))
    luna.add_task(Task("Brush coat",       "grooming",    15, "low",    recurring=True))

    # ---- Deliberate conflict: two tasks overlap at 07:00 ----
    mochi.add_task(Task("Training session", "enrichment", 45, "medium", due_time=time(7, 0)))

    # ----------------------------------------------------------------
    # 1. Full schedule (priority-sorted, then time-ordered)
    # ----------------------------------------------------------------
    section("1. Today's Full Schedule")
    scheduler = Scheduler(owner)
    scheduler.generate_schedule()
    print(scheduler.get_summary())

    # ----------------------------------------------------------------
    # 2. sort_by_time demo — raw unsorted vs sorted
    # ----------------------------------------------------------------
    section("2. sort_by_time — all Mochi tasks ordered chronologically")
    time_sorted = scheduler.sort_by_time(mochi.tasks)
    for t in time_sorted:
        print(f"  {t}")

    # ----------------------------------------------------------------
    # 3. filter_tasks demos
    # ----------------------------------------------------------------
    section("3a. filter_tasks — only Mochi's tasks")
    mochi_only = scheduler.filter_tasks(scheduler.schedule, pet_name="Mochi")
    for t in mochi_only:
        print(f"  {t}")

    section("3b. filter_tasks — only 'walk' category across all pets")
    walks = scheduler.filter_tasks(scheduler.schedule, category="walk")
    for t in walks:
        print(f"  {t}")

    section("3c. filter_tasks — pending (not completed) tasks")
    pending = scheduler.filter_tasks(scheduler.schedule, completed=False)
    print(f"  {len(pending)} pending task(s)")

    # ----------------------------------------------------------------
    # 4. Recurring task auto-scheduling via timedelta
    # ----------------------------------------------------------------
    section("4. Recurring task — mark_complete then check next_due_date")
    walk = mochi.tasks[2]  # "Morning walk" (recurring=True)
    print(f"  Before: is_due_today={walk.is_due_today()}, next_due_date={walk.next_due_date}")
    walk.mark_complete()
    print(f"  After:  completed={walk.completed}, next_due_date={walk.next_due_date}")
    print(f"  is_due_today (should be False until tomorrow) = {walk.is_due_today()}")

    # ----------------------------------------------------------------
    # 5. Conflict detection warnings
    # ----------------------------------------------------------------
    section("5. Conflict detection warnings")
    warnings = scheduler.conflict_warnings()
    if warnings:
        for w in warnings:
            print(f"  {w}")
    else:
        print("  No conflicts detected.")


if __name__ == "__main__":
    main()
