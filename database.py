import os
import json
from datetime import datetime, timedelta
import hashlib
# CORRECTED IMPORT: We now import the specific error class 'LibsqlError'
from libsql_client import create_client, LibsqlError

try:
    import streamlit as st
    db_url = st.secrets["TURSO_DB_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]
except (AttributeError, KeyError):
    from google.colab import userdata
    db_url = userdata.get("TURSO_DB_URL")
    auth_token = userdata.get("TURSO_AUTH_TOKEN")
    
db = create_client(url=db_url, auth_token=auth_token)

def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def setup_database():
    db.batch([
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)",
        "CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT, due_date TEXT, notes TEXT, questions TEXT, subtasks TEXT, blocked_reason TEXT, created_at TEXT, linked_people TEXT, owner TEXT, recurrence_rule TEXT)",
        "CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, username TEXT, name TEXT, interaction_log TEXT, UNIQUE(username, name))"
    ])
    try:
        db.execute("ALTER TABLE tasks ADD COLUMN recurrence_rule TEXT")
    except LibsqlError: pass

def add_user(username, password):
    try:
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        return True
    except LibsqlError: return False

def verify_user(username, password):
    rs = db.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    return len(rs.rows) > 0 and rs.rows[0][0] == hash_password(password)

def rows_to_dicts(rs):
    return [dict(zip(rs.columns, row)) for row in rs.rows]

def add_task(username, title, due_date, notes, questions, subtasks, linked_people, recurrence_rule):
    params = (title, "To-Do", due_date, notes, questions, json.dumps([{"text": s.strip(), "done": False} for s in subtasks.split('\n') if s.strip()]), datetime.now().isoformat(), json.dumps(linked_people), username, recurrence_rule)
    db.execute("INSERT INTO tasks (title, status, due_date, notes, questions, subtasks, created_at, linked_people, owner, recurrence_rule) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", params)

def get_all_tasks(username):
    rs = db.execute("SELECT * FROM tasks WHERE owner=? ORDER BY due_date ASC", (username,))
    return rows_to_dicts(rs)

def update_task(username, task_id, title, status, due_date, notes, questions, subtasks, blocked_reason, linked_people, recurrence_rule):
    params = (title, status, due_date, notes, questions, json.dumps(subtasks), blocked_reason, json.dumps(linked_people), recurrence_rule, task_id, username)
    db.execute("UPDATE tasks SET title=?, status=?, due_date=?, notes=?, questions=?, subtasks=?, blocked_reason=?, linked_people=?, recurrence_rule=? WHERE id=? AND owner=?", params)

def complete_recurring_task(username, task):
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
        db.execute("UPDATE tasks SET due_date = ? WHERE id = ? AND owner = ?", (next_due_date.isoformat(), task['id'], username))

def delete_task(username, task_id):
    db.execute("DELETE FROM tasks WHERE id=? AND owner=?", (task_id, username))

def add_person(username, name):
    db.execute("INSERT INTO people (username, name, interaction_log) VALUES (?, ?, ?)", (username, name, ""))
def get_all_people(username):
    rs = db.execute("SELECT * FROM people WHERE username=? ORDER BY name ASC", (username,))
    return rows_to_dicts(rs)
def update_person_log(username, person_id, log):
    db.execute("UPDATE people SET interaction_log=? WHERE id=? AND username=?", (log, person_id, username))
