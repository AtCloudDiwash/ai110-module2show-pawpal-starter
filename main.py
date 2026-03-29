"""
main.py — CLI demo script for PawPal+
Run: python main.py
"""

from datetime import time
from pawpal_system import Owner, Pet, Task, Scheduler


def main():
    # --- Owner ---
    owner = Owner(name="Jordan", email="jordan@example.com", available_minutes_per_day=120)

    # --- Pets ---
    mochi = Pet(name="Mochi", species="dog", breed="Shiba Inu", age=3)
    luna  = Pet(name="Luna",  species="cat", breed="Tabby",     age=5)

    owner.add_pet(mochi)
    owner.add_pet(luna)

    # --- Tasks for Mochi ---
    mochi.add_task(Task(
        title="Morning walk",
        category="walk",
        duration_minutes=30,
        priority="high",
        due_time=time(7, 0),
        recurring=True,
    ))
    mochi.add_task(Task(
        title="Breakfast feeding",
        category="feeding",
        duration_minutes=10,
        priority="high",
        due_time=time(7, 30),
        recurring=True,
    ))
    mochi.add_task(Task(
        title="Flea medication",
        category="medication",
        duration_minutes=5,
        priority="medium",
        due_time=time(8, 0),
        recurring=False,
        notes="Apply topical treatment between shoulder blades",
    ))
    mochi.add_task(Task(
        title="Evening walk",
        category="walk",
        duration_minutes=40,
        priority="high",
        due_time=time(18, 0),
        recurring=True,
    ))

    # --- Tasks for Luna ---
    luna.add_task(Task(
        title="Breakfast feeding",
        category="feeding",
        duration_minutes=5,
        priority="high",
        due_time=time(7, 15),
        recurring=True,
    ))
    luna.add_task(Task(
        title="Vet appointment",
        category="appointment",
        duration_minutes=60,
        priority="high",
        due_time=time(10, 0),
        recurring=False,
        notes="Annual check-up — bring vaccination records",
    ))
    luna.add_task(Task(
        title="Brush coat",
        category="grooming",
        duration_minutes=15,
        priority="low",
        recurring=True,
    ))

    # --- Schedule ---
    scheduler = Scheduler(owner)
    scheduler.generate_schedule()

    print(scheduler.get_summary())

    # Show what was skipped due to time budget
    all_today = []
    for pet in owner.pets:
        all_today.extend(pet.get_tasks_for_today())
    skipped = [t for t in all_today if t not in scheduler.schedule]
    if skipped:
        print("\n  Tasks deferred (over time budget):")
        for t in skipped:
            print(f"    - {t.title} ({t.duration_minutes} min, priority: {t.priority})")


if __name__ == "__main__":
    main()
