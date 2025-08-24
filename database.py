import streamlit as st
import json
from datetime import datetime, timedelta
import hashlib
from supabase import create_client, Client

# --- Supabase Connection ---
@st.cache_resource
def get_db_client():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

db: Client = get_db_client()

# --- User Management ---
def hash_password(password): return hashlib.sha256(password.encode()).hexdigest()

def add_user(username, password):
    try:
        db.table('users').insert({
            "username": username,
            "password_hash": hash_password(password)
        }).execute()
        return True
    except Exception as e:
        # Supabase client raises a generic exception for unique constraint violations
        if 'duplicate key value violates unique constraint' in str(e):
            return False
        raise e

def verify_user(username, password):
    user = db.table('users').select("password_hash").eq('username', username).execute().data
    if not user:
        return False
    return user[0]['password_hash'] == hash_password(password)

# --- Task Functions ---
def add_task(username, title, due_date, notes, questions, subtasks, linked_people, recurrence_rule):
    subtasks_list = [{"text": s.strip(), "done": False} for s in subtasks.split('\n') if s.strip()]
    db.table('tasks').insert({
        'owner': username, 'title': title, 'due_date': due_date, 'notes': notes,
        'questions': questions, 'subtasks': subtasks_list, 'status': 'To-Do',
        'linked_people': linked_people, 'recurrence_rule': recurrence_rule
    }).execute()

def get_all_tasks(username):
    return db.table('tasks').select("*").eq('owner', username).order('due_date').execute().data

def update_task(username, task_id, title, status, due_date, notes, questions, subtasks, blocked_reason, linked_people, recurrence_rule):
    db.table('tasks').update({
        'title': title, 'status': status, 'due_date': due_date, 'notes': notes,
        'questions': questions, 'subtasks': subtasks, 'blocked_reason': blocked_reason,
        'linked_people': linked_people, 'recurrence_rule': recurrence_rule
    }).eq('id', task_id).eq('owner', username).execute()

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
        db.table('tasks').update({'due_date': next_due_date.isoformat()}).eq('id', task['id']).eq('owner', username).execute()

def delete_task(username, task_id):
    db.table('tasks').delete().eq('id', task_id).eq('owner', username).execute()

# --- People Functions ---
def add_person(username, name):
    db.table('people').insert({'username': username, 'name': name}).execute()

def get_all_people(username):
    return db.table('people').select("*").eq('username', username).order('name').execute().data

def update_person_log(username, person_id, log):
    db.table('people').update({'interaction_log': log}).eq('id', person_id).eq('username', username).execute()
