#!/usr/bin/env python3
"""
CampusIQ - Edumarshal Integration Core
======================================
Automated client for scraping and caching MAIT attendance, student profile,
and official institute circulars/PDFs from the Edumarshal API.

License: MIT
"""

import sys
import os
import re
import ssl
import json
import time
import datetime
import urllib.request
import urllib.parse
from typing import Dict, List, Optional, Any, Tuple

DEFAULT_USERNAME = os.environ.get("EDUMARSHAL_USERNAME", "08414802725")
DEFAULT_PASSWORD = os.environ.get("EDUMARSHAL_PASSWORD", "mait@2029")
EDUMARSHAL_BASE = "https://app.edumarshal.com"
CLOUDFRONT_BASE = "https://dnhxw4vnj977w.cloudfront.net"
CIRCULARS_CACHE_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "circulars_cache.json")

# Cache token and data in memory with TTL per username
_SESSION_CACHE = {}


class EdumarshalClient:
    """Client for authenticating and fetching data from Edumarshal."""

    def __init__(self, username: str = DEFAULT_USERNAME, password: str = DEFAULT_PASSWORD):
        self.username = username
        self.password = password
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.base_url = EDUMARSHAL_BASE

        if self.username not in _SESSION_CACHE:
            _SESSION_CACHE[self.username] = {
                "token_data": None,
                "token_expiry": 0,
                "profile_data": None,
                "profile_expiry": 0,
                "attendance_data": None,
                "attendance_expiry": 0,
                "calendar_data": None,
                "calendar_expiry": 0,
                "circulars_data": None,
                "circulars_expiry": 0
            }

    @property
    def cache(self) -> Dict[str, Any]:
        return _SESSION_CACHE[self.username]

    def authenticate(self, force: bool = False) -> Dict[str, Any]:
        """Authenticate via OAuth2 Password Grant and obtain Bearer token."""
        now = time.time()
        cached_tok = self.cache.get("token_data")
        if not force and cached_tok and now < self.cache.get("token_expiry", 0):
            return cached_tok

        post_data = urllib.parse.urlencode({
            "grant_type": "password",
            "username": self.username,
            "password": self.password,
            "remember": "true"
        }).encode("utf-8")

        req = urllib.request.Request(
            f"{self.base_url}/Token",
            data=post_data,
            headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "okhttp/4.9.0"
            }
        )

        try:
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=10) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))
                expires_in = int(token_data.get("expires_in", 86400))
                # Set local expiry 5 minutes before official expiry
                self.cache["token_data"] = token_data
                self.cache["token_expiry"] = now + max(60, expires_in - 300)
                return token_data
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8", errors="ignore")
            raise RuntimeError(f"Edumarshal login failed (HTTP {e.code}): {err_body}")
        except Exception as e:
            raise RuntimeError(f"Edumarshal network connection failed: {e}")

    def _get_headers(self) -> Dict[str, str]:
        """Get standard authenticated request headers."""
        token_data = self.authenticate()
        return {
            "Authorization": f"Bearer {token_data['access_token']}",
            "X-UserId": str(token_data["X-UserId"]),
            "X-ContextId": str(token_data["X-ContextId"]),
            "X-RX": str(token_data["X-RX"]),
            "User-Agent": "okhttp/4.9.0",
            "Accept": "application/json"
        }

    def get_student_profile(self, force: bool = False) -> Dict[str, Any]:
        """Fetch official student profile details from Edumarshal."""
        now = time.time()
        if not force and self.cache.get("profile_data") and now < self.cache.get("profile_expiry", 0):
            return self.cache["profile_data"]

        headers = self._get_headers()
        token_data = self.authenticate()
        user_id = token_data["X-UserId"]

        url = f"{self.base_url}/api/User/GetByUserId/{user_id}?y=0"
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        first_name = (data.get("firstName") or "").strip()
        last_name = (data.get("lastName") or "").strip()
        full_name = f"{first_name} {last_name}".strip() or data.get("fullName") or first_name

        profile = {
            "user_id": user_id,
            "first_name": first_name,
            "last_name": last_name,
            "full_name": full_name,
            "roll_number": (data.get("rollNumber") or data.get("admissionNumber") or self.username).strip(),
            "admission_number": (data.get("admissionNumber") or "").strip(),
            "email": (data.get("email") or "").strip(),
            "semester": data.get("semester") or 3,
            "course_name": data.get("courseName"),
            "branch_name": data.get("branchName"),
            "context_id": token_data.get("X-ContextId")
        }

        self.cache["profile_data"] = profile
        self.cache["profile_expiry"] = now + 1800
        return profile

    def get_attendance(self, force: bool = False) -> Dict[str, Any]:
        """Fetch subject-wise attendance and overall aggregate statistics."""
        now = time.time()
        if not force and self.cache.get("attendance_data") and now < self.cache.get("attendance_expiry", 0):
            return self.cache["attendance_data"]

        headers = self._get_headers()
        token_data = self.authenticate()
        user_id = token_data["X-UserId"]

        url = f"{self.base_url}/api/SubjectAttendance/GetPresentAbsentStudent?isDateWise=false&termId=0&userId={user_id}&y=0"
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        std_details = data.get("stdSubAtdDetails", {})
        sub_attendance_list = std_details.get("studentSubjectAttendance", [])

        subjects_summary = []
        overall_stats = {
            "percentage": float(std_details.get("overallPercentage") or 0.0),
            "present": float(std_details.get("overallPresent") or 0.0),
            "total": float(std_details.get("overallLecture") or 0.0),
            "absent": max(0.0, float(std_details.get("overallLecture") or 0.0) - float(std_details.get("overallPresent") or 0.0))
        }

        if sub_attendance_list:
            first_entry = sub_attendance_list[0]
            if "studentPercentage" in first_entry:
                overall_stats["percentage"] = float(first_entry.get("studentPercentage") or overall_stats["percentage"])
                overall_stats["present"] = float(first_entry.get("studentPresentAttendance") or overall_stats["present"])
                overall_stats["total"] = float(first_entry.get("studentTotalAttendance") or overall_stats["total"])
                overall_stats["absent"] = max(0.0, overall_stats["total"] - overall_stats["present"])

            for sub in first_entry.get("subjects", []):
                name = sub.get("name", "Unknown Subject")
                code = sub.get("code", "")
                pct = float(sub.get("percentageAttendance") or 0.0)
                present = int(sub.get("presentLeactures") or 0)
                total = int(sub.get("totalLeactures") or 0)
                absent = max(0, total - present)

                subjects_summary.append({
                    "id": sub.get("id"),
                    "name": name,
                    "code": code,
                    "percentage": round(pct, 2),
                    "present": present,
                    "absent": absent,
                    "total": total,
                    "status": "Safe" if pct >= 75.0 else ("Warning" if pct >= 60.0 else "Critical")
                })

        result = {
            "status": "success",
            "student_roll": self.username,
            "overall": overall_stats,
            "subjects_count": len(subjects_summary),
            "subjects": subjects_summary,
            "updated_at": datetime.datetime.now().isoformat()
        }

        # Cache for 15 minutes
        self.cache["attendance_data"] = result
        self.cache["attendance_expiry"] = now + 900
        return result

    def get_datewise_attendance(self, force: bool = False) -> Dict[str, Any]:
        """Fetch itemized date-by-date attendance logs for the interactive calendar."""
        now = time.time()
        if not force and self.cache.get("calendar_data") and now < self.cache.get("calendar_expiry", 0):
            return self.cache["calendar_data"]

        headers = self._get_headers()
        token_data = self.authenticate()
        user_id = token_data["X-UserId"]

        url = f"{self.base_url}/api/SubjectAttendance/GetPresentAbsentStudent?isDateWise=true&termId=0&userId={user_id}&y=0"
        req = urllib.request.Request(url, headers=headers)

        with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))

        att_list = data.get("attendanceData") or []
        dates_map = {}

        for a in att_list:
            d_raw = a.get("absentDate")
            if not d_raw:
                continue
            d_str = d_raw.split("T")[0]
            try:
                dt = datetime.datetime.fromisoformat(d_str)
            except Exception:
                continue

            lbl = (a.get("attendanceLable") or "--").strip()
            if lbl == "--":
                continue

            is_absent = bool(a.get("isAbsent") or lbl == "A")
            sub_name = (a.get("subjectName") or "Academic Lecture").strip()

            if d_str not in dates_map:
                dates_map[d_str] = {
                    "date": d_str,
                    "year": dt.year,
                    "month": dt.month,
                    "day": dt.day,
                    "weekday": dt.strftime("%A"),
                    "present_count": 0,
                    "absent_count": 0,
                    "total_lectures": 0,
                    "lectures": []
                }

            entry = dates_map[d_str]
            entry["total_lectures"] += 1
            if is_absent:
                entry["absent_count"] += 1
                status = "A"
            else:
                entry["present_count"] += 1
                status = "P"

            entry["lectures"].append({
                "subject": sub_name,
                "status": status,
                "is_absent": is_absent
            })

        # Calculate day statuses
        for d_str, v in dates_map.items():
            tot = v["total_lectures"]
            pres = v["present_count"]
            if tot == 0:
                v["status"] = "OFF"
                v["percentage"] = 0.0
            elif pres == tot:
                v["status"] = "FULL"
                v["percentage"] = 100.0
            elif pres == 0:
                v["status"] = "ABSENT"
                v["percentage"] = 0.0
            else:
                v["status"] = "PARTIAL"
                v["percentage"] = round((pres / tot) * 100.0, 1)

        result = {
            "status": "success",
            "student_roll": self.username,
            "total_days_logged": len(dates_map),
            "dates": dates_map,
            "updated_at": datetime.datetime.now().isoformat()
        }

        self.cache["calendar_data"] = result
        self.cache["calendar_expiry"] = now + 900
        return result

    def get_circulars(self, force: bool = False) -> List[Dict[str, Any]]:
        """Fetch all official MAIT circulars, notices of the day, and attachments."""
        now = time.time()
        if not force and self.cache.get("circulars_data") and now < self.cache.get("circulars_expiry", 0):
            return self.cache["circulars_data"]

        try:
            headers = self._get_headers()
            token_data = self.authenticate()
            org_id = token_data["X-ContextId"]
        except Exception as e:
            print(f"[!] Warning authenticating for Edumarshal circulars: {e}", file=sys.stderr)
            if os.path.exists(CIRCULARS_CACHE_FILE):
                try:
                    with open(CIRCULARS_CACHE_FILE, "r", encoding="utf-8") as f:
                        cached = json.load(f)
                        if cached:
                            return cached
                except Exception:
                    pass
            return []

        today = datetime.datetime.now().strftime("%Y-%m-%d")
        circulars_map = {}

        # 1. Fetch Mode 0 notices (General Notice Board)
        try:
            url_notices = f"{self.base_url}/api/OrgNews?orgId={org_id}&mode=0"
            req = urllib.request.Request(url_notices, headers=headers)
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=10) as resp:
                notices_list = json.loads(resp.read().decode("utf-8"))
                for n in notices_list:
                    nid = n.get("newsId")
                    if nid and nid not in circulars_map:
                        circulars_map[nid] = self._normalize_circular(n)
        except Exception as e:
            print(f"[!] Warning fetching OrgNews: {e}", file=sys.stderr)

        # 2. Fetch Notice of the Day
        try:
            url_notd = f"{self.base_url}/api/OrgNews/NewsOfTheDay?orgId={org_id}&date={today}&y=0"
            req = urllib.request.Request(url_notd, headers=headers)
            with urllib.request.urlopen(req, context=self.ssl_ctx, timeout=8) as resp:
                notd_list = json.loads(resp.read().decode("utf-8"))
                for n in notd_list:
                    nid = n.get("newsId")
                    if nid and nid not in circulars_map:
                        norm = self._normalize_circular(n)
                        norm["is_today_notice"] = True
                        circulars_map[nid] = norm
        except Exception as e:
            print(f"[!] Warning fetching NewsOfTheDay: {e}", file=sys.stderr)

        # Sort circulars by date descending
        sorted_circulars = sorted(
            list(circulars_map.values()),
            key=lambda x: x.get("raw_date", ""),
            reverse=True
        )

        if sorted_circulars:
            self.cache["circulars_data"] = sorted_circulars
            self.cache["circulars_expiry"] = now + 900
            try:
                os.makedirs(os.path.dirname(CIRCULARS_CACHE_FILE), exist_ok=True)
                with open(CIRCULARS_CACHE_FILE, "w", encoding="utf-8") as f:
                    json.dump(sorted_circulars, f, indent=2)
            except Exception as e:
                print(f"[!] Warning writing circulars cache: {e}", file=sys.stderr)
            return sorted_circulars

        if os.path.exists(CIRCULARS_CACHE_FILE):
            try:
                with open(CIRCULARS_CACHE_FILE, "r", encoding="utf-8") as f:
                    cached = json.load(f)
                    if cached:
                        return cached
            except Exception:
                pass

        return sorted_circulars

    def _normalize_circular(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize raw circular record into clean CampusIQ schema."""
        title = raw.get("title", "").strip()
        raw_html = raw.get("content", "") or ""
        clean_text = " ".join(re.sub(r"<[^>]+>", " ", raw_html).split()).strip()

        start_date = raw.get("startDate", "")
        formatted_date = raw.get("startDateString")
        if not formatted_date and start_date:
            try:
                dt = datetime.datetime.fromisoformat(start_date.split("T")[0])
                formatted_date = dt.strftime("%d-%m-%Y")
            except Exception:
                formatted_date = start_date.split("T")[0]

        attachments = []
        for att in (raw.get("attachments") or []):
            blob_url = att.get("blobUrl")
            blob_name = att.get("blobName", "attachment.pdf")
            blob_id = att.get("blobId")
            if not blob_url and blob_id:
                blob_url = f"{CLOUDFRONT_BASE}/{blob_id}"
            if blob_url:
                attachments.append({
                    "name": blob_name,
                    "url": blob_url,
                    "id": blob_id
                })

        news_id = raw.get("newsId", 0)
        pdf_url = attachments[0]["url"] if attachments else f"{self.base_url}/dashboard/stu"

        # Categorize urgency
        title_lower = title.lower()
        if any(w in title_lower for w in ["urgent", "important", "alert", "exam", "datesheet", "schedule"]):
            urgency = "HIGH"
        elif any(w in title_lower for w in ["orientation", "registration", "deadline", "internship", "placement"]):
            urgency = "MEDIUM"
        else:
            urgency = "LOW"

        return {
            "notice_id": f"mait_edu_{news_id}",
            "news_id": news_id,
            "title": title,
            "summary": clean_text[:280] + ("..." if len(clean_text) > 280 else ""),
            "full_content": clean_text,
            "html_content": raw_html,
            "date": formatted_date or "Recent",
            "raw_date": start_date or "",
            "source": "MAIT",
            "college": "Maharaja Agrasen Institute of Technology",
            "issuing_wing": "MAIT Academic Administration (Edumarshal)",
            "category": "MAIT Circulars",
            "urgency": urgency,
            "url": pdf_url,
            "original_url": pdf_url,
            "attachments": attachments,
            "has_attachment": len(attachments) > 0,
            "target_audience": "B.Tech Students / Faculty",
            "action_required": "Review MAIT institute circular and note relevant deadlines or instructions."
        }


def verify_and_extract_identity(
    username: str,
    password: str,
    student_name: Optional[str] = None,
    student_email: Optional[str] = None
) -> Dict[str, Any]:
    """
    Authenticate with Edumarshal, fetch official student profile,
    and verify that the student name matches the logged-in Google account name.
    Returns verified enrollment number, name, and semester.
    """
    client = EdumarshalClient(username=username, password=password)
    try:
        token_data = client.authenticate(force=True)
    except Exception as e:
        return {
            "verified": False,
            "error_type": "AUTH_FAILED",
            "reason": f"Edumarshal login failed: {str(e)}"
        }

    try:
        profile = client.get_student_profile(force=True)
    except Exception as e:
        return {
            "verified": False,
            "error_type": "PROFILE_FETCH_FAILED",
            "reason": f"Failed to retrieve student profile from Edumarshal: {str(e)}"
        }

    # Name matching verification
    if student_name:
        def tokenize(s: str) -> set:
            return set(re.findall(r"[a-z0-9]+", (s or "").lower()))

        u_tokens = tokenize(student_name)
        e_first = (profile.get("first_name") or "").lower().strip()
        e_last = (profile.get("last_name") or "").lower().strip()
        e_full = (profile.get("full_name") or "").lower().strip()
        e_tokens = tokenize(e_full) | tokenize(e_first) | tokenize(e_last)

        matched_tokens = {t for t in (u_tokens & e_tokens) if len(t) >= 3}
        email_matched = False
        if student_email and profile.get("email"):
            email_matched = student_email.lower().strip() == profile.get("email", "").lower().strip()

        if not matched_tokens and not email_matched:
            return {
                "verified": False,
                "error_type": "NAME_MISMATCH",
                "reason": (
                    f"Identity verification failed: The Edumarshal account belongs to '{profile.get('full_name', 'Unknown')}', "
                    f"which does not match your signed-in name ('{student_name}'). "
                    f"Please enter your own personal Edumarshal credentials."
                ),
                "edumarshal_name": profile.get("full_name"),
                "signed_in_name": student_name
            }

    roll_number = profile.get("roll_number") or profile.get("admission_number") or username
    return {
        "verified": True,
        "roll_number": roll_number,
        "admission_number": profile.get("admission_number") or roll_number,
        "first_name": profile.get("first_name"),
        "full_name": profile.get("full_name"),
        "email": profile.get("email"),
        "semester": profile.get("semester") or 3,
        "course_name": profile.get("course_name"),
        "branch_name": profile.get("branch_name"),
        "user_id": token_data.get("X-UserId"),
        "context_id": token_data.get("X-ContextId")
    }


# Global singleton instance for public readouts
default_edumarshal_client = EdumarshalClient()

def get_mait_attendance(force: bool = False, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    client = EdumarshalClient(username, password) if username and password else default_edumarshal_client
    return client.get_attendance(force=force)

def get_mait_calendar(force: bool = False, username: Optional[str] = None, password: Optional[str] = None) -> Dict[str, Any]:
    client = EdumarshalClient(username, password) if username and password else default_edumarshal_client
    return client.get_datewise_attendance(force=force)

def get_mait_circulars(force: bool = False) -> List[Dict[str, Any]]:
    return default_edumarshal_client.get_circulars(force=force)


# Quick CLI test execution
if __name__ == "__main__":
    if DEFAULT_USERNAME and DEFAULT_PASSWORD:
        print(f"[*] Testing Edumarshal connection for user {DEFAULT_USERNAME}...")
        cal = get_mait_calendar(username=DEFAULT_USERNAME, password=DEFAULT_PASSWORD)
        print(f"[+] Total days in calendar: {cal.get('total_days_logged', 0)}")
    else:
        print("[*] No EDUMARSHAL_USERNAME or EDUMARSHAL_PASSWORD configured in environment.")
