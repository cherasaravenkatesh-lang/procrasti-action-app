import os
import json
from datetime import datetime, timedelta
import hashlib
from libsql_client import create_client, exceptions

# This try/except block allows the app to run both locally in Colab
# and when deployed on Streamlit Cloud.
try:
    # Deployed on Streamlit Cloud: Load secrets from st.secrets
    import streamlit as st
    db_url = st.secrets["TURSO_DB_URL"]
    auth_token = st.secrets["TURSO_AUTH_TOKEN"]
except (AttributeError, KeyError):
    # Running locally or in Colab: Load secrets from environment variables/userdata
    from google.colab import userdata
    db_url = userdata.get("TURSO_DB_URL")
    auth_token = userdata.get("TURSO_AUTH_TOKEN")
    
# Create a single, global client to connect to your Turso database
db = create_client(url=db_url, auth_token=auth_token)

# --- Setup and User Management ---
def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def setup_database():
    """Ensures all necessary tables and columns exist on the remote Turso DB."""
    db.batch([
        "CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)",
        """
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY, title TEXT, status TEXT, due_date TEXT, 
            notes TEXT, questions TEXT, subtasks TEXT, blocked_reason TEXT, 
            created_at TEXT, linked_people TEXT, owner TEXT, recurrence_rule TEXT
        )
        """,
        """
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY, username TEXT, name TEXT, 
            interaction_log TEXT, UNIQUE(username, name)
        )
        """
    ])
    # Add recurrence_rule column if it doesn't exist (for backward compatibility)
    try:
        db.execute("ALTER TABLE tasks ADD COLUMN recurrence_rule TEXT")
        print("Added 'recurrence_rule' column to tasks table.")
    except exceptions.LibsqlError:
        pass # Column already exists, which is fine.

def add_user(username, password):
    try:
        db.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        return True
    except exceptions.LibsqlError: return False

def verify_user(username, password):
    rs = db.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    return len(rs.rows) > 0 and rs.rows[0][0] == hash_password(password)

def rows_to_dicts(rs):
    """Converts Turso's ResultSet to a list of dictionaries."""
    return [dict(zip(rs.columns, row)) for row in rs.rows]

# --- Task Functions ---
def add_task(username, title, due_date, notes, questions, subtasks, linked_people, recurrence_rule):
    created_at = datetime.now().isoformat()
    subtasks_json = json.dumps([{"text": s.strip(), "done": False} for s in subtasks.split('\n') if s.strip()])
    linked_people_json = json.dumps(linked_people)
    query = """
        INSERT INTO tasks (title, status, due_date, notes, questions, subtasks, created_at, linked_people, owner, recurrence_rule) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (title, "To-Do", due_date, notes, questions, subtasks_json, created_at, linked_people_json, username, recurrence_rule)
    db.execute(query, params)

def get_all_tasks(username):
    rs = db.execute("SELECT * FROM tasks WHERE owner=? ORDER BY due_date ASC", (username,))
    return rows_to_dicts(rs)

def update_task(username, task_id, title, status, due_date, notes, questions, subtasks, blocked_reason, linked_people, recurrence_rule):
    params = (title, status, due_date, notes, questions, json.dumps(subtasks), blocked_reason, json.dumps(linked_people), recurrence_rule, task_id, username)
    db.execute("""
        UPDATE tasks SET title=?, status=?, due_date=?, notes=?, questions=?, 
        subtasks=?, blocked_reason=?, linked_people=?, recurrence_rule=? WHERE id=? AND owner=?
    """, params)

def complete_recurring_task(username, task):
    """Calculates the next due date for a recurring task and updates it."""
    rule = task['recurrence_rule']
    current_due_date = datetime.fromisoformat(task['due_date'])
    next_due_date = None

    if rule == 'weekly':
        next_due_date = current_due_date + timedelta(weeks=1)
    elif rule == 'monthly':
        # This simple logic adds ~30 days. More complex logic could be used for specific day of month.
        next_due_date = current_due_date + timedelta(days=30)
    elif rule.startswith('weekdays:'):
        days_of_week = rule.split(':')[1] # e.g., "MTWHF"
        day_map = {'M': 0, 'T': 1, 'W': 2, 'H': 3, 'F': 4, 'S': 5, 'U': 6}
        enabled_days = [day_map[day] for day in days_of_week]
        
        start_date = current_due_date + timedelta(days=1)
        for i in range(8): # Check the next 7 days
            if start_date.weekday() in enabled_days:
                next_due_date = start_date
                break
            start_date += timedelta(days=1)
    
    if next_due_date:
        db.execute("UPDATE tasks SET due_date = ? WHERE id = ? AND owner = ?", (next_due_date.isoformat(), task['id'], username))

def delete_task(username, task_id):
    db.execute("DELETE FROM tasks WHERE id=? AND owner=?", (task_id, username))

# --- People Functions (no changes needed) ---
def add_person(username, name):
    db.execute("INSERT INTO people (username, name, interaction_log) VALUES (?, ?, ?)", (username, name, ""))
def get_all_people(username):
    rs = db.execute("SELECT * FROM people WHERE username=? ORDER BY name ASC", (username,))
    return rows_to_dicts(rs)
def update_person_log(username, person_id, log):
    db.execute("UPDATE people SET interaction_log=? WHERE id=? AND username=?", (log, person_id, username))
