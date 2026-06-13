# database.py
# SQLite database — users, sessions, errors, progress

import sqlite3
import json
from datetime import datetime
import os
DB_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "native.db")


def get_connection():
    return sqlite3.connect(DB_PATH)

def create_tables():
    conn = get_connection()
    c = conn.cursor()

    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            native_language TEXT DEFAULT 'es-ES',
            learning_language TEXT DEFAULT 'en-US',
            level TEXT DEFAULT 'unknown',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            character TEXT,
            mode TEXT DEFAULT 'solo',
            started_at TEXT DEFAULT CURRENT_TIMESTAMP,
            ended_at TEXT,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS errors (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER,
            error_type TEXT,
            original TEXT,
            correction TEXT,
            context TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions(id)
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS progress (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            session_id INTEGER,
            accuracy REAL,
            fluency REAL,
            prosody REAL,
            grammar REAL,
            vocabulary REAL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS user_topics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            topic TEXT,
            priority TEXT DEFAULT 'medium',
            frequency INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(user_id, topic),
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)

        # Add summary column to sessions if not exists
    try:
        c.execute("""
                  ALTER TABLE sessions ADD COLUMN summary TEXT
                """)
    except:
        pass
        

    conn.commit()
    conn.close()

def create_user(name):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM users WHERE name = ?", (name,))
    user = c.fetchone()
    if user:
        conn.close()
        return user[0]
    c.execute("INSERT INTO users (name) VALUES (?)", (name,))
    conn.commit()
    user_id = c.lastrowid
    conn.close()
    return user_id

def create_session(user_id, character="Sarah", mode="solo"):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT INTO sessions (user_id, character, mode) VALUES (?, ?, ?)",
        (user_id, character, mode)
    )
    conn.commit()
    session_id = c.lastrowid
    conn.close()
    return session_id

def save_errors(session_id, errors):
    if not errors:
        return
    conn = get_connection()
    c = conn.cursor()
    for error in errors:
        c.execute("""
            INSERT INTO errors (session_id, error_type, original, correction, context)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            error.get("type", "unknown"),
            error.get("original", ""),
            error.get("correction", ""),
            error.get("context", "")
        ))
    conn.commit()
    conn.close()

def save_progress(user_id, session_id, scores):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO progress (user_id, session_id, accuracy, fluency, prosody, grammar, vocabulary)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        user_id,
        session_id,
        scores.get("accuracy", 0),
        scores.get("fluency", 0),
        scores.get("prosody", 0),
        scores.get("grammar", 0),
        scores.get("vocabulary", 0)
    ))
    conn.commit()
    conn.close()

def get_user_history(user_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT error_type, original, correction
        FROM errors e
        JOIN sessions s ON e.session_id = s.id
        WHERE s.user_id = ?
        ORDER BY e.created_at DESC
        LIMIT 50
    """, (user_id,))
    history = c.fetchall()
    conn.close()
    return history
def save_session_summary(user_id: int, session_id: int, summary: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        UPDATE sessions SET summary = ?, ended_at = CURRENT_TIMESTAMP
        WHERE id = ?
    """, (summary, session_id))
    conn.commit()
    conn.close()

def save_user_topic(user_id: int, topic: str, priority: str = "medium"):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        INSERT INTO user_topics (user_id, topic, priority)
        VALUES (?, ?, ?)
        ON CONFLICT(user_id, topic) DO UPDATE SET
        frequency = frequency + 1,
        priority = excluded.priority
    """, (user_id, topic, priority))
    conn.commit()
    conn.close()

def get_user_context(user_id: int) -> dict:
    conn = get_connection()
    c = conn.cursor()

    # Get frequent errors
    c.execute("""
        SELECT error_type, original, correction, COUNT(*) as count
        FROM errors e
        JOIN sessions s ON e.session_id = s.id
        WHERE s.user_id = ?
        GROUP BY original
        ORDER BY count DESC
        LIMIT 5
    """, (user_id,))
    errors = c.fetchall()

    # Get topics
    c.execute("""
        SELECT topic, priority, frequency
        FROM user_topics
        WHERE user_id = ?
        ORDER BY frequency DESC
        LIMIT 10
    """, (user_id,))
    topics = c.fetchall()

    # Get last session summary
    c.execute("""
        SELECT summary FROM sessions
        WHERE user_id = ? AND summary IS NOT NULL
        ORDER BY ended_at DESC
        LIMIT 1
    """, (user_id,))
    last_summary = c.fetchone()

    # Get progress trend
    c.execute("""
        SELECT AVG(accuracy), AVG(fluency)
        FROM progress
        WHERE user_id = ?
    """, (user_id,))
    avg_scores = c.fetchone()

    conn.close()

    return {
        "frequent_errors": [
            {"type": e[0], "original": e[1], "correction": e[2], "count": e[3]}
            for e in errors
        ],
        "topics": [
            {"topic": t[0], "priority": t[1], "frequency": t[2]}
            for t in topics
        ],
        "last_summary": last_summary[0] if last_summary else None,
        "avg_accuracy": avg_scores[0] if avg_scores[0] else 0,
        "avg_fluency": avg_scores[1] if avg_scores[1] else 0,
    }