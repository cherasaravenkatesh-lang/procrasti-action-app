import streamlit as st
import database as db
import pandas as pd
from datetime import datetime, timedelta
import time
import json

# --- Page Configuration ---
st.set_page_config(
    page_title="Procrasti-Action",
    page_icon="🚀",
    layout="wide"
)

# --- Initialize Database ---
db.setup_database()

# --- Pomodoro Timer State ---
if 'pomodoro_mode' not in st.session_state:
    st.session_state.pomodoro_mode = "Work"  # Work, Short Break, Long Break
if 'pomodoro_seconds' not in st.session_state:
    st.session_state.pomodoro_seconds = 25 * 60
if 'pomodoro_running' not in st.session_state:
    st.session_state.pomodoro_running = False
if 'pomodoro_sessions' not in st.session_state:
    st.session_state.pomodoro_sessions = 0

# --- Helper Functions ---
def format_date(date_str):
    if date_str:
        return datetime.fromisoformat(date_str).strftime("%a, %b %d, %Y")
    return "No date"

def check_reminders(tasks):
    now = datetime.now()
    for task in tasks:
        if task['due_date'] and task['status'] != 'Completed':
            due = datetime.fromisoformat(task['due_date'])
            if now.date() == due.date() and now < due:
                 st.toast(f"🔔 Reminder: '{task['title']}' is due today!", icon="🔔")
            elif due < now:
                 st.toast(f"🚨 Overdue: '{task['title']}' was due on {format_date(task['due_date'])}", icon="🚨")

# --- Sidebar for Pomodoro and Quick Add ---
with st.sidebar:
    st.title("Procrasti-Action")
    st.image("https://img.icons8.com/plasticine/100/000000/rocket.png", width=100) # Placeholder logo
    
    st.header("🍅 Pomodoro Timer")
    
    # Pomodoro settings
    work_mins = st.number_input('Work Minutes', value=25, min_value=1, max_value=60)
    short_break_mins = st.number_input('Short Break Minutes', value=5, min_value=1, max_value=30)
    long_break_mins = st.number_input('Long Break Minutes', value=15, min_value=1, max_value=60)
    
    timer_placeholder = st.empty()
    
    col1, col2, col3 = st.columns(3)
    if col1.button("Start", use_container_width=True, disabled=st.session_state.pomodoro_running):
        st.session_state.pomodoro_running = True
        st.session_state.pomodoro_mode = "Work"
        st.session_state.pomodoro_seconds = work_mins * 60
        st.rerun()

    if col2.button("Pause", use_container_width=True, disabled=not st.session_state.pomodoro_running):
        st.session_state.pomodoro_running = False
        st.rerun()

    if col3.button("Reset", use_container_width=True):
        st.session_state.pomodoro_running = False
        st.session_state.pomodoro_mode = "Work"
        st.session_state.pomodoro_seconds = work_mins * 60
        st.session_state.pomodoro_sessions = 0
        st.rerun()

    if st.session_state.pomodoro_running:
        while st.session_state.pomodoro_seconds > 0 and st.session_state.pomodoro_running:
            mins, secs = divmod(st.session_state.pomodoro_seconds, 60)
            timer_placeholder.metric(f"🕒 {st.session_state.pomodoro_mode}", f"{mins:02d}:{secs:02d}")
            time.sleep(1)
            st.session_state.pomodoro_seconds -= 1
        
        if st.session_state.pomodoro_running: # If timer finished naturally
            st.session_state.pomodoro_running = False
            st.balloons()
            if st.session_state.pomodoro_mode == "Work":
                st.session_state.pomodoro_sessions += 1
                if st.session_state.pomodoro_sessions % 4 == 0:
                    st.session_state.pomodoro_mode = "Long Break"
                    st.session_state.pomodoro_seconds = long_break_mins * 60
                else:
                    st.session_state.pomodoro_mode = "Short Break"
                    st.session_state.pomodoro_seconds = short_break_mins * 60
            else: # If a break finishes
                st.session_state.pomodoro_mode = "Work"
                st.session_state.pomodoro_seconds = work_mins * 60
            st.rerun()
    else:
        mins, secs = divmod(st.session_state.pomodoro_seconds, 60)
        timer_placeholder.metric(f"🕒 {st.session_state.pomodoro_mode}", f"{mins:02d}:{secs:02d}")
        
    st.info(f"Completed Sessions: {st.session_state.pomodoro_sessions}")

# --- Main App Interface ---
tab1, tab2, tab3, tab4 = st.tabs(["🎯 Dashboard", "📝 All Tasks", "🗓️ Calendar", "👥 People"])

# Fetch all data once
tasks = db.get_all_tasks()
people = db.get_all_people()

# Check reminders on each run
check_reminders(tasks)

with tab1:
    st.header("🎯 Dashboard")
    st.write(f"Hello! Today is **{datetime.now().strftime('%A, %B %d')}**. You have **{len([t for t in tasks if t['status'] != 'Completed'])}** active tasks.")
    
    col1, col2, col3 = st.columns(3)
    
    today = datetime.now().date()
    
    with col1:
        st.subheader("🔥 Due Today")
        today_tasks = [t for t in tasks if t['due_date'] and datetime.fromisoformat(t['due_date']).date() == today and t['status'] != 'Completed']
        if today_tasks:
            for task in today_tasks:
                st.checkbox(f"{task['title']}", key=f"dash_done_{task['id']}")
        else:
            st.write("No tasks due today. Time to plan or relax!")

    with col2:
        st.subheader("⚠️ Overdue")
        overdue_tasks = [t for t in tasks if t['due_date'] and datetime.fromisoformat(t['due_date']).date() < today and t['status'] != 'Completed']
        if overdue_tasks:
            for task in overdue_tasks:
                st.error(f"**{task['title']}** - Due: {format_date(task['due_date'])}")
        else:
            st.write("Nothing overdue. Great job!")

    with col3:
        st.subheader("🛑 Blocked")
        blocked_tasks = [t for t in tasks if t['status'] == 'Blocked']
        if blocked_tasks:
            for task in blocked_tasks:
                st.warning(f"**{task['title']}** - Reason: {task['blocked_reason'] or 'Not specified'}")
        else:
            st.write("No blocked tasks!")

with tab2:
    st.header("📝 All Tasks")

    # --- Add New Task Form ---
    with st.expander("➕ Add a New Action Item"):
        with st.form("new_task_form", clear_on_submit=True):
            title = st.text_input("Task Title *", placeholder="e.g., Finalize project report")
            due_date = st.date_input("Due Date", value=None)
            notes = st.text_area("Context & Notes")
            questions = st.text_area("Questions to Ask", placeholder="e.g., Who is the final approver?")
            subtasks = st.text_area("Sub-tasks (one per line)")
            
            submitted = st.form_submit_button("Add Task")
            if submitted:
                if not title:
                    st.error("Task Title is required.")
                else:
                    db.add_task(title, str(due_date) if due_date else None, notes, questions, subtasks)
                    st.success(f"Added task: {title}")
                    st.rerun()
    
    # --- Task Display ---
    st.subheader("Your Action Items")
    
    filter_status = st.multiselect("Filter by status:", options=["To-Do", "In Progress", "Blocked", "Completed"], default=["To-Do", "In Progress", "Blocked"])
    
    for task in tasks:
        if task['status'] in filter_status:
            with st.expander(f"{'✅' if task['status'] == 'Completed' else '◻️'} **{task['title']}** (Due: {format_date(task['due_date'])})"):
                
                # Use a form for each task to manage its state
                with st.form(key=f"form_{task['id']}"):
                    new_title = st.text_input("Title", value=task['title'], key=f"title_{task['id']}")
                    
                    cols = st.columns(2)
                    new_status = cols[0].selectbox("Status", options=["To-Do", "In Progress", "Blocked", "Completed"], index=["To-Do", "In Progress", "Blocked", "Completed"].index(task['status']), key=f"status_{task['id']}")
                    
                    due_date_val = datetime.fromisoformat(task['due_date']) if task['due_date'] else None
                    new_due_date = cols[1].date_input("Due Date", value=due_date_val, key=f"date_{task['id']}")

                    new_notes = st.text_area("Notes", value=task['notes'], key=f"notes_{task['id']}")
                    new_questions = st.text_area("Questions", value=task['questions'], key=f"questions_{task['id']}")

                    new_blocked_reason = task['blocked_reason']
                    if new_status == 'Blocked':
                        new_blocked_reason = st.text_input("Reason for being blocked?", value=task.get('blocked_reason', ''), key=f"blocked_{task['id']}")

                    st.write("**Sub-tasks:**")
                    subtasks_list = json.loads(task['subtasks']) if task['subtasks'] else []
                    
                    for i, subtask in enumerate(subtasks_list):
                        subtasks_list[i]['done'] = st.checkbox(subtask['text'], value=subtask['done'], key=f"sub_{task['id']}_{i}")

                    # --- Action Buttons ---
                    action_cols = st.columns(2)
                    if action_cols[0].form_submit_button("💾 Save Changes", use_container_width=True):
                        db.update_task(task['id'], new_title, new_status, str(new_due_date) if new_due_date else None, new_notes, new_questions, subtasks_list, new_blocked_reason)
                        st.success(f"Updated '{new_title}'")
                        st.rerun()

                    if action_cols[1].form_submit_button("🗑️ Delete", type="primary", use_container_width=True):
                        db.delete_task(task['id'])
                        st.warning(f"Deleted '{task['title']}'")
                        st.rerun()

with tab3:
    st.header("🗓️ Calendar View")
    st.write("This is a simplified calendar view showing tasks with due dates.")

    # We use pandas to create a timeline that Streamlit can display
    task_data = []
    for task in tasks:
        if task['due_date']:
            task_data.append(dict(
                Task=task['title'], 
                Start=datetime.fromisoformat(task['due_date']), 
                Finish=datetime.fromisoformat(task['due_date']) + timedelta(hours=1), # a small duration for visualization
                Status=task['status']
            ))
    
    if task_data:
        df = pd.DataFrame(task_data)
        st.timeline(df, x_start="Start", x_end="Finish", y="Task", group="Status")
    else:
        st.info("No tasks with due dates to display on the calendar.")

with tab4:
    st.header("👥 People & Interactions")

    with st.expander("Add New Person"):
        with st.form("new_person_form", clear_on_submit=True):
            person_name = st.text_input("Person's Name")
            if st.form_submit_button("Add Person"):
                if person_name:
                    try:
                        db.add_person(person_name)
                        st.success(f"Added {person_name}.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Could not add {person_name}. They may already exist.")
                else:
                    st.warning("Please enter a name.")

    selected_person_name = st.selectbox("Select a person to view/edit their interaction log:", [p['name'] for p in people])
    
    if selected_person_name:
        person = next((p for p in people if p['name'] == selected_person_name), None)
        if person:
            st.subheader(f"Log for {person['name']}")
            with st.form(key=f"person_log_{person['id']}"):
                log_content = st.text_area(
                    "Interaction Log (add new notes at the top)", 
                    value=person['interaction_log'], 
                    height=300
                )
                if st.form_submit_button("Save Log"):
                    db.update_person_log(person['id'], log_content)
                    st.success("Log updated!")
                    st.rerun()
