import sqlite3
import json
from datetime import datetime
import hashlib # For secure password hashing

# --- User Management Functions ---
def hash_password(password):
    """Hashes a password for storing."""
    return hashlib.sha256(password.encode()).hexdigest()

def setup_users_db():
    """Sets up the central database for user credentials."""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def add_user(username, password):
    """Adds a new user to the users database."""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError: # This happens if the username already exists
        return False
    finally:
        conn.close()

def verify_user(username, password):
    """Verifies a user's credentials."""
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hash_password(password):
        return True
    return False

# --- User-Specific Data Functions ---

def get_user_db_path(username):
    """Creates a unique database file path for each user."""
    return f"{username}_data.db"

def setup_database(username):
    """Sets up the tasks and people tables for a specific user."""
    db_path = get_user_db_path(username)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, status TEXT NOT NULL,
            due_date TEXT, notes TEXT, questions TEXT, subtasks TEXT,
            blocked_reason TEXT, created_at TEXT NOT NULL
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT NOT NULL UNIQUE, interaction_log TEXT
        )
    ''')
    conn.commit()
    conn.close()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def execute_query(username, query, params=(), fetchone=False, fetchall=False):
    db_path = get_user_db_path(username)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = dict_factory
        c = conn.cursor()
        c.execute(query, params)
        if fetchone: return c.fetchone()
        if fetchall: return c.fetchall()
        conn.commit()

# --- All data functions now require 'username' as the first argument ---
def add_task(username, title, due_date, notes, questions, subtasks):
    created_at = datetime.now().isoformat()
    subtasks_json = json.dumps([{"text": s.strip(), "done": False} for s in subtasks.split('\n') if s.strip()])
    query = "INSERT INTO tasks (title, status, due_date, notes, questions, subtasks, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    params = (title, "To-Do", due_date, notes, questions, subtasks_json, created_at)
    execute_query(username, query, params)

def get_all_tasks(username):
    return execute_query(username, "SELECT * FROM tasks ORDER BY due_date ASC", fetchall=True)

def update_task(username, task_id, title, status, due_date, notes, questions, subtasks, blocked_reason):
    subtasks_json = json.dumps(subtasks)
    query = "UPDATE tasks SET title=?, status=?, due_date=?, notes=?, questions=?, subtasks=?, blocked_reason=? WHERE id=?"
    params = (title, status, due_date, notes, questions, subtasks_json, blocked_reason, task_id)
    execute_query(username, query, params)

def delete_task(username, task_id):
    execute_query(username, "DELETE FROM tasks WHERE id=?", (task_id,))

def add_person(username, name):
    execute_query(username, "INSERT INTO people (name, interaction_log) VALUES (?, ?)", (name, ""))

def get_all_people(username):
    return execute_query(username, "SELECT * FROM people ORDER BY name ASC", fetchall=True)

def update_person_log(username, person_id, log):
    execute_query(username, "UPDATE people SET interaction_log=? WHERE id=?", (log, person_id))
