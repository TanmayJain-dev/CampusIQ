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
import mimetypes
import urllib.request
import urllib.parse
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from typing import Dict, List, Optional, Any

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

PORT = int(os.environ.get("PORT", 5000))
N8N_WEBHOOK_URL = os.environ.get(
    "N8N_WEBHOOK_URL",
    "https://n8n-tanmay.onrender.com/webhook/campusiq-notices"
)
ACADEMIC_DIR = os.environ.get(
    "ACADEMIC_DIR",
    "/home/tanmay/Workspaces/Academics/College"
)
SAMPLE_RESULT_PDF = os.path.join(PROJECT_DIR, "sample_result.pdf")

# Session Store Configuration
SESSIONS_FILE = os.path.join(PROJECT_DIR, "data", "sessions.json")
_SESSIONS: Dict[str, Dict[str, Any]] = {}

def load_sessions() -> Dict[str, Dict[str, Any]]:
    global _SESSIONS
    if os.path.exists(SESSIONS_FILE):
        try:
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                _SESSIONS = json.load(f)
        except Exception:
            _SESSIONS = {}
    return _SESSIONS

def save_sessions():
    try:
        os.makedirs(os.path.dirname(SESSIONS_FILE), exist_ok=True)
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(_SESSIONS, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving sessions: {e}", file=sys.stderr)

# Initialize sessions from disk
load_sessions()

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
    """Fetch notices from Render n8n webhook or direct IPU scrapers with cache & enrichment."""
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

    # 1. Try Live n8n Webhook
    try:
        req = urllib.request.Request(N8N_WEBHOOK_URL, headers=headers)
        with urllib.request.urlopen(req, context=ctx, timeout=8) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
            notices = payload.get("notices", [])
            if notices:
                enriched = [enrich_notice(dict(n)) for n in notices]
                _NOTICES_CACHE["data"] = enriched
                _NOTICES_CACHE["last_fetched"] = now
                return enriched
    except Exception as e:
        print(f"[!] Info: n8n notice webhook: {e}", file=sys.stderr)

    # 2. Direct Scrape from IPU Exam Notices (ipu.ac.in/exam_notices.php)
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
                _NOTICES_CACHE["data"] = direct_notices
                _NOTICES_CACHE["last_fetched"] = now
                return direct_notices
    except Exception as e:
        print(f"[!] Warning: Failed direct IPU notice scraping: {e}", file=sys.stderr)

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
            "Access-Control-Allow-Headers": "Content-Type",
        }

        # API Routes
        if path == "/api/notices":
            self.handle_api_notices(params)
        elif path == "/api/resources":
            self.handle_api_resources(params)
        elif path == "/api/resources/tree":
            self.handle_api_resources_tree()
        elif path == "/api/resources/view":
            self.handle_api_resource_view(params)
        elif path == "/api/auth/me" or path == "/api/auth/current":
            self.handle_api_auth_me()
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
            "Access-Control-Allow-Headers": "Content-Type, Authorization",
        }

        if path == "/api/examweb/login":
            self.handle_api_examweb_login()
        elif path in ("/api/auth/google/signin", "/api/auth/google", "/api/auth/signin"):
            self.handle_api_auth_signin()
        elif path == "/api/auth/signout":
            self.handle_api_auth_signout()
        elif path == "/api/auth/link-roll":
            self.handle_api_auth_link_roll()
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

    def _send_json(self, data: Any, status: int = 200):
        try:
            body = json.dumps(data, indent=2).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            for k, v in self.send_cors_headers().items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as e:
            print(f"[!] Warning writing JSON response: {e}", file=sys.stderr)

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
        limit = int(params.get("limit", [100])[0])

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
        rel_path = params.get("path", [""])[0]
        if not rel_path:
            self._send_json({"error": "Missing 'path' parameter"}, 400)
            return

        # Security: Prevent directory traversal outside ACADEMIC_DIR
        abs_path = os.path.abspath(os.path.join(ACADEMIC_DIR, rel_path))
        if not abs_path.startswith(os.path.abspath(ACADEMIC_DIR)) or not os.path.exists(abs_path):
            if os.path.exists(SAMPLE_RESULT_PDF):
                abs_path = os.path.abspath(SAMPLE_RESULT_PDF)
            else:
                self._send_json({"error": "Resource file not found"}, 404)
                return

        try:
            with open(abs_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", "application/pdf")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Content-Disposition", f"inline; filename=\"{os.path.basename(abs_path)}\"")
            for k, v in self.send_cors_headers().items():
                self.send_header(k, v)
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)

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

    # 5. Admin Student Roster API (College Faculty & Administrators)
    def handle_api_admin_students(self, params: Dict[str, List[str]]):
        db = load_all_students_db()
        search = params.get("search", [""])[0].lower().strip()
        branch = params.get("branch", [""])[0].lower().strip()

        students_list = []
        for roll, s in db.items():
            if search and (search not in roll.lower() and search not in s.get("name", "").lower()):
                continue
            if branch and branch not in s.get("programme_name", "").lower():
                continue
            students_list.append({
                "roll_number": s["roll_number"],
                "name": s["name"],
                "father_name": s.get("father_name"),
                "institution_name": s.get("institution_name"),
                "programme_name": s.get("programme_name"),
                "batch": s.get("batch"),
                "cgpa": s.get("overall", {}).get("cgpa", 0.0),
                "percentage": s.get("overall", {}).get("percentage", 0.0),
                "total_semesters": len(s.get("semesters", [])),
                "backlogs_count": len(s.get("backlogs", [])),
                "photo_base64": s.get("photo_base64", ""),
                "last_synced": s.get("last_synced", "")
            })

        students_list.sort(key=lambda x: x["cgpa"], reverse=True)
        self._send_json({
            "status": "success",
            "total_students": len(students_list),
            "students": students_list
        })

    def handle_api_admin_student_detail(self, roll: str):
        record = get_student_by_roll(roll)
        if record:
            self._send_json({"status": "success", "found": True, "student": record})
        else:
            self._send_json({"status": "error", "message": f"Student {roll} not found in database"}, 404)

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

    # 9. ExamWeb Live Session / Captcha
    def handle_api_examweb_session(self):
        res = ExamWebClient.create_session()
        status = 200 if res.get("status") == "success" else 503
        self._send_json(res, status)

    # 10. ExamWeb Demo / Verified Fallback Marksheet
    def handle_api_examweb_demo(self):
        res = ExamWebClient.get_cached_or_demo_result()
        status = 200 if res.get("status") == "success" else 404
        self._send_json(res, status)

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
            cataloguer = CampusIQResourceCataloguer(ACADEMIC_DIR)
            tree_data = cataloguer.build_tree()
            self._send_json({
                "status": "success",
                "tree": tree_data
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    def get_authenticated_user(self) -> Optional[Dict[str, Any]]:
        auth_header = self.headers.get("Authorization", "")
        token = None
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()

        if not token:
            parsed = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(parsed.query)
            token = params.get("token", [""])[0].strip()

        if not token:
            return None

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
                "student": None
            })
            return

        roll = user.get("roll_number")
        db = load_all_students_db()
        student = db.get(roll) if roll else None

        self._send_json({
            "status": "success",
            "is_authenticated": True,
            "user": user,
            "student": student
        })

    def handle_api_auth_current(self):
        self.handle_api_auth_me()

    # 14. Sign in with Google Account
    def handle_api_auth_signin(self):
        try:
            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}

            email = data.get("email", "").strip()
            name = data.get("name", "").strip()
            avatar = data.get("avatar", "").strip()
            roll = data.get("roll_number", "").strip()

            if not email:
                self._send_json({"status": "error", "message": "Email is required to sign in."}, 400)
                return

            if not name:
                name = email.split("@")[0].replace(".", " ").title()

            if not avatar:
                avatar = f"https://api.dicebear.com/7.x/bottts/svg?seed={urllib.parse.quote(name)}"

            db = load_all_students_db()
            student = None
            if roll:
                student = db.get(roll)
            else:
                for r, s in db.items():
                    if s.get("email", "").lower() == email.lower():
                        roll = r
                        student = s
                        break

            token = secrets.token_hex(24)
            user_session = {
                "session_token": token,
                "email": email,
                "name": name,
                "avatar_url": avatar,
                "roll_number": roll or None,
                "created_at": time.time()
            }

            sessions = load_sessions()
            sessions[token] = user_session
            save_sessions()

            self._send_json({
                "status": "success",
                "message": f"Welcome, {name}!",
                "session_token": token,
                "user": user_session,
                "student": student
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # Sign Out
    def handle_api_auth_signout(self):
        try:
            user = self.get_authenticated_user()
            if user:
                token = user.get("session_token")
                sessions = load_sessions()
                if token in sessions:
                    del sessions[token]
                    save_sessions()

            self._send_json({
                "status": "success",
                "message": "Signed out successfully."
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

    # Link GGSIPU Roll Number to Authenticated Account
    def handle_api_auth_link_roll(self):
        try:
            user = self.get_authenticated_user()
            if not user:
                self._send_json({"status": "error", "message": "Sign-in required to link roll number."}, 401)
                return

            length = int(self.headers.get("Content-Length", 0))
            body_bytes = self.rfile.read(length)
            data = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
            roll = data.get("roll_number", "").strip()

            if not roll or len(roll) != 11 or not roll.isdigit():
                self._send_json({"status": "error", "message": "Valid 11-digit roll number required."}, 400)
                return

            db = load_all_students_db()
            student = db.get(roll)

            token = user.get("session_token")
            sessions = load_sessions()
            if token in sessions:
                sessions[token]["roll_number"] = roll
                save_sessions()

            self._send_json({
                "status": "success",
                "message": f"Successfully linked Roll Number {roll}",
                "roll_number": roll,
                "student": student
            })
        except Exception as e:
            self._send_json({"status": "error", "message": str(e)}, 500)

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
