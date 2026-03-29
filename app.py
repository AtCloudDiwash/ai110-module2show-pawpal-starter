"""
app.py — Streamlit UI for PawPal+
Challenges: JSON persistence, weighted scheduling mode, next-slot finder.
"""

import os
import streamlit as st
from datetime import time

from pawpal_system import Owner, Pet, Task, Scheduler

DATA_FILE = "data.json"

st.set_page_config(page_title="PawPal+", page_icon="🐾", layout="wide")

# ---------------------------------------------------------------------------
# Session state bootstrap — load from data.json if it exists
# ---------------------------------------------------------------------------
if "owner" not in st.session_state:
    if os.path.exists(DATA_FILE):
        try:
            st.session_state.owner = Owner.load_from_json(DATA_FILE)
        except Exception:
            st.session_state.owner = None
    else:
        st.session_state.owner = None


def _save() -> None:
    """Persist current owner state to data.json after every mutation."""
    if st.session_state.owner is not None:
        st.session_state.owner.save_to_json(DATA_FILE)


# ---------------------------------------------------------------------------
# Owner setup screen (shown once, skipped if loaded from file)
# ---------------------------------------------------------------------------
if st.session_state.owner is None:
    st.title("🐾 Welcome to PawPal+")
    st.caption("A smart daily care planner for your pets.")
    with st.form("owner_form"):
        c1, c2, c3 = st.columns(3)
        with c1:
            owner_name = st.text_input("Your name", value="Jordan")
        with c2:
            owner_email = st.text_input("Email (optional)")
        with c3:
            budget = st.number_input(
                "Daily care budget (minutes)",
                min_value=10, max_value=1440, value=120,
            )
        if st.form_submit_button("Create profile", use_container_width=True):
            st.session_state.owner = Owner(
                name=owner_name.strip(),
                email=owner_email.strip(),
                available_minutes_per_day=int(budget),
            )
            _save()
            st.rerun()
    st.stop()

owner: Owner = st.session_state.owner

# ---------------------------------------------------------------------------
# Sidebar — owner summary, filters, persistence controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.header("🐾 PawPal+")
    st.markdown(f"**Owner:** {owner.name}")
    st.markdown(f"**Daily budget:** {owner.available_minutes_per_day} min")

    if os.path.exists(DATA_FILE):
        st.caption(f"💾 Auto-saved to `{DATA_FILE}`")

    st.divider()
    st.subheader("Filter task view")
    filter_pet    = st.selectbox("Pet",      ["All pets"]        + [p.name for p in owner.pets])
    filter_cat    = st.selectbox("Category", ["All categories",
                                              "walk", "feeding", "medication",
                                              "appointment", "grooming", "enrichment"])
    filter_status = st.radio("Status", ["All", "Pending", "Completed"])

    st.divider()
    st.subheader("Scheduling mode")
    sched_mode = st.radio(
        "Algorithm",
        ["Standard (priority tiers)", "Weighted (urgency score)"],
        help=(
            "Standard: high → medium → low tiers, then by time.\n\n"
            "Weighted: composite score = priority + category urgency + time bonus. "
            "Finer-grained — medications rank above walks within the same tier."
        ),
    )

    st.divider()
    col_r, col_d = st.columns(2)
    with col_r:
        if st.button("Reset app", use_container_width=True):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            st.session_state.clear()
            st.rerun()
    with col_d:
        if st.button("Clear data", use_container_width=True,
                     help="Delete saved data.json"):
            if os.path.exists(DATA_FILE):
                os.remove(DATA_FILE)
            st.success("data.json deleted.")

# ---------------------------------------------------------------------------
# Header metrics
# ---------------------------------------------------------------------------
st.title("🐾 PawPal+")
total_tasks = sum(len(p.tasks) for p in owner.pets)
m1, m2, m3 = st.columns(3)
m1.metric("Pets registered", len(owner.pets))
m2.metric("Total tasks",     total_tasks)
m3.metric("Daily budget",    f"{owner.available_minutes_per_day} min")

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
            pet_age   = st.number_input("Age", min_value=0, max_value=30, value=2)
        if st.form_submit_button("Add pet", use_container_width=True):
            if pet_name.strip().lower() in [p.name.lower() for p in owner.pets]:
                st.warning(f"'{pet_name}' is already registered.")
            else:
                owner.add_pet(Pet(
                    name=pet_name.strip(), species=pet_species,
                    breed=pet_breed.strip(), age=int(pet_age),
                ))
                _save()
                st.rerun()

if not owner.pets:
    st.info("No pets yet — add one above.")
    st.stop()

# ---------------------------------------------------------------------------
# Add a Care Task
# ---------------------------------------------------------------------------
with st.expander("📋 Add a Care Task"):
    with st.form("add_task_form"):
        sel_pet = st.selectbox("Assign to", [p.name for p in owner.pets])
        c1, c2, c3 = st.columns(3)
        with c1:
            task_title    = st.text_input("Title", value="Morning walk")
            task_category = st.selectbox("Category", [
                "walk", "feeding", "medication",
                "appointment", "grooming", "enrichment",
            ])
        with c2:
            task_duration = st.number_input("Duration (min)", min_value=1, max_value=240, value=20)
            task_priority = st.selectbox("Priority", ["high", "medium", "low"])
        with c3:
            use_time  = st.checkbox("Set a due time?")
            task_hour = st.number_input("Hour (0–23)",  min_value=0, max_value=23, value=8,  disabled=not use_time)
            task_min  = st.number_input("Minute (0–59)", min_value=0, max_value=59, value=0, disabled=not use_time)
        task_recurring = st.checkbox("Recurring daily?")
        task_notes     = st.text_area("Notes (optional)", height=60)

        if st.form_submit_button("Add task", use_container_width=True):
            due = time(int(task_hour), int(task_min)) if use_time else None
            target = next(p for p in owner.pets if p.name == sel_pet)
            target.add_task(Task(
                title=task_title.strip(), category=task_category,
                duration_minutes=int(task_duration), priority=task_priority,
                due_time=due, recurring=task_recurring, notes=task_notes.strip(),
            ))
            _save()
            st.rerun()

# ---------------------------------------------------------------------------
# Current Tasks (sidebar filters applied)
# ---------------------------------------------------------------------------
st.subheader("Current Tasks")

PRIORITY_ICON = {"high": "🔴", "medium": "🟡", "low": "🟢"}

all_pairs = [(p.name, t) for p in owner.pets for t in p.tasks]

def _apply_filters(pairs):
    r = pairs
    if filter_pet    != "All pets":        r = [(n, t) for n, t in r if n == filter_pet]
    if filter_cat    != "All categories":  r = [(n, t) for n, t in r if t.category == filter_cat]
    if filter_status == "Pending":         r = [(n, t) for n, t in r if not t.completed]
    elif filter_status == "Completed":     r = [(n, t) for n, t in r if t.completed]
    return r

filtered = _apply_filters(all_pairs)

if not filtered:
    st.info("No tasks match the current filters." if all_pairs else "No tasks added yet.")
else:
    st.dataframe(
        [{
            "Pet":      n,
            "Task":     t.title,
            "Category": t.category,
            "Priority": f"{PRIORITY_ICON.get(t.priority,'')} {t.priority}",
            "Duration": f"{t.duration_minutes} min",
            "Due":      t.due_time.strftime("%I:%M %p") if t.due_time else "anytime",
            "Recurring": "yes" if t.recurring else "no",
            "Status":   "✅ done" if t.completed else "○ pending",
        } for n, t in filtered],
        use_container_width=True, hide_index=True,
    )

st.divider()

# ---------------------------------------------------------------------------
# Generate Today's Schedule
# ---------------------------------------------------------------------------
st.subheader("Generate Today's Schedule")
weighted_mode = "Weighted" in sched_mode

if st.button("Generate schedule", type="primary"):
    scheduler = Scheduler(owner)
    if weighted_mode:
        scheduler.generate_weighted_schedule()
    else:
        scheduler.generate_schedule()
    st.session_state["last_scheduler"] = scheduler

if "last_scheduler" in st.session_state:
    scheduler: Scheduler = st.session_state["last_scheduler"]

    if not scheduler.schedule:
        st.warning("No tasks are due today — all done or none added yet.")
    else:
        algo_label = "Weighted urgency" if weighted_mode else "Priority tiers"
        total_min  = sum(t.duration_minutes for t in scheduler.schedule)
        n_conflicts = len(scheduler.detect_conflicts())

        s1, s2, s3, s4 = st.columns(4)
        s1.metric("Algorithm",       algo_label)
        s2.metric("Scheduled tasks", len(scheduler.schedule))
        s3.metric("Total time",      f"{total_min} min")
        s4.metric("Conflicts",       n_conflicts,
                  delta=n_conflicts or None, delta_color="inverse")

        # Conflict warnings
        for w in scheduler.conflict_warnings():
            st.error(w)

        # Schedule table — show urgency score in weighted mode
        rows = []
        for i, task in enumerate(scheduler.schedule, start=1):
            row = {
                "#":        i,
                "Pet":      task.pet_name,
                "Task":     task.title,
                "Category": task.category,
                "Priority": f"{PRIORITY_ICON.get(task.priority,'')} {task.priority}",
                "Time":     task.due_time.strftime("%I:%M %p") if task.due_time else "anytime",
                "Duration": f"{task.duration_minutes} min",
            }
            if weighted_mode:
                row["Urgency score"] = scheduler.score_task(task)
            if task.notes:
                row["Notes"] = task.notes
            rows.append(row)
        st.dataframe(rows, use_container_width=True, hide_index=True)

        # Next available slot finder
        with st.expander("🔍 Find next available slot"):
            slot_duration = st.number_input(
                "Task duration (min)", min_value=5, max_value=240, value=30, key="slot_dur"
            )
            slot_earliest_h = st.number_input(
                "Search from hour", min_value=0, max_value=23, value=6, key="slot_h"
            )
            if st.button("Find slot"):
                slot = scheduler.find_next_available_slot(
                    int(slot_duration), earliest=time(int(slot_earliest_h), 0)
                )
                if slot:
                    st.success(f"Next free {slot_duration}-min slot: **{slot.strftime('%I:%M %p')}**")
                else:
                    st.warning("No free slot found before midnight.")

        # Deferred tasks
        all_today = [t for p in owner.pets for t in p.get_tasks_for_today()]
        deferred  = [t for t in all_today if t not in scheduler.schedule]
        if deferred:
            with st.expander(f"⏳ {len(deferred)} task(s) deferred (over budget)"):
                for t in deferred:
                    st.markdown(
                        f"- **{t.title}** ({t.pet_name}) — "
                        f"{t.duration_minutes} min, {t.priority} priority"
                    )
