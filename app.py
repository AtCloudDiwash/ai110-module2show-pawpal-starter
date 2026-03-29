"""
app.py — Streamlit UI for PawPal+
Phase 3: fully wired to pawpal_system.py backend.
"""

import streamlit as st
from datetime import time

# Step 1: Import backend classes
from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="centered")
st.title("🐾 PawPal+")

# ---------------------------------------------------------------------------
# Step 2: Application "memory" — persist Owner in session_state so data
#         survives every Streamlit re-run (form submit, button click, etc.)
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None   # not set up yet

# ---------------------------------------------------------------------------
# Owner setup (shown only until an owner is created)
# ---------------------------------------------------------------------------
if st.session_state.owner is None:
    st.subheader("Welcome! Let's set up your profile.")
    with st.form("owner_form"):
        owner_name = st.text_input("Your name", value="Jordan")
        owner_email = st.text_input("Email (optional)", value="")
        budget = st.number_input(
            "Available time for pet care today (minutes)",
            min_value=10, max_value=1440, value=120
        )
        submitted = st.form_submit_button("Create profile")

    if submitted:
        st.session_state.owner = Owner(
            name=owner_name,
            email=owner_email,
            available_minutes_per_day=int(budget),
        )
        st.rerun()
    st.stop()   # don't render rest of the app until owner exists

# Convenience reference
owner: Owner = st.session_state.owner

st.markdown(f"**Owner:** {owner.name}  |  **Daily budget:** {owner.available_minutes_per_day} min")
st.divider()

# ---------------------------------------------------------------------------
# Step 3a: Add a Pet — wired to Owner.add_pet()
# ---------------------------------------------------------------------------
with st.expander("Add a Pet", expanded=len(owner.pets) == 0):
    with st.form("add_pet_form"):
        col1, col2 = st.columns(2)
        with col1:
            pet_name    = st.text_input("Pet name", value="Mochi")
            pet_species = st.selectbox("Species", ["dog", "cat", "other"])
        with col2:
            pet_breed = st.text_input("Breed (optional)", value="")
            pet_age   = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
        add_pet_btn = st.form_submit_button("Add pet")

    if add_pet_btn:
        existing_names = [p.name.lower() for p in owner.pets]
        if pet_name.strip().lower() in existing_names:
            st.warning(f"A pet named '{pet_name}' is already registered.")
        else:
            owner.add_pet(Pet(
                name=pet_name.strip(),
                species=pet_species,
                breed=pet_breed.strip(),
                age=int(pet_age),
            ))
            st.success(f"Added {pet_name}!")
            st.rerun()

# Show registered pets
if owner.pets:
    st.subheader("Your Pets")
    for pet in owner.pets:
        st.markdown(f"- **{pet.name}** ({pet.species}{', ' + pet.breed if pet.breed else ''}, age {pet.age})")
else:
    st.info("No pets yet. Add one above.")
    st.stop()

st.divider()

# ---------------------------------------------------------------------------
# Step 3b: Add a Task — wired to Pet.add_task()
# ---------------------------------------------------------------------------
st.subheader("Add a Care Task")
with st.form("add_task_form"):
    pet_names = [p.name for p in owner.pets]
    selected_pet = st.selectbox("Assign to pet", pet_names)

    col1, col2, col3 = st.columns(3)
    with col1:
        task_title    = st.text_input("Task title", value="Morning walk")
        task_category = st.selectbox("Category", ["walk", "feeding", "medication", "appointment", "grooming", "enrichment"])
    with col2:
        task_duration = st.number_input("Duration (minutes)", min_value=1, max_value=240, value=20)
        task_priority = st.selectbox("Priority", ["high", "medium", "low"])
    with col3:
        use_time   = st.checkbox("Set a due time?")
        task_hour  = st.number_input("Hour (0–23)", min_value=0, max_value=23, value=8, disabled=not use_time)
        task_min   = st.number_input("Minute (0–59)", min_value=0, max_value=59, value=0, disabled=not use_time)

    task_recurring = st.checkbox("Recurring daily?")
    task_notes     = st.text_area("Notes (optional)", value="", height=60)
    add_task_btn   = st.form_submit_button("Add task")

if add_task_btn:
    due_time = time(int(task_hour), int(task_min)) if use_time else None
    new_task = Task(
        title=task_title.strip(),
        category=task_category,
        duration_minutes=int(task_duration),
        priority=task_priority,
        due_time=due_time,
        recurring=task_recurring,
        notes=task_notes.strip(),
    )
    # Wire to Pet.add_task()
    target_pet = next(p for p in owner.pets if p.name == selected_pet)
    target_pet.add_task(new_task)
    st.success(f"Task '{task_title}' added to {selected_pet}!")
    st.rerun()

# Show current tasks per pet
st.divider()
st.subheader("Current Tasks")
any_tasks = False
for pet in owner.pets:
    if pet.tasks:
        any_tasks = True
        st.markdown(f"**{pet.name}**")
        for task in pet.tasks:
            status = "✓" if task.completed else "○"
            time_str = task.due_time.strftime("%I:%M %p") if task.due_time else "anytime"
            st.markdown(
                f"&nbsp;&nbsp;[{status}] {task.title} — {task.category}, "
                f"{task.duration_minutes} min, {task.priority}, @ {time_str}"
            )
if not any_tasks:
    st.info("No tasks added yet.")

st.divider()

# ---------------------------------------------------------------------------
# Step 3c: Generate Schedule — wired to Scheduler.generate_schedule()
# ---------------------------------------------------------------------------
st.subheader("Generate Today's Schedule")
if st.button("Generate schedule"):
    scheduler = Scheduler(owner)
    scheduler.generate_schedule()

    if not scheduler.schedule:
        st.warning("No tasks are due today (all completed or none added).")
    else:
        st.success(f"Scheduled {len(scheduler.schedule)} task(s) — {sum(t.duration_minutes for t in scheduler.schedule)} min total")

        for i, task in enumerate(scheduler.schedule, start=1):
            time_str = task.due_time.strftime("%I:%M %p") if task.due_time else "anytime"
            priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(task.priority, "⚪")
            st.markdown(
                f"**{i}. {task.title}** {priority_color}  \n"
                f"&nbsp;&nbsp;{task.category} | {task.duration_minutes} min | {time_str}"
                + (f"  \n&nbsp;&nbsp;_{task.notes}_" if task.notes else "")
            )

        # Conflict warnings
        conflicts = scheduler.detect_conflicts()
        if conflicts:
            st.warning(f"⚠ {len(conflicts)} time conflict(s) detected:")
            for a, b in conflicts:
                st.markdown(f"- **{a.title}** overlaps with **{b.title}**")

        # Deferred tasks
        all_today = []
        for pet in owner.pets:
            all_today.extend(pet.get_tasks_for_today())
        deferred = [t for t in all_today if t not in scheduler.schedule]
        if deferred:
            with st.expander("Tasks deferred (over time budget)"):
                for t in deferred:
                    st.markdown(f"- {t.title} ({t.duration_minutes} min, {t.priority})")

st.divider()

# Reset button (bottom of page)
if st.button("Reset app"):
    st.session_state.clear()
    st.rerun()
