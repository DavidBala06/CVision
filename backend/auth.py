"""
Auth Module — SQLite Users DB

Manages a lightweight SQLite database for user authentication.
Auto-seeds a demo user on first run.
"""
import sqlite3
import hashlib
import secrets
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "data" / "auth.db"


def _hash_password(password: str, salt: str = "") -> str:
    """Hash a password using SHA-256 with salt. 
    Uses hashlib instead of bcrypt to avoid extra native dependencies."""
    if not salt:
        salt = secrets.token_hex(16)
    hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
    return f"{salt}${hashed}"


def _verify_password(password: str, stored_hash: str) -> bool:
    """Verify a password against a stored hash."""
    salt = stored_hash.split("$")[0]
    return _hash_password(password, salt) == stored_hash


def _get_connection() -> sqlite3.Connection:
    """Get a connection to the auth database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


def init_auth_db():
    """Initialize the users table and seed the demo user if needed."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT NOT NULL DEFAULT '',
            role TEXT NOT NULL DEFAULT 'recruiter',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    # Seed demo user if table is empty
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]

    if count == 0:
        demo_hash = _hash_password("talent2024")
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            ("demo", demo_hash, "Demo Recruiter", "recruiter"),
        )
        print("[Auth] Seeded demo user: demo / talent2024")

    conn.commit()
    conn.close()


def authenticate_user(username: str, password: str) -> dict | None:
    """Authenticate a user. Returns user dict on success, None on failure."""
    conn = _get_connection()
    cursor = conn.cursor()

    cursor.execute(
        "SELECT id, username, password_hash, full_name, role FROM users WHERE username = ?",
        (username,),
    )
    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    if not _verify_password(password, row["password_hash"]):
        return None

    return {
        "id": row["id"],
        "username": row["username"],
        "full_name": row["full_name"],
        "role": row["role"],
    }


def create_user(username: str, password: str, full_name: str = "", role: str = "recruiter") -> bool:
    """Create a new user. Returns True on success, False if username exists."""
    conn = _get_connection()
    cursor = conn.cursor()

    try:
        password_hash = _hash_password(password)
        cursor.execute(
            "INSERT INTO users (username, password_hash, full_name, role) VALUES (?, ?, ?, ?)",
            (username, password_hash, full_name, role),
        )
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()
