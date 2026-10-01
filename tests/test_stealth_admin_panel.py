#!/usr/bin/env python3
"""
tests/test_stealth_admin_panel.py
=================================
Automated verification for CampusIQ Master Admin Console:
1. Gating & 401 Unauthorized for unauthenticated requests.
2. Master passcode verification and admin token issuance.
3. Querying student roster and deep student dossiers (profile, marksheet, attendance).
4. Updating student records (CGPA, SGPA, attendance percentages, verification status).
5. Creation and deletion of student dossiers.
"""

import sys
import os
import time
import json
import urllib.request
import urllib.error
import threading
from http.server import ThreadingHTTPServer

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

import campusiq_db
import server

TEST_PORT = 9876
TEST_BASE = f"http://127.0.0.1:{TEST_PORT}"


def make_request(method, path, body=None, headers=None):
    url = f"{TEST_BASE}{path}"
    req_headers = {"Content-Type": "application/json"}
    if headers:
        req_headers.update(headers)

    data = None
    if body is not None:
        if isinstance(body, (dict, list)):
            data = json.dumps(body).encode("utf-8")
        elif isinstance(body, str):
            data = body.encode("utf-8")

    req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            resp_body = resp.read().decode("utf-8")
            try:
                return status, json.loads(resp_body)
            except Exception:
                return status, resp_body
    except urllib.error.HTTPError as e:
        resp_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(resp_body)
        except Exception:
            return e.code, resp_body


def main():
    print("=" * 65)
    print("🧪 TESTING STEALTH ADMIN PANEL GATEWAY, DOSSIERS & LIVE EDITOR")
    print("=" * 65)

    # Initialize database
    campusiq_db.init_db()

    # Start test server in background thread
    httpd = ThreadingHTTPServer(("127.0.0.1", TEST_PORT), server.CampusIQRequestHandler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    try:
        # TEST 1: Unauthenticated Security Gatekeeper
        print("\n[TEST 1] Verifying 401 Unauthorized for Unauthenticated Requests...")
        status, res = make_request("GET", "/api/admin/students")
        assert status == 401, f"Expected 401 for GET /api/admin/students, got {status}"
        print("  ✓ GET /api/admin/students rejected with 401")

        status, res = make_request("POST", "/api/admin/student/update", body={"roll_number": "000"})
        assert status == 401, f"Expected 401 for POST /api/admin/student/update, got {status}"
        print("  ✓ POST /api/admin/student/update rejected with 401")

        status, res = make_request("POST", "/api/admin/student/create", body={"roll_number": "000"})
        assert status == 401, f"Expected 401 for POST /api/admin/student/create, got {status}"
        print("  ✓ POST /api/admin/student/create rejected with 401")

        # TEST 2: Passcode Authentication
        print("\n[TEST 2] Verifying Master Passcode Authentication...")
        status, res = make_request("POST", "/api/admin/auth", body={"passcode": "wrong_passcode"})
        assert status == 401, f"Expected 401 for wrong passcode, got {status}"
        print("  ✓ Incorrect passcode rejected with 401")

        status, res = make_request("POST", "/api/admin/auth", body={"passcode": "mait@admin2026"})
        assert status == 200, f"Expected 200 for correct passcode, got {status}: {res}"
        assert res.get("status") == "success" and "token" in res, f"Expected token in response, got {res}"
        admin_token = res["token"]
        print(f"  ✓ Passcode verified successfully. Obtained Admin Token: {admin_token[:16]}...")

        admin_headers = {"X-Admin-Token": admin_token}

        # TEST 3: Admin Student Roster
        print("\n[TEST 3] Fetching Admin Student Roster with Security Clearance...")
        status, res = make_request("GET", "/api/admin/students", headers=admin_headers)
        assert status == 200, f"Expected 200 for GET /api/admin/students, got {status}: {res}"
        students = res.get("students", [])
        print(f"  ✓ Retrieved {len(students)} student dossiers from database/registry")

        # TEST 4: Create New Student Record
        print("\n[TEST 4] Creating Test Student Record via Admin API...")
        test_roll = "99988877766"
        new_student_payload = {
            "roll_number": test_roll,
            "name": "Super Admin Test Subject",
            "father_name": "Test Father",
            "email": "test.subject@ipu.ac.in",
            "branch": "CSE",
            "semester": 4,
            "overall": {
                "cgpa": 8.75,
                "percentage": 83.1,
                "total_credits": 75
            },
            "semesters": [
                {
                    "semester_number": 1,
                    "sgpa": 8.50,
                    "credits_secured": 25,
                    "papers": [
                        {"paper_code": "ETCS-101", "paper_title": "Programming in C", "credits": 4, "total_marks": 85, "grade": "A+", "status": "PASS"}
                    ]
                }
            ],
            "attendance": {
                "overall": {
                    "percentage": 88.0,
                    "present": 88,
                    "total": 100,
                    "bunk_buffer": 8
                },
                "courses": [
                    {"name": "Computer Networks", "code": "CIC-201", "percentage": 90.0, "present": 36, "total": 40}
                ]
            }
        }

        status, res = make_request("POST", "/api/admin/student/create", body=new_student_payload, headers=admin_headers)
        assert status in (200, 201), f"Expected 200/201 for create student, got {status}: {res}"
        print(f"  ✓ Student {test_roll} created successfully")

        # TEST 5: Deep Dossier Inspection
        print("\n[TEST 5] Inspecting Full Student Dossier (/api/admin/students/<roll>/full)...")
        status, res = make_request("GET", f"/api/admin/students/{test_roll}/full", headers=admin_headers)
        assert status == 200, f"Expected 200 for full dossier, got {status}: {res}"
        st_data = res.get("student", {})
        assert st_data.get("name") == "Super Admin Test Subject"
        assert st_data.get("overall", {}).get("cgpa") == 8.75
        assert st_data.get("attendance", {}).get("overall", {}).get("percentage") == 88.0
        print("  ✓ Full student record verified: Name, CGPA, and Attendance matched")

        # TEST 6: Live Data Mutation & Overrides
        print("\n[TEST 6] Live Editing Student Records (CGPA -> 9.92, Attendance -> 96.5%)...")
        update_payload = {
            "roll_number": test_roll,
            "name": "Super Admin Test Subject (Honors)",
            "overall": {
                "cgpa": 9.92,
                "percentage": 94.2,
                "total_credits": 80
            },
            "attendance": {
                "overall": {
                    "percentage": 96.5,
                    "present": 97,
                    "total": 100,
                    "bunk_buffer": 16
                },
                "courses": [
                    {"name": "Computer Networks", "code": "CIC-201", "percentage": 97.5, "present": 39, "total": 40}
                ]
            }
        }
        status, res = make_request("POST", "/api/admin/student/update", body=update_payload, headers=admin_headers)
        assert status == 200, f"Expected 200 for student update, got {status}: {res}"
        print("  ✓ Update payload accepted")

        # Verify mutation persisted
        status, res = make_request("GET", f"/api/admin/students/{test_roll}/full", headers=admin_headers)
        assert status == 200, f"Expected 200 for inspection, got {status}: {res}"
        updated_st = res.get("student", {})
        assert updated_st.get("name") == "Super Admin Test Subject (Honors)", f"Expected updated name, got {updated_st.get('name')}"
        assert abs(updated_st.get("overall", {}).get("cgpa") - 9.92) < 0.01, f"Expected 9.92 CGPA, got {updated_st.get('overall')}"
        assert abs(updated_st.get("attendance", {}).get("overall", {}).get("percentage") - 96.5) < 0.01, f"Expected 96.5% attendance, got {updated_st.get('attendance')}"
        print("  ✓ Ground truth mutation verified in database: 9.92 CGPA & 96.5% Attendance")

        # TEST 7: Delete Student Record
        print("\n[TEST 7] Deleting Test Student Record...")
        status, res = make_request("POST", "/api/admin/student/delete", body={"roll_number": test_roll}, headers=admin_headers)
        assert status == 200, f"Expected 200 for student delete, got {status}: {res}"
        print("  ✓ Delete request accepted")

        # Confirm 404 after deletion
        status, res = make_request("GET", f"/api/admin/students/{test_roll}/full", headers=admin_headers)
        assert status == 404, f"Expected 404 for deleted student, got {status}"
        print("  ✓ Verified student is completely purged from records")

        print("\n" + "=" * 65)
        print("🎉 ALL STEALTH ADMIN PANEL TESTS PASSED (100% SUCCESS)")
        print("=" * 65)

    finally:
        httpd.shutdown()
        server_thread.join(timeout=2.0)


if __name__ == "__main__":
    main()
