import sqlite3
from datetime import datetime
from pathlib import Path

DB_PATH = Path("bot_data.db")

def init_db():
    """Initialize the database with all required tables"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        
        # User join dates table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS user_join_dates (
            chat_id INTEGER,
            user_id INTEGER,
            join_date TEXT,
            PRIMARY KEY (chat_id, user_id)
        )
        """)
        
        # Welcome messages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS welcome_messages (
            chat_id INTEGER PRIMARY KEY,
            message TEXT
        )
        """)
        
        # Goodbye messages table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS goodbye_messages (
            chat_id INTEGER PRIMARY KEY,
            message TEXT
        )
        """)
        
        conn.commit()

def store_join_date(chat_id: int, user_id: int):
    """Store or update a user's join date"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO user_join_dates (chat_id, user_id, join_date)
        VALUES (?, ?, ?)
        """, (chat_id, user_id, datetime.now().isoformat()))
        conn.commit()

def get_join_date(chat_id: int, user_id: int) -> datetime:
    """Get a user's join date"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT join_date FROM user_join_dates
        WHERE chat_id = ? AND user_id = ?
        """, (chat_id, user_id))
        result = cursor.fetchone()
        return datetime.fromisoformat(result[0]) if result else None

def set_welcome_message(chat_id: int, message: str):
    """Set welcome message for a chat"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO welcome_messages (chat_id, message)
        VALUES (?, ?)
        """, (chat_id, message))
        conn.commit()

def get_welcome_message(chat_id: int) -> str:
    """Get welcome message for a chat"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT message FROM welcome_messages
        WHERE chat_id = ?
        """, (chat_id,))
        result = cursor.fetchone()
        return result[0] if result else None

def set_goodbye_message(chat_id: int, message: str):
    """Set goodbye message for a chat"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        INSERT OR REPLACE INTO goodbye_messages (chat_id, message)
        VALUES (?, ?)
        """, (chat_id, message))
        conn.commit()

def get_goodbye_message(chat_id: int) -> str:
    """Get goodbye message for a chat"""
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT message FROM goodbye_messages
        WHERE chat_id = ?
        """, (chat_id,))
        result = cursor.fetchone()
        return result[0] if result else None

# Add to your database.py
def add_mute_record(chat_id: int, user_id: int, until_date: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS mute_records (
            chat_id INTEGER,
            user_id INTEGER,
            until_date INTEGER,
            PRIMARY KEY (chat_id, user_id)
        )
        """)
        cursor.execute("""
        INSERT OR REPLACE INTO mute_records (chat_id, user_id, until_date)
        VALUES (?, ?, ?)
        """, (chat_id, user_id, until_date))
        conn.commit()

def get_active_mutes():
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        SELECT chat_id, user_id, until_date FROM mute_records
        WHERE until_date > ?
        """, (int(time.time()),))
        return cursor.fetchall()

def remove_mute_record(chat_id: int, user_id: int):
    with sqlite3.connect(DB_PATH) as conn:
        cursor = conn.cursor()
        cursor.execute("""
        DELETE FROM mute_records
        WHERE chat_id = ? AND user_id = ?
        """, (chat_id, user_id))
        conn.commit()

# Initialize database when module loads
init_db()
