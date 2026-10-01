import os
import sys
import json
import time
import urllib.request
import urllib.error
import threading
from http.server import ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import server

TEST_PORT = 9876
BASE_URL = f"http://127.0.0.1:{TEST_PORT}"

def run_test_server():
    server_address = ("127.0.0.1", TEST_PORT)
    httpd = ThreadingHTTPServer(server_address, server.CampusIQRequestHandler)
    httpd.serve_forever()

def http_req(path, method="GET", data=None, token=None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            content = json.loads(resp.read().decode("utf-8"))
            return status, content
    except urllib.error.HTTPError as e:
        status = e.code
        try:
            content = json.loads(e.read().decode("utf-8"))
        except Exception:
            content = {"error": str(e)}
        return status, content

def main():
    print("Starting background test server on port", TEST_PORT)
    t = threading.Thread(target=run_test_server, daemon=True)
    t.start()
    time.sleep(1.5)

    print("TEST 1: Unauthenticated /api/auth/me")
    st, res = http_req("/api/auth/me")
    assert st == 200, f"Expected 200, got {st}"
    assert res["is_authenticated"] is False, f"Expected False, got {res}"
    print("PASS: Unauthenticated user correctly reported as not authenticated.")

    print("TEST 2: Reject Password Sign-In (/api/auth/login)")
    st, res = http_req("/api/auth/login", method="POST", data={
        "email": "student@ipu.ac.in",
        "password": "Password123"
    })
    assert st == 403, f"Expected 403 Forbidden, got {st}: {res}"
    assert "disabled" in res.get("message", "").lower(), f"Expected disabled message, got {res}"
    print("PASS: Password sign-in successfully rejected with 403.")

    print("TEST 3: Reject Password Registration (/api/auth/register)")
    st, res = http_req("/api/auth/register", method="POST", data={
        "email": "newstudent@ipu.ac.in",
        "name": "New Student",
        "password": "Password123"
    })
    assert st == 403, f"Expected 403 Forbidden, got {st}: {res}"
    assert "disabled" in res.get("message", "").lower(), f"Expected disabled message, got {res}"
    print("PASS: Password registration successfully rejected with 403.")

    print("TEST 4: Reject Manual Roll Number Entry (/api/auth/link-roll)")
    st, res = http_req("/api/auth/link-roll", method="POST", data={"roll_number": "01234567890"})
    assert st == 403, f"Expected 403, got {st}: {res}"
    assert res.get("error_type") == "MANUAL_ENTRY_DISABLED", f"Expected MANUAL_ENTRY_DISABLED, got {res}"
    print("PASS: Manual roll entry successfully blocked with 403 MANUAL_ENTRY_DISABLED.")

    print("TEST 5: Unlinked Attendance Status for Unauthenticated / Unlinked User")
    st, res = http_req("/api/edumarshal/attendance")
    assert st == 200, f"Expected 200, got {st}"
    assert res.get("status") == "unlinked", f"Expected status 'unlinked', got {res}"
    print("PASS: Unlinked attendance endpoint returns unlinked status correctly.")

    print("TEST 6: Unlinked Calendar Status for Unauthenticated / Unlinked User")
    st, res = http_req("/api/edumarshal/calendar")
    assert st == 200, f"Expected 200, got {st}"
    assert res.get("status") == "unlinked", f"Expected status 'unlinked', got {res}"
    print("PASS: Unlinked calendar endpoint returns unlinked status correctly.")

    print("TEST 7: Disabled ExamWeb Demo Endpoint")
    st, res = http_req("/api/examweb/demo")
    assert st == 403, f"Expected 403, got {st}: {res}"
    print("PASS: ExamWeb demo endpoint successfully returns 403 disabled.")

    print("TEST 8: Google Session Authentication Verification")
    import secrets
    test_token = secrets.token_hex(24)
    sessions = server.load_sessions()
    sessions[test_token] = {
        "session_token": test_token,
        "email": "verified.student@ipu.ac.in",
        "name": "Verified Student",
        "avatar_url": "https://api.dicebear.com/7.x/bottts/svg?seed=VerifiedStudent",
        "roll_number": None,
        "is_verified": False,
        "auth_provider": "google",
        "created_at": time.time()
    }
    server.save_sessions()

    st, res = http_req("/api/auth/me", token=test_token)
    assert st == 200, f"Expected 200, got {st}: {res}"
    assert res["is_authenticated"] is True, f"Expected True, got {res}"
    assert res["user"]["email"] == "verified.student@ipu.ac.in"
    assert res["user"]["auth_provider"] == "google"
    print("PASS: Google session authenticated and verified.")

    print("TEST 9: Edumarshal Verification Requires Valid Credentials")
    st, res = http_req("/api/edumarshal/verify-and-link", method="POST", data={
        "username": "01234567890",
        "password": "wrong_password"
    }, token=test_token)
    assert st in (400, 401), f"Expected 400 or 401, got {st}: {res}"
    print("PASS: Invalid Edumarshal credentials rejected.")

    # Clean up test session
    sessions = server.load_sessions()
    if test_token in sessions:
        del sessions[test_token]
        server.save_sessions()

    print("\n======================================================")
    print("PASS: ALL 9 AUTOMATED INTEGRATION TESTS PASSED PERFECTLY")
    print("======================================================\n")

if __name__ == "__main__":
    main()
