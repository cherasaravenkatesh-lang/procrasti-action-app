import sqlite3
import json
from datetime import datetime
import hashlib

# --- User Management (No changes) ---
def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()
def setup_users_db():
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute('CREATE TABLE IF NOT EXISTS users (username TEXT PRIMARY KEY, password_hash TEXT NOT NULL)'); conn.commit(); conn.close()
def add_user(username, password):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    try: c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password))); conn.commit(); return True
    except sqlite3.IntegrityError: return False
    finally: conn.close()
def verify_user(username, password):
    conn = sqlite3.connect("users.db"); c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,)); result = c.fetchone(); conn.close()
    return result and result[0] == hash_password(password)

# --- User-Specific Data Functions (Schema and Logic Updates) ---
def get_user_db_path(username): return f"{username}_data.db"

def setup_database(username):
    db_path = get_user_db_path(username)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (id INTEGER PRIMARY KEY, title TEXT, status TEXT, due_date TEXT, notes TEXT, questions TEXT, subtasks TEXT, blocked_reason TEXT, created_at TEXT, linked_people TEXT)
    ''')
    # This creates the table with the old schema if it doesn't exist
    c.execute('''
        CREATE TABLE IF NOT EXISTS people (id INTEGER PRIMARY KEY, name TEXT UNIQUE, interaction_log TEXT)
    ''')

    # --- ROBUST MIGRATION CODE ---
    # This block checks for columns and adds them if they are missing.
    try:
        # Check if 'linked_people' column exists in tasks
        c.execute("SELECT linked_people FROM tasks LIMIT 1")
    except sqlite3.OperationalError:
        c.execute("ALTER TABLE tasks ADD COLUMN linked_people TEXT")
        
    try:
        # Check if 'username' column exists in people
        c.execute("SELECT username FROM people LIMIT 1")
    except sqlite3.OperationalError:
        # If 'username' column is missing, the table is old. We'll rebuild it.
        # This is a simple migration strategy for this app's scale.
        c.execute("CREATE TABLE people_new (id INTEGER PRIMARY KEY, username TEXT, name TEXT, interaction_log TEXT, UNIQUE(username, name))")
        c.execute("INSERT INTO people_new (id, name, interaction_log) SELECT id, name, interaction_log FROM people")
        c.execute("DROP TABLE people")
        c.execute("ALTER TABLE people_new RENAME TO people")

    conn.commit()
    conn.close()

# The rest of the file is identical to the previous version
def dict_factory(cursor, row):
    d = {};
    for idx, col in enumerate(cursor.description): d[col[0]] = row[idx]
    return d
def execute_query(username, query, params=(), fetchone=False, fetchall=False):
    db_path = get_user_db_path(username)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = dict_factory; c = conn.cursor(); c.execute(query, params)
        if fetchone: return c.fetchone()
        if fetchall: return c.fetchall()
        conn.commit()
def add_task(username, title, due_date, notes, questions, subtasks, linked_people):
    params = (title, "To-Do", due_date, notes, questions, json.dumps([{"text": s.strip(), "done": False} for s in subtasks.split('\n') if s.strip()]), datetime.now().isoformat(), json.dumps(linked_people))
    execute_query(username, "INSERT INTO tasks (title, status, due_date, notes, questions, subtasks, created_at, linked_people) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", params)
def get_all_tasks(username): return execute_query(username, "SELECT * FROM tasks ORDER BY due_date ASC", fetchall=True)
def update_task(username, task_id, title, status, due_date, notes, questions, subtasks, blocked_reason, linked_people):
    params = (title, status, due_date, notes, questions, json.dumps(subtasks), blocked_reason, json.dumps(linked_people), task_id)
    execute_query(username, "UPDATE tasks SET title=?, status=?, due_date=?, notes=?, questions=?, subtasks=?, blocked_reason=?, linked_people=? WHERE id=?", params)
def delete_task(username, task_id): execute_query(username, "DELETE FROM tasks WHERE id=?", (task_id,))
def add_person(username, name): execute_query(username, "INSERT INTO people (username, name, interaction_log) VALUES (?, ?, ?)", (username, name, ""))
def get_all_people(username): return execute_query(username, "SELECT * FROM people WHERE username=? ORDER BY name ASC", (username,), fetchall=True)
def update_person_log(username, person_id, log): execute_query(username, "UPDATE people SET interaction_log=? WHERE id=? AND username=?", (log, person_id, username))
