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

# Cache token and data in memory with TTL
_SESSION_CACHE = {
    "token_data": None,
    "token_expiry": 0,
    "attendance_data": None,
    "attendance_expiry": 0,
    "circulars_data": None,
    "circulars_expiry": 0
}


class EdumarshalClient:
    """Client for authenticating and fetching data from Edumarshal."""

    def __init__(self, username: str = DEFAULT_USERNAME, password: str = DEFAULT_PASSWORD):
        self.username = username
        self.password = password
        self.ssl_ctx = ssl.create_default_context()
        self.ssl_ctx.check_hostname = False
        self.ssl_ctx.verify_mode = ssl.CERT_NONE
        self.base_url = EDUMARSHAL_BASE

    def authenticate(self, force: bool = False) -> Dict[str, Any]:
        """Authenticate via OAuth2 Password Grant and obtain Bearer token."""
        now = time.time()
        cached_tok = _SESSION_CACHE["token_data"]
        if not force and cached_tok and now < _SESSION_CACHE["token_expiry"]:
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
                _SESSION_CACHE["token_data"] = token_data
                _SESSION_CACHE["token_expiry"] = now + max(60, expires_in - 300)
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

    def get_attendance(self, force: bool = False) -> Dict[str, Any]:
        """Fetch subject-wise attendance and overall aggregate statistics."""
        now = time.time()
        if not force and _SESSION_CACHE["attendance_data"] and now < _SESSION_CACHE["attendance_expiry"]:
            return _SESSION_CACHE["attendance_data"]

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
        _SESSION_CACHE["attendance_data"] = result
        _SESSION_CACHE["attendance_expiry"] = now + 900
        return result

    def get_circulars(self, force: bool = False) -> List[Dict[str, Any]]:
        """Fetch all official MAIT circulars, notices of the day, and attachments."""
        now = time.time()
        if not force and _SESSION_CACHE["circulars_data"] and now < _SESSION_CACHE["circulars_expiry"]:
            return _SESSION_CACHE["circulars_data"]

        headers = self._get_headers()
        token_data = self.authenticate()
        org_id = token_data["X-ContextId"]
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

        _SESSION_CACHE["circulars_data"] = sorted_circulars
        _SESSION_CACHE["circulars_expiry"] = now + 900
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


# Global singleton instance
default_edumarshal_client = EdumarshalClient()

def get_mait_attendance(force: bool = False) -> Dict[str, Any]:
    return default_edumarshal_client.get_attendance(force=force)

def get_mait_circulars(force: bool = False) -> List[Dict[str, Any]]:
    return default_edumarshal_client.get_circulars(force=force)


# Quick CLI test execution
if __name__ == "__main__":
    client = EdumarshalClient()
    print("[*] Testing Edumarshal Authentication...")
    tok = client.authenticate()
    print(f"[+] Authenticated! UserId={tok.get('X-UserId')}, ContextId={tok.get('X-ContextId')}")

    print("\n[*] Fetching Attendance...")
    att = client.get_attendance()
    print(f"[+] Attendance: {att['overall']['percentage']}% ({att['overall']['present']}/{att['overall']['total']})")
    for s in att["subjects"]:
        print(f"    - {s['name']} ({s['code']}): {s['percentage']}% ({s['present']}/{s['total']}) [{s['status']}]")

    print("\n[*] Fetching MAIT Circulars...")
    circs = client.get_circulars()
    print(f"[+] Fetched {len(circs)} circulars:")
    for c in circs[:5]:
        att_str = f" [Attachment: {c['attachments'][0]['name']}]" if c['has_attachment'] else ""
        print(f"    - [{c['date']}] {c['title']}{att_str}")
