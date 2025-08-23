import sqlite3
import json
from datetime import datetime
import hashlib

# --- User Management Functions (No changes here) ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def setup_users_db():
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
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    try:
        c.execute("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, hash_password(password)))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    conn = sqlite3.connect("users.db")
    c = conn.cursor()
    c.execute("SELECT password_hash FROM users WHERE username = ?", (username,))
    result = c.fetchone()
    conn.close()
    if result and result[0] == hash_password(password):
        return True
    return False

# --- User-Specific Data Functions (Schema and Logic Updates) ---

def get_user_db_path(username):
    return f"{username}_data.db"

def setup_database(username):
    """Sets up the database for a specific user with updated schemas."""
    db_path = get_user_db_path(username)
    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # UPDATED TASKS TABLE: Added 'linked_people' column to store JSON
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT, title TEXT NOT NULL, status TEXT NOT NULL,
            due_date TEXT, notes TEXT, questions TEXT, subtasks TEXT,
            blocked_reason TEXT, created_at TEXT NOT NULL,
            linked_people TEXT 
        )
    ''')
    
    # UPDATED PEOPLE TABLE: Uniqueness is now a combination of username and name
    c.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT NOT NULL,
            name TEXT NOT NULL, 
            interaction_log TEXT,
            UNIQUE(username, name)
        )
    ''')
    
    # --- Code to add new columns if the table already exists (for backward compatibility) ---
    try:
        c.execute("ALTER TABLE tasks ADD COLUMN linked_people TEXT")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    try:
        # This is more complex to update, so for simplicity we assume new structure
        # In a real-world scenario, you'd migrate data carefully
        pass
    except:
        pass

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

# --- Task Functions ---
def add_task(username, title, due_date, notes, questions, subtasks, linked_people):
    created_at = datetime.now().isoformat()
    subtasks_json = json.dumps([{"text": s.strip(), "done": False} for s in subtasks.split('\n') if s.strip()])
    linked_people_json = json.dumps(linked_people) # Pass a list of dicts
    query = """
        INSERT INTO tasks (title, status, due_date, notes, questions, subtasks, created_at, linked_people) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (title, "To-Do", due_date, notes, questions, subtasks_json, created_at, linked_people_json)
    execute_query(username, query, params)

def get_all_tasks(username):
    return execute_query(username, "SELECT * FROM tasks ORDER BY due_date ASC", fetchall=True)

def update_task(username, task_id, title, status, due_date, notes, questions, subtasks, blocked_reason, linked_people):
    subtasks_json = json.dumps(subtasks)
    linked_people_json = json.dumps(linked_people)
    query = """
        UPDATE tasks SET title=?, status=?, due_date=?, notes=?, questions=?, 
        subtasks=?, blocked_reason=?, linked_people=? WHERE id=?
    """
    params = (title, status, due_date, notes, questions, subtasks_json, blocked_reason, linked_people_json, task_id)
    execute_query(username, query, params)

def delete_task(username, task_id):
    execute_query(username, "DELETE FROM tasks WHERE id=?", (task_id,))

# --- People Functions (Corrected Logic) ---
def add_person(username, name):
    # Now correctly adds the username to enforce user-specific uniqueness
    query = "INSERT INTO people (username, name, interaction_log) VALUES (?, ?, ?)"
    params = (username, name, "")
    execute_query(username, query, params)

def get_all_people(username):
    # Correctly fetches only the people belonging to the logged-in user
    return execute_query(username, "SELECT * FROM people WHERE username=? ORDER BY name ASC", (username,), fetchall=True)

def update_person_log(username, person_id, log):
    # The WHERE clause ensures a user can only update their own contacts
    query = "UPDATE people SET interaction_log=? WHERE id=? AND username=?"
    params = (log, person_id, username)
    execute_query(username, query, params)
