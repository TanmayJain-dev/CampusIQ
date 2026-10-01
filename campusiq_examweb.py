#!/usr/bin/env python3
"""
CampusIQ - GGSIPU ExamWeb Scraper & Marksheet Engine
===================================================
Reverse-engineered client for the official GGSIPU student examination portal
(https://examweb.ggsipu.ac.in).

Features:
- Live session initiation and CAPTCHA extraction with Base64 encoding.
- Integrated OCR pre-solver via Tesseract.
- Client-side matching SHA-256 salting and password hashing.
- Student profile and official photo extraction (Base64 JPEG).
- Ground-truth syllabus credit mapping (verified against USICT 2021-22+ scheme).
- Exact format matching GGSIPU Semester Grade Sheets & Consolidated Performance Records.
- Persistent student database for College Administrators & Faculty.
- Private backlog / supplementary alert engine.
"""

import os
import re
import time
import json
import uuid
import base64
import hashlib
import tempfile
import subprocess
from typing import Dict, Any, Optional, Tuple, List
import requests
import urllib3
from bs4 import BeautifulSoup

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)
STUDENTS_DB_FILE = os.path.join(DATA_DIR, "students_database.json")

# Verified Ground-Truth GGSIPU B.Tech Scheme Course Credits Mapping
# Verified from GGSIPU official syllabus & student result dossiers
OFFICIAL_CREDITS_MAP = {
    # --- Semester 1 (Total: 21 Credits) ---
    "BS103": 3, "BS-103": 3,   # Applied Chemistry
    "BS105": 3, "BS-105": 3,   # Applied Physics - I
    "ES107": 3, "ES-107": 3,   # Electrical Science
    "BS111": 3, "BS-111": 3,   # Applied Mathematics - I
    "HS115": 2, "HS-115": 2,   # Human Values and Ethics
    "ES119": 3, "ES-119": 3,   # Manufacturing Process
    "BS151": 1, "BS-151": 1,   # Applied Physics - I Lab
    "BS155": 1, "BS-155": 1,   # Applied Chemistry Lab
    "ES157": 1, "ES-157": 1,   # Engineering Graphics - I
    "ES159": 1, "ES-159": 1,   # Electrical Science Lab
    
    # --- Semester 2 (Total: 23 Credits) ---
    "ES102": 3, "ES-102": 3,   # Programming in 'C'
    "BS106": 3, "BS-106": 3,   # Applied Physics - II
    "BS110": 3, "BS-110": 3,   # Environmental Studies
    "BS112": 3, "BS-112": 3,   # Applied Mathematics - II
    "HS114": 3, "HS-114": 3,   # Communication Skills
    "BS152": 1, "BS-152": 1,   # Physics - II Lab
    "ES154": 1, "ES-154": 1,   # Programming in 'C' Lab
    "ES158": 1, "ES-158": 1,   # Engineering Graphics - II
    "BS162": 1, "BS-162": 1,   # Environmental Studies Lab
    "ES164": 1, "ES-164": 1,   # Workshop Technology
    "ES114": 3, "ES-114": 3,   # Engineering Mechanics

    # --- Semester 3 (Total: 26 Credits) ---
    "ES201": 4, "ES-201": 4,   # Computational Methods
    "HS203": 2, "HS-203": 2,   # Indian Knowledge System
    "CIC205": 4, "CIC-205": 4, # Discrete Mathematics
    "ECC207": 4, "ECC-207": 4, # Digital Logic and Computer Design
    "CIC209": 4, "CIC-209": 4, # Data Structures
    "CIC211": 4, "CIC-211": 4, # Object-Oriented Programming using C++
    "ES251": 1, "ES-251": 1,   # Computational Methods Lab
    "ECC253": 1, "ECC-253": 1, # Digital Logic and Computer Design Lab
    "CIC255": 1, "CIC-255": 1, # Data Structures Lab
    "CIC257": 1, "CIC-257": 1, # OOP using C++ Lab

    # --- Semester 4 (Total: 26 Credits) ---
    "BS202": 4, "BS-202": 4,   # Probability, Statistics and Linear Programming
    "HS204": 2, "HS-204": 2,   # Technical Writing
    "CIC206": 4, "CIC-206": 4, # Theory of Computation
    "EEC208": 4, "EEC-208": 4, # Circuits and Systems
    "CIC210": 4, "CIC-210": 4, # Database Management Systems
    "CIC212": 4, "CIC-212": 4, # Programming in Java
    "BS252": 1, "BS-252": 1,   # Probability & Stats Lab
    "EEC254": 1, "EEC-254": 1, # Circuits & Systems Lab
    "CIC256": 1, "CIC-256": 1, # DBMS Lab
    "CIC258": 1, "CIC-258": 1, # Java Lab

    # --- Semester 5 (Total: 24 Credits) ---
    "HS301": 2, "HS-301": 2,   # Economics for Engineers
    "CIC303": 3, "CIC-303": 3, # Compiler Design
    "CIC305": 4, "CIC-305": 4, # Operating Systems
    "CIC307": 4, "CIC-307": 4, # Computer Networks
    "CIC309": 3, "CIC-309": 3, # Software Engineering
    "CIC311": 4, "CIC-311": 4, # Design and Analysis of Algorithms
    "CIC351": 1, "CIC-351": 1, # Compiler Design Lab
    "CIC353": 1, "CIC-353": 1, # Operating Systems Lab
    "CIC355": 1, "CIC-355": 1, # Computer Networks Lab
    "CIC357": 1, "CIC-357": 1, # Software Engineering Lab
}

ACTIVE_SESSIONS: Dict[str, Dict[str, Any]] = {}
SESSION_EXPIRY_SECONDS = 180  # 3 minutes


def clean_expired_sessions():
    now = time.time()
    expired = [k for k, v in ACTIVE_SESSIONS.items() if now - v.get("created_at", 0) > SESSION_EXPIRY_SECONDS]
    for k in expired:
        ACTIVE_SESSIONS.pop(k, None)


def marks_to_grade_and_point(marks: float) -> Tuple[str, int]:
    """Official GGSIPU Ordinance 10-point Grading System."""
    if marks >= 90:
        return "O", 10
    elif marks >= 75:
        return "A+", 9
    elif marks >= 65:
        return "A", 8
    elif marks >= 55:
        return "B+", 7
    elif marks >= 50:
        return "B", 6
    elif marks >= 45:
        return "C", 5
    elif marks >= 40:
        return "P", 4
    else:
        return "F", 0


def normalize_paper_code(code: str) -> str:
    """Formats code to standard university format (e.g. BS103 -> BS-103)."""
    clean = code.strip().upper()
    m = re.match(r"^([A-Z]+)(\d+)$", clean)
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return clean


def solve_captcha_ocr(image_bytes: bytes) -> str:
    """Uses local Tesseract OCR to suggest the captcha characters."""
    try:
        from PIL import Image, ImageEnhance
        import io
        img = Image.open(io.BytesIO(image_bytes)).convert("L")
        enh = ImageEnhance.Contrast(img).enhance(2.0)
        
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            enh.save(tmp.name)
            tmp_path = tmp.name

        cmd = [
            "tesseract", tmp_path, "stdout",
            "--psm", "7",
            "-c", "tessedit_char_whitelist=abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=3)
        if os.path.exists(tmp_path):
            os.remove(tmp_path)
            
        raw = res.stdout.strip()
        cleaned = re.sub(r"[^a-zA-Z0-9]", "", raw)
        return cleaned[:7]
    except Exception:
        return ""


# =============================================================================
# PERSISTENT STUDENT DATABASE ENGINE (FOR COLLEGE ADMINS & FACULTY)
# =============================================================================

def save_student_to_db(record: Dict[str, Any]):
    """Persists a verified student profile & academic dossier to the central database."""
    roll = record.get("student", {}).get("roll_number")
    if not roll:
        return

    db = load_all_students_db()
    db[roll] = {
        "roll_number": roll,
        "name": record.get("student", {}).get("name"),
        "father_name": record.get("student", {}).get("father_name"),
        "mother_name": record.get("student", {}).get("mother_name"),
        "institution_name": record.get("student", {}).get("institution_name"),
        "programme_name": record.get("student", {}).get("programme_name"),
        "batch": record.get("student", {}).get("batch"),
        "admission_year": record.get("student", {}).get("admission_year"),
        "photo_base64": record.get("student", {}).get("photo_base64"),
        "email": record.get("student", {}).get("email"),
        "mobile": record.get("student", {}).get("mobile"),
        "overall": record.get("overall", {}),
        "semesters": record.get("semesters", []),
        "backlogs": record.get("student", {}).get("private_backlogs", []),
        "last_synced": time.strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        with open(STUDENTS_DB_FILE, "w", encoding="utf-8") as f:
            json.dump(db, f, indent=2)
    except Exception as e:
        print(f"[!] Error saving student database: {e}")


def load_all_students_db() -> Dict[str, Any]:
    """Retrieves all students from the persistent database."""
    if os.path.exists(STUDENTS_DB_FILE):
        try:
            with open(STUDENTS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def get_student_by_roll(roll_number: str) -> Optional[Dict[str, Any]]:
    """Fetches a single student profile by roll number."""
    db = load_all_students_db()
    return db.get(roll_number.strip())


# =============================================================================
# EXAMWEB CLIENT & MARKSHEET BUILDER
# =============================================================================

class ExamWebClient:
    """Manages interaction with examweb.ggsipu.ac.in and data typesetting."""

    @staticmethod
    def create_session() -> Dict[str, Any]:
        clean_expired_sessions()
        session = requests.Session()
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Language": "en-US,en;q=0.9",
        })

        try:
            resp = session.get("https://examweb.ggsipu.ac.in/web/login.jsp", verify=False, timeout=12)
            jsessionid = session.cookies.get("JSESSIONID")
            if not jsessionid:
                m = re.search(r"jsessionid=([A-Fa-f0-9]+)", resp.text)
                if m:
                    jsessionid = m.group(1)

            if not jsessionid:
                raise ValueError("Failed to obtain JSESSIONID from GGSIPU ExamWeb.")

            captcha_url = f"https://examweb.ggsipu.ac.in/web/captcha;jsessionid={jsessionid}"
            r_captcha = session.get(captcha_url, headers={"Referer": "https://examweb.ggsipu.ac.in/web/login.jsp"}, verify=False, timeout=12)
            captcha_bytes = r_captcha.content
            captcha_b64 = "data:image/png;base64," + base64.b64encode(captcha_bytes).decode("ascii")

            ocr_text = solve_captcha_ocr(captcha_bytes)
            session_id = str(uuid.uuid4())
            ACTIVE_SESSIONS[session_id] = {
                "session": session,
                "jsessionid": jsessionid,
                "created_at": time.time()
            }

            return {
                "status": "success",
                "session_id": session_id,
                "captcha_base64": captcha_b64,
                "ocr_suggestion": ocr_text
            }
        except Exception as e:
            print(f"[ExamWebClient] Session creation exception: {type(e).__name__}: {str(e)}")
            return {
                "status": "error",
                "message": f"Unable to reach GGSIPU ExamWeb portal: {str(e)}"
            }

    @staticmethod
    def login_and_fetch(session_id: str, username: str, password: str, captcha: str) -> Dict[str, Any]:
        clean_expired_sessions()
        sess_data = ACTIVE_SESSIONS.get(session_id)
        if not sess_data:
            return {
                "status": "error",
                "error_code": "SESSION_EXPIRED",
                "message": "Session expired or invalid. Please refresh the CAPTCHA."
            }

        session: requests.Session = sess_data["session"]
        jsessionid: str = sess_data["jsessionid"]

        salt = captcha.strip()
        combined = password + salt
        hashed_passwd = base64.b64encode(hashlib.sha256(combined.encode("utf-8")).digest()).decode("utf-8")

        login_url = f"https://examweb.ggsipu.ac.in/web/login;jsessionid={jsessionid}"
        payload = {
            "username": username.strip(),
            "passwd": hashed_passwd,
            "captcha": salt
        }
        headers = {
            "Referer": "https://examweb.ggsipu.ac.in/web/login.jsp",
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "https://examweb.ggsipu.ac.in"
        }

        try:
            r_login = session.post(login_url, data=payload, headers=headers, verify=False, timeout=12)
            soup = BeautifulSoup(r_login.text, "html.parser")
            msg_box = soup.find(class_="message-box")

            if msg_box:
                err_text = msg_box.get_text(strip=True)
                if "Invalid Captcha" in err_text:
                    return {"status": "error", "error_code": "INVALID_CAPTCHA", "message": "Invalid Captcha code. Please check and retry."}
                elif "Session Expired" in err_text:
                    return {"status": "error", "error_code": "SESSION_EXPIRED", "message": "ExamWeb session expired. Please refresh the CAPTCHA."}
                else:
                    return {"status": "error", "error_code": "LOGIN_FAILED", "message": err_text}

            if "studenthome" not in r_login.url and "Home Page" not in r_login.text:
                return {"status": "error", "error_code": "AUTH_FAILED", "message": "Login failed. Please verify your enrollment number and password."}

            # 1. Fetch Student Profile & Photo
            profile_url = "https://examweb.ggsipu.ac.in/web/student/profile"
            r_prof = session.get(profile_url, headers={"Referer": "https://examweb.ggsipu.ac.in/web/student/studenthome"}, verify=False, timeout=8)
            profile_data = {}
            photo_b64 = ""

            prof_soup = BeautifulSoup(r_prof.text, "html.parser")
            data_div = prof_soup.find("div", id="data")
            if data_div and data_div.string:
                try:
                    prof_json = json.loads(data_div.string)
                    if isinstance(prof_json, list) and len(prof_json) > 0:
                        profile_data = prof_json[0]
                        photo_raw = profile_data.get("stimage", "")
                        if photo_raw:
                            photo_b64 = "data:image/jpeg;base64," + photo_raw.replace("\n", "").replace("\r", "")
                except Exception as ex:
                    print(f"Error parsing profile JSON: {ex}")

            # 2. Fetch Semester Results
            search_url = "https://examweb.ggsipu.ac.in/web/student/search?flag=2&euno=100"
            r_search = session.get(search_url, headers={"Referer": "https://examweb.ggsipu.ac.in/web/student/studenthome"}, verify=False, timeout=12)
            search_json = r_search.json()

            if search_json.get("status") != "OK" or "message" not in search_json:
                return {"status": "error", "message": "No result records found on ExamWeb."}

            res_data = json.loads(search_json["message"])
            stprofile = res_data.get("stprofile", {})
            stresult = res_data.get("stresult", [])

            # Consolidate Student Info
            student_info = {
                "roll_number": stprofile.get("nrollno") or profile_data.get("nrollno") or username,
                "name": stprofile.get("stname") or profile_data.get("stname") or "STUDENT",
                "father_name": profile_data.get("father", "N/A"),
                "mother_name": profile_data.get("mother", "N/A"),
                "gender": profile_data.get("gender", ""),
                "email": profile_data.get("email", ""),
                "mobile": profile_data.get("mobno", ""),
                "batch": stprofile.get("byoa") or profile_data.get("byoa") or "2025",
                "admission_year": stprofile.get("yoa") or profile_data.get("yoa") or "2025",
                "programme_code": stprofile.get("prgcode") or profile_data.get("prgcode") or "",
                "programme_name": stprofile.get("prgname") or profile_data.get("prgname") or "BACHELOR OF TECHNOLOGY",
                "institution_code": stprofile.get("icode") or profile_data.get("icode") or "",
                "institution_name": stprofile.get("iname") or profile_data.get("iname") or "GGSIPU AFFILIATED INSTITUTE",
                "photo_base64": photo_b64,
                "private_backlogs": []
            }

            return ExamWebClient.build_marksheet_record(student_info, stresult)

        except Exception as e:
            return {"status": "error", "message": f"An error occurred while fetching records: {str(e)}"}

    @staticmethod
    def build_marksheet_record(student_info: Dict[str, Any], stresult: List[List[Any]]) -> Dict[str, Any]:
        """Processes raw examweb rows into official GGSIPU Marksheet & Performance Dossier format."""
        semesters_dict: Dict[int, List[Dict[str, Any]]] = {}
        backlogs = []

        for row in stresult:
            # row: [sem, papercode, subjectname, internal, external, total, status, exam_month_year, declared_date]
            sem_num = int(row[0]) if str(row[0]).isdigit() else 1
            raw_paper_code = str(row[1]).strip().upper()
            norm_code = normalize_paper_code(raw_paper_code)
            subject_name = str(row[2]).strip()
            int_marks_str = str(row[3]).strip()
            ext_marks_str = str(row[4]).strip()
            total_marks_str = str(row[5]).strip()
            status_code = str(row[6]).strip()
            exam_session = str(row[7]).strip()
            declared_date = str(row[8]).strip()

            total_marks = float(total_marks_str) if total_marks_str.replace(".", "", 1).isdigit() else 0.0
            grade, grade_point = marks_to_grade_and_point(total_marks)

            # Accurate Syllabus Credit Lookup
            credits = OFFICIAL_CREDITS_MAP.get(norm_code, OFFICIAL_CREDITS_MAP.get(raw_paper_code, 1 if "LAB" in subject_name.upper() else 3))
            
            # GGSIPU Rule: Full credits awarded if passed (>= 40), otherwise 0
            is_pass = total_marks >= 40.0
            credits_secured = credits if is_pass else 0
            credit_points = grade_point * credits

            if not is_pass or grade == "F":
                backlogs.append({
                    "semester": sem_num,
                    "paper_code": norm_code,
                    "subject_name": subject_name,
                    "total_marks": total_marks,
                    "declared_date": declared_date,
                    "exam_session": exam_session
                })

            # Format examination title (e.g. "12,2025" -> "December 2025")
            exam_title = exam_session
            if "," in exam_session:
                m_part, y_part = exam_session.split(",", 1)
                months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
                if m_part.isdigit() and 1 <= int(m_part) <= 12:
                    exam_title = f"{months[int(m_part)-1]} {y_part}"

            subj_obj = {
                "paper_code": norm_code,
                "paper_title": subject_name,
                "credits": credits,
                "internal_marks": int_marks_str,   # INT
                "external_marks": ext_marks_str,   # EXT
                "total_marks": int(total_marks) if total_marks.is_integer() else total_marks,
                "credits_secured": credits_secured, # CS
                "grade": grade,
                "grade_point": grade_point,         # GP
                "credit_points": credit_points,
                "status_code": status_code,
                "exam_session": exam_title,
                "declared_date": declared_date
            }

            if sem_num not in semesters_dict:
                semesters_dict[sem_num] = []
            semesters_dict[sem_num].append(subj_obj)

        student_info["private_backlogs"] = backlogs

        # Calculate exact SGPA, Percentage, and Cumulative Record
        semesters_list = []
        cum_credits = 0
        cum_credits_secured = 0
        cum_credit_points = 0
        cum_total_marks = 0
        cum_max_marks = 0

        ord_sem_names = {1: "FIRST SEMESTER", 2: "SECOND SEMESTER", 3: "THIRD SEMESTER", 4: "FOURTH SEMESTER", 5: "FIFTH SEMESTER"}

        for sem_num in sorted(semesters_dict.keys()):
            subjects = semesters_dict[sem_num]
            sem_credits = sum(s["credits"] for s in subjects)
            sem_credits_secured = sum(s["credits_secured"] for s in subjects)
            sem_credit_points = sum(s["credit_points"] for s in subjects)
            sem_marks = sum(s["total_marks"] for s in subjects)
            sem_max_marks = len(subjects) * 100

            sgpa = round(sem_credit_points / sem_credits, 2) if sem_credits > 0 else 0.0
            sem_pct = round((sem_marks / sem_max_marks) * 100, 2) if sem_max_marks > 0 else 0.0

            cum_credits += sem_credits
            cum_credits_secured += sem_credits_secured
            cum_credit_points += sem_credit_points
            cum_total_marks += sem_marks
            cum_max_marks += sem_max_marks

            running_cgpa = round(cum_credit_points / cum_credits, 2) if cum_credits > 0 else 0.0

            semesters_list.append({
                "semester": sem_num,
                "semester_name": ord_sem_names.get(sem_num, f"SEMESTER {sem_num}"),
                "examination": subjects[0]["exam_session"] if subjects else "Regular",
                "declared_date": subjects[0]["declared_date"] if subjects else "",
                "total_subjects": len(subjects),
                "total_credits": sem_credits,
                "credits_earned": sem_credits_secured,
                "total_marks": sem_marks,
                "max_marks": sem_max_marks,
                "sgpa": sgpa,
                "percentage": sem_pct,
                "result_status": "PASSED" if all(s["total_marks"] >= 40 for s in subjects) else "RE-APPEAR",
                "cumulative_credits": cum_credits_secured,
                "cumulative_cgpa": running_cgpa,
                "subjects": subjects
            })

        final_cgpa = round(cum_credit_points / cum_credits, 2) if cum_credits > 0 else 0.0
        final_pct = round((cum_total_marks / cum_max_marks) * 100, 3) if cum_max_marks > 0 else 0.0

        result_package = {
            "status": "success",
            "student": student_info,
            "overall": {
                "total_semesters": len(semesters_list),
                "total_credits": cum_credits,
                "credits_earned": cum_credits_secured,
                "total_marks": cum_total_marks,
                "max_marks": cum_max_marks,
                "cgpa": final_cgpa,
                "percentage": round(final_pct, 2),
                "exact_percentage": f"{final_pct:.3f}%",
                "division": "FIRST DIVISION WITH DISTINCTION" if final_cgpa >= 7.5 else ("FIRST DIVISION" if final_cgpa >= 6.5 else "SECOND DIVISION"),
                "result_status": "PASSED" if len(backlogs) == 0 else f"{len(backlogs)} BACKLOG(S)"
            },
            "semesters": semesters_list,
            "backlogs": backlogs
        }

        # Save to persistent database for Faculty / Admin Roster
        save_student_to_db(result_package)

        # Cache verified result
        cache_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cached_verified_result.json")
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(result_package, f, indent=2)
        except Exception:
            pass

        return result_package

    @staticmethod
    def get_cached_or_demo_result() -> Dict[str, Any]:
        """Demo marksheet preview has been disabled."""
        return {
            "status": "error",
            "message": "Demo marksheet has been disabled. Please enter your roll number and ExamWeb credentials to fetch your verified result."
        }

