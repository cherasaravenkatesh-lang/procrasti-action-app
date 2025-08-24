import streamlit as st
import json
from datetime import datetime, timedelta
import hashlib
from libsql_client import create_client, LibsqlError

# The client is created ONCE using Streamlit's cache.
# This function will only be called a single time.
@st.cache_resource
def get_db_client():
    # We use the HTTPS URL, which forces the synchronous HTTP client.
    # This is the key to avoiding all asyncio errors.
    url = st.secrets["TURSO_DB_URL_HTTPS"] 
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]
    return create_client(url=url, auth_token=auth_token)

# --- All functions are now normal, synchronous functions ---

def setup_database():
    client = get_db_client()
    client.batch([
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT, due_date TEXT, notes TEXT, questions TEXT, subtasks TEXT, blocked_reason TEXT, created_at TEXT, linked_people TEXT, owner TEXT, recurrence_rule TEXT)",
        "CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, username TEXT, name TEXT, interaction_log TEXT, UNIQUE(username, name))"
    ])
    try:
        client.execute("ALTER TABLE tasks ADD COLUMN recurrence_rule TEXT")
    except LibsqlError: pass

def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password):
    client = get_db_client()
    try:
        client.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        return True
    except LibsqlError: return False

def verify_user(username, password):
    client = get_db_client()
    rs = client.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    return len(rs.rows) > 0 and rs.rows[0][0] == hash_password(password)

def rows_to_dicts(rs): return [dict(zip(rs.columns, row)) for row in rs.rows]

def add_task(username, title, due_date, notes, questions, subtasks, linked_people, recurrence_rule):
    client = get_db_client()
    params = (title, "To-Do", due_date, notes, questions, json.dumps([{"text": s.strip(), "done": False} for s in subtasks.split('\n') if s.strip()]), datetime.now().isoformat(), json.dumps(linked_people), username, recurrence_rule)
    client.execute("INSERT INTO tasks (title, status, due_date, notes, questions, subtasks, created_at, linked_people, owner, recurrence_rule) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", params)

def get_all_tasks(username):
    client = get_db_client()
    rs = client.execute("SELECT * FROM tasks WHERE owner=? ORDER BY due_date ASC", (username,))
    return rows_to_dicts(rs)

def update_task(username, task_id, title, status, due_date, notes, questions, subtasks, blocked_reason, linked_people, recurrence_rule):
    client = get_db_client()
    params = (title, status, due_date, notes, questions, json.dumps(subtasks), blocked_reason, json.dumps(linked_people), recurrence_rule, task_id, username)
    client.execute("UPDATE tasks SET title=?, status=?, due_date=?, notes=?, questions=?, subtasks=?, blocked_reason=?, linked_people=?, recurrence_rule=? WHERE id=? AND owner=?", params)

def complete_recurring_task(username, task):
    client = get_db_client()
    rule = task['recurrence_rule']; current_due_date = datetime.fromisoformat(task['due_date']); next_due_date = None
    if rule == 'weekly': next_due_date = current_due_date + timedelta(weeks=1)
    elif rule == 'monthly': next_due_date = current_due_date + timedelta(days=30)
    elif rule.startswith('weekdays:'):
        days_of_week = rule.split(':')[1]; day_map = {'M': 0, 'T': 1, 'W': 2, 'H': 3, 'F': 4, 'S': 5, 'U': 6}
        enabled_days = [day_map[day] for day in days_of_week]; start_date = current_due_date + timedelta(days=1)
        for i in range(8):
            if start_date.weekday() in enabled_days: next_due_date = start_date; break
            start_date += timedelta(days=1)
    if next_due_date:
        client.execute("UPDATE tasks SET due_date = ? WHERE id = ? AND owner = ?", (next_due_date.isoformat(), task['id'], username))

def delete_task(username, task_id):
    client = get_db_client()
    client.execute("DELETE FROM tasks WHERE id=? AND owner=?", (task_id, username))

def add_person(username, name):
    client = get_db_client()
    client.execute("INSERT INTO people (username, name, interaction_log) VALUES (?, ?, ?)", (username, name, ""))

def get_all_people(username):
    client = get_db_client()
    rs = client.execute("SELECT * FROM people WHERE username=? ORDER BY name ASC", (username,))
    return rows_to_dicts(rs)

def update_person_log(username, person_id, log):
    client = get_db_client()
    client.execute("UPDATE people SET interaction_log=? WHERE id=? AND username=?", (log, person_id, username))
