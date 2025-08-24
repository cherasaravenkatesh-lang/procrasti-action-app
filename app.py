import streamlit as st
import database as db
import pandas as pd
from datetime import datetime
import time
import json
from libsql_client import LibsqlError

# --- Page Config & DB Setup ---
st.set_page_config(page_title="Procrasti-Action", page_icon="✅", layout="wide")
db.setup_database() # This is now a simple, synchronous call

# --- Authentication ---
if 'authenticated' not in st.session_state: st.session_state.authenticated = False

def login_form():
    st.title("Procrasti-Action"); st.markdown("Tame your tasks, master your time.")
    choice = st.selectbox("Login or Signup", ["Login", "Sign Up"], label_visibility="collapsed")
    with st.form("auth_form"):
        st.subheader("Create a New Account" if choice == "Sign Up" else "Log In")
        username = st.text_input("Username"); password = st.text_input("Password", type="password")
        if st.form_submit_button(label=choice):
            if not username or not password: st.error("Username and password are required."); return
            if choice == "Sign Up":
                if db.add_user(username, password): st.success("Account created! Please log in.")
                else: st.error("Username already exists.")
            elif choice == "Login":
                if db.verify_user(username, password):
                    st.session_state.authenticated = True; st.session_state.username = username; st.rerun()
                else: st.error("Invalid username or password.")

if not st.session_state.authenticated:
    login_form()
    st.stop()

# --- Main App ---
current_user = st.session_state.username

# --- Sidebar (Unchanged) ---
with st.sidebar:
    st.title(f"Welcome, {current_user}!");
    if st.button("Logout", use_container_width=True): st.session_state.authenticated = False; st.session_state.username = ""; st.rerun()
    st.divider(); st.header("Focus Timer")
    work_mins = st.slider('Focus Minutes', 1, 60, 25); short_break_mins = st.slider('Short Break', 1, 30, 5)
    timer_placeholder = st.empty(); col1, col2, col3 = st.columns(3)
    if col1.button("Start", use_container_width=True, disabled=st.session_state.pomodoro_running): st.session_state.pomodoro_running = True; st.session_state.pomodoro_mode = "Focus"; st.session_state.pomodoro_seconds = work_mins * 60; st.rerun()
    if col2.button("Pause", use_container_width=True, disabled=not st.session_state.pomodoro_running): st.session_state.pomodoro_running = False; st.rerun()
    if col3.button("Reset", use_container_width=True): st.session_state.pomodoro_running = False; st.session_state.pomodoro_mode = "Focus"; st.session_state.pomodoro_seconds = work_mins * 60; st.session_state.pomodoro_sessions = 0; st.rerun()
    if st.session_state.pomodoro_running:
        while st.session_state.pomodoro_seconds > 0 and st.session_state.pomodoro_running:
            mins, secs = divmod(st.session_state.pomodoro_seconds, 60); timer_placeholder.metric(f"{st.session_state.pomodoro_mode}", f"{mins:02d}:{secs:02d}"); time.sleep(1); st.session_state.pomodoro_seconds -= 1
        if st.session_state.pomoro_running:
            st.session_state.pomoro_running = False; st.toast("Session complete!", icon="🎉")
            st.session_state.pomoro_mode = "Break" if st.session_state.pomoro_mode == "Focus" else "Focus"
            st.session_state.pomoro_seconds = short_break_mins * 60 if st.session_state.pomoro_mode == "Break" else work_mins * 60
            if st.session_state.pomoro_mode == "Focus": st.session_state.pomoro_sessions += 1; st.rerun()
    else: mins, secs = divmod(st.session_state.pomodoro_seconds, 60); timer_placeholder.metric(f"{st.session_state.pomodoro_mode}", f"{mins:02d}:{secs:02d}")
    st.info(f"Completed Sessions: {st.session_state.pomodoro_sessions}")

# --- Data Fetching (Now simple synchronous calls) ---
tasks = db.get_all_tasks(current_user)
people = db.get_all_people(current_user)
people_names = [p['name'] for p in people]

# --- UI Tabs (The code is the same, but the underlying calls are now sync) ---
tab1, tab2, tab3, tab4 = st.tabs(["Dashboard", "All Tasks", "Calendar", "People"])
# ... PASTE THE FULL UI CODE (ALL FOUR `with tabX:` BLOCKS) FROM YOUR LAST WORKING VERSION HERE ...
# The code does not need to change because we are no longer using `await` or `asyncio.run`.
with tab1:
    st.header("Dashboard"); st.write(f"Today is **{datetime.now().strftime('%A, %B %d')}**. You have **{len([t for t in tasks if t['status'] != 'Completed'])}** active tasks.")
    col1, col2 = st.columns(2); today = datetime.now().date()
    with col1:
        st.subheader("Due Today / Overdue");
        due_today = [t for t in tasks if t['due_date'] and datetime.fromisoformat(t['due_date']).date() == today and t['status'] != 'Completed']
        overdue = [t for t in tasks if t['due_date'] and datetime.fromisoformat(t['due_date']).date() < today and t['status'] != 'Completed']
        if not due_today and not overdue: st.success("Nothing is immediately due. Great job!")
        for task in overdue: st.error(f"**{task['title']}** - Was due: {format_date(task['due_date'])}")
        for task in due_today: st.warning(f"**{task['title']}** - Due today")
    with col2:
        st.subheader("Blocked Tasks"); blocked_tasks = [t for t in tasks if t['status'] == 'Blocked']
        if blocked_tasks:
            for task in blocked_tasks: st.info(f"**{task['title']}** - Reason: {task['blocked_reason'] or 'Not specified'}")
        else: st.info("No blocked tasks. Keep up the momentum!")
with tab2:
    st.header("All Tasks")
    with st.expander("Add a New Task"):
        with st.form("new_task_form", clear_on_submit=True):
            title = st.text_input("Task Title *"); due_date = st.date_input("Due Date", value=None); notes = st.text_area("Notes & Context")
            st.markdown("**Recurrence**"); recur_type = st.selectbox("Repeats", ["None", "Weekly", "Monthly", "Specific Days"])
            weekdays_options = []
            if recur_type == "Specific Days": weekdays_options = st.multiselect("On which days?", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"])
            questions = st.text_area("General Questions"); subtasks = st.text_area("Sub-tasks (one per line)")
            st.markdown("**Link People**"); linked_people_names = st.multiselect("Select people to link", options=people_names)
            if st.form_submit_button("Add Task", type="primary"):
                if not title: st.warning("Task Title is required."); st.stop()
                recurrence_rule = None
                if recur_type == 'Weekly': recurrence_rule = 'weekly'
                elif recur_type == 'Monthly': recurrence_rule = 'monthly'
                elif recur_type == 'Specific Days' and weekdays_options:
                    day_map = {"Monday": "M", "Tuesday": "T", "Wednesday": "W", "Thursday": "H", "Friday": "F", "Saturday": "S", "Sunday": "U"}
                    rule_str = "".join([day_map[day] for day in weekdays_options]); recurrence_rule = f'weekdays:{rule_str}'
                linked_people_data = [{"name": name, "question": ""} for name in linked_people_names]
                db.add_task(current_user, title, str(due_date) if due_date else None, notes, questions, subtasks, linked_people_data, recurrence_rule)
                st.toast(f"Added task: {title}", icon="➕"); st.rerun()
    st.divider()
    filter_status = st.multiselect("Filter by status:", options=["To-Do", "In Progress", "Blocked", "Completed"], default=["To-Do", "In Progress", "Blocked"])
    for task in tasks:
        if task['status'] in filter_status:
            due_date_str = f" (Due: {format_date(task['due_date'])})" if task['due_date'] else ""
            recur_icon = "🔄" if task.get('recurrence_rule') else ""
            with st.status(f"{recur_icon} {task['title']}{due_date_str}".strip(), expanded=False, state=("complete" if task['status'] == 'Completed' else "running")):
                session_key = f"linked_people_{task['id']}"
                linked_people_list = json.loads(task['linked_people']) if task.get('linked_people') else []
                if session_key not in st.session_state: st.session_state[session_key] = linked_people_list
                st.markdown("**Linked People & Questions**"); indices_to_remove = []
                for i, person in enumerate(st.session_state[session_key]):
                    col1, col2, col3 = st.columns([3, 5, 1]); col1.markdown(f"**{person['name']}**")
                    st.session_state[session_key][i]['question'] = col2.text_input("Question for person", value=person.get('question', ''), key=f"q_{task['id']}_{i}", label_visibility="collapsed")
                    if col3.button("✖️", key=f"del_{task['id']}_{i}"): indices_to_remove.append(i)
                if indices_to_remove: st.session_state[session_key] = [p for i, p in enumerate(st.session_state[session_key]) if i not in indices_to_remove]; st.rerun()
                new_person_name = st.selectbox("Add a person", options=[""] + people_names, key=f"add_person_{task['id']}")
                if new_person_name:
                    if not any(p['name'] == new_person_name for p in st.session_state[session_key]):
                        st.session_state[session_key].append({"name": new_person_name, "question": ""}); st.rerun()
                st.divider()
                with st.form(key=f"form_{task['id']}"):
                    st.markdown("**Task Details**"); new_title = st.text_input("Title", value=task['title']); cols = st.columns(2)
                    new_status = cols[0].selectbox("Status", options=["To-Do", "In Progress", "Blocked", "Completed"], index=["To-Do", "In Progress", "Blocked", "Completed"].index(task['status']))
                    due_date_val = datetime.fromisoformat(task['due_date']) if task['due_date'] else None; new_due_date = cols[1].date_input("Due Date", value=due_date_val)
                    new_notes = st.text_area("Notes", value=task['notes']); new_questions = st.text_area("General Questions", value=task['questions'])
                    new_blocked_reason = task['blocked_reason'] if task['status'] == 'Blocked' else ''
                    if new_status == 'Blocked': new_blocked_reason = st.text_input("Reason for being blocked?", value=task.get('blocked_reason', ''))
                    st.markdown("**Recurrence**"); current_rule = task.get('recurrence_rule') or 'None'; recur_map = {'None': 0, 'weekly': 1, 'monthly': 2}
                    default_index = recur_map.get(current_rule, 3)
                    new_recur_type = st.selectbox("Repeats", ["None", "Weekly", "Monthly", "Specific Days"], index=default_index, key=f"recur_{task['id']}")
                    new_weekdays_options = []
                    if new_recur_type == "Specific Days":
                        day_map_inv = {"M": "Monday", "T": "Tuesday", "W": "Wednesday", "H": "Thursday", "F": "Friday", "S": "Saturday", "U": "Sunday"}
                        default_days = [day_map_inv[char] for char in current_rule.split(':')[1]] if current_rule and current_rule.startswith('weekdays:') else []
                        new_weekdays_options = st.multiselect("On which days?", ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"], default=default_days, key=f"weekdays_{task['id']}")
                    st.markdown("**Sub-tasks**"); subtasks_list = json.loads(task['subtasks']) if task['subtasks'] else []
                    for i, subtask in enumerate(subtasks_list): subtasks_list[i]['done'] = st.checkbox(subtask['text'], value=subtask['done'], key=f"sub_{task['id']}_{i}")
                    btn_cols = st.columns(2)
                    if btn_cols[0].form_submit_button("Save Changes", type="primary", use_container_width=True):
                        new_recurrence_rule = None
                        if new_recur_type == 'Weekly': new_recurrence_rule = 'weekly'
                        elif new_recur_type == 'Monthly': new_recurrence_rule = 'monthly'
                        elif new_recur_type == 'Specific Days' and new_weekdays_options:
                            day_map = {"Monday": "M", "Tuesday": "T", "Wednesday": "W", "Thursday": "H", "Friday": "F", "Saturday": "S", "Sunday": "U"}
                            rule_str = "".join([day_map[day] for day in new_weekdays_options]); new_recurrence_rule = f'weekdays:{rule_str}'
                        if new_status == 'Completed' and task.get('recurrence_rule') and task.get('due_date'):
                            db.complete_recurring_task(current_user, task)
                            st.toast(f"Completed and rescheduled '{new_title}'!", icon="👍")
                        else:
                            db.update_task(current_user, task['id'], new_title, new_status, str(new_due_date) if new_due_date else None, new_notes, new_questions, subtasks_list, new_blocked_reason, st.session_state[session_key], new_recurrence_rule)
                            st.toast(f"Updated '{new_title}'", icon="💾")
                        del st.session_state[session_key]; st.rerun()
                    if btn_cols[1].form_submit_button("Delete", use_container_width=True):
                        db.delete_task(current_user, task['id'])
                        del st.session_state[session_key]; st.toast(f"Deleted '{task['title']}'", icon="🗑️"); st.rerun()
with tab3:
    st.header("Calendar");
    task_data = [{'Task': t['title'], 'Date': datetime.fromisoformat(t['due_date']).date(), 'Duration': 1} for t in tasks if t['due_date']]
    if task_data: df = pd.DataFrame(task_data).set_index('Date').sort_index(); st.bar_chart(df[['Duration']]); st.dataframe(df.reset_index()[['Task', 'Date']], use_container_width=True)
    else: st.info("No tasks with due dates to display on the calendar.")
with tab4:
    st.header("People")
    with st.expander("Add New Person"):
        with st.form("new_person_form", clear_on_submit=True):
            person_name = st.text_input("Person's Name")
            if st.form_submit_button("Add Person", type="primary"):
                if person_name:
                    try:
                        db.add_person(current_user, person_name)
                        st.toast(f"Added {person_name}.", icon="👥"); st.rerun()
                    except LibsqlError: st.error(f"'{person_name}' already exists in your contacts.")
                    except Exception as e: st.error(f"An error occurred: {e}")
                else: st.warning("Please enter a name.")
    if not people: st.info("You haven't added any people yet.")
    else:
        selected_person_name = st.selectbox("Select a person:", people_names)
        person = next((p for p in people if p['name'] == selected_person_name), None)
        if person:
            with st.form(key=f"person_log_{person['id']}"):
                log_content = st.text_area("Interaction Log", value=person['interaction_log'], height=300)
                if st.form_submit_button("Save Log", type="primary"):
                    db.update_person_log(current_user, person['id'], log_content)
                    st.toast("Log updated!", icon="📝"); st.rerun()
