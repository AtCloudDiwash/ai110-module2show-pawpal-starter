"""
app.py — Streamlit UI for PawPal+
Phase 6: polished UI reflecting the full algorithmic layer.
"""

import streamlit as st
from datetime import time

from pawpal_system import Owner, Pet, Task, Scheduler

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ---------------------------------------------------------------------------
# Session state bootstrap
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    st.session_state.owner = None

# ---------------------------------------------------------------------------
# Owner setup screen (shown once)
# ---------------------------------------------------------------------------
if st.session_state.owner is None:
    st.title("🐾 Welcome to PawPal+")
    st.caption("A smart daily care planner for your pets.")
    with st.form("owner_form"):
        col1, col2, col3 = st.columns(3)
        with col1:
            owner_name = st.text_input("Your name", value="Jordan")
        with col2:
            owner_email = st.text_input("Email (optional)", value="")
        with col3:
            budget = st.number_input(
                "Daily care budget (minutes)",
                min_value=10, max_value=1440, value=120,
                help="Total minutes available for pet care today."
            )
        submitted = st.form_submit_button("Create profile", use_container_width=True)

    if submitted:
        st.session_state.owner = Owner(
            name=owner_name.strip(),
            email=owner_email.strip(),
            available_minutes_per_day=int(budget),
        )
        st.rerun()
    st.stop()

# ---------------------------------------------------------------------------
# Sidebar — owner summary + view filters
# ---------------------------------------------------------------------------
owner: Owner = st.session_state.owner

with st.sidebar:
    st.header("🐾 PawPal+")
    st.markdown(f"**Owner:** {owner.name}")
    st.markdown(f"**Daily budget:** {owner.available_minutes_per_day} min")
    st.divider()

    st.subheader("Filter task view")
    filter_pet = st.selectbox(
        "Pet",
        ["All pets"] + [p.name for p in owner.pets],
        key="filter_pet",
    )
    filter_cat = st.selectbox(
        "Category",
        ["All categories", "walk", "feeding", "medication",
         "appointment", "grooming", "enrichment"],
        key="filter_cat",
    )
    filter_status = st.radio(
        "Status",
        ["All", "Pending", "Completed"],
        key="filter_status",
    )
    st.divider()
    if st.button("Reset app", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# ---------------------------------------------------------------------------
# Main area header
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")
total_tasks = sum(len(p.tasks) for p in owner.pets)
col_m1, col_m2, col_m3 = st.columns(3)
col_m1.metric("Pets registered", len(owner.pets))
col_m2.metric("Total tasks", total_tasks)
col_m3.metric("Budget remaining", f"{owner.available_minutes_per_day} min")

st.divider()

# ---------------------------------------------------------------------------
# Add a Pet
# ---------------------------------------------------------------------------
with st.expander("➕ Add a Pet", expanded=len(owner.pets) == 0):
    with st.form("add_pet_form"):
        c1, c2 = st.columns(2)
        with c1:
            pet_name    = st.text_input("Pet name", value="Mochi")
            pet_species = st.selectbox("Species", ["dog", "cat", "other"])
        with c2:
            pet_breed = st.text_input("Breed (optional)")
            pet_age   = st.number_input("Age (years)", min_value=0, max_value=30, value=2)
        if st.form_submit_button("Add pet", use_container_width=True):
            if pet_name.strip().lower() in [p.name.lower() for p in owner.pets]:
                st.warning(f"'{pet_name}' is already registered.")
            else:
                owner.add_pet(Pet(
                    name=pet_name.strip(), species=pet_species,
                    breed=pet_breed.strip(), age=int(pet_age),
                ))
                st.rerun()

if not owner.pets:
    st.info("No pets yet — add one above to get started.")
    st.stop()

# ---------------------------------------------------------------------------
# Add a Care Task
# ---------------------------------------------------------------------------
with st.expander("📋 Add a Care Task"):
    with st.form("add_task_form"):
        selected_pet = st.selectbox("Assign to", [p.name for p in owner.pets])
        c1, c2, c3 = st.columns(3)
        with c1:
            task_title    = st.text_input("Title", value="Morning walk")
            task_category = st.selectbox(
                "Category",
                ["walk", "feeding", "medication", "appointment", "grooming", "enrichment"]
            )
        with c2:
            task_duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
            task_priority = st.selectbox("Priority", ["high", "medium", "low"])
        with c3:
            use_time  = st.checkbox("Set a due time?")
            task_hour = st.number_input("Hour (0–23)", min_value=0, max_value=23,
                                        value=8, disabled=not use_time)
            task_min  = st.number_input("Minute (0–59)", min_value=0, max_value=59,
                                        value=0, disabled=not use_time)
        task_recurring = st.checkbox("Recurring daily?")
        task_notes     = st.text_area("Notes (optional)", height=60)

        if st.form_submit_button("Add task", use_container_width=True):
            due = time(int(task_hour), int(task_min)) if use_time else None
            target = next(p for p in owner.pets if p.name == selected_pet)
            target.add_task(Task(
                title=task_title.strip(), category=task_category,
                duration_minutes=int(task_duration), priority=task_priority,
                due_time=due, recurring=task_recurring, notes=task_notes.strip(),
            ))
            st.rerun()

# ---------------------------------------------------------------------------
# Current Tasks (with sidebar filters applied)
# ---------------------------------------------------------------------------
st.subheader("Current Tasks")

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}
STATUS_ICON   = {"done": "✅", "pending": "○"}

all_tasks_flat: list[tuple[str, Task]] = []
for pet in owner.pets:
    for task in pet.tasks:
        all_tasks_flat.append((pet.name, task))

# Apply sidebar filters
def _apply_filters(pairs):
    result = pairs
    if filter_pet != "All pets":
        result = [(n, t) for n, t in result if n == filter_pet]
    if filter_cat != "All categories":
        result = [(n, t) for n, t in result if t.category == filter_cat]
    if filter_status == "Pending":
        result = [(n, t) for n, t in result if not t.completed]
    elif filter_status == "Completed":
        result = [(n, t) for n, t in result if t.completed]
    return result

filtered = _apply_filters(all_tasks_flat)

if not filtered:
    st.info("No tasks match the current filters." if all_tasks_flat else "No tasks added yet.")
else:
    rows = []
    for pet_label, task in filtered:
        rows.append({
            "Pet":      pet_label,
            "Task":     task.title,
            "Category": task.category,
            "Priority": f"{PRIORITY_ICON.get(task.priority, '')} {task.priority}",
            "Duration": f"{task.duration_minutes} min",
            "Due":      task.due_time.strftime("%I:%M %p") if task.due_time else "anytime",
            "Recurring": "yes" if task.recurring else "no",
            "Status":   "✅ done" if task.completed else "○ pending",
        })
    st.dataframe(rows, use_container_width=True, hide_index=True)

st.divider()

# ---------------------------------------------------------------------------
# Generate Today's Schedule
# ---------------------------------------------------------------------------
st.subheader("Generate Today's Schedule")

if st.button("Generate schedule", use_container_width=False, type="primary"):
    scheduler = Scheduler(owner)
    scheduler.generate_schedule()
    st.session_state["last_schedule"] = scheduler

# Display last generated schedule (persists across re-runs)
if "last_schedule" in st.session_state:
    scheduler: Scheduler = st.session_state["last_schedule"]

    if not scheduler.schedule:
        st.warning("No tasks are due today — all done or none added yet.")
    else:
        # ---- Summary metrics ----
        total_min   = sum(t.duration_minutes for t in scheduler.schedule)
        n_conflicts = len(scheduler.detect_conflicts())
        s1, s2, s3 = st.columns(3)
        s1.metric("Scheduled tasks", len(scheduler.schedule))
        s2.metric("Total time",      f"{total_min} min")
        s3.metric("Conflicts",       n_conflicts, delta=n_conflicts or None,
                  delta_color="inverse")

        # ---- Conflict warnings (prominent) ----
        for warning in scheduler.conflict_warnings():
            st.error(warning)

        # ---- Schedule table ----
        st.markdown("#### Ordered care plan")
        sched_rows = []
        for i, task in enumerate(scheduler.schedule, start=1):
            sched_rows.append({
                "#":        i,
                "Pet":      task.pet_name,
                "Task":     task.title,
                "Category": task.category,
                "Priority": f"{PRIORITY_ICON.get(task.priority, '')} {task.priority}",
                "Time":     task.due_time.strftime("%I:%M %p") if task.due_time else "anytime",
                "Duration": f"{task.duration_minutes} min",
                "Notes":    task.notes or "",
            })
        st.dataframe(sched_rows, use_container_width=True, hide_index=True)

        # ---- Deferred tasks ----
        all_today = [t for p in owner.pets for t in p.get_tasks_for_today()]
        deferred  = [t for t in all_today if t not in scheduler.schedule]
        if deferred:
            with st.expander(f"⏳ {len(deferred)} task(s) deferred (over budget)"):
                for t in deferred:
                    st.markdown(
                        f"- **{t.title}** ({t.pet_name}) — "
                        f"{t.duration_minutes} min, priority: {t.priority}"
                    )
                st.caption(
                    "These tasks didn't fit in your daily budget. "
                    "Consider raising your budget or lowering task durations."
                )
