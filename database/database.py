import sqlite3
from datetime import datetime
import os

DATABASE_NAME = "user_data.db"

def init_db():
    """Initialize the database"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_join_dates (
            chat_id INTEGER,
            user_id INTEGER,
            join_date TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
        """)
        conn.commit()

def store_join_date(chat_id: int, user_id: int):
    """Store or update a user's join date"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO user_join_dates (chat_id, user_id, join_date)
        VALUES (?, ?, ?)
        """, (chat_id, user_id, datetime.now().isoformat()))
        conn.commit()

def get_join_date(chat_id: int, user_id: int) -> datetime:
    """Get a user's join date"""
    with sqlite3.connect(DATABASE_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT join_date FROM user_join_dates
        WHERE chat_id = ? AND user_id = ?
        """, (chat_id, user_id))
        result = cursor.fetchone()
        return datetime.fromisoformat(result[0]) if result else None

# Initialize database when module loads
init_db()
