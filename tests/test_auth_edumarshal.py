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

    print("TEST 2: Reject Manual Roll Number Entry")
    st, res = http_req("/api/auth/link-roll", method="POST", data={"roll_number": "08414802725"})
    assert st == 403, f"Expected 403, got {st}: {res}"
    assert res.get("error_type") == "MANUAL_ENTRY_DISABLED", f"Expected MANUAL_ENTRY_DISABLED, got {res}"
    print("PASS: Manual roll entry successfully blocked with 403 MANUAL_ENTRY_DISABLED.")

    print("TEST 3: Authenticate User (Tanmay)")
    st, res = http_req("/api/auth/login", method="POST", data={
        "email": "tanmay.jain@ipu.ac.in",
        "password": "Tanmay@2008"
    })
    assert st == 200, f"Login failed: {st}, {res}"
    token = res["session_token"]
    print(f"PASS: Logged in as Tanmay. Session token obtained: {token[:8]}...")

    print("TEST 4: Edumarshal Verification with Invalid Credentials")
    st, res = http_req("/api/edumarshal/verify-and-link", method="POST", data={
        "username": "08414802725",
        "password": "wrong_password_123"
    }, token=token)
    assert st == 400, f"Expected 400, got {st}: {res}"
    assert res.get("status") == "error", f"Expected error, got {res}"
    print("PASS: Invalid Edumarshal credentials rejected with 400.")

    print("TEST 5: Edumarshal Verification with Valid Credentials")
    st, res = http_req("/api/edumarshal/verify-and-link", method="POST", data={
        "username": "08414802725",
        "password": "mait@2029"
    }, token=token)
    assert st == 200, f"Expected 200, got {st}: {res}"
    assert res.get("status") == "success", f"Expected success, got {res}"
    assert res.get("roll_number") == "08414802725", f"Expected roll 08414802725, got {res}"
    assert res.get("is_verified") is True, f"Expected is_verified True, got {res}"
    print(f"PASS: Edumarshal credentials verified and official roll auto-filled: {res.get('roll_number')}")

    print("TEST 6: /api/auth/me Reflects Verified Enrollment")
    st, res = http_req("/api/auth/me", token=token)
    assert st == 200, f"Expected 200, got {st}"
    assert res["is_authenticated"] is True, f"Expected True, got {res}"
    assert res["is_verified"] is True, f"Expected is_verified True, got {res}"
    assert res["user"]["roll_number"] == "08414802725", f"Expected roll 08414802725, got {res}"
    assert res["has_edumarshal"] is True, f"Expected has_edumarshal True, got {res}"
    if "edumarshal" in res["user"] and isinstance(res["user"]["edumarshal"], dict):
        assert "password" not in res["user"]["edumarshal"], "Security invariant violated: password in /api/auth/me!"
    print("PASS: Profile reflects verified enrollment, is_verified flag, and credentials sanitized.")

    print("TEST 7: Duplicate Enrollment Protection Across Accounts")
    st, res = http_req("/api/auth/register", method="POST", data={
        "email": "peer.student@ipu.ac.in",
        "name": "Peer Student",
        "password": "Password@123"
    })
    assert st in (200, 201, 409), f"Register unexpected status: {st}, {res}"
    if st == 409:
        st, res = http_req("/api/auth/login", method="POST", data={
            "email": "peer.student@ipu.ac.in",
            "password": "Password@123"
        })
    peer_token = res["session_token"]

    st, res = http_req("/api/edumarshal/verify-and-link", method="POST", data={
        "username": "08414802725",
        "password": "mait@2029"
    }, token=peer_token)
    assert st in (400, 409), f"Expected 400 (name mismatch) or 409 (duplicate enrollment), got {st}: {res}"
    print(f"PASS: Peer account impersonation/duplicate attempt prevented (status {st}, reason: {res.get('message')})")

    print("TEST 8: /api/edumarshal/calendar Endpoint")
    st, res = http_req("/api/edumarshal/calendar", token=token)
    assert st == 200, f"Expected 200, got {st}"
    assert "dates" in res, f"Expected dates key, got {res.keys()}"
    assert len(res["dates"]) >= 30, f"Expected >=30 academic days, got {len(res['dates'])}"
    print(f"PASS: Calendar endpoint returned {len(res['dates'])} academic days.")

    print("TEST 9: /api/edumarshal/attendance Endpoint")
    st, res = http_req("/api/edumarshal/attendance", token=token)
    assert st == 200, f"Expected 200, got {st}"
    assert "overall" in res, f"Expected overall key, got {res.keys()}"
    assert res["overall"]["percentage"] > 80.0, f"Expected aggregate >80%, got {res['overall']}"
    assert len(res.get("subjects", [])) >= 8, f"Expected >=8 subjects, got {len(res.get('subjects', []))}"
    pct = res["overall"]["percentage"]
    cnt = len(res["subjects"])
    print(f"PASS: Attendance endpoint returned aggregate {pct}% across {cnt} subjects.")

    print("\n======================================================")
    print("PASS: ALL 9 AUTOMATED INTEGRATION TESTS PASSED PERFECTLY")
    print("======================================================\n")

if __name__ == "__main__":
    main()
