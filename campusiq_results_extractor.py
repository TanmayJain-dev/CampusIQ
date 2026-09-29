#!/usr/bin/env python3
"""
CampusIQ - GGSIPU Result Scraper & Extractor
============================================
High-performance, dependency-light parser for GGSIPU Examination Tabulation Sheets.
Extracts student records, subjects, marks, grades, computes SGPA/CGPA, class/college ranks,
and scrapes published results from ipu.ac.in.

Author: CampusIQ Automation Core / Antigravity
License: MIT
"""

import sys
import os
import re
import json
import ssl
import html
import urllib.request
import argparse
from typing import Dict, List, Optional, Any
import pymupdf

# Official GGSIPU College Mapping
INSTITUTION_MAP = {
    "148": "Maharaja Agrasen Institute of Technology (MAIT)",
    "964": "Maharaja Agrasen Institute of Technology (MAIT - 2nd Shift)",
    "164": "University School of Information, Comm. & Tech (USICT)",
    "156": "Maharaja Surajmal Institute of Technology (MSIT)",
    "965": "Maharaja Surajmal Institute of Technology (MSIT - 2nd Shift)",
    "115": "Bharati Vidyapeeth's College of Engineering (BVCOE)",
    "962": "Bharati Vidyapeeth's College of Engineering (BVCOE - 2nd Shift)",
    "208": "Bhagwan Parshuram Institute of Technology (BPIT)",
    "963": "Bhagwan Parshuram Institute of Technology (BPIT - 2nd Shift)",
    "133": "HMR Institute of Technology & Management (HMRITM)",
    "150": "Jagan Institute of Management Studies (JIMS)",
    "512": "Delhi Technical Campus (DTC)",
    "768": "Vivekananda Institute of Professional Studies (VIPS-TC)",
}

# Common GGSIPU Programme Codes
PROGRAMME_MAP = {
    "027": "B.Tech Computer Science & Engineering (CSE)",
    "031": "B.Tech Information Technology (IT)",
    "028": "B.Tech Electronics & Communication Engineering (ECE)",
    "049": "B.Tech Computer Science & Technology (CST)",
    "119": "B.Tech Artificial Intelligence & Data Science (AI-DS)",
    "120": "B.Tech Artificial Intelligence & Machine Learning (AI-ML)",
    "036": "B.Tech Mechanical & Automation Engineering (MAE)",
    "056": "B.Tech Electrical & Electronics Engineering (EEE)",
    "032": "B.Tech CSE (Integrated / Dual Degree)",
    "020": "Bachelor of Commerce (Hons)",
    "017": "Bachelor of Business Administration (BBA)",
}

GRADE_POINTS = {
    "O": 10.0,
    "A+": 9.0,
    "A": 8.0,
    "B+": 7.0,
    "B": 6.0,
    "C": 5.0,
    "P": 4.0,
    "F": 0.0,
}


class GGSIPUResultParser:
    """Parser for GGSIPU Result Tabulation Sheets and Scheme of Examinations PDFs."""

    def __init__(self, pdf_source: str):
        """
        Initialize parser with either local file path or remote PDF URL.
        """
        self.pdf_source = pdf_source
        self.doc = None
        self.schemes: Dict[str, Dict[str, Any]] = {}
        self.results: List[Dict[str, Any]] = []
        self._load_document()

    def _load_document(self):
        if self.pdf_source.startswith("http://") or self.pdf_source.startswith("https://"):
            print(f"[*] Downloading PDF from {self.pdf_source} ...", file=sys.stderr)
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            req = urllib.request.Request(
                self.pdf_source,
                headers={"User-Agent": "Mozilla/5.0 (CampusIQ / Antigravity Bot)"}
            )
            with urllib.request.urlopen(req, context=ctx, timeout=30) as resp:
                pdf_bytes = resp.read()
            self.doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        else:
            if not os.path.exists(self.pdf_source):
                raise FileNotFoundError(f"PDF file not found: {self.pdf_source}")
            self.doc = pymupdf.open(self.pdf_source)
        print(f"[+] Loaded PDF successfully. Total pages: {len(self.doc)}", file=sys.stderr)

    def parse_schemes(self) -> Dict[str, Dict[str, Any]]:
        """Extract schemes of examination (Subject definitions)."""
        schemes = {}
        for page_idx in range(len(self.doc)):
            text = self.doc[page_idx].get_text()
            if "(SCHEME OF EXAMINATIONS)" not in text:
                continue
            
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            scheme_id_match = re.search(r"SchemeID:\s*(\d+)", text)
            scheme_id = scheme_id_match.group(1) if scheme_id_match else "DEFAULT"
            
            # Find subject table start (after 'Pass Marks' header)
            start_idx = -1
            for idx, l in enumerate(lines):
                if "Pass Marks" in l:
                    start_idx = idx + 1
                    break

            if start_idx == -1:
                continue

            current_idx = start_idx
            if scheme_id not in schemes:
                schemes[scheme_id] = {}

            while current_idx < len(lines):
                # An S.No is 2 digits like '01', followed immediately by 5-6 digit paper ID
                if re.match(r"^\d{2}$", lines[current_idx]) and current_idx + 4 < len(lines) and re.match(r"^\d{5,6}$", lines[current_idx + 1]):
                    paper_id = lines[current_idx + 1]
                    paper_code = lines[current_idx + 2]
                    name = lines[current_idx + 3]
                    credits_str = lines[current_idx + 4]
                    credits = int(credits_str) if credits_str.isdigit() else 0

                    schemes[scheme_id][paper_id] = {
                        "paper_id": paper_id,
                        "paper_code": paper_code,
                        "name": name,
                        "credits": credits
                    }
                    # Advance to next entry
                    current_idx += 5
                    while current_idx < len(lines) and not (re.match(r"^\d{2}$", lines[current_idx]) and current_idx + 1 < len(lines) and re.match(r"^\d{5,6}$", lines[current_idx + 1])):
                        current_idx += 1
                else:
                    current_idx += 1
                    
        self.schemes = schemes
        return schemes

    def parse_results(self) -> List[Dict[str, Any]]:
        """Parse all student results across all pages."""
        results = []
        roll_re = re.compile(r"^\d{11}$")
        paper_re = re.compile(r"^(\d{5,6})\((\d+)\)$")
        tot_grade_re = re.compile(r"^(\d+|A|C|D|RL)\(([A-Z\+]+)\)$|^([ACDRL])$")

        for page_idx in range(len(self.doc)):
            page_text = self.doc[page_idx].get_text()
            if "RESULT TABULATION SHEET" not in page_text:
                continue

            sem_match = re.search(r"Sem\./Year:\s*(\d+)", page_text)
            semester = int(sem_match.group(1)) if sem_match else None

            batch_match = re.search(r"Batch:\s*(\d+)", page_text)
            batch = int(batch_match.group(1)) if batch_match else None

            exam_match = re.search(r"Examination:\s*([^\n\r]+)", page_text)
            exam_name = exam_match.group(1).strip() if exam_match else ""

            inst_code_match = re.search(r"Institution Code:\s*(\d+)", page_text)
            inst_name_match = re.search(r"Institution:\s*([^\n\r]+)", page_text)
            inst_code = inst_code_match.group(1) if inst_code_match else None
            inst_name = inst_name_match.group(1).strip() if inst_name_match else None

            prog_code_match = re.search(r"Result of Programme Code:\s*(\d+)", page_text)
            prog_name_match = re.search(r"Programme Name:\s*([^\n\r]+)", page_text)
            prog_code = prog_code_match.group(1) if prog_code_match else None
            prog_name = prog_name_match.group(1).strip() if prog_name_match else None

            lines = [l.strip() for l in page_text.splitlines() if l.strip()]

            i = 0
            while i < len(lines):
                line = lines[i]
                if roll_re.match(line):
                    roll = line
                    name = lines[i+1] if i+1 < len(lines) else ""
                    sid_line = lines[i+2] if i+2 < len(lines) else ""
                    scheme_line = lines[i+3] if i+3 < len(lines) else ""

                    sid_match = re.search(r"SID:\s*(\d+)", sid_line)
                    scheme_id_match = re.search(r"SchemeID:\s*(\d+)", scheme_line)
                    sid = sid_match.group(1) if sid_match else None
                    scheme_id = scheme_id_match.group(1) if scheme_id_match else None

                    subj_idx = i + 4
                    marks = {}

                    while subj_idx < len(lines):
                        sub_line = lines[subj_idx]
                        m = paper_re.match(sub_line)
                        if not m:
                            if roll_re.match(sub_line) or "Result of Programme" in sub_line or "*Passed with Grace" in sub_line or "Date on which" in sub_line:
                                break
                            subj_idx += 1
                            continue

                        paper_id = m.group(1)
                        paper_credits = int(m.group(2))
                        subj_idx += 1

                        minor = None
                        major = None
                        total = None
                        grade = None

                        while subj_idx < len(lines) and not paper_re.match(lines[subj_idx]) and not roll_re.match(lines[subj_idx]):
                            curr = lines[subj_idx]
                            tg_match = tot_grade_re.match(curr)
                            if tg_match:
                                if tg_match.group(1):
                                    raw_tot = tg_match.group(1)
                                    total = int(raw_tot) if raw_tot.isdigit() else 0
                                    grade = tg_match.group(2)
                                elif tg_match.group(3):
                                    grade = tg_match.group(3)
                                    total = 0
                                subj_idx += 1
                                break
                            else:
                                parts = curr.split()
                                if len(parts) == 2:
                                    minor = int(parts[0]) if parts[0].isdigit() else None
                                    major = int(parts[1]) if parts[1].isdigit() else None
                                elif len(parts) == 1 and parts[0].isdigit():
                                    if minor is None:
                                        minor = int(parts[0])
                                    else:
                                        major = int(parts[0])
                            subj_idx += 1

                        subject_title = "Unknown Subject"
                        paper_code = ""
                        for s_id, s_papers in self.schemes.items():
                            if paper_id in s_papers:
                                subject_title = s_papers[paper_id].get("name", "")
                                paper_code = s_papers[paper_id].get("paper_code", "")
                                break

                        marks[paper_id] = {
                            "paper_id": paper_id,
                            "paper_code": paper_code,
                            "subject_name": subject_title,
                            "credits": paper_credits,
                            "minor": minor,
                            "major": major,
                            "total": total,
                            "grade": grade,
                            "grade_point": GRADE_POINTS.get(grade, 0.0) if grade else 0.0
                        }

                    earned_credits = 0
                    total_credits = 0
                    weighted_points = 0.0
                    total_obtained = 0
                    max_obtainable = 0
                    backlogs = 0

                    for p_id, p_info in marks.items():
                        c = p_info["credits"]
                        gp = p_info["grade_point"]
                        tot = p_info["total"] or 0
                        gr = p_info["grade"]

                        total_credits += c
                        total_obtained += tot
                        max_obtainable += 100

                        if gr in ["F", "A", "C", "D"]:
                            backlogs += 1
                        else:
                            earned_credits += c
                            weighted_points += (c * gp)

                    sgpa = round(weighted_points / total_credits, 2) if total_credits > 0 else 0.0
                    percentage = round((total_obtained / max_obtainable) * 100, 2) if max_obtainable > 0 else 0.0

                    student_inst_code = roll[3:6]
                    student_prog_code = roll[6:9]
                    student_batch_yr = 2000 + int(roll[9:11])

                    results.append({
                        "roll_number": roll,
                        "name": name,
                        "sid": sid,
                        "scheme_id": scheme_id,
                        "semester": semester,
                        "batch": batch or student_batch_yr,
                        "examination": exam_name,
                        "institution_code": student_inst_code or inst_code,
                        "institution_name": INSTITUTION_MAP.get(student_inst_code, inst_name or "GGSIPU Affiliated"),
                        "programme_code": student_prog_code or prog_code,
                        "programme_name": PROGRAMME_MAP.get(student_prog_code, prog_name or "Engineering & Technology"),
                        "total_credits": total_credits,
                        "earned_credits": earned_credits,
                        "sgpa": sgpa,
                        "percentage": percentage,
                        "backlogs_count": backlogs,
                        "result_status": "PASS" if backlogs == 0 else f"REAPPEAR ({backlogs} backlogs)",
                        "marks": marks
                    })
                    i = subj_idx
                else:
                    i += 1

        self.results = results
        return results


class GGSIPUResultsPortalScraper:
    """Scrapes official results page at ipu.ac.in/exam_results.php."""

    URL = "https://ipu.ac.in/exam_results.php"

    @classmethod
    def fetch_published_results(cls, limit: int = 20, query: Optional[str] = None) -> List[Dict[str, str]]:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            cls.URL,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) CampusIQ"}
        )

        with urllib.request.urlopen(req, context=ctx, timeout=20) as resp:
            page_html = resp.read().decode("utf-8", errors="ignore")

        rows = re.findall(r"<tr[^>]*>[\s\S]*?</tr>", page_html, re.I)
        published = []

        for r in rows:
            pdf_match = re.search(r"href=[\x27\x22]([^\x27\x22]+\.pdf)[\x27\x22]", r, re.I)
            date_match = re.search(r"\b(\d{2}-\d{2}-\d{4})\b", r)
            if not pdf_match:
                continue

            link = pdf_match.group(1).strip()
            if not link.startswith("http"):
                link = "https://ipu.ac.in/" + link.lstrip("/")

            clean_text = re.sub(r"<[^>]+>", " ", r)
            clean_text = re.sub(r"\s+", " ", clean_text).strip()
            date_str = date_match.group(1) if date_match else "Recent"
            title = html.unescape(clean_text.replace(date_str, "").strip())

            if query and query.lower() not in title.lower():
                continue

            published.append({
                "title": title,
                "url": link,
                "date": date_str
            })
            if len(published) >= limit:
                break

        return published


def print_student_card(s: Dict[str, Any]):
    """Print an aesthetic, readable terminal card for a student."""
    print("=" * 78)
    print(f"🎓 CampusIQ Academic Report: {s['name']} (Roll: {s['roll_number']})")
    print("=" * 78)
    print(f"🏛️  College   : {s['institution_name']} [Code: {s['institution_code']}]")
    print(f"📚 Programme : {s['programme_name']} [Code: {s['programme_code']}]")
    print(f"📅 Semester  : Semester {s['semester']} (Batch: {s['batch']}) | Exam: {s['examination']}")
    print(f"🎯 Status    : {s['result_status']}")
    print(f"⭐ SGPA      : {s['sgpa']:.2f} / 10.00 | Percentage: {s['percentage']:.2f}%")
    print(f"⚡ Credits   : {s['earned_credits']} / {s['total_credits']} credits secured")
    print("-" * 78)
    print(f"{'Paper ID':<10} {'Subject Name':<34} {'Minor':<7} {'Major':<7} {'Total':<7} {'Grade':<6} {'Credits'}")
    print("-" * 78)
    for pid, m in s["marks"].items():
        name = m.get("subject_name") or m.get("paper_code") or pid
        if len(name) > 32:
            name = name[:29] + "..."
        minor = str(m.get("minor") if m.get("minor") is not None else "-")
        major = str(m.get("major") if m.get("major") is not None else "-")
        tot = str(m.get("total") if m.get("total") is not None else "-")
        gr = m.get("grade") or "-"
        cr = str(m.get("credits") or "-")
        print(f"{pid:<10} {name:<34} {minor:<7} {major:<7} {tot:<7} {gr:<6} {cr}")
    print("=" * 78)
    print()


def print_leaderboard(results: List[Dict[str, Any]], top_n: int = 15):
    """Print ranked leaderboard sorted by SGPA."""
    ranked = sorted(results, key=lambda x: (x["sgpa"], x["percentage"]), reverse=True)
    print("\n" + "=" * 80)
    print(f"🏆 CAMPUSIQ ACADEMIC LEADERBOARD (Top {min(top_n, len(ranked))} Students)")
    print("=" * 80)
    print(f"{'Rank':<6} {'Roll Number':<13} {'Student Name':<25} {'SGPA':<8} {'%':<7} {'Status'}")
    print("-" * 80)
    for rank, s in enumerate(ranked[:top_n], 1):
        name = s['name'][:23]
        status = "PASSED" if s['backlogs_count'] == 0 else f"{s['backlogs_count']} Drops"
        print(f"#{rank:<5} {s['roll_number']:<13} {name:<25} {s['sgpa']:<8.2f} {s['percentage']:<7.1f} {status}")
    print("=" * 80 + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="CampusIQ - GGSIPU Result Scraper, Analyzer & Academic Leaderboard"
    )
    parser.add_argument("--pdf", type=str, help="Path or URL to GGSIPU result PDF")
    parser.add_argument("--scrape-latest", type=int, nargs="?", const=15, help="Scrape latest results published on ipu.ac.in")
    parser.add_argument("--search", type=str, help="Keyword filter for scraping results portal")
    parser.add_argument("--roll", type=str, help="Filter by student 11-digit roll number")
    parser.add_argument("--college", type=str, help="Filter by 3-digit institution code (e.g. 148 for MAIT)")
    parser.add_argument("--branch", type=str, help="Filter by 3-digit programme code (e.g. 027 for CSE)")
    parser.add_argument("--batch", type=int, help="Filter by batch year (e.g. 2024)")
    parser.add_argument("--rank", action="store_true", help="Display ranked leaderboard")
    parser.add_argument("--export-json", type=str, help="Path to write extracted results as JSON")

    args = parser.parse_args()

    # Mode 1: Scrape portal
    if args.scrape_latest is not None:
        print(f"[*] Scraping latest {args.scrape_latest} results from IPU portal...")
        items = GGSIPUResultsPortalScraper.fetch_published_results(limit=args.scrape_latest, query=args.search)
        print(f"\n📢 Found {len(items)} published result sheets:")
        print("-" * 90)
        for idx, item in enumerate(items, 1):
            print(f"{idx:2d}. [{item['date']}] {item['title']}")
            print(f"    🔗 {item['url']}")
        print("-" * 90)
        return

    # Mode 2: Parse PDF
    if not args.pdf:
        parser.print_help()
        sys.exit(1)

    extractor = GGSIPUResultParser(args.pdf)
    extractor.parse_schemes()
    all_results = extractor.parse_results()

    # Filtering
    filtered = all_results
    if args.roll:
        filtered = [r for r in filtered if r["roll_number"] == args.roll]
    if args.college:
        filtered = [r for r in filtered if r["institution_code"] == args.college]
    if args.branch:
        filtered = [r for r in filtered if r["programme_code"] == args.branch]
    if args.batch:
        filtered = [r for r in filtered if r["batch"] == args.batch]

    print(f"\n[+] Extracted {len(all_results)} total students from PDF. ({len(filtered)} match filters)", file=sys.stderr)

    if args.roll:
        if filtered:
            for s in filtered:
                print_student_card(s)
        else:
            print(f"[-] No student found with roll number: {args.roll}")
    elif args.rank:
        print_leaderboard(filtered)
    else:
        for s in filtered[:3]:
            print_student_card(s)
        if len(filtered) > 3:
            print(f"... and {len(filtered) - 3} more students. Use --rank to see full leaderboard or --export-json to save all.")

    if args.export_json:
        with open(args.export_json, "w") as f:
            json.dump(filtered, f, indent=2)
        print(f"[✓] Saved {len(filtered)} structured student records to {args.export_json}", file=sys.stderr)


if __name__ == "__main__":
    main()
