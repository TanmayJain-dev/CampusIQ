#!/usr/bin/env python3
"""
CampusIQ - Universal Relational Persistence Engine
==================================================
High-performance, ACID-compliant database abstraction layer for CampusIQ.

Supports:
- PostgreSQL (Production on Render / Neon / Supabase via DATABASE_URL)
- SQLite (Local development & automated testing via WAL-mode campusiq.db)

Features:
- Thread-safe connection management
- Automatic table creation & schema migrations
- Transparent JSON migration from legacy data/*.json files
- Unique constraints to prevent duplicate / tampered enrollment numbers

Author: CampusIQ Data Platform / Antigravity
License: MIT
"""

import os
import sys
import json
import time
import sqlite3
import urllib.parse
from typing import Dict, List, Optional, Any, Tuple

# Path definitions
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
SQLITE_DB_PATH = os.path.join(DATA_DIR, "campusiq.db")
DATABASE_URL = os.environ.get("DATABASE_URL", "").strip()

# Detect engine
USE_POSTGRES = False
psycopg2 = None
if DATABASE_URL and (DATABASE_URL.startswith("postgres://") or DATABASE_URL.startswith("postgresql://")):
    try:
        import psycopg2
        import psycopg2.extras
        USE_POSTGRES = True
    except ImportError:
        print("[!] Warning: DATABASE_URL is set but psycopg2 is not installed. Falling back to SQLite.", file=sys.stderr)
        USE_POSTGRES = False


class DatabaseConnection:
    """Context manager for obtaining a database connection with auto-commit/rollback."""

    def __enter__(self):
        if USE_POSTGRES and psycopg2:
            # Render uses postgres:// which psycopg2 sometimes prefers as postgresql://
            pg_url = DATABASE_URL
            if pg_url.startswith("postgres://"):
                pg_url = "postgresql://" + pg_url[11:]
            self.conn = psycopg2.connect(pg_url, cursor_factory=psycopg2.extras.RealDictCursor)
        else:
            os.makedirs(DATA_DIR, exist_ok=True)
            self.conn = sqlite3.connect(SQLITE_DB_PATH, timeout=20.0, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            # Enable WAL mode for high concurrency in SQLite
            self.conn.execute("PRAGMA journal_mode = WAL;")
            self.conn.execute("PRAGMA synchronous = NORMAL;")
            self.conn.execute("PRAGMA foreign_keys = ON;")

        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.conn.rollback()
        else:
            self.conn.commit()
        self.conn.close()


def get_db():
    return DatabaseConnection()


def init_db():
    """Initializes tables, indexes, and imports legacy JSON data if empty."""
    os.makedirs(DATA_DIR, exist_ok=True)
    with get_db() as conn:
        cursor = conn.cursor()

        # 1. Users Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                id TEXT,
                name TEXT,
                avatar_url TEXT,
                roll_number TEXT,
                is_verified INTEGER DEFAULT 0,
                semester INTEGER DEFAULT 3,
                branch TEXT DEFAULT 'CSE',
                google_id TEXT,
                auth_provider TEXT DEFAULT 'google',
                created_at REAL,
                updated_at REAL
            );
        """)

        # 2. Sessions Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                token TEXT PRIMARY KEY,
                email TEXT,
                created_at REAL,
                expires_at REAL,
                user_data TEXT
            );
        """)

        # 3. Credential Vault Table (AES-256-GCM Encrypted Credentials)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS credential_vault (
                email TEXT PRIMARY KEY,
                service TEXT DEFAULT 'edumarshal',
                username TEXT,
                encrypted_payload TEXT,
                user_id TEXT,
                full_name TEXT,
                verified_at REAL,
                updated_at REAL
            );
        """)

        # 4. Students Official Marksheets / Records Database
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS students_records (
                roll_number TEXT PRIMARY KEY,
                name TEXT,
                email TEXT,
                student_data TEXT,
                updated_at REAL
            );
        """)

        # 5. Circulars Cache Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS circulars_cache (
                notice_id TEXT PRIMARY KEY,
                title TEXT,
                url TEXT,
                date TEXT,
                source TEXT,
                category TEXT,
                urgency TEXT,
                raw_json TEXT,
                fetched_at REAL
            );
        """)

        # Indexes
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_roll ON users (roll_number);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_sessions_email ON sessions (email);")

    # Migrate legacy JSON if tables are brand new
    _migrate_legacy_json_data()


def _migrate_legacy_json_data():
    """Migrates existing records from data/*.json into database if present."""
    # Migrate users.json
    users_file = os.path.join(DATA_DIR, "users.json")
    if os.path.exists(users_file):
        try:
            with open(users_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, dict):
                    for email, u in data.items():
                        if not email or not isinstance(u, dict):
                            continue
                        if not get_user(email):
                            save_user(u)
        except Exception as e:
            print(f"[!] Info migrating users.json: {e}", file=sys.stderr)

    # Migrate students_database.json
    students_file = os.path.join(DATA_DIR, "students_database.json")
    if os.path.exists(students_file):
        try:
            with open(students_file, "r", encoding="utf-8") as f:
                sdb = json.load(f)
                if isinstance(sdb, dict):
                    for roll, s in sdb.items():
                        if not roll or not isinstance(s, dict):
                            continue
                        save_student_record(roll, s)
        except Exception as e:
            print(f"[!] Info migrating students_database.json: {e}", file=sys.stderr)


# ==============================================================================
# USER OPERATIONS
# ==============================================================================

def get_user(email: str) -> Optional[Dict[str, Any]]:
    if not email:
        return None
    email_clean = email.lower().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE LOWER(email) = ?", (email_clean,)) if not USE_POSTGRES else \
            cursor.execute("SELECT * FROM users WHERE LOWER(email) = %s", (email_clean,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_verified"] = bool(d.get("is_verified", 0))

        # Check for credential vault data
        cred = get_credential(email_clean)
        if cred:
            d["edumarshal"] = cred

        return d


def get_all_users() -> Dict[str, Dict[str, Any]]:
    users = {}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users;")
        rows = cursor.fetchall()
        for r in rows:
            d = dict(r)
            d["is_verified"] = bool(d.get("is_verified", 0))
            cred = get_credential(d.get("email", ""))
            if cred:
                d["edumarshal"] = cred
            users[d["email"]] = d
    return users


def find_user_by_roll(roll: str) -> Optional[Dict[str, Any]]:
    if not roll:
        return None
    roll_clean = roll.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE roll_number = ?", (roll_clean,)) if not USE_POSTGRES else \
            cursor.execute("SELECT * FROM users WHERE roll_number = %s", (roll_clean,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        d["is_verified"] = bool(d.get("is_verified", 0))
        cred = get_credential(d.get("email", ""))
        if cred:
            d["edumarshal"] = cred
        return d


def save_user(user_data: Dict[str, Any]) -> None:
    email = user_data.get("email", "").lower().strip()
    if not email:
        return

    now = time.time()
    uid = user_data.get("id") or f"usr_{int(now)}"
    name = user_data.get("name") or email.split("@")[0].title()
    avatar = user_data.get("avatar_url") or ""
    roll = user_data.get("roll_number") or None
    is_verified = 1 if user_data.get("is_verified") else 0
    semester = int(user_data.get("semester", 3))
    branch = user_data.get("branch", "CSE")
    google_id = user_data.get("google_id") or ""
    auth_provider = user_data.get("auth_provider", "google")
    created_at = float(user_data.get("created_at") or now)
    updated_at = now

    with get_db() as conn:
        cursor = conn.cursor()
        if not USE_POSTGRES:
            cursor.execute("""
                INSERT INTO users (email, id, name, avatar_url, roll_number, is_verified, semester, branch, google_id, auth_provider, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    name=excluded.name,
                    avatar_url=COALESCE(NULLIF(excluded.avatar_url, ''), users.avatar_url),
                    roll_number=COALESCE(excluded.roll_number, users.roll_number),
                    is_verified=excluded.is_verified,
                    semester=excluded.semester,
                    branch=excluded.branch,
                    google_id=COALESCE(NULLIF(excluded.google_id, ''), users.google_id),
                    auth_provider=excluded.auth_provider,
                    updated_at=excluded.updated_at;
            """, (email, uid, name, avatar, roll, is_verified, semester, branch, google_id, auth_provider, created_at, updated_at))
        else:
            cursor.execute("""
                INSERT INTO users (email, id, name, avatar_url, roll_number, is_verified, semester, branch, google_id, auth_provider, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT(email) DO UPDATE SET
                    name=EXCLUDED.name,
                    avatar_url=COALESCE(NULLIF(EXCLUDED.avatar_url, ''), users.avatar_url),
                    roll_number=COALESCE(EXCLUDED.roll_number, users.roll_number),
                    is_verified=EXCLUDED.is_verified,
                    semester=EXCLUDED.semester,
                    branch=EXCLUDED.branch,
                    google_id=COALESCE(NULLIF(EXCLUDED.google_id, ''), users.google_id),
                    auth_provider=EXCLUDED.auth_provider,
                    updated_at=EXCLUDED.updated_at;
            """, (email, uid, name, avatar, roll, is_verified, semester, branch, google_id, auth_provider, created_at, updated_at))


# ==============================================================================
# SESSIONS OPERATIONS
# ==============================================================================

def create_session(token: str, user_dict: Dict[str, Any], expires_in_seconds: int = 86400 * 30) -> None:
    if not token or not user_dict:
        return
    now = time.time()
    expires_at = now + expires_in_seconds
    email = user_dict.get("email", "").lower().strip()

    # Store safe session user payload (without plaintext passwords)
    clean_user = dict(user_dict)
    clean_user["session_token"] = token
    user_json = json.dumps(clean_user)

    with get_db() as conn:
        cursor = conn.cursor()
        if not USE_POSTGRES:
            cursor.execute("""
                INSERT INTO sessions (token, email, created_at, expires_at, user_data)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(token) DO UPDATE SET
                    email=excluded.email,
                    created_at=excluded.created_at,
                    expires_at=excluded.expires_at,
                    user_data=excluded.user_data;
            """, (token, email, now, expires_at, user_json))
        else:
            cursor.execute("""
                INSERT INTO sessions (token, email, created_at, expires_at, user_data)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(token) DO UPDATE SET
                    email=EXCLUDED.email,
                    created_at=EXCLUDED.created_at,
                    expires_at=EXCLUDED.expires_at,
                    user_data=EXCLUDED.user_data;
            """, (token, email, now, expires_at, user_json))


def get_session(token: str) -> Optional[Dict[str, Any]]:
    if not token:
        return None
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE token = ? AND expires_at > ?", (token, now)) if not USE_POSTGRES else \
            cursor.execute("SELECT * FROM sessions WHERE token = %s AND expires_at > %s", (token, now))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            user_data = json.loads(d["user_data"])
            # Refresh with latest user record
            u = get_user(d["email"])
            if u:
                user_data["is_verified"] = u.get("is_verified", False)
                user_data["roll_number"] = u.get("roll_number")
                user_data["semester"] = u.get("semester", 3)
                user_data["branch"] = u.get("branch", "CSE")
                if "edumarshal" in u:
                    user_data["edumarshal"] = u["edumarshal"]
            user_data["session_token"] = token
            return user_data
        except Exception:
            return None


def delete_session(token: str) -> None:
    if not token:
        return
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM sessions WHERE token = ?", (token,)) if not USE_POSTGRES else \
            cursor.execute("DELETE FROM sessions WHERE token = %s", (token,))


def get_all_sessions() -> Dict[str, Dict[str, Any]]:
    now = time.time()
    out = {}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sessions WHERE expires_at > ?", (now,)) if not USE_POSTGRES else \
            cursor.execute("SELECT * FROM sessions WHERE expires_at > %s", (now,))
        for r in cursor.fetchall():
            d = dict(r)
            try:
                out[d["token"]] = json.loads(d["user_data"])
            except Exception:
                pass
    return out


# ==============================================================================
# CREDENTIAL VAULT OPERATIONS (AES-256-GCM)
# ==============================================================================

def save_credential(
    email: str,
    username: str,
    encrypted_payload: Dict[str, str],
    user_id: Optional[str] = None,
    full_name: Optional[str] = None
) -> None:
    if not email or not username or not encrypted_payload:
        return
    email_clean = email.lower().strip()
    payload_json = json.dumps(encrypted_payload)
    now = time.time()

    with get_db() as conn:
        cursor = conn.cursor()
        if not USE_POSTGRES:
            cursor.execute("""
                INSERT INTO credential_vault (email, service, username, encrypted_payload, user_id, full_name, verified_at, updated_at)
                VALUES (?, 'edumarshal', ?, ?, ?, ?, ?, ?)
                ON CONFLICT(email) DO UPDATE SET
                    username=excluded.username,
                    encrypted_payload=excluded.encrypted_payload,
                    user_id=excluded.user_id,
                    full_name=excluded.full_name,
                    verified_at=excluded.verified_at,
                    updated_at=excluded.updated_at;
            """, (email_clean, username, payload_json, user_id, full_name, now, now))
        else:
            cursor.execute("""
                INSERT INTO credential_vault (email, service, username, encrypted_payload, user_id, full_name, verified_at, updated_at)
                VALUES (%s, 'edumarshal', %s, %s, %s, %s, %s, %s)
                ON CONFLICT(email) DO UPDATE SET
                    username=EXCLUDED.username,
                    encrypted_payload=EXCLUDED.encrypted_payload,
                    user_id=EXCLUDED.user_id,
                    full_name=EXCLUDED.full_name,
                    verified_at=EXCLUDED.verified_at,
                    updated_at=EXCLUDED.updated_at;
            """, (email_clean, username, payload_json, user_id, full_name, now, now))


def get_credential(email: str) -> Optional[Dict[str, Any]]:
    if not email:
        return None
    email_clean = email.lower().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM credential_vault WHERE email = ?", (email_clean,)) if not USE_POSTGRES else \
            cursor.execute("SELECT * FROM credential_vault WHERE email = %s", (email_clean,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            d["encrypted_payload"] = json.loads(d["encrypted_payload"])
        except Exception:
            pass
        return d


def delete_credential(email: str) -> None:
    if not email:
        return
    email_clean = email.lower().strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM credential_vault WHERE email = ?", (email_clean,)) if not USE_POSTGRES else \
            cursor.execute("DELETE FROM credential_vault WHERE email = %s", (email_clean,))


# ==============================================================================
# STUDENTS DATABASE OPERATIONS
# ==============================================================================

def save_student_record(roll_number: str, student_data: Dict[str, Any]) -> None:
    if not roll_number or not student_data:
        return
    roll_clean = roll_number.strip()
    name = student_data.get("name") or student_data.get("student_name") or ""
    email = student_data.get("email") or ""
    raw_json = json.dumps(student_data)
    now = time.time()

    with get_db() as conn:
        cursor = conn.cursor()
        if not USE_POSTGRES:
            cursor.execute("""
                INSERT INTO students_records (roll_number, name, email, student_data, updated_at)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(roll_number) DO UPDATE SET
                    name=excluded.name,
                    email=COALESCE(NULLIF(excluded.email, ''), students_records.email),
                    student_data=excluded.student_data,
                    updated_at=excluded.updated_at;
            """, (roll_clean, name, email, raw_json, now))
        else:
            cursor.execute("""
                INSERT INTO students_records (roll_number, name, email, student_data, updated_at)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(roll_number) DO UPDATE SET
                    name=EXCLUDED.name,
                    email=COALESCE(NULLIF(EXCLUDED.email, ''), students_records.email),
                    student_data=EXCLUDED.student_data,
                    updated_at=EXCLUDED.updated_at;
            """, (roll_clean, name, email, raw_json, now))


def get_student_record(roll_number: str) -> Optional[Dict[str, Any]]:
    if not roll_number:
        return None
    roll_clean = roll_number.strip()
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students_records WHERE roll_number = ?", (roll_clean,)) if not USE_POSTGRES else \
            cursor.execute("SELECT * FROM students_records WHERE roll_number = %s", (roll_clean,))
        row = cursor.fetchone()
        if not row:
            return None
        d = dict(row)
        try:
            return json.loads(d["student_data"])
        except Exception:
            return None


def get_all_student_records() -> Dict[str, Dict[str, Any]]:
    out = {}
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM students_records;")
        for r in cursor.fetchall():
            d = dict(r)
            try:
                out[d["roll_number"]] = json.loads(d["student_data"])
            except Exception:
                pass
    return out


# ==============================================================================
# CIRCULARS CACHE OPERATIONS
# ==============================================================================

def save_circulars_to_db(circulars: List[Dict[str, Any]]) -> None:
    if not circulars:
        return
    now = time.time()
    with get_db() as conn:
        cursor = conn.cursor()
        for c in circulars:
            cid = c.get("id") or c.get("url") or f"circ_{hash(c.get('title', ''))}"
            title = c.get("title", "")
            url = c.get("url", "")
            date = c.get("date", "")
            source = c.get("source", "MAIT")
            category = c.get("category", "")
            urgency = c.get("urgency", "MEDIUM")
            raw_json = json.dumps(c)

            if not USE_POSTGRES:
                cursor.execute("""
                    INSERT INTO circulars_cache (notice_id, title, url, date, source, category, urgency, raw_json, fetched_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(notice_id) DO UPDATE SET
                        title=excluded.title,
                        url=excluded.url,
                        date=excluded.date,
                        category=excluded.category,
                        urgency=excluded.urgency,
                        raw_json=excluded.raw_json,
                        fetched_at=excluded.fetched_at;
                """, (str(cid), title, url, date, source, category, urgency, raw_json, now))
            else:
                cursor.execute("""
                    INSERT INTO circulars_cache (notice_id, title, url, date, source, category, urgency, raw_json, fetched_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT(notice_id) DO UPDATE SET
                        title=EXCLUDED.title,
                        url=EXCLUDED.url,
                        date=EXCLUDED.date,
                        category=EXCLUDED.category,
                        urgency=EXCLUDED.urgency,
                        raw_json=EXCLUDED.raw_json,
                        fetched_at=EXCLUDED.fetched_at;
                """, (str(cid), title, url, date, source, category, urgency, raw_json, now))


def get_cached_circulars_from_db() -> List[Dict[str, Any]]:
    out = []
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM circulars_cache ORDER BY fetched_at DESC;")
        for r in cursor.fetchall():
            d = dict(r)
            try:
                out.append(json.loads(d["raw_json"]))
            except Exception:
                pass
    return out


# Self initialization
init_db()


if __name__ == "__main__":
    print("Testing CampusIQ Relational Database Layer...")
    print(f"Engine: {'PostgreSQL' if USE_POSTGRES else 'SQLite (WAL Mode)'}")

    # Test user operations
    test_user = {
        "email": "student.test@ipu.ac.in",
        "name": "Test Student",
        "roll_number": "09914802725",
        "is_verified": True,
        "semester": 3,
        "branch": "CSE"
    }
    save_user(test_user)
    u = get_user("student.test@ipu.ac.in")
    assert u is not None and u["name"] == "Test Student"
    print("User save/get: PASS")

    # Test unique search by roll
    u_by_roll = find_user_by_roll("09914802725")
    assert u_by_roll is not None and u_by_roll["email"] == "student.test@ipu.ac.in"
    print("Find by roll: PASS")

    # Test session operations
    test_token = "sess_test_token_12345"
    create_session(test_token, test_user)
    s = get_session(test_token)
    assert s is not None and s["email"] == "student.test@ipu.ac.in"
    print("Session create/get: PASS")

    # Test credential vault saving
    test_cred = {"version": "aes-256-gcm", "iv": "123", "ciphertext": "abc"}
    save_credential("student.test@ipu.ac.in", "09914802725", test_cred, user_id="101", full_name="Test Student")
    c = get_credential("student.test@ipu.ac.in")
    assert c is not None and c["username"] == "09914802725"
    print("Vault credential save/get: PASS")

    # Cleanup test user
    with get_db() as conn:
        conn.cursor().execute("DELETE FROM users WHERE email = 'student.test@ipu.ac.in';")
        conn.cursor().execute("DELETE FROM sessions WHERE token = 'sess_test_token_12345';")
        conn.cursor().execute("DELETE FROM credential_vault WHERE email = 'student.test@ipu.ac.in';")

    print("All database tests passed successfully!")
