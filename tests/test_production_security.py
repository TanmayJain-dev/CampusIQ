#!/usr/bin/env python3
"""
tests/test_production_security.py
=================================
Automated verification suite for CampusIQ Production Security & Persistence:
1. AES-256-GCM authenticated credential vault & tampering rejection.
2. Relational database persistence (users, sessions, credentials, uniqueness).
3. HttpOnly cookie authentication in server request handling.
4. Security headers verification (X-Content-Type-Options, X-Frame-Options, Referrer-Policy).
5. SSRF protection in Notice Proxy.
"""

import sys
import os
import json
import time
import base64
import urllib.request
import urllib.error
import threading

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import campusiq_vault
import campusiq_db
import server

TEST_PORT = 9877
TEST_BASE = f"http://127.0.0.1:{TEST_PORT}"


def start_test_server():
    httpd = server.ThreadingHTTPServer(("127.0.0.1", TEST_PORT), server.CampusIQRequestHandler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.5)
    return httpd


def run_tests():
    print("=" * 60)
    print("🧪 CAMPUSIQ PRODUCTION SECURITY & PERSISTENCE TEST SUITE")
    print("=" * 60)

    # -------------------------------------------------------------
    # TEST 1: AES-256-GCM Vault Integrity & Tampering Protection
    # -------------------------------------------------------------
    print("TEST 1: AES-256-GCM Vault Encryption & Decryption")
    secret = "TestStudentPass#2026"
    context = "student:08414802725"
    encrypted = campusiq_vault.encrypt_credential(secret, context=context)
    assert encrypted["version"] == "aes-256-gcm"
    assert "iv" in encrypted and "ciphertext" in encrypted

    decrypted = campusiq_vault.decrypt_credential(encrypted, context=context)
    assert decrypted == secret, f"Expected {secret}, got {decrypted}"

    # Tampering test: corrupt ciphertext
    raw_ct = bytearray(base64.b64decode(encrypted["ciphertext"]))
    raw_ct[4] ^= 0x55
    corrupted_payload = dict(encrypted)
    corrupted_payload["ciphertext"] = base64.b64encode(raw_ct).decode("utf-8")

    tamper_caught = False
    try:
        campusiq_vault.decrypt_credential(corrupted_payload, context=context)
    except ValueError:
        tamper_caught = True
    assert tamper_caught, "FAIL: Tampered ciphertext was NOT caught by GCM auth tag!"
    print("PASS: AES-256-GCM encryption verified and tampered payload safely rejected.")

    # -------------------------------------------------------------
    # TEST 2: Relational DB Operations & Zero Plaintext in Vault
    # -------------------------------------------------------------
    print("TEST 2: Database Persistence & Zero Plaintext Credential Verification")
    test_email = "student.vault@ipu.ac.in"
    user_record = {
        "email": test_email,
        "name": "Vault Verified Student",
        "roll_number": "08814802725",
        "is_verified": True,
        "semester": 3,
        "branch": "CSE"
    }
    campusiq_db.save_user(user_record)
    saved_user = campusiq_db.get_user(test_email)
    assert saved_user is not None
    assert saved_user["roll_number"] == "08814802725"
    assert saved_user["is_verified"] is True

    # Save encrypted credential to vault
    campusiq_db.save_credential(
        email=test_email,
        username="08814802725",
        encrypted_payload=encrypted,
        user_id="usr_test_101",
        full_name="Vault Verified Student"
    )
    cred = campusiq_db.get_credential(test_email)
    assert cred is not None
    # Crucial check: make sure plaintext password is NOT in the database!
    assert "password" not in cred
    assert "encrypted_payload" in cred
    assert cred["encrypted_payload"]["version"] == "aes-256-gcm"
    print("PASS: Database correctly stores encrypted vault payloads without plaintext passwords.")

    # -------------------------------------------------------------
    # TEST 3: HttpOnly Cookie Session Authentication & Security Headers
    # -------------------------------------------------------------
    print("TEST 3: HttpOnly Cookie Authentication & Security Headers")
    server_instance = start_test_server()

    test_token = "sess_prod_token_sec_999"
    campusiq_db.create_session(test_token, saved_user)

    req = urllib.request.Request(f"{TEST_BASE}/api/auth/me")
    req.add_header("Cookie", f"campusiq_session={test_token}")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        headers = dict(resp.headers)
        body = json.loads(resp.read().decode("utf-8"))

        # Verify authentication via cookie alone (no Bearer header)
        assert body.get("is_authenticated") is True
        assert body["user"]["email"] == test_email
        assert body["user"]["roll_number"] == "08814802725"

        # Verify security headers
        assert headers.get("X-Content-Type-Options") == "nosniff"
        assert headers.get("X-Frame-Options") == "DENY"
        assert headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    print("PASS: User authenticated via HttpOnly cookie; security headers confirmed on response.")

    # -------------------------------------------------------------
    # TEST 4: SSRF Protection on Notice Proxy
    # -------------------------------------------------------------
    print("TEST 4: SSRF Protection & Strict Domain Validation on Notice Proxy")
    # Subdomain of permitted domain: should be allowed (or 500/timeout connecting upstream, but NOT 403)
    # Attacker domain with matching suffix (e.g. evilipu.ac.in): MUST be rejected with 403
    evil_urls = [
        "http://evilipu.ac.in/malicious.pdf",
        "http://fake-onrender.com/steal.pdf",
        "file:///etc/passwd",
        "ftp://ipu.ac.in/test.pdf"
    ]
    for evil in evil_urls:
        try:
            req = urllib.request.Request(f"{TEST_BASE}/api/notices/proxy?url={urllib.parse.quote(evil)}")
            with urllib.request.urlopen(req, timeout=5) as resp:
                assert False, f"FAIL: Malicious URL {evil} was not rejected!"
        except urllib.error.HTTPError as e:
            assert e.code in (400, 403), f"Expected 400 or 403, got HTTP {e.code} for {evil}"
    print("PASS: SSRF protection strictly blocked suffix-spoofing and invalid URI schemes.")

    # -------------------------------------------------------------
    # TEST 5: Signout Clears HttpOnly Cookie
    # -------------------------------------------------------------
    print("TEST 5: Signout Endpoint Clears Cookie & Revokes Database Session")
    req = urllib.request.Request(f"{TEST_BASE}/api/auth/signout", method="POST")
    req.add_header("Cookie", f"campusiq_session={test_token}")
    with urllib.request.urlopen(req, timeout=5) as resp:
        assert resp.status == 200
        set_cookie = resp.headers.get("Set-Cookie", "")
        assert "campusiq_session=" in set_cookie
        assert "Max-Age=0" in set_cookie
        assert "HttpOnly" in set_cookie

    # Verify session is revoked in database
    revoked_session = campusiq_db.get_session(test_token)
    assert revoked_session is None, "FAIL: Session was not deleted from DB after signout!"
    print("PASS: Signout successfully revoked session in database and sent cookie eviction header.")

    # Cleanup
    with campusiq_db.get_db() as conn:
        conn.cursor().execute("DELETE FROM users WHERE email = ?", (test_email,))
        conn.cursor().execute("DELETE FROM sessions WHERE token = ?", (test_token,))
        conn.cursor().execute("DELETE FROM credential_vault WHERE email = ?", (test_email,))

    server_instance.shutdown()

    print("=" * 60)
    print("🎉 ALL PRODUCTION SECURITY & PERSISTENCE TESTS PASSED!")
    print("=" * 60)


if __name__ == "__main__":
    run_tests()
