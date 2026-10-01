#!/usr/bin/env python3
"""
tests/test_sliding_session_and_error_ui.py
==========================================
Verifies:
1. 30-day sliding session expiration in campusiq_db.
2. Cookie header containing Max-Age=2592000 and standard Expires HTTP-date.
3. Refreshing of session cookie on /api/auth/me.
"""

import sys
import os
import time
import json
import urllib.request
import threading
from http.server import ThreadingHTTPServer

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import campusiq_db
import server

TEST_PORT = 9875
TEST_BASE = f"http://127.0.0.1:{TEST_PORT}"


def main():
    print("=" * 60)
    print("🧪 TESTING 30-DAY SLIDING SESSIONS & PERSISTENCE HEADERS")
    print("=" * 60)

    # 1. Test Sliding Session in Database
    print("TEST 1: Sliding Session Expiration Extension")
    test_token = "sess_sliding_test_token_123"
    test_email = "sliding.student@ipu.ac.in"
    user_dict = {
        "email": test_email,
        "name": "Sliding Student",
        "roll_number": "08914802725",
        "is_verified": True
    }
    campusiq_db.save_user(user_dict)

    # Create session that has only 15 days remaining (< 20 days remaining threshold)
    now = time.time()
    old_expires_at = now + (86400 * 15)
    with campusiq_db.get_db() as conn:
        cursor = conn.cursor()
        user_json = json.dumps(user_dict)
        if not campusiq_db.USE_POSTGRES:
            cursor.execute("""
                INSERT OR REPLACE INTO sessions (token, email, created_at, expires_at, user_data)
                VALUES (?, ?, ?, ?, ?)
            """, (test_token, test_email, now - (86400 * 15), old_expires_at, user_json))
        else:
            cursor.execute("""
                INSERT INTO sessions (token, email, created_at, expires_at, user_data)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT(token) DO UPDATE SET
                    expires_at=EXCLUDED.expires_at,
                    user_data=EXCLUDED.user_data;
            """, (test_token, test_email, now - (86400 * 15), old_expires_at, user_json))
        conn.commit()

    # Verify initial expiration is ~15 days out
    with campusiq_db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT expires_at FROM sessions WHERE token = ?", (test_token,)) if not campusiq_db.USE_POSTGRES else \
            cursor.execute("SELECT expires_at FROM sessions WHERE token = %s", (test_token,))
        row = cursor.fetchone()
        assert row is not None
        exp = float(dict(row)["expires_at"])
        assert abs(exp - old_expires_at) < 5, f"Expected {old_expires_at}, got {exp}"

    # Now call get_session(token) - this should trigger the sliding window extension back to 30 days!
    retrieved = campusiq_db.get_session(test_token)
    assert retrieved is not None
    assert retrieved["email"] == test_email

    # Check that expires_at was slid forward in the database to ~30 days (now + 86400 * 30)
    with campusiq_db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT expires_at FROM sessions WHERE token = ?", (test_token,)) if not campusiq_db.USE_POSTGRES else \
            cursor.execute("SELECT expires_at FROM sessions WHERE token = %s", (test_token,))
        row = cursor.fetchone()
        new_exp = float(dict(row)["expires_at"])
        expected_new_exp = time.time() + (86400 * 30)
        diff = abs(new_exp - expected_new_exp)
        assert diff < 10, f"Sliding expiration failed! Diff: {diff}s, new_exp: {new_exp}, expected: {expected_new_exp}"
        print(f"PASS: Session automatically slid forward from 15 days to 30 days ({new_exp - time.time():.0f}s remaining).")

    # 2. Test Cookie Format with Expires attribute
    print("TEST 2: Cookie Format and RFC-7231 Expires Attribute")
    httpd = ThreadingHTTPServer(("127.0.0.1", TEST_PORT), server.CampusIQRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)

    req = urllib.request.Request(f"{TEST_BASE}/api/auth/me")
    req.add_header("Cookie", f"campusiq_session={test_token}")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        headers = dict(resp.headers)
        set_cookie = headers.get("Set-Cookie", "")
        assert "campusiq_session=" in set_cookie, f"Missing campusiq_session in {set_cookie}"
        assert "Max-Age=2592000" in set_cookie, f"Missing Max-Age=2592000 in {set_cookie}"
        assert "Expires=" in set_cookie, f"Missing Expires= in {set_cookie}"
        assert "HttpOnly" in set_cookie, f"Missing HttpOnly in {set_cookie}"
        assert "SameSite=Lax" in set_cookie, f"Missing SameSite=Lax in {set_cookie}"
        print(f"PASS: Set-Cookie validated with 30-day sliding lifespan:\n      {set_cookie}")

    # Cleanup
    with campusiq_db.get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM users WHERE email = ?", (test_email,)) if not campusiq_db.USE_POSTGRES else \
            cursor.execute("DELETE FROM users WHERE email = %s", (test_email,))
        cursor.execute("DELETE FROM sessions WHERE token = ?", (test_token,)) if not campusiq_db.USE_POSTGRES else \
            cursor.execute("DELETE FROM sessions WHERE token = %s", (test_token,))
        conn.commit()

    httpd.shutdown()
    print("=" * 60)
    print("🎉 ALL 30-DAY SLIDING SESSION TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    main()
