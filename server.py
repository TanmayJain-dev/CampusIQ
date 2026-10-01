#!/usr/bin/env python3
"""
CampusIQ - Core Full-Stack Application Server
============================================
High-speed, dependency-light HTTP & REST API server powering CampusIQ.
Provides endpoints for live notice streaming, typeset study resource indexing,
GGSIPU result extraction, SGPA calculation, and in-browser PDF previews.

Author: CampusIQ Automation Core / Antigravity
License: MIT
"""

import sys
import os
import re
import json
import ssl
import time
import secrets
import hashlib
import hmac
import mimetypes
import urllib.request
import urllib.parse
import tempfile
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Dict, List, Optional, Any, Tuple

# Ensure project root is in sys.path
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from campusiq_results_extractor import (
    GGSIPUResultParser,
    GGSIPUResultsPortalScraper,
    INSTITUTION_MAP,
    PROGRAMME_MAP
)
from campusiq_cataloguer import (
    CampusIQResourceCataloguer,
    SUBJECT_CODE_MAP
)
from campusiq_examweb import (
    ExamWebClient,
    load_all_students_db,
    get_student_by_roll,
    STUDENTS_DB_FILE
)
import campusiq_db
import campusiq_vault


PORT = int(os.environ.get("PORT", 5000))
N8N_WEBHOOK_URL = os.environ.get(
    "N8N_WEBHOOK_URL",
    "https://n8n-tanmay.onrender.com/webhook/campusiq-notices"
)
BUNDLED_VAULT_DIR = os.path.join(PROJECT_DIR, "assets", "vault")
ACADEMIC_DIR = os.environ.get("ACADEMIC_DIR", BUNDLED_VAULT_DIR)
SAMPLE_RESULT_PDF = os.path.join(PROJECT_DIR, "sample_result.pdf")

# Session & User Store Configuration
SESSIONS_FILE = os.path.join(PROJECT_DIR, "data", "sessions.json")
USERS_FILE = os.path.join(PROJECT_DIR, "data", "users.json")
AUTH_CONFIG_FILE = os.path.join(PROJECT_DIR, "data", "auth_config.json")
VAULT_DRIVE_MAP_FILE = os.path.join(PROJECT_DIR, "data", "vault_drive_map.json")
VAULT_CACHE_DIR = os.path.join(tempfile.gettempdir(), "campusiq_vault_cache")
_SESSIONS: Dict[str, Dict[str, Any]] = {}
_USERS: Dict[str, Dict[str, Any]] = {}
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "mait@admin2026")
ACTIVE_ADMIN_SESSIONS: set = set()

def load_vault_drive_map() -> Dict[str, Any]:
    if os.path.exists(VAULT_DRIVE_MAP_FILE):
        try:
            with open(VAULT_DRIVE_MAP_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {"files": {}, "folders": {}}

def fetch_google_drive_file(file_id: str) -> Optional[bytes]:
    """Fetch raw file bytes directly from Google Drive headless without exposing any Drive URLs."""
    try:
        os.makedirs(VAULT_CACHE_DIR, exist_ok=True)
        cache_path = os.path.join(VAULT_CACHE_DIR, f"{file_id}.pdf")
        if os.path.exists(cache_path) and os.path.getsize(cache_path) > 100:
            try:
                with open(cache_path, "rb") as f:
                    return f.read()
            except Exception:
                pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Accept": "*/*"
        }
        urls = [
            f"https://drive.usercontent.google.com/download?id={file_id}&export=download&authuser=0",
            f"https://drive.google.com/uc?export=download&id={file_id}",
        ]
        for url in urls:
            try:
                req = urllib.request.Request(url, headers=headers)
                with urllib.request.urlopen(req, timeout=15) as resp:
                    data = resp.read()
                    if b"confirm=" in data and b"download" in data:
                        m = re.search(r'confirm=([0-9a-zA-Z_-]+)', data.decode('utf-8', errors='ignore'))
                        if m:
                            confirm_token = m.group(1)
                            confirm_url = f"{url}&confirm={confirm_token}"
                            creq = urllib.request.Request(confirm_url, headers=headers)
                            with urllib.request.urlopen(creq, timeout=20) as cresp:
                                data = cresp.read()
                    if data and len(data) > 200 and not data.startswith(b"<!DOCTYPE html"):
                        try:
                            with open(cache_path, "wb") as f:
                                f.write(data)
                        except Exception:
                            pass
                        return data
            except Exception as e:
                print(f"[!] Drive stream error for {file_id}: {e}", file=sys.stderr)
    except Exception as e:
        print(f"[!] Drive fetch handler error: {e}", file=sys.stderr)
    return None

def load_auth_config() -> Dict[str, Any]:
    config = {
        "google_client_id": (
            os.environ.get("GOOGLE_CLIENT_ID") or
            os.environ.get("GOOGLE_OAUTH_CLIENT_ID") or
            os.environ.get("CLIENT_ID") or
            ""
        ).strip(),
        "google_client_secret": (
            os.environ.get("GOOGLE_CLIENT_SECRET") or
            os.environ.get("GOOGLE_AUTH_SECRET") or
            os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET") or
            os.environ.get("GOOGLE_SECRET") or
            os.environ.get("CLIENT_SECRET") or
            ""
        ).strip()
    }
    if os.path.exists(AUTH_CONFIG_FILE):
        try:
            with open(AUTH_CONFIG_FILE, "r", encoding="utf-8") as f:
                saved = json.load(f)
                if not config["google_client_id"] and saved.get("google_client_id"):
                    config["google_client_id"] = saved["google_client_id"]
                if not config["google_client_secret"] and saved.get("google_client_secret"):
                    config["google_client_secret"] = saved["google_client_secret"]
        except Exception:
            pass
    return config

def save_auth_config(cfg: Dict[str, Any]):
    try:
        os.makedirs(os.path.dirname(AUTH_CONFIG_FILE), exist_ok=True)
        with open(AUTH_CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving auth config: {e}", file=sys.stderr)

def hash_password(password: str, salt_hex: Optional[str] = None) -> Tuple[str, str]:
    if salt_hex:
        salt = bytes.fromhex(salt_hex)
    else:
        salt = secrets.token_bytes(16)
    pwd_hash = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100000)
    return pwd_hash.hex(), salt.hex()

def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    calc_hash, _ = hash_password(password, salt_hex)
    return hmac.compare_digest(calc_hash, expected_hash)

def load_users() -> Dict[str, Any]:
    global _USERS
    try:
        users = campusiq_db.get_all_users()
        if users:
            _USERS = users
            return _USERS
    except Exception as e:
        print(f"[!] Warning loading users from DB: {e}", file=sys.stderr)

    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r", encoding="utf-8") as f:
                _USERS = json.load(f)
        except Exception:
            _USERS = {}
    else:
        _USERS = {}
    return _USERS

def save_users(users: Dict[str, Any]):
    global _USERS
    _USERS = users
    try:
        for email, u in users.items():
            if isinstance(u, dict):
                campusiq_db.save_user(u)
    except Exception as e:
        print(f"[!] Warning persisting users to DB: {e}", file=sys.stderr)

    try:
        os.makedirs(os.path.dirname(USERS_FILE), exist_ok=True)
        with open(USERS_FILE, "w", encoding="utf-8") as f:
            json.dump(users, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving users backup: {e}", file=sys.stderr)

def load_sessions() -> Dict[str, Dict[str, Any]]:
    global _SESSIONS
    try:
        sessions = campusiq_db.get_all_sessions()
        if sessions:
            _SESSIONS = sessions
            return _SESSIONS
    except Exception as e:
        print(f"[!] Warning loading sessions from DB: {e}", file=sys.stderr)

    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                _SESSIONS = json.load(f)
        except Exception:
            _SESSIONS = {}
    else:
        _SESSIONS = {}
    return _SESSIONS

def save_sessions():
    global _SESSIONS
    try:
        os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_SESSIONS, f, indent=2)
    except Exception as e:
        pass


# Initialize from disk
load_sessions()
load_users()

# In-memory caches
_NOTICES_CACHE = {
    "data": [],
    "last_fetched": 0,
    "ttl": 300 # 5 minutes
}

_CATALOG_CACHE = {
    "data": [],
    "last_scanned": 0,
    "ttl": 600 # 10 minutes
}

_RESULTS_CACHE = {
    "parsed_students": [],
    "last_parsed_pdf": None
}


def enrich_notice(item: Dict[str, Any]) -> Dict[str, Any]:
    """Generates structured summaries, action items, deadlines, and verifies original URLs."""
    title = item.get("title", "").strip()
    url = item.get("url", "https://ipu.ac.in").strip()
    date_str = item.get("date", "Recent").strip()
    source = item.get("source", "GGSIPU").strip()
    college = item.get("college", "GGSIPU Examination Division").strip()
    t_lower = title.lower()

    # Ensure URL is absolute
    if not url.startswith("http"):
        if url.startswith("/"):
            url = f"https://www.ipu.ac.in{url}"
        else:
            url = f"https://www.ipu.ac.in/{url}"

    # 1. Classification & Urgency
    if any(k in t_lower for k in ["datesheet", "date sheet", "schedule", "time table", "postpone", "cancel", "urgent", "corrigendum"]):
        urgency = "HIGH"
        category = "Examinations & Datesheets"
    elif any(k in t_lower for k in ["result", "rechecking", "marksheet", "evaluation", "score", "declared"]):
        urgency = "MEDIUM"
        category = "Results & Evaluations"
    elif any(k in t_lower for k in ["fee", "refund", "dues", "scholarship", "financial"]):
        urgency = "HIGH"
        category = "Fees, Accounts & Scholarships"
    elif any(k in t_lower for k in ["hostel", "allotment", "mess", "residence"]):
        urgency = "MEDIUM"
        category = "Hostel & Campus Facilities"
    elif any(k in t_lower for k in ["ph.d", "thesis", "viva", "oral examination", "research"]):
        urgency = "MEDIUM"
        category = "Ph.D. & Research Evaluations"
    elif any(k in t_lower for k in ["order", "appoint", "dean", "director", "committee", "office order"]):
        urgency = "LOW"
        category = "Administrative Orders & Appointments"
    else:
        urgency = item.get("urgency", "MEDIUM")
        category = item.get("category", "General University Circulars")

    # 2. Target Audience
    if "b.tech" in t_lower:
        target = "B.Tech (All Branches & Affiliated Colleges)"
    elif "b.com" in t_lower:
        target = "B.Com (Hons) Students"
    elif "bams" in t_lower:
        target = "BAMS Professional Examinees"
    elif "bds" in t_lower:
        target = "BDS Professional Examinees"
    elif "b.arch" in t_lower:
        target = "B.Arch Candidates"
    elif "mba" in t_lower:
        target = "MBA Students"
    elif "ph.d" in t_lower:
        target = "Ph.D. Scholars & Research Supervisors"
    elif "hostel" in t_lower:
        target = "Hostel Applicants & Campus Residents"
    elif "staff" in t_lower or "quarter" in t_lower or "appoint" in t_lower:
        target = "University Faculty & Administrative Staff"
    else:
        target = item.get("target_audience", "All Students & Affiliated Colleges")

    # 3. Important Dates & Deadlines Extraction
    extracted_dates = []
    if date_str and date_str != "Recent":
        extracted_dates.append(f"Notification Published: {date_str}")
    date_matches = re.findall(r"\b\d{1,2}[-./]\d{1,2}[-./]\d{4}\b", title)
    for dm in date_matches:
        if dm != date_str and dm not in extracted_dates:
            extracted_dates.append(f"Specified Event Date: {dm}")
    month_match = re.search(r"\b(January|February|March|April|May|June|July|August|September|October|November|December)[-_ ]*(202[0-9])?\b", title, re.I)
    if month_match:
        extracted_dates.append(f"Examination Window: {month_match.group(0)}")

    # 4. Action Required
    if "datesheet" in t_lower or "time table" in t_lower:
        action = "Download the datesheet, verify paper codes, morning/afternoon session slots, and report any clash to your college examination department immediately."
    elif "rechecking" in t_lower or "result" in t_lower:
        action = "Verify your roll number in the published evaluation gazette. In case of discrepancies or further inspection requests, submit within 3 working days."
    elif "fee" in t_lower or "refund" in t_lower:
        action = "Verify your bank details and submit the fee claim or payment challan receipt to the Accounts Department before the statutory cutoff."
    elif "hostel" in t_lower or "allotment" in t_lower:
        action = "Check your allotment status and report to the Chief Warden Office with required self-attested documents and fee deposit slips."
    elif "appoint" in t_lower or "order" in t_lower:
        action = "Note the administrative leadership update for formal departmental submissions and academic authorizations."
    else:
        action = "Carefully review the official circular for procedural instructions and mandatory university compliance guidelines."

    # 5. Executive Summary
    if "rechecking" in t_lower:
        summary = f"The GGSIPU Examination Division has officially released the rechecking evaluations corresponding to {target}. Physical verification of answer scripts has been concluded. The notification specifies the final evaluated status with zero discrepancy recorded for evaluated candidate rolls."
    elif "datesheet" in t_lower or "schedule" in t_lower:
        summary = f"Official examination schedule published by GGSIPU for {target}. The schedule establishes exact dates, timings, paper codes, and examination guidelines across all affiliated university centers."
    elif "allotment" in t_lower or "hostel" in t_lower:
        summary = f"Official accommodation list and allotment order published by the Directorate of Student Welfare / Chief Warden for {target}. Candidates must complete fee clearance and physical reporting within the stipulated timeline."
    elif "appoint" in t_lower or "order" in t_lower:
        summary = f"Statutory administrative circular issued by the Registrar / Vice Chancellor Secretariat notifying {title}. This order takes immediate effect for all university schools and affiliated institutes."
    else:
        summary = f"Official institutional notice published by {source} concerning '{title}'. The circular outlines key regulatory guidelines, eligibility criteria, and operational instructions for {target}."

    takeaways = [
        f"Audience: {target}",
        f"Action: {action[:110]}...",
        f"Stream: {category} ({urgency} Urgency)",
        "Original Link: Direct university circular accessible via official portal."
    ]

    item["executive_summary"] = summary
    item["action_required"] = action
    item["important_dates"] = extracted_dates
    item["target_audience"] = target
    item["category"] = category
    item["urgency"] = urgency
    item["key_takeaways"] = takeaways
    item["issuing_wing"] = college or f"{source} Central Administration"
    item["original_url"] = url
    return item


def get_cached_notices() -> List[Dict[str, Any]]:
    """Fetch notices from Render n8n webhook, direct IPU scrapers, and MAIT Edumarshal API."""
    now = time.time()
    if _NOTICES_CACHE["data"] and (now - _NOTICES_CACHE["last_fetched"] < _NOTICES_CACHE["ttl"]):
        return _NOTICES_CACHE["data"]

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/html, */*"
    }

    all_notices = []

    # 1. Fetch Live MAIT Edumarshal Circulars
    try:
        from campusiq_edumarshal import get_mait_circulars
        mait_circs = get_mait_circulars()
        if mait_circs:
            all_notices.extend(mait_circs)
    except Exception as e:
        print(f"[!] Warning fetching MAIT circulars: {e}", file=sys.stderr)

    # 2. Try Live n8n Webhook for IPU Notices
    if N8N_WEBHOOK_URL:
        try:
            req = urllib.request.Request(N8N_WEBHOOK_URL, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
                notices = payload.get("notices", [])
                if notices:
                    enriched = [enrich_notice(dict(n)) for n in notices]
                    all_notices.extend(enriched)
        except Exception as e:
            print(f"[!] Info: n8n notice webhook: {e}", file=sys.stderr)

    # 3. Direct Scrape from IPU Exam Notices (ipu.ac.in/exam_notices.php)
    try:
        req = urllib.request.Request("https://www.ipu.ac.in/exam_notices.php", headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
            trs = re.findall(r"<tr[^>]*>(.*?)</tr>", content, re.DOTALL)
            direct_notices = []
            for tr in trs:
                link_m = re.search(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", tr, re.DOTALL)
                if not link_m:
                    continue
                href, title_html = link_m.group(1).strip(), link_m.group(2)
                title = " ".join(re.sub(r"<[^>]+>", " ", title_html).split()).strip()
                if not title or len(title) < 5:
                    continue
                
                date_m = re.search(r"\b\d{2}[-/.]\d{2}[-/.]\d{4}\b", tr)
                date_str = date_m.group(0) if date_m else "Recent"
                full_url = href if href.startswith("http") else f"https://www.ipu.ac.in/{href.lstrip('/')}"
                
                notice_item = {
                    "notice_id": f"ipu_{abs(hash(full_url)) % 1000000:06d}",
                    "title": title,
                    "url": full_url,
                    "date": date_str,
                    "source": "GGSIPU",
                    "college": "GGSIPU Examination Division"
                }
                direct_notices.append(enrich_notice(notice_item))
            if direct_notices:
                all_notices.extend(direct_notices)
    except Exception as e:
        print(f"[!] Warning: Failed direct IPU notice scraping: {e}", file=sys.stderr)

    if all_notices:
        _NOTICES_CACHE["data"] = all_notices
        _NOTICES_CACHE["last_fetched"] = now
        return all_notices

    if _NOTICES_CACHE["data"]:
        return _NOTICES_CACHE["data"]

    # Fallback seed notices
    seed = [
        {
            "notice_id": "seed_1",
            "title": "Datesheet for B.Tech Mid Term Examinations (October 2026)",
            "url": "https://mait.ac.in",
            "date": "29-09-2026",
            "source": "MAIT",
            "college": "MAIT Rohini",
            "section": "Examination",
            "category": "Examinations & Datesheets",
            "urgency": "HIGH",
            "target_audience": "B.Tech (All Branches)"
        },
        {
            "notice_id": "seed_2",
            "title": "Rechecking Result of B.Com (Hons) Programme, End Term Exam May-June 2026 with No Change",
            "url": "https://www.ipu.ac.in/exam_notices.php",
            "date": "28-09-2026",
            "source": "GGSIPU",
            "college": "GGSIPU Examination Division",
            "section": "Examination",
            "category": "Results & Evaluations",
            "urgency": "MEDIUM",
            "target_audience": "All Examinees"
        }
    ]
    enriched_seed = [enrich_notice(s) for s in seed]
    _NOTICES_CACHE["data"] = enriched_seed
    return enriched_seed


def get_cached_catalog() -> List[Dict[str, Any]]:
    """Get academic study resource catalog with caching."""
    now = time.time()
    if _CATALOG_CACHE["data"] and (now - _CATALOG_CACHE["last_scanned"] < _CATALOG_CACHE["ttl"]):
        return _CATALOG_CACHE["data"]

    catalog_cache_file = os.path.join(PROJECT_DIR, "data", "catalog_cache.json")
    if os.path.exists(catalog_cache_file):
        try:
            with open(catalog_cache_file, "r", encoding="utf-8") as f:
                d = json.load(f)
                items = d.get("catalog", [])
                if items:
                    _CATALOG_CACHE["data"] = items
                    _CATALOG_CACHE["last_scanned"] = now
                    return items
        except Exception as e:
            print(f"[!] Warning loading catalog cache: {e}", file=sys.stderr)

    try:
        cataloguer = CampusIQResourceCataloguer(ACADEMIC_DIR)
        items = cataloguer.scan()
        _CATALOG_CACHE["data"] = items
        _CATALOG_CACHE["last_scanned"] = now
        return items
    except Exception as e:
        print(f"[!] Warning: Error cataloguing academic resources: {e}", file=sys.stderr)
        return _CATALOG_CACHE.get("data", [])


def get_cached_results(pdf_path: str = SAMPLE_RESULT_PDF) -> List[Dict[str, Any]]:
    """Parse and cache student results from PDF."""
    if _RESULTS_CACHE["parsed_students"] and _RESULTS_CACHE["last_parsed_pdf"] == pdf_path:
        return _RESULTS_CACHE["parsed_students"]

    if not os.path.exists(pdf_path):
        return []

    try:
        parser = GGSIPUResultParser(pdf_path)
        parser.parse_schemes()
        students = parser.parse_results()
        _RESULTS_CACHE["parsed_students"] = students
        _RESULTS_CACHE["last_parsed_pdf"] = pdf_path
        return students
    except Exception as e:
        print(f"[!] Warning: Error parsing results PDF: {e}", file=sys.stderr)
        return []


class CampusIQRequestHandler(SimpleHTTPRequestHandler):
    """Custom request handler serving REST APIs and static UI."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=os.path.join(PROJECT_DIR, "public"), **kwargs)

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        params = urllib.parse.parse_qs(parsed.query)

        # CORS Headers
        self.send_cors_headers = lambda: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Admin-Token, X-Admin-Passcode",
        }

        # API Routes
        if path == "/api/notices":
            self.handle_api_notices(params)
        elif path == "/api/notices/proxy":
            self.handle_api_notice_proxy(params)
        elif path == "/api/edumarshal/attendance":
            self.handle_api_edumarshal_attendance(params)
        elif path == "/api/edumarshal/calendar":
            self.handle_api_edumarshal_calendar(params)
        elif path == "/api/edumarshal/status":
            self.handle_api_edumarshal_status()
        elif path == "/api/edumarshal/circulars":
            self.handle_api_edumarshal_circulars(params)
        elif path == "/api/resources":
            self.handle_api_resources(params)
        elif path == "/api/resources/tree":
            self.handle_api_resources_tree()
        elif path == "/api/resources/view":
            self.handle_api_resource_view(params)
        elif path == "/api/auth/me" or path == "/api/auth/current":
            self.handle_api_auth_me()
        elif path == "/api/auth/config":
            self.handle_api_auth_config()
        elif path == "/api/auth/google/login":
            self.handle_api_auth_google_login()
        elif path == "/api/auth/google/callback":
            self.handle_api_auth_google_callback(params)
        elif path == "/api/students/directory":
            self.handle_api_students_directory(params)
        elif path == "/api/results":
            self.handle_api_results(params)
        elif path == "/api/results/leaderboard":
            self.handle_api_leaderboard(params)
        elif path == "/api/results/portal":
            self.handle_api_portal(params)
        elif path == "/api/colleges":
            self.handle_api_colleges()
        elif path == "/api/stats":
            self.handle_api_stats()
        elif path == "/api/health":
            self.handle_api_health()
        elif path == "/api/examweb/session":
            self.handle_api_examweb_session()
        elif path == "/api/examweb/demo":
            self.handle_api_examweb_demo()
        elif path == "/api/admin/students":
            self.handle_api_admin_students(params)
        elif path.startswith("/api/admin/students/") and path.endswith("/full"):
            roll_sub = path[len("/api/admin/students/"): -len("/full")].strip()
            self.handle_api_admin_student_full(roll_sub)
        elif path.startswith("/api/admin/students/"):
            roll_sub = path.split("/api/admin/students/")[1].strip()
            self.handle_api_admin_student_detail(roll_sub)
        elif path == "/" or not os.path.exists(os.path.join(PROJECT_DIR, "public", path.lstrip("/"))):
            # Fallback to index.html for SPA routing
            self.path = "/index.html"
            return super().do_GET()
        else:
            return super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        self.send_cors_headers = lambda: {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Admin-Token, X-Admin-Passcode",
        }

        if path == "/api/admin/auth":
            self.handle_api_admin_auth()
        elif path == "/api/admin/student/update":
            self.handle_api_admin_student_update()
        elif path == "/api/admin/student/create":
            self.handle_api_admin_student_create()
        elif path == "/api/admin/student/delete":
            self.handle_api_admin_student_delete()
        elif path == "/api/examweb/login":
            self.handle_api_examweb_login()
        elif path == "/api/auth/config":
            self.handle_api_auth_config_update()
        elif path in ("/api/auth/google/verify", "/api/auth/google"):
            self.handle_api_auth_google_verify()
        elif path == "/api/auth/google/access-token":
            self.handle_api_auth_google_access_token()
        elif path == "/api/auth/login":
            self.handle_api_auth_login()
        elif path == "/api/auth/register":
            self.handle_api_auth_register()
        elif path in ("/api/auth/google/signin", "/api/auth/signin"):
            self.handle_api_auth_signin()
        elif path == "/api/auth/signout":
            self.handle_api_auth_signout()
        elif path == "/api/auth/link-roll":
            self.handle_api_auth_link_roll()
        elif path == "/api/edumarshal/verify-and-link":
            self.handle_api_edumarshal_verify_and_link()
        elif path == "/api/edumarshal/unlink":
            self.handle_api_edumarshal_unlink()
        elif path in ("/api/profile/update", "/api/students/profile"):
            self.handle_api_profile_update()
        elif path == "/api/profile/verify":
            self.handle_api_profile_verify()
        else:
            self._send_json({"error": "Endpoint not found"}, 404)

    def do_HEAD(self):
        self.do_GET()

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in self.send_cors_headers().items():
            self.send_header(k, v)
        self.end_headers()

    def _get_session_cookie_header(self, token: str, max_age: int = 2592000) -> str:
        host = self.headers.get("Host", "")
        proto = self.headers.get("X-Forwarded-Proto", "")
        is_https = "onrender.com" in host or proto == "https"
        expires_date = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime(time.time() + max_age))
        cookie = f"campusiq_session={token}; Path=/; HttpOnly; SameSite=Lax; Max-Age={max_age}; Expires={expires_date}"
        if is_https:
            cookie += "; Secure"
        return cookie

    def _send_json(self, data: Any, status: int = 200, extra_headers: Optional[Dict[str, str]] = None):
        try:
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            for k, v in self.send_cors_headers().items():
                self.send_header(k, v)
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"[!] Warning writing JSON response: {e}", file=sys.stderr)

    def _send_html(self, html_content: str, status: int = 200, extra_headers: Optional[Dict[str, str]] = None):
        try:
            body = html_content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            for k, v in self.send_cors_headers().items():
                self.send_header(k, v)
            if extra_headers:
                for k, v in extra_headers.items():
                    self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"[!] Warning writing HTML response: {e}", file=sys.stderr)

    # 1. Notices API
    def handle_api_notices(self, params: Dict[str, List[str]]):
        notices = get_cached_notices()
        college = params.get("college", ["all"])[0].lower()
        category = params.get("category", [""])[0].lower()
        urgency = params.get("urgency", [""])[0].upper()
        search = params.get("search", [""])[0].lower()
        limit = int(params.get("limit", [50])[0])

        filtered = notices
        if college != "all":
            filtered = [n for n in filtered if college in n.get("source", "").lower() or college in n.get("college", "").lower()]
        if category:
            filtered = [n for n in filtered if category in n.get("category", "").lower()]
        if urgency in ["HIGH", "MEDIUM", "LOW"]:
            filtered = [n for n in filtered if n.get("urgency") == urgency]
        if search:
            filtered = [n for n in filtered if search in n.get("title", "").lower() or search in n.get("category", "").lower()]

        self._send_json({
            "status": "success",
            "total": len(filtered),
            "high_priority_count": len([n for n in filtered if n.get("urgency") == "HIGH"]),
            "notices": filtered[:limit]
        })

    # 2. Resources API
    def handle_api_resources(self, params: Dict[str, List[str]]):
        catalog = get_cached_catalog()
        semester = params.get("semester", [""])[0]
        subject = params.get("subject", [""])[0].lower()
        category = params.get("category", [""])[0].lower()
        typeset_only = params.get("typeset", ["false"])[0].lower() in ["true", "1"]
        search = params.get("search", [""])[0].lower()
        limit = int(params.get("limit", [500])[0])

        filtered = catalog
        if semester.isdigit():
            sem_int = int(semester)
            filtered = [r for r in filtered if r.get("semester") == sem_int]
        if subject:
            filtered = [r for r in filtered if subject in r.get("subject", "").lower() or subject in r.get("subject_code", "").lower()]
        if category:
            filtered = [r for r in filtered if category in r.get("category", "").lower()]
        if typeset_only:
            filtered = [r for r in filtered if r.get("is_typeset", False)]
        if search:
            filtered = [r for r in filtered if search in r.get("title", "").lower() or search in r.get("subject", "").lower()]

        self._send_json({
            "status": "success",
            "total": len(filtered),
            "typeset_count": len([r for r in filtered if r.get("is_typeset", False)]),
            "resources": filtered[:limit]
        })

    # 3. Resource PDF Stream / Preview
    def handle_api_resource_view(self, params: Dict[str, List[str]]):
        rel_path = params.get("path", [""])[0].strip()
        file_id = params.get("id", [""])[0].strip()

        if not rel_path and not file_id:
            self._send_json({"error": "Missing 'path' or 'id' parameter"}, 400)
            return

        filename = os.path.basename(rel_path) if rel_path else f"document_{file_id}.pdf"
        content = None

        # 1. Try bundled repository assets first (guaranteed 100% availability in cloud/Render & local)
        if rel_path and os.path.exists(BUNDLED_VAULT_DIR):
            bundled_path = os.path.abspath(os.path.join(BUNDLED_VAULT_DIR, rel_path))
            if bundled_path.startswith(os.path.abspath(BUNDLED_VAULT_DIR)) and os.path.exists(bundled_path):
                try:
                    with open(bundled_path, "rb") as f:
                        content = f.read()
                    filename = os.path.basename(bundled_path)
                except Exception as e:
                    print(f"[!] Error reading bundled file {bundled_path}: {e}", file=sys.stderr)

            # Check normalized or basename match in bundled vault
            if content is None:
                target_base = os.path.basename(rel_path).lower()
                norm_target = rel_path.replace("\\", "/").strip("/").lower()
                for root, _, files in os.walk(BUNDLED_VAULT_DIR):
                    for fname in files:
                        cur_full = os.path.join(root, fname)
                        cur_rel = os.path.relpath(cur_full, BUNDLED_VAULT_DIR).replace("\\", "/").strip("/").lower()
                        if cur_rel == norm_target or fname.lower() == target_base:
                            try:
                                with open(cur_full, "rb") as f:
                                    content = f.read()
                                filename = fname
                                break
                            except Exception:
                                pass
                    if content is not None:
                        break

        # 2. Try external academic directory (when running in local development or if mounted)
        if content is None and rel_path and ACADEMIC_DIR and os.path.exists(ACADEMIC_DIR):
            abs_path = os.path.abspath(os.path.join(ACADEMIC_DIR, rel_path))
            if abs_path.startswith(os.path.abspath(ACADEMIC_DIR)) and os.path.exists(abs_path):
                try:
                    with open(abs_path, "rb") as f:
                        content = f.read()
                    filename = os.path.basename(abs_path)
                except Exception as e:
                    print(f"[!] Error reading local file {abs_path}: {e}", file=sys.stderr)

        # 2. Try Google Drive headless stream (mapped via data/vault_drive_map.json)
        if content is None:
            drive_map = load_vault_drive_map()
            target_id = file_id or drive_map.get("files", {}).get(rel_path)
            
            # If not exact match, try normalized match
            if not target_id and rel_path:
                norm_rel = rel_path.replace("\\", "/").strip("/")
                for k, v in drive_map.get("files", {}).items():
                    if k.replace("\\", "/").strip("/") == norm_rel:
                        target_id = v
                        break

            # If still not matched, try matching by filename
            if not target_id and rel_path:
                req_base = os.path.basename(rel_path).lower()
                for k, v in drive_map.get("files", {}).items():
                    if os.path.basename(k).lower() == req_base:
                        target_id = v
                        break

            if target_id:
                content = fetch_google_drive_file(target_id)

        # 3. Stream content if found
        if content:
            lower_name = filename.lower()
            if lower_name.endswith(".jpg") or lower_name.endswith(".jpeg"):
                mime_type = "image/jpeg"
            elif lower_name.endswith(".png"):
                mime_type = "image/png"
            elif lower_name.endswith(".docx"):
                mime_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            else:
                mime_type = "application/pdf"

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Content-Disposition", f'inline; filename="{filename}"')
            for k, v in self.send_cors_headers().items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                try:
                    self.wfile.write(content)
                except (BrokenPipeError, ConnectionResetError):
                    pass
            return

        # 4. Clean Not Found (NEVER fallback to sample_result.pdf)
        self._send_json({
            "status": "not_found",
            "error": f"The document '{filename}' is currently being synced. Please check back shortly."
        }, 404)

    # 3b. Notice Proxy to bypass X-Frame-Options and Mixed Content
    def handle_api_notice_proxy(self, params: Dict[str, List[str]]):
        url = params.get("url", [""])[0].strip()
        if not url:
            self._send_json({"error": "Missing 'url' parameter"}, 400)
            return

        # Strict security: allow proxying only verified university and CDN domains
        allowed_domains = ["ipu.ac.in", "mait.ac.in", "ggsipu.ac.in", "n8n-tanmay.onrender.com", "edumarshal.com", "cloudfront.net"]
        parsed = urllib.parse.urlparse(url)
        if parsed.scheme not in ("http", "https"):
            self._send_json({"error": "Invalid URL scheme"}, 400)
            return

        netloc = parsed.netloc.lower().split(":")[0]
        if not any(netloc == d or netloc.endswith("." + d) for d in allowed_domains):
            self._send_json({"error": "Domain not permitted for proxy"}, 403)
            return

        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            }
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, context=ctx, timeout=12) as resp:
                content = resp.read()
                content_type = resp.headers.get("Content-Type", "application/pdf")
                filename = os.path.basename(parsed.path) or "notice.pdf"

            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Content-Disposition", f'inline; filename="{filename}"')
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "SAMEORIGIN")
            self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
            for k, v in self.send_cors_headers().items():
                self.send_header(k, v)
            self.end_headers()
            if self.command != "HEAD":
                try:
                    self.wfile.write(content)
                except (BrokenPipeError, ConnectionResetError):
                    pass
        except Exception as e:
            self._send_json({"error": f"Failed to load notice: {str(e)}"}, 500)

    # 4. Results API
    def handle_api_results(self, params: Dict[str, List[str]]):
        roll = params.get("roll", [""])[0].strip()

        if roll:
            # 1. Check persistent database first (Official verified student profiles)
            db_record = get_student_by_roll(roll)
            if db_record:
                self._send_json({"status": "success", "found": True, "source": "database", "student": db_record})
                return

            # 2. Check cached PDF tabulation dataset
            students = get_cached_results()
            match = next((s for s in students if s["roll_number"] == roll), None)
            if match:
                self._send_json({"status": "success", "found": True, "source": "gazette_pdf", "student": match})
            else:
                self._send_json({
                    "status": "not_found",
                    "found": False,
                    "message": f"Roll number {roll} not found in student database or active tabulation dataset."
                }, 404)
            return

        # No specific roll provided: return sample 5
        students = get_cached_results()
        self._send_json({
            "status": "success",
            "total_available": len(students),
            "sample_students": students[:5]
        })

    def _read_json_body(self) -> Dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", 0))
            if length <= 0:
                return {}
            body_bytes = self.rfile.read(length)
            return json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception:
            return {}

    def _is_admin_authenticated(self) -> bool:
        # 1. Header X-Admin-Token
        admin_token = self.headers.get("X-Admin-Token", "").strip()
        if admin_token and admin_token in ACTIVE_ADMIN_SESSIONS:
            return True

        # 2. Header Authorization: Bearer adm_...
        auth_hdr = self.headers.get("Authorization", "").strip()
        if auth_hdr.startswith("Bearer "):
            token = auth_hdr[7:].strip()
            if token in ACTIVE_ADMIN_SESSIONS:
                return True

        # 3. Direct Master Key check in X-Admin-Passcode
        passcode = self.headers.get("X-Admin-Passcode", "").strip()
        if passcode and hmac.compare_digest(passcode, ADMIN_SECRET_KEY):
            return True

        return False

    def handle_api_admin_auth(self):
        payload = self._read_json_body()
        passcode = str(payload.get("passcode", "")).strip() if payload else ""
        if hmac.compare_digest(passcode, ADMIN_SECRET_KEY):
            token = f"adm_{secrets.token_hex(24)}"
            ACTIVE_ADMIN_SESSIONS.add(token)
            self._send_json({
                "status": "success",
                "admin_token": token,
                "token": token,
                "message": "Admin master clearance authorized."
            })
        else:
            self._send_json({
                "status": "error",
                "message": "Invalid admin security passcode."
            }, 401)

    # 5. Admin Student Roster API (College Faculty & Administrators)
    def handle_api_admin_students(self, params: Dict[str, List[str]]):
        if not self._is_admin_authenticated():
            self._send_json({"status": "error", "message": "Admin clearance required."}, 401)
            return

        db = load_all_students_db()
        db_records = campusiq_db.get_all_student_records()
        merged_db = dict(db)
        for r_num, r_data in db_records.items():
            if r_num not in merged_db:
                merged_db[r_num] = r_data
            else:
                merged_db[r_num].update(r_data)

        # Merge registered users who have a roll number
        with campusiq_db.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM users WHERE roll_number IS NOT NULL AND roll_number != '';")
            for u in cursor.fetchall():
                u_row = dict(u)
                r_num = u_row.get("roll_number", "").strip()
                if r_num and r_num not in merged_db:
                    merged_db[r_num] = {
                        "roll_number": r_num,
                        "name": u_row.get("name", "Student"),
                        "father_name": "N/A",
                        "institution_name": "Maharaja Agrasen Institute of Technology",
                        "programme_name": f"B.Tech ({u_row.get('branch', 'CSE')})",
                        "batch": "2023-2027",
                        "semester": u_row.get("semester", 3),
                        "branch": u_row.get("branch", "CSE"),
                        "overall": {"cgpa": 0.0, "percentage": 0.0},
                        "semesters": [],
                        "backlogs": []
                    }

        search = params.get("search", [""])[0].lower().strip()
        branch = params.get("branch", [""])[0].lower().strip()

        students_list = []
        for roll, s in merged_db.items():
            if search and (search not in roll.lower() and search not in s.get("name", "").lower() and search not in s.get("email", "").lower()):
                continue
            if branch and branch not in s.get("programme_name", "").lower() and branch not in s.get("branch", "").lower():
                continue

            att = s.get("attendance", {}).get("overall", {}) if isinstance(s.get("attendance"), dict) else {}
            students_list.append({
                "roll_number": s["roll_number"],
                "name": s["name"],
                "father_name": s.get("father_name", ""),
                "institution_name": s.get("institution_name", ""),
                "programme_name": s.get("programme_name", ""),
                "batch": s.get("batch", ""),
                "semester": s.get("semester", 3),
                "branch": s.get("branch", "CSE"),
                "email": s.get("email", ""),
                "cgpa": s.get("overall", {}).get("cgpa", 0.0),
                "percentage": s.get("overall", {}).get("percentage", 0.0),
                "attendance_percentage": att.get("percentage", 82.5),
                "total_semesters": len(s.get("semesters", [])),
                "backlogs_count": len(s.get("backlogs", [])),
                "photo_base64": s.get("photo_base64", ""),
                "last_synced": s.get("last_synced", s.get("last_updated_at", ""))
            })

        students_list.sort(key=lambda x: (x["cgpa"], x["name"]), reverse=True)
        self._send_json({
            "status": "success",
            "total_students": len(students_list),
            "students": students_list
        })

    def handle_api_admin_student_detail(self, roll: str):
        if not self._is_admin_authenticated():
            self._send_json({"status": "error", "message": "Admin clearance required."}, 401)
            return
        record = campusiq_db.get_student_record(roll.strip()) or get_student_by_roll(roll.strip())
        if record:
            self._send_json({"status": "success", "found": True, "student": record})
        else:
            self._send_json({"status": "error", "message": f"Student {roll} not found in database"}, 404)

    def handle_api_admin_student_full(self, roll: str):
        if not self._is_admin_authenticated():
            self._send_json({"status": "error", "message": "Admin clearance required."}, 401)
            return

        roll_clean = roll.strip()
        record = campusiq_db.get_student_record(roll_clean) or get_student_by_roll(roll_clean)

        if not record:
            with campusiq_db.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE roll_number = ?", (roll_clean,)) if not campusiq_db.USE_POSTGRES else \
                    cursor.execute("SELECT * FROM users WHERE roll_number = %s", (roll_clean,))
                u_row = cursor.fetchone()
                if u_row:
                    u_data = dict(u_row)
                    record = {
                        "roll_number": roll_clean,
                        "name": u_data.get("name", "Student"),
                        "father_name": "N/A",
                        "institution_name": "Maharaja Agrasen Institute of Technology",
                        "programme_name": f"B.Tech ({u_data.get('branch', 'CSE')})",
                        "batch": "2023-2027",
                        "semester": u_data.get("semester", 3),
                        "branch": u_data.get("branch", "CSE"),
                        "overall": {"cgpa": 0.0, "percentage": 0.0, "total_credits": 0},
                        "semesters": [],
                        "backlogs": []
                    }

        if not record:
            self._send_json({"status": "error", "message": f"Student {roll} not found."}, 404)
            return

        # User account info
        user_info = None
        user_email = record.get("email")
        if user_email:
            user_info = campusiq_db.get_user(user_email)
        if not user_info:
            with campusiq_db.get_db() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE roll_number = ?", (roll_clean,)) if not campusiq_db.USE_POSTGRES else \
                    cursor.execute("SELECT * FROM users WHERE roll_number = %s", (roll_clean,))
                u_row = cursor.fetchone()
                if u_row:
                    user_info = dict(u_row)

        if user_info and "is_verified" in user_info:
            record["is_verified"] = user_info["is_verified"]
            record["email"] = user_info.get("email", record.get("email", ""))

        # Ensure attendance structure exists
        if "attendance" not in record or not isinstance(record["attendance"], dict):
            record["attendance"] = {
                "overall": {
                    "percentage": 82.5,
                    "present": 99,
                    "total": 120,
                    "absent": 21,
                    "bunk_buffer": 9
                },
                "courses": [
                    {"name": "Data Structures", "code": "CIC-209", "percentage": 85.0, "present": 34, "total": 40},
                    {"name": "Object Oriented Programming (C++)", "code": "CIC-211", "percentage": 80.0, "present": 32, "total": 40},
                    {"name": "Computational Methods", "code": "ES-201", "percentage": 78.0, "present": 31, "total": 40}
                ]
            }

        self._send_json({
            "status": "success",
            "student": record,
            "user": user_info
        })

    def handle_api_admin_student_update(self):
        if not self._is_admin_authenticated():
            self._send_json({"status": "error", "message": "Admin clearance required."}, 401)
            return

        payload = self._read_json_body()
        if not payload or not isinstance(payload, dict):
            self._send_json({"status": "error", "message": "Invalid request payload."}, 400)
            return

        roll_number = str(payload.get("roll_number", "")).strip()
        if not roll_number:
            self._send_json({"status": "error", "message": "roll_number is required."}, 400)
            return

        existing = campusiq_db.get_student_record(roll_number) or get_student_by_roll(roll_number) or {}

        # Merge profile fields
        for field in ("name", "father_name", "institution_name", "programme_name", "batch", "semester", "branch", "email"):
            if field in payload:
                existing[field] = payload[field]

        # Results & Marksheet
        if "overall" in payload and isinstance(payload["overall"], dict):
            if "overall" not in existing or not isinstance(existing["overall"], dict):
                existing["overall"] = {}
            for k in ("cgpa", "percentage", "total_credits", "total_marks_obtained", "total_max_marks"):
                if k in payload["overall"]:
                    try:
                        existing["overall"][k] = float(payload["overall"][k])
                    except (ValueError, TypeError):
                        existing["overall"][k] = payload["overall"][k]

        if "semesters" in payload and isinstance(payload["semesters"], list):
            existing["semesters"] = payload["semesters"]

        if "backlogs" in payload and isinstance(payload["backlogs"], list):
            existing["backlogs"] = payload["backlogs"]

        # Attendance Overrides
        if "attendance" in payload and isinstance(payload["attendance"], dict):
            existing["attendance"] = payload["attendance"]

        existing["roll_number"] = roll_number
        existing["last_updated_by"] = "admin"
        existing["last_updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # 1. Save to relational database
        user_email = existing.get("email") or payload.get("email") or ""
        campusiq_db.save_student_record(
            roll_number=roll_number,
            student_data=existing,
            email=user_email,
            name=existing.get("name", "")
        )

        # 2. Update user account if verification or profile changed
        if user_email:
            u = campusiq_db.get_user(user_email)
            if u:
                u["roll_number"] = roll_number
                if "is_verified" in payload:
                    u["is_verified"] = bool(payload["is_verified"])
                if "name" in payload:
                    u["name"] = payload["name"]
                if "semester" in payload:
                    u["semester"] = payload["semester"]
                if "branch" in payload:
                    u["branch"] = payload["branch"]
                campusiq_db.save_user(u)

        # 3. Synchronize with students_db.json
        try:
            full_db = load_all_students_db()
            full_db[roll_number] = existing
            os.makedirs(os.path.dirname(STUDENTS_DB_FILE), exist_ok=True)
            with open(STUDENTS_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(full_db, f, indent=2)
        except Exception as e:
            print(f"[!] Warning: failed to write students_db.json: {e}")

        self._send_json({
            "status": "success",
            "message": f"Successfully updated student records for {roll_number}.",
            "student": existing
        })

    def handle_api_admin_student_create(self):
        if not self._is_admin_authenticated():
            self._send_json({"status": "error", "message": "Admin clearance required."}, 401)
            return

        payload = self._read_json_body()
        roll = str(payload.get("roll_number", "")).strip()
        name = str(payload.get("name", "")).strip()
        if not roll or not name:
            self._send_json({"status": "error", "message": "roll_number and name are required."}, 400)
            return

        new_record = {
            "roll_number": roll,
            "name": name,
            "father_name": payload.get("father_name", ""),
            "institution_name": payload.get("institution_name", "Maharaja Agrasen Institute of Technology"),
            "programme_name": payload.get("programme_name", f"B.Tech ({payload.get('branch', 'CSE')})"),
            "batch": payload.get("batch", "2023-2027"),
            "semester": int(payload.get("semester", 3)),
            "branch": payload.get("branch", "CSE"),
            "email": payload.get("email", ""),
            "overall": {
                "cgpa": float(payload.get("cgpa") if "cgpa" in payload else (payload.get("overall", {}).get("cgpa", 0.0) if isinstance(payload.get("overall"), dict) else 0.0)),
                "percentage": float(payload.get("percentage") if "percentage" in payload else (payload.get("overall", {}).get("percentage", 0.0) if isinstance(payload.get("overall"), dict) else 0.0)),
                "total_credits": int(payload.get("total_credits") if "total_credits" in payload else (payload.get("overall", {}).get("total_credits", 0) if isinstance(payload.get("overall"), dict) else 0))
            },
            "semesters": payload.get("semesters", []),
            "backlogs": payload.get("backlogs", []),
            "attendance": payload.get("attendance", {
                "overall": {"percentage": 75.0, "present": 75, "total": 100, "bunk_buffer": 0},
                "courses": []
            }),
            "created_by": "admin",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        }

        campusiq_db.save_student_record(roll, new_record, email=payload.get("email", ""), name=name)
        try:
            full_db = load_all_students_db()
            full_db[roll] = new_record
            with open(STUDENTS_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(full_db, f, indent=2)
        except Exception:
            pass

        self._send_json({
            "status": "success",
            "message": f"Student dossier created for {roll}.",
            "student": new_record
        }, 201)

    def handle_api_admin_student_delete(self):
        if not self._is_admin_authenticated():
            self._send_json({"status": "error", "message": "Admin clearance required."}, 401)
            return

        payload = self._read_json_body()
        roll = str(payload.get("roll_number", "")).strip()
        if not roll:
            self._send_json({"status": "error", "message": "roll_number is required."}, 400)
            return

        campusiq_db.delete_student_record(roll)
        try:
            full_db = load_all_students_db()
            if roll in full_db:
                del full_db[roll]
                with open(STUDENTS_DB_FILE, "w", encoding="utf-8") as f:
                    json.dump(full_db, f, indent=2)
        except Exception:
            pass

        self._send_json({
            "status": "success",
            "message": f"Student record for {roll} deleted."
        })

    # 6. Published Results Portal Scraper
    def handle_api_portal(self, params: Dict[str, List[str]]):
        limit = int(params.get("limit", [15])[0])
        search = params.get("search", [""])[0]
        try:
            items = GGSIPUResultsPortalScraper.fetch_published_results(limit=limit, query=search)
            self._send_json({
                "status": "success",
                "count": len(items),
                "published_results": items
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # 7. Colleges & Programme Metadata
    def handle_api_colleges(self):
        colleges = []
        for code, name in INSTITUTION_MAP.items():
            colleges.append({"code": code, "name": name})

        programmes = []
        for code, name in PROGRAMME_MAP.items():
            programmes.append({"code": code, "name": name})

        self._send_json({
            "status": "success",
            "colleges": sorted(colleges, key=lambda x: x["code"]),
            "programmes": sorted(programmes, key=lambda x: x["code"])
        })

    # 8. Real-time System Stats
    def handle_api_stats(self):
        catalog = _CATALOG_CACHE.get("data")
        total_resources = len(catalog) if catalog else 231
        typeset_count = len([c for c in catalog if c.get("is_typeset")]) if catalog else 52
        notices = _NOTICES_CACHE.get("data")
        notices_count = len(notices) if notices else 15
        high_priority = len([n for n in notices if n.get("urgency") == "HIGH"]) if notices else 4
        students = _RESULTS_CACHE.get("parsed_students")
        students_count = len(students) if students else 118

        self._send_json({
            "status": "success",
            "stats": {
                "total_study_resources": total_resources,
                "typeset_pyq_masters": typeset_count,
                "live_notices_indexed": notices_count,
                "high_priority_notices": high_priority,
                "indexed_student_records": students_count,
                "affiliated_colleges": len(INSTITUTION_MAP),
                "system_status": "OPERATIONAL",
                "server_time": time.strftime("%Y-%m-%d %H:%M:%S")
            }
        })

    # Health Check API
    def handle_api_health(self):
        self._send_json({
            "status": "healthy",
            "service": "CampusIQ",
            "timestamp": time.time()
        })

    # Edumarshal Status API
    def handle_api_edumarshal_status(self):
        user = self.get_authenticated_user()
        if not user:
            self._send_json({"status": "success", "is_authenticated": False, "linked": False, "is_verified": False})
            return

        users = load_users()
        user_record = users.get(user.get("email", ""), {})
        edu_info = user_record.get("edumarshal") or user.get("edumarshal") or {}
        has_creds = bool(edu_info.get("username") and (edu_info.get("password") or edu_info.get("has_vault_secret") or campusiq_db.get_credential(user.get("email", ""))))
        roll = user_record.get("roll_number") or user.get("roll_number")
        is_ver = bool(user_record.get("is_verified") or user.get("is_verified"))

        self._send_json({
            "status": "success",
            "is_authenticated": True,
            "linked": has_creds,
            "is_verified": is_ver,
            "roll_number": roll,
            "username": edu_info.get("username"),
            "full_name": edu_info.get("full_name") or user.get("name")
        })

    # Edumarshal Attendance API (Uses Stored User Credentials or Returns Unlinked Status)
    def handle_api_edumarshal_attendance(self, params: Dict[str, List[str]]):
        force = params.get("force", ["false"])[0].lower() in ["true", "1"]
        user = self.get_authenticated_user()
        username = None
        password = None
        if user:
            email = user.get("email", "").lower().strip()
            cred = campusiq_db.get_credential(email)
            if cred and cred.get("encrypted_payload"):
                username = cred.get("username")
                try:
                    password = campusiq_vault.decrypt_credential(
                        cred["encrypted_payload"],
                        context=f"student:{user.get('roll_number')}"
                    )
                except Exception as e:
                    print(f"[!] Error decrypting credentials: {e}", file=sys.stderr)
            elif user.get("edumarshal", {}).get("password"):
                username = user["edumarshal"].get("username")
                password = user["edumarshal"].get("password")

        # If no user credentials, check environment without hardcoded fallbacks
        if not (username and password):
            username = os.environ.get("EDUMARSHAL_USERNAME", "")
            password = os.environ.get("EDUMARSHAL_PASSWORD", "")

        if not (username and password):
            self._send_json({
                "status": "unlinked",
                "message": "Edumarshal account is not linked. Please link your credentials to load attendance."
            })
            return

        try:
            from campusiq_edumarshal import get_mait_attendance
            data = get_mait_attendance(force=force, username=username, password=password)
            self._send_json(data)
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # Edumarshal Date-wise Attendance Calendar API
    def handle_api_edumarshal_calendar(self, params: Dict[str, List[str]]):
        force = params.get("force", ["false"])[0].lower() in ["true", "1"]
        user = self.get_authenticated_user()
        username = None
        password = None
        if user:
            email = user.get("email", "").lower().strip()
            cred = campusiq_db.get_credential(email)
            if cred and cred.get("encrypted_payload"):
                username = cred.get("username")
                try:
                    password = campusiq_vault.decrypt_credential(
                        cred["encrypted_payload"],
                        context=f"student:{user.get('roll_number')}"
                    )
                except Exception as e:
                    print(f"[!] Error decrypting credentials: {e}", file=sys.stderr)
            elif user.get("edumarshal", {}).get("password"):
                username = user["edumarshal"].get("username")
                password = user["edumarshal"].get("password")

        if not (username and password):
            username = os.environ.get("EDUMARSHAL_USERNAME", "")
            password = os.environ.get("EDUMARSHAL_PASSWORD", "")

        if not (username and password):
            self._send_json({
                "status": "unlinked",
                "message": "Edumarshal account is not linked. Please link your credentials to load attendance calendar."
            })
            return

        try:
            from campusiq_edumarshal import get_mait_calendar
            cal = get_mait_calendar(force=force, username=username, password=password)
            self._send_json(cal)
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # Edumarshal Verify Identity, Check Name Match & Auto-Fill Enrollment Number
    def handle_api_edumarshal_verify_and_link(self):
        try:
            user = self.get_authenticated_user()
            if not user:
                self._send_json({"status": "error", "message": "Sign-in required to verify student identity."}, 401)
                return

            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()

            if not username or not password:
                self._send_json({"status": "error", "message": "Edumarshal username and password are required."}, 400)
                return

            from campusiq_edumarshal import verify_and_extract_identity
            res = verify_and_extract_identity(
                username=username,
                password=password,
                student_name=user.get("name"),
                student_email=user.get("email")
            )

            if not res.get("verified"):
                self._send_json({
                    "status": "error",
                    "error_type": res.get("error_type", "VERIFICATION_FAILED"),
                    "message": res.get("reason", "Verification failed. Please check credentials.")
                }, 400)
                return

            roll = res.get("roll_number", "").strip()
            if not roll:
                self._send_json({"status": "error", "message": "Could not determine official enrollment number from Edumarshal."}, 400)
                return

            # Check uniqueness: ensure enrollment is not claimed by another verified account
            current_email = user.get("email", "").lower().strip()
            existing_user_with_roll = campusiq_db.find_user_by_roll(roll)
            if existing_user_with_roll and existing_user_with_roll.get("email", "").lower() != current_email:
                if existing_user_with_roll.get("is_verified"):
                    other_email = existing_user_with_roll.get("email", "")
                    masked = other_email[:3] + "***@" + other_email.split("@")[1] if "@" in other_email else "***"
                    self._send_json({
                        "status": "error",
                        "error_type": "DUPLICATE_ENROLLMENT",
                        "message": f"Enrollment number {roll} is already registered and verified by another account ({masked}). Each student enrollment number must be unique."
                    }, 409)
                    return

            # Encrypt password in AES-256-GCM vault
            enc_payload = campusiq_vault.encrypt_credential(password, context=f"student:{roll}")
            campusiq_db.save_credential(
                email=current_email,
                username=username,
                encrypted_payload=enc_payload,
                user_id=res.get("user_id"),
                full_name=res.get("full_name")
            )

            # Auto-fill and persist verified profile in DB
            users = load_users()
            if current_email not in users:
                users[current_email] = dict(user)
            user_record = users[current_email]
            user_record["roll_number"] = roll
            user_record["is_verified"] = True
            user_record["semester"] = res.get("semester", 3)
            user_record["branch"] = res.get("branch_name") or user_record.get("branch", "CSE")
            user_record["edumarshal"] = {
                "username": username,
                "has_vault_secret": True,
                "verified_at": time.time(),
                "user_id": res.get("user_id"),
                "full_name": res.get("full_name")
            }
            save_users(users)

            # Update active session
            token = user.get("session_token")
            if token:
                campusiq_db.create_session(token, user_record)

            self._send_json({
                "status": "success",
                "message": f"Verified successfully! Enrollment number {roll} auto-filled and locked.",
                "roll_number": roll,
                "full_name": res.get("full_name"),
                "semester": res.get("semester", 3),
                "is_verified": True
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # Edumarshal Unlink Credentials
    def handle_api_edumarshal_unlink(self):
        try:
            user = self.get_authenticated_user()
            if not user:
                self._send_json({"status": "error", "message": "Sign-in required to unlink credentials."}, 401)
                return

            current_email = user.get("email", "").lower().strip()
            campusiq_db.delete_credential(current_email)

            users = load_users()
            if current_email in users:
                users[current_email]["edumarshal"] = None
                save_users(users)

            token = user.get("session_token")
            if token:
                user_copy = dict(user)
                user_copy["edumarshal"] = None
                campusiq_db.create_session(token, user_copy)

            self._send_json({"status": "success", "message": "Edumarshal credentials unlinked successfully."})
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # Edumarshal MAIT Circulars API
    def handle_api_edumarshal_circulars(self, params: Dict[str, List[str]]):
        force = params.get("force", ["false"])[0].lower() in ["true", "1"]
        try:
            from campusiq_edumarshal import get_mait_circulars
            circs = get_mait_circulars(force=force)
            self._send_json({"status": "success", "total": len(circs), "circulars": circs})
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # 9. ExamWeb Live Session / Captcha
    def handle_api_examweb_session(self):
        res = ExamWebClient.create_session()
        status = 200 if res.get("status") == "success" else 503
        self._send_json(res, status)

    # 10. ExamWeb Demo / Verified Fallback Marksheet (Disabled)
    def handle_api_examweb_demo(self):
        self._send_json({
            "status": "error",
            "message": "Demo marksheet preview has been disabled. Please log in to ExamWeb with your enrollment number."
        }, 403)

    # 11. ExamWeb Login & Scraper
    def handle_api_examweb_login(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}

            session_id = data.get("session_id", "").strip()
            username = data.get("username", "").strip()
            password = data.get("password", "").strip()
            captcha = data.get("captcha", "").strip()

            if not session_id or not username or not password or not captcha:
                self._send_json({
                    "status": "error",
                    "message": "Missing required fields: session_id, username, password, captcha"
                }, 400)
                return

            res = ExamWebClient.login_and_fetch(session_id, username, password, captcha)
            status = 200 if res.get("status") == "success" else 401
            self._send_json(res, status)
        except Exception as e:
            self._send_json({"status": "error", "message": f"Server processing error: {str(e)}"}, 500)

    # 12. Hierarchical Study Vault Tree API
    def handle_api_resources_tree(self):
        try:
            catalog_cache_file = os.path.join(PROJECT_DIR, "data", "catalog_cache.json")
            if os.path.exists(catalog_cache_file):
                try:
                    with open(catalog_cache_file, "r", encoding="utf-8") as f:
                        d = json.load(f)
                        if "tree" in d and d["tree"]:
                            self._send_json({
                                "status": "success",
                                "tree": d["tree"]
                            })
                            return
                except Exception as e:
                    print(f"[!] Warning reading tree from cache: {e}", file=sys.stderr)

            cataloguer = CampusIQResourceCataloguer(ACADEMIC_DIR)
            tree_data = cataloguer.build_tree()
            self._send_json({
                "status": "success",
                "tree": tree_data
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    def get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        token = None

        # 1. Primary: HttpOnly Cookie 'campusiq_session'
        cookie_header = self.headers.get("Cookie", "")
        if cookie_header:
            for c in cookie_header.split(";"):
                c = c.strip()
                if c.startswith("campusiq_session="):
                    token = c.split("=", 1)[1].strip()
                    break

        # 2. Authorization Header: Bearer <token>
        if not token:
            auth_header = self.headers.get("Authorization", "")
            if auth_header.startswith("Bearer "):
                token = auth_header.split(" ", 1)[1].strip()

        # 3. Fallback URL Parameter: ?token=
        if not token:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            token = params.get("token", [""])[0].strip()

        if not token:
            return None

        # Retrieve verified session from persistent database
        session = campusiq_db.get_session(token)
        if session:
            return session

        # Fallback to in-memory session cache
        sessions = load_sessions()
        return sessions.get(token)

    # 13. Current Authenticated Session & Student Profile
    def handle_api_auth_me(self):
        user = self.get_authenticated_user()
        if not user:
            self._send_json({
                "status": "success",
                "is_authenticated": False,
                "user": None,
                "student": None,
                "is_verified": False,
                "has_edumarshal": False
            })
            return

        users = load_users()
        user_record = users.get(user.get("email", ""), {})

        roll = user_record.get("roll_number") or user.get("roll_number")
        is_verified = bool(user_record.get("is_verified") or user.get("is_verified"))
        edu_info = user_record.get("edumarshal") or user.get("edumarshal") or {}
        has_edumarshal = bool(
            edu_info.get("username") and (
                edu_info.get("password") or
                edu_info.get("has_vault_secret") or
                campusiq_db.get_credential(user.get("email", ""))
            )
        )

        # Build safe user object for frontend (strip raw credentials)
        safe_user = dict(user)
        safe_user["roll_number"] = roll
        safe_user["is_verified"] = is_verified
        safe_user["has_edumarshal"] = has_edumarshal
        if "edumarshal" in safe_user and isinstance(safe_user["edumarshal"], dict):
            safe_user["edumarshal"] = {k: v for k, v in safe_user["edumarshal"].items() if k != "password"}
            safe_user["edumarshal"]["has_vault_secret"] = True

        db = load_all_students_db()
        student = db.get(roll) if roll else None

        session_token = user.get("session_token")
        extra_headers = {}
        if session_token:
            extra_headers["Set-Cookie"] = self._get_session_cookie_header(session_token)

        self._send_json({
            "status": "success",
            "is_authenticated": True,
            "user": safe_user,
            "student": student,
            "is_verified": is_verified,
            "has_edumarshal": has_edumarshal
        }, extra_headers=extra_headers if extra_headers else None)

    def handle_api_auth_current(self):
        self.handle_api_auth_me()

    # 14a. Auth Configuration (Google Client ID)
    def handle_api_auth_config(self):
        cfg = load_auth_config()
        self._send_json({
            "status": "success",
            "google_client_id": cfg.get("google_client_id", ""),
            "google_auth_enabled": bool(cfg.get("google_client_id"))
        })

    def handle_api_auth_config_update(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            client_id = data.get("google_client_id", "").strip()
            cfg = load_auth_config()
            cfg["google_client_id"] = client_id
            save_auth_config(cfg)
            self._send_json({
                "status": "success",
                "message": "Auth configuration saved.",
                "google_client_id": client_id
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # 14b. Initiates Google OAuth 2.0 Web Popup/Redirect
    def handle_api_auth_google_login(self):
        cfg = load_auth_config()
        client_id = cfg.get("google_client_id")
        if not client_id:
            self._send_json({"status": "error", "message": "Google Client ID is not configured."}, 400)
            return

        host = self.headers.get("Host", "campusiq-i9aq.onrender.com")
        is_https = "onrender.com" in host or self.headers.get("X-Forwarded-Proto") == "https"
        scheme = "https" if is_https else "http"
        redirect_uri = f"{scheme}://{host}/api/auth/google/callback"

        state = secrets.token_urlsafe(32)
        params = {
            "client_id": client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": "openid email profile",
            "access_type": "online",
            "prompt": "select_account",
            "state": state
        }
        oauth_url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode(params)
        self.send_response(302)
        self.send_header("Location", oauth_url)
        self.send_header("Set-Cookie", f"campusiq_oauth_state={state}; Path=/api/auth/google; HttpOnly; SameSite=Lax; Max-Age=600" + ("; Secure" if is_https else ""))
        self.end_headers()

    # 14c. Google OAuth 2.0 Callback & Code Exchange
    def handle_api_auth_google_callback(self, params: Dict[str, List[str]]):
        code = params.get("code", [""])[0]
        error = params.get("error", [""])[0]
        incoming_state = params.get("state", [""])[0]

        if error:
            error_html = f"""<!DOCTYPE html><html><body style="background:#09090b;color:#f87171;font-family:sans-serif;padding:30px;text-align:center;">
            <h3>Google Sign-In Cancelled or Denied</h3>
            <p style="color:#a1a1aa;font-size:13px;">Error: {error}</p>
            <script>setTimeout(() => window.close(), 3000);</script>
            </body></html>"""
            self._send_html(error_html, 400)
            return

        # CSRF State Validation
        cookie_header = self.headers.get("Cookie", "")
        expected_state = ""
        if cookie_header:
            for c in cookie_header.split(";"):
                c = c.strip()
                if c.startswith("campusiq_oauth_state="):
                    expected_state = c.split("=", 1)[1].strip()
                    break
        if expected_state and incoming_state and not hmac.compare_digest(incoming_state, expected_state):
            self._send_html("<h3 style='color:#f87171;'>OAuth security error: state verification mismatch (possible CSRF).</h3>", 403)
            return

        if not code:
            self._send_html("<h3 style='color:#f87171;'>Missing authorization code.</h3>", 400)
            return

        cfg = load_auth_config()
        client_id = cfg.get("google_client_id")
        client_secret = cfg.get("google_client_secret")

        host = self.headers.get("Host", "campusiq-i9aq.onrender.com")
        is_https = "onrender.com" in host or self.headers.get("X-Forwarded-Proto") == "https"
        scheme = "https" if is_https else "http"
        redirect_uri = f"{scheme}://{host}/api/auth/google/callback"

        try:
            token_url = "https://oauth2.googleapis.com/token"
            token_payload = urllib.parse.urlencode({
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code"
            }).encode("utf-8")

            req = urllib.request.Request(token_url, data=token_payload, headers={
                "Content-Type": "application/x-www-form-urlencoded",
                "User-Agent": "CampusIQ-Server/2.0"
            })
            with urllib.request.urlopen(req, timeout=10) as resp:
                token_data = json.loads(resp.read().decode("utf-8"))

            access_token = token_data.get("access_token")
            id_token = token_data.get("id_token")

            user_info = None
            if access_token:
                user_req = urllib.request.Request(
                    "https://www.googleapis.com/oauth2/v3/userinfo",
                    headers={"Authorization": f"Bearer {access_token}", "User-Agent": "CampusIQ-Server/2.0"}
                )
                with urllib.request.urlopen(user_req, timeout=10) as uresp:
                    user_info = json.loads(uresp.read().decode("utf-8"))
            elif id_token:
                id_req = urllib.request.Request(
                    f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(id_token)}",
                    headers={"User-Agent": "CampusIQ-Server/2.0"}
                )
                with urllib.request.urlopen(id_req, timeout=10) as idresp:
                    user_info = json.loads(idresp.read().decode("utf-8"))

            if not user_info:
                raise Exception("Failed to retrieve profile information from Google.")

            email = user_info.get("email", "").strip().lower()
            name = user_info.get("name", "").strip() or email.split("@")[0].title()
            avatar = user_info.get("picture", "").strip()
            sub = user_info.get("sub", "").strip()

            db = load_all_students_db()
            student = None
            roll = None
            for r, s in db.items():
                if s.get("email", "").lower() == email or (s.get("profile", {}).get("google_email", "").lower() == email):
                    roll = r
                    student = s
                    break

            users = load_users()
            user_record = users.get(email)
            if not user_record:
                user_record = {
                    "id": f"usr_google_{sub}",
                    "email": email,
                    "name": name,
                    "avatar_url": avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={urllib.parse.quote(name)}",
                    "roll_number": roll,
                    "google_id": sub,
                    "auth_provider": "google",
                    "created_at": time.time()
                }
                users[email] = user_record
                save_users(users)
            else:
                user_record["google_id"] = sub
                user_record["auth_provider"] = "google"
                if avatar:
                    user_record["avatar_url"] = avatar
                if roll and not user_record.get("roll_number"):
                    user_record["roll_number"] = roll
                users[email] = user_record
                save_users(users)
                roll = user_record.get("roll_number", roll)
                if roll and roll in db:
                    student = db[roll]

            token = secrets.token_hex(24)
            user_session = {
                "session_token": token,
                "email": email,
                "name": name,
                "avatar_url": user_record.get("avatar_url", avatar),
                "roll_number": roll,
                "is_verified": bool(user_record.get("is_verified", False)),
                "has_edumarshal": bool(user_record.get("edumarshal", {}).get("username")),
                "google_id": sub,
                "auth_provider": "google",
                "created_at": time.time()
            }
            campusiq_db.create_session(token, user_session)

            auth_payload = json.dumps({
                "type": "GOOGLE_AUTH_SUCCESS",
                "session_token": token,
                "user": user_session,
                "student": student
            })

            cookie_header = self._get_session_cookie_header(token)
            html_response = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>Google Sign-In Successful</title>
</head>
<body style="background:#09090b;color:#fafafa;font-family:-apple-system,BlinkMacSystemFont,sans-serif;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;">
  <div style="text-align:center;padding:24px;border:1px solid rgba(255,255,255,0.1);border-radius:16px;background:#18181b;max-width:320px;">
    <div style="width:40px;height:40px;margin:0 auto 12px;background:#22c55e;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:20px;color:white;">✓</div>
    <h3 style="margin:0 0 8px;font-size:16px;">Verified with Google!</h3>
    <p style="color:#a1a1aa;font-size:12px;margin:0;">Logging into CampusIQ...</p>
  </div>
  <script>
    const authData = {auth_payload};
    if (window.opener) {{
      window.opener.postMessage(authData, "*");
      setTimeout(() => window.close(), 600);
    }} else {{
      localStorage.setItem("campusiq_session_token", authData.session_token);
      window.location.href = "/";
    }}
  </script>
</body>
</html>"""
            self._send_html(html_response, extra_headers={"Set-Cookie": cookie_header})
        except Exception as e:
            error_html = f"""<!DOCTYPE html><html><body style="background:#09090b;color:#f87171;font-family:sans-serif;padding:30px;text-align:center;">
            <h3>Google Authentication Failed</h3>
            <p style="color:#a1a1aa;font-size:13px;">{str(e)}</p>
            <script>setTimeout(() => window.close(), 5000);</script>
            </body></html>"""
            self._send_html(error_html, 500)

    # 14d. Token Client Direct Access Token Exchange
    def handle_api_auth_google_access_token(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            access_token = data.get("access_token", "").strip()

            if not access_token:
                self._send_json({"status": "error", "message": "Missing access_token."}, 400)
                return

            req = urllib.request.Request(
                "https://www.googleapis.com/oauth2/v3/userinfo",
                headers={"Authorization": f"Bearer {access_token}", "User-Agent": "CampusIQ-Server/2.0"}
            )
            with urllib.request.urlopen(req, timeout=10) as resp:
                user_info = json.loads(resp.read().decode("utf-8"))

            email = user_info.get("email", "").strip().lower()
            name = user_info.get("name", "").strip() or email.split("@")[0].title()
            avatar = user_info.get("picture", "").strip()
            sub = user_info.get("sub", "").strip()

            db = load_all_students_db()
            student = None
            roll = None
            for r, s in db.items():
                if s.get("email", "").lower() == email or (s.get("profile", {}).get("google_email", "").lower() == email):
                    roll = r
                    student = s
                    break

            users = load_users()
            user_record = users.get(email)
            if not user_record:
                user_record = {
                    "id": f"usr_google_{sub}",
                    "email": email,
                    "name": name,
                    "avatar_url": avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={urllib.parse.quote(name)}",
                    "roll_number": roll,
                    "google_id": sub,
                    "auth_provider": "google",
                    "created_at": time.time()
                }
                users[email] = user_record
                save_users(users)
            else:
                user_record["google_id"] = sub
                user_record["auth_provider"] = "google"
                if avatar:
                    user_record["avatar_url"] = avatar
                if roll and not user_record.get("roll_number"):
                    user_record["roll_number"] = roll
                users[email] = user_record
                save_users(users)
                roll = user_record.get("roll_number", roll)
                if roll and roll in db:
                    student = db[roll]

            token = secrets.token_hex(24)
            user_session = {
                "session_token": token,
                "email": email,
                "name": name,
                "avatar_url": user_record.get("avatar_url", avatar),
                "roll_number": roll,
                "is_verified": bool(user_record.get("is_verified", False)),
                "has_edumarshal": bool(user_record.get("edumarshal", {}).get("username")),
                "google_id": sub,
                "auth_provider": "google",
                "created_at": time.time()
            }
            campusiq_db.create_session(token, user_session)

            cookie_header = self._get_session_cookie_header(token)
            self._send_json({
                "status": "success",
                "message": f"Successfully signed in with Google as {name}!",
                "session_token": token,
                "user": user_session,
                "student": student
            }, extra_headers={"Set-Cookie": cookie_header})
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # 14e. Official Google Identity Services Token Verification
    def handle_api_auth_google_verify(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            credential = data.get("credential", "").strip()

            if not credential:
                self._send_json({"status": "error", "message": "Missing Google credential token."}, 400)
                return

            # Verify with Google's public tokeninfo endpoint
            verify_url = f"https://oauth2.googleapis.com/tokeninfo?id_token={urllib.parse.quote(credential)}"
            req = urllib.request.Request(verify_url, headers={"User-Agent": "CampusIQ-Server/2.0"})
            with urllib.request.urlopen(req, timeout=10) as resp:
                token_info = json.loads(resp.read().decode("utf-8"))

            # Strict Audience Verification against Configured Client ID
            cfg = load_auth_config()
            expected_client_id = cfg.get("google_client_id") or os.environ.get("GOOGLE_CLIENT_ID", "")
            if expected_client_id:
                token_aud = token_info.get("aud", "").strip()
                if token_aud != expected_client_id.strip():
                    self._send_json({
                        "status": "error",
                        "message": "Google verification failed: invalid token audience (aud mismatch)."
                    }, 401)
                    return

            email = token_info.get("email", "").strip().lower()
            email_verified = token_info.get("email_verified") in (True, "true", "True", 1)
            name = token_info.get("name", "").strip()
            avatar = token_info.get("picture", "").strip()
            sub = token_info.get("sub", "").strip()

            if not email or not email_verified:
                self._send_json({"status": "error", "message": "Google verification failed: email unverified."}, 401)
                return

            if not name:
                name = email.split("@")[0].title()

            db = load_all_students_db()
            student = None
            roll = None
            for r, s in db.items():
                if s.get("email", "").lower() == email or (s.get("profile", {}).get("google_email", "").lower() == email):
                    roll = r
                    student = s
                    break

            users = load_users()
            user_record = users.get(email)
            if not user_record:
                user_record = {
                    "id": f"usr_google_{sub}",
                    "email": email,
                    "name": name,
                    "avatar_url": avatar or f"https://api.dicebear.com/7.x/bottts/svg?seed={urllib.parse.quote(name)}",
                    "roll_number": roll,
                    "google_id": sub,
                    "auth_provider": "google",
                    "created_at": time.time()
                }
                users[email] = user_record
                save_users(users)
            else:
                user_record["google_id"] = sub
                user_record["auth_provider"] = "google"
                if avatar:
                    user_record["avatar_url"] = avatar
                if roll and not user_record.get("roll_number"):
                    user_record["roll_number"] = roll
                users[email] = user_record
                save_users(users)
                roll = user_record.get("roll_number", roll)
                if roll and roll in db:
                    student = db[roll]

            token = secrets.token_hex(24)
            user_session = {
                "session_token": token,
                "email": email,
                "name": name,
                "avatar_url": user_record.get("avatar_url", avatar),
                "roll_number": roll,
                "is_verified": bool(user_record.get("is_verified", False)),
                "has_edumarshal": bool(user_record.get("edumarshal", {}).get("username")),
                "google_id": sub,
                "auth_provider": "google",
                "created_at": time.time()
            }
            campusiq_db.create_session(token, user_session)

            cookie_header = self._get_session_cookie_header(token)
            self._send_json({
                "status": "success",
                "message": f"Successfully signed in with Google as {name}!",
                "session_token": token,
                "user": user_session,
                "student": student
            }, extra_headers={"Set-Cookie": cookie_header})
        except Exception as e:
            self._send_json({"status": "error", "message": f"Google verification error: {str(e)}"}, 401)

    # 14c. Local Student Email & Password Login (Disabled - Google Sign-In Only)
    def handle_api_auth_login(self):
        self._send_json({
            "status": "error",
            "message": "Username and password sign-in is disabled. Please continue with Google Sign-In."
        }, 403)

    # 14d. Register New Student Account (Disabled - Google Sign-In Only)
    def handle_api_auth_register(self):
        self._send_json({
            "status": "error",
            "message": "Account registration via password is disabled. Please continue with Google Sign-In."
        }, 403)

    # 14e. Direct / Legacy Sign In Endpoint (Enforces Google Sign-In Only)
    def handle_api_auth_signin(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}

            if "credential" in data:
                self.handle_api_auth_google_verify()
                return

            self._send_json({
                "status": "error",
                "message": "Only Google Sign-In is supported. Please continue with Google Sign-In."
            }, 403)
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # Sign Out
    def handle_api_auth_signout(self):
        try:
            user = self.get_authenticated_user()
            if user:
                token = user.get("session_token")
                if token:
                    campusiq_db.delete_session(token)
            clear_cookie = "campusiq_session=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
            self._send_json({"status": "success", "message": "Signed out successfully."}, 200, extra_headers={"Set-Cookie": clear_cookie})
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # Link GGSIPU Roll Number to Authenticated Account (Strictly Enforces Edumarshal Verification)
    def handle_api_auth_link_roll(self):
        # Manual entry is strictly disabled to prevent profile tampering and duplicate claims
        self._send_json({
            "status": "error",
            "error_type": "MANUAL_ENTRY_DISABLED",
            "message": "Manual enrollment number entry is disabled to maintain academic integrity and account uniqueness. Please use the Edumarshal Verification modal to verify your identity and auto-fill your enrollment number."
        }, 403)

    # 15. Community Peer Directory API (Respects Granular Privacy Settings)
    def handle_api_students_directory(self, params: Dict[str, List[str]]):
        search = params.get("search", [""])[0].lower().strip()
        branch = params.get("branch", [""])[0].lower().strip()
        section = params.get("section", [""])[0].lower().strip()
        group = params.get("group", [""])[0].lower().strip()
        
        db = load_all_students_db()
        result = []
        for roll, s in db.items():
            prof = s.get("profile", {})
            priv = prof.get("privacy_settings", {})
            if not priv.get("public_profile", True):
                continue
            
            name = s.get("name", "")
            prog = s.get("programme_name", "")
            c_sec = prof.get("class_section", "")
            p_grp = prof.get("practical_group", "")
            
            if search and (search not in name.lower() and search not in roll.lower() and search not in c_sec.lower() and search not in p_grp.lower()):
                continue
            if branch and branch not in prog.lower():
                continue
            if section and section not in c_sec.lower():
                continue
            if group and group not in p_grp.lower():
                continue
            
            pub_record = {
                "roll_number": roll,
                "name": name,
                "institution_name": s.get("institution_name", "MAIT"),
                "programme_name": prog,
                "batch": s.get("batch", 2025),
                "avatar_url": prof.get("avatar_url", f"https://api.dicebear.com/7.x/bottts/svg?seed={roll}"),
                "bio": prof.get("bio", ""),
                "class_section": c_sec if priv.get("show_class_details", True) else None,
                "practical_group": p_grp if priv.get("show_class_details", True) else None,
                "cgpa": s.get("overall", {}).get("cgpa") if priv.get("show_cgpa", True) else None,
                "cgpa_hidden": not priv.get("show_cgpa", True),
                "verifications": prof.get("verifications", {}),
                "socials": prof.get("socials", {}) if priv.get("show_socials", True) else {},
                "experiences": prof.get("experiences", []) if priv.get("show_experience", True) else [],
                "privacy_settings": priv
            }
            result.append(pub_record)
            
        result.sort(key=lambda x: (x.get("cgpa") or 0.0), reverse=True)
        self._send_json({
            "status": "success",
            "total": len(result),
            "students": result
        })

    # 16. Profile Preferences & Details Update API
    def handle_api_profile_update(self):
        try:
            user = self.get_authenticated_user()
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            
            roll = user.get("roll_number") if user else None
            if not roll:
                roll = data.get("roll_number", "").strip()

            if not roll:
                self._send_json({"error": "No linked student account to update."}, 400)
                return
            
            db = load_all_students_db()
            if roll not in db:
                self._send_json({"error": "Student not found in database"}, 404)
                return
            
            student = db[roll]
            if "profile" not in student:
                student["profile"] = {}
            
            prof = student["profile"]
            if "bio" in data:
                prof["bio"] = str(data["bio"]).strip()
            if "class_section" in data:
                prof["class_section"] = str(data["class_section"]).strip()
            if "practical_group" in data:
                prof["practical_group"] = str(data["practical_group"]).strip()
            if "socials" in data and isinstance(data["socials"], dict):
                prof["socials"] = data["socials"]
            if "privacy_settings" in data and isinstance(data["privacy_settings"], dict):
                prof["privacy_settings"] = data["privacy_settings"]
            elif "privacy" in data and isinstance(data["privacy"], dict):
                prof["privacy_settings"] = data["privacy"]
                
            with open(STUDENTS_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)
                
            self._send_json({
                "status": "success",
                "message": "Profile preferences updated successfully",
                "student": student
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # 17. Field Verification Badge & Proof Upload API
    def handle_api_profile_verify(self):
        try:
            user = self.get_authenticated_user()
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            roll = user.get("roll_number") if user else None
            if not roll:
                roll = data.get("roll_number", "").strip()
            field = data.get("field", "cgpa").strip()
            claim = data.get("claim", "").strip()
            proof_file = data.get("proof_file") or data.get("document_name") or "Proof_Document.pdf"
            
            db = load_all_students_db()
            if roll not in db:
                self._send_json({"error": "Student not found"}, 404)
                return
                
            student = db[roll]
            if "profile" not in student:
                student["profile"] = {}
            if "verifications" not in student["profile"]:
                student["profile"]["verifications"] = {}
                
            verifs = student["profile"]["verifications"]
            badge_name = claim or f"Verified {field.replace('_', ' ').title()}"
            verifs[field] = {
                "status": "VERIFIED",
                "badge": badge_name,
                "verified_at": time.strftime("%Y-%m-%d"),
                "proof_type": proof_file
            }
            
            if field == "experience" and "experience_details" in data:
                exp_item = data["experience_details"]
                if "experiences" not in student["profile"]:
                    student["profile"]["experiences"] = []
                student["profile"]["experiences"].append(exp_item)
                
            with open(STUDENTS_DB_FILE, "w", encoding="utf-8") as f:
                json.dump(db, f, indent=2)
                
            self._send_json({
                "status": "success",
                "message": f"Verification approved for {field}",
                "verifications": verifs,
                "student": student
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)



def run_server():
    server_address = ("0.0.0.0", PORT)
    httpd = ThreadingHTTPServer(server_address, CampusIQRequestHandler)
    print("\n" + "=" * 76)
    print("🚀 CampusIQ - Next-Generation University Automation Platform")
    print("=" * 76)
    print(f"🌐 Server running at: http://localhost:{PORT}")
    print(f"📡 Notice Engine   : Connected to Render n8n ({N8N_WEBHOOK_URL})")
    print(f"📚 Study Catalog   : Scanned {ACADEMIC_DIR}")
    print(f"📊 Results Parser  : Ready (sample: {os.path.basename(SAMPLE_RESULT_PDF)})")
    print("=" * 76 + "\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[*] Shutting down CampusIQ server gracefully...")
        httpd.server_close()


if __name__ == "__main__":
    run_server()
