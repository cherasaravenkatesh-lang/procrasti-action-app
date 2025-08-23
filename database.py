import sqlite3
import json
from datetime import datetime

DB_NAME = "procrasti_action.db"

def setup_database():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    # Tasks Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            due_date TEXT,
            notes TEXT,
            questions TEXT,
            subtasks TEXT,
            blocked_reason TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    # People Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS people (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            interaction_log TEXT
        )
    ''')
    conn.commit()
    conn.close()

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

def execute_query(query, params=(), fetchone=False, fetchall=False):
    with sqlite3.connect(DB_NAME) as conn:
        conn.row_factory = dict_factory
        c = conn.cursor()
        c.execute(query, params)
        if fetchone:
            return c.fetchone()
        if fetchall:
            return c.fetchall()
        conn.commit()

# --- Task Functions ---
def add_task(title, due_date, notes, questions, subtasks):
    created_at = datetime.now().isoformat()
    subtasks_json = json.dumps([{"text": s.strip(), "done": False} for s in subtasks.split('\n') if s.strip()])
    query = "INSERT INTO tasks (title, status, due_date, notes, questions, subtasks, created_at) VALUES (?, ?, ?, ?, ?, ?, ?)"
    params = (title, "To-Do", due_date, notes, questions, subtasks_json, created_at)
    execute_query(query, params)

def get_all_tasks():
    return execute_query("SELECT * FROM tasks ORDER BY due_date ASC", fetchall=True)

def update_task(task_id, title, status, due_date, notes, questions, subtasks, blocked_reason):
    subtasks_json = json.dumps(subtasks) # Subtasks will be passed as a list of dicts already
    query = """
        UPDATE tasks SET title=?, status=?, due_date=?, notes=?, questions=?, subtasks=?, blocked_reason=?
        WHERE id=?
    """
    params = (title, status, due_date, notes, questions, subtasks_json, blocked_reason, task_id)
    execute_query(query, params)

def delete_task(task_id):
    execute_query("DELETE FROM tasks WHERE id=?", (task_id,))

# --- People Functions ---
def add_person(name):
    execute_query("INSERT INTO people (name, interaction_log) VALUES (?, ?)", (name, ""))

def get_all_people():
    return execute_query("SELECT * FROM people ORDER BY name ASC", fetchall=True)

def update_person_log(person_id, log):
    execute_query("UPDATE people SET interaction_log=? WHERE id=?", (log, person_id))
