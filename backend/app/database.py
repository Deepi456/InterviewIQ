"""
Database initialization and connection management for InterviewIQ.
Supports SQLite for local development, easily extensible for production databases.
"""

import sqlite3
import os
from pathlib import Path
from typing import Optional

# Database file location
DB_DIR = Path(__file__).parent.parent.parent / "data"
DB_DIR.mkdir(exist_ok=True)
DB_PATH = DB_DIR / "interviewiq.db"


def get_connection(db_path: Optional[str] = None) -> sqlite3.Connection:
    """Get database connection with row factory for dict-like access."""
    target = db_path if db_path else str(DB_PATH)
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: Optional[str] = None):
    """Initialize database with all required tables."""
    conn = get_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Interview sessions table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_sessions (
            session_id TEXT PRIMARY KEY,
            job_role TEXT NOT NULL,
            total_questions INTEGER NOT NULL DEFAULT 10,
            current_question_number INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL DEFAULT 'in_progress',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            skills_json TEXT
        )
    """)
    _add_column_if_missing(cursor, "interview_sessions", "user_id", "TEXT")
    _add_column_if_missing(cursor, "interview_sessions", "interview_type", "TEXT DEFAULT 'Technical'")
    _add_column_if_missing(cursor, "interview_sessions", "difficulty", "TEXT DEFAULT 'Medium'")
    _add_column_if_missing(cursor, "interview_sessions", "started_at", "TIMESTAMP")
    _add_column_if_missing(cursor, "interview_sessions", "last_activity_at", "TIMESTAMP")
    _add_column_if_missing(cursor, "interview_sessions", "integrity_events_json", "TEXT DEFAULT '[]'")
    _add_column_if_missing(cursor, "interview_sessions", "expires_at", "TIMESTAMP")
    
    # Asked questions tracking (prevents repetition)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS asked_questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            question_number INTEGER NOT NULL,
            asked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id),
            UNIQUE(session_id, question_id)
        )
    """)
    # Candidate answers and scoring
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS candidate_answers (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            question_id TEXT NOT NULL,
            answer TEXT NOT NULL,
            score REAL,
            feedback TEXT,
            skill TEXT,
            difficulty TEXT,
            answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id)
        )
    """)
    _add_column_if_missing(cursor, "candidate_answers", "evaluation_status", "TEXT DEFAULT 'pending'")
    _add_column_if_missing(cursor, "candidate_answers", "evaluation_error", "TEXT")
    _add_column_if_missing(cursor, "candidate_answers", "evaluation_json", "TEXT")
    _add_column_if_missing(cursor, "candidate_answers", "evaluated_at", "TIMESTAMP")
    cursor.execute("""
        CREATE UNIQUE INDEX IF NOT EXISTS idx_candidate_answers_session_question
        ON candidate_answers(session_id, question_id)
    """)
    
    # Interview performance summary
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_performance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL UNIQUE,
            total_score REAL,
            average_score REAL,
            skill_scores TEXT,
            completed_at TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id)
        )
    """)
    
    # Interview reports (Phase 5)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS interview_reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL UNIQUE,
            overall_score REAL,
            performance_level TEXT,
            summary TEXT,
            report_json TEXT NOT NULL,
            ai_generated BOOLEAN DEFAULT 1,
            automation_status TEXT DEFAULT 'NOT_SENT',
            delivery_email TEXT,
            last_sent_at TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES interview_sessions(session_id)
        )
    """)

    # Add delivery-tracking columns for existing databases.
    try:
        columns = [row[1] for row in cursor.execute("PRAGMA table_info(interview_reports)").fetchall()]
        for col_name, col_sql in {
            'automation_status': "ALTER TABLE interview_reports ADD COLUMN automation_status TEXT DEFAULT 'NOT_SENT'",
            'delivery_email': "ALTER TABLE interview_reports ADD COLUMN delivery_email TEXT",
            'last_sent_at': "ALTER TABLE interview_reports ADD COLUMN last_sent_at TIMESTAMP",
        }.items():
            if col_name not in columns:
                cursor.execute(col_sql)
    except Exception:
        pass
    
    conn.commit()
    conn.close()
    print(f"Database initialized at {DB_PATH}")


def _add_column_if_missing(cursor, table: str, column: str, definition: str):
    columns = [row[1] for row in cursor.execute(f"PRAGMA table_info({table})").fetchall()]
    if column not in columns:
        cursor.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")


def clear_database():
    """Clear all data from database (for testing)."""
    if DB_PATH.exists():
        os.remove(DB_PATH)
        print(f"✓ Database cleared: {DB_PATH}")


if __name__ == "__main__":
    init_database()
