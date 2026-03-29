# PawPal+ (Module 2 Project)

You are building **PawPal+**, a Streamlit app that helps a pet owner plan care tasks for their pet.

## Scenario

A busy pet owner needs help staying consistent with pet care. They want an assistant that can:

- Track pet care tasks (walks, feeding, meds, enrichment, grooming, etc.)
- Consider constraints (time available, priority, owner preferences)
- Produce a daily plan and explain why it chose that plan

Your job is to design the system first (UML), then implement the logic in Python, then connect it to the Streamlit UI.

## What you will build

Your final app should:

- Let a user enter basic owner + pet info
- Let a user add/edit tasks (duration + priority at minimum)
- Generate a daily schedule/plan based on constraints and priorities
- Display the plan clearly (and ideally explain the reasoning)
- Include tests for the most important scheduling behaviors

## Smarter Scheduling

PawPal+ includes four algorithmic features that make the daily plan intelligent:

| Feature | How it works |
|---------|-------------|
| **Sort by priority** | Tasks are ranked high → medium → low, then by `due_time` within each tier, so the most urgent items always appear first. |
| **Sort by time** | A separate `sort_by_time()` pass reorders the final accepted schedule chronologically so the output reads like a real itinerary. |
| **Filter tasks** | `filter_tasks()` accepts any combination of `pet_name`, `completed`, and `category` keyword filters, making it easy to answer questions like "what walks are still pending for Mochi?" |
| **Recurring tasks** | When a recurring task is marked complete, `timedelta(days=1)` schedules its next occurrence for tomorrow. It disappears from today's list immediately and reappears automatically the next day. |
| **Conflict detection** | The scheduler compares every pair of timed tasks and flags any whose time windows overlap (`[start, start + duration)`). Warnings are returned as plain strings so the UI can display them without crashing. |

## Getting started

### Setup

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### Suggested workflow

1. Read the scenario carefully and identify requirements and edge cases.
2. Draft a UML diagram (classes, attributes, methods, relationships).
3. Convert UML into Python class stubs (no logic yet).
4. Implement scheduling logic in small increments.
5. Add tests to verify key behaviors.
6. Connect your logic to the Streamlit UI in `app.py`.
7. Refine UML so it matches what you actually built.
