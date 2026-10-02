#!/usr/bin/env python3
"""
crawl_btech_drive.py - Robust Google Drive Crawler & Vault Mapper for CampusIQ
=============================================================================
Recursively indexes academic resources from the B.Tech Google Drive repository
(Folder: 1OMHVvF9WLbbIiJhFVDsKyHcFZHpEFQvd).
Maps every file's Google Drive ID into data/vault_drive_map.json.

Author: CampusIQ Engineering Core / Antigravity
License: MIT
"""

import os
import sys
import re
import html
import json
import time
import urllib.request
import urllib.error
from typing import Dict, List, Tuple, Any, Optional

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
VAULT_DRIVE_MAP_FILE = os.path.join(DATA_DIR, "vault_drive_map.json")
BTECH_ROOT_FOLDER_ID = "1OMHVvF9WLbbIiJhFVDsKyHcFZHpEFQvd"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def clean_name(raw: str) -> str:
    return html.unescape(raw).strip()

def fetch_folder_items(folder_id: str) -> List[Tuple[str, str, bool]]:
    """
    Fetches items inside a Google Drive folder.
    Returns: list of (item_id, item_name, is_folder)
    """
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            content = resp.read().decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as e:
        if e.code in (404, 403):
            # Missing or inaccessible folder, do not retry
            return []
        time.sleep(1.0)
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                content = resp.read().decode("utf-8", errors="ignore")
        except Exception:
            return []
    except Exception:
        return []

    matches = re.findall(r'data-id=\"([a-zA-Z0-9_-]{28,40})\".*?<strong class=\"DNoYtb\">([^<]+)</strong>', content, re.DOTALL)
    items = []
    seen = set()
    for fid, raw_name in matches:
        if fid in seen or fid == folder_id:
            continue
        seen.add(fid)
        name = clean_name(raw_name)
        
        idx = content.find(fid)
        block = content[max(0, idx - 100):idx + 300]
        is_folder = "application/vnd.google-apps.folder" in block or not (
            "." in name and any(name.lower().endswith(ext) for ext in [
                ".pdf", ".docx", ".pptx", ".zip", ".png", ".jpg", ".jpeg", ".mp4", ".xlsx"
            ])
        )
        items.append((fid, name, is_folder))
    return items

def normalize_subject_name(raw_name: str) -> str:
    s = raw_name.strip()
    s_low = s.lower()
    
    mapping = {
        "applied chemistry": "Applied Chemistry",
        "applied mathematics 1": "Applied Mathematics I",
        "applied maths 1": "Applied Mathematics I",
        "applied mathematics1": "Applied Mathematics I",
        "applied maths i": "Applied Mathematics I",
        "applied mathematics i": "Applied Mathematics I",
        "applied mathematics 2": "Applied Mathematics II",
        "applied maths 2": "Applied Mathematics II",
        "applied mathematics2": "Applied Mathematics II",
        "applied maths ii": "Applied Mathematics II",
        "applied mathematics ii": "Applied Mathematics II",
        "applied physics 1": "Applied Physics I",
        "applied physics1": "Applied Physics I",
        "applied physics i": "Applied Physics I",
        "applied physics 2": "Applied Physics II",
        "applied physics2": "Applied Physics II",
        "applied physics ii": "Applied Physics II",
        "communication skills": "Communication Skills",
        "communication skill": "Communication Skills",
        "electrical science": "Electrical Science",
        "engineering graphics": "Engineering Graphics",
        "engineering graphic": "Engineering Graphics",
        "engineering mechanics": "Engineering Mechanics",
        "environmental science": "Environmental Studies",
        "environmental studies": "Environmental Studies",
        "human values and professional ethics": "Human Values and Professional Ethics",
        "human values": "Human Values and Professional Ethics",
        "indian constitution": "Indian Constitution",
        "manufacturing process": "Manufacturing Processes",
        "manufacturing processes": "Manufacturing Processes",
        "programming in c": "Programming in C",
        "workshop practice": "Workshop Practice",
        "computational methods": "Computational Methods",
        "data structures": "Data Structures",
        "data structure": "Data Structures",
        "discrete mathematics": "Discrete Mathematics",
        "digital logic and circuit design": "Digital Logic and Circuit Design",
        "object oriented programming": "Object Oriented Programming",
        "indian knowledge system": "Indian Knowledge System",
        "computer organization and architecture": "Computer Organization & Architecture",
        "operating systems": "Operating Systems",
        "operating system": "Operating Systems",
        "database management systems": "Database Management Systems",
        "dbms": "Database Management Systems",
        "software engineering": "Software Engineering",
        "computer networks": "Computer Networks"
    }
    
    for k, v in mapping.items():
        if s_low == k or s_low.startswith(k):
            return v
    return s.title()

def determine_category(path_parts: List[str], filename: str) -> Tuple[str, str]:
    full_str = " / ".join(path_parts + [filename]).lower()
    
    if "akash" in full_str or "aakash" in full_str:
        return ("Akash Solved Question Banks", "Akash")
    elif "mid sem" in full_str or "midterm" in full_str or "class test" in full_str:
        return ("Mid-Term Papers & PYQs", "PYQs/Mid Sems")
    elif "end sem" in full_str or "endterm" in full_str:
        return ("End-Term Papers & PYQs", "PYQs/End Sems")
    elif "pyq" in full_str or "question paper" in full_str or "previous year" in full_str:
        return ("Previous Year Papers", "PYQs")
    elif "syllabus" in full_str:
        return ("Official Syllabus & Blueprints", "Syllabus")
    elif "lab" in full_str or "practical" in full_str or "manual" in full_str:
        return ("Practical Files & Lab Manuals", "Practical Files")
    elif "book" in full_str or "textbook" in full_str:
        return ("Reference Books & Guides", "Books")
    elif "notes" in full_str or "unit" in full_str or "theory" in full_str or "lecture" in full_str:
        return ("Lecture Notes & Theory", "Notes")
    elif "assignment" in full_str or "tutorial" in full_str:
        return ("Assignments & Tutorials", "Assignments")
    else:
        return ("General Academic Materials", "General")

def crawl_folder_recursive(folder_id: str, path_prefix: List[str], depth: int = 0) -> List[Dict[str, Any]]:
    if depth > 5:
        return []
    results = []
    items = fetch_folder_items(folder_id)
    time.sleep(0.04)
    
    for fid, name, is_folder in items:
        lower_name = name.lower()
        if any(bad in lower_name for bad in ["personal", "reliance", "photo", "certificate", ".tmp", "desktop.ini"]):
            continue
            
        cur_path = path_prefix + [name]
        if is_folder:
            results.extend(crawl_folder_recursive(fid, cur_path, depth + 1))
        else:
            if lower_name.endswith((".pdf", ".docx", ".pptx", ".zip", ".jpg", ".png")):
                results.append({
                    "id": fid,
                    "filename": name,
                    "path_parts": cur_path[:-1],
                    "raw_path": "/".join(cur_path)
                })
    return results

def crawl_branch_semesters(dept_name: str, dept_folder_id: str, target_sems: Optional[List[int]] = None) -> List[Dict[str, Any]]:
    print(f"\n📂 Crawling Department: {dept_name} (ID: {dept_folder_id})")
    sem_folders = fetch_folder_items(dept_folder_id)
    dept_files = []
    
    for sem_id, sem_name, is_folder in sem_folders:
        if not is_folder:
            continue
        m = re.search(r"Sem(?:ester)?\s*(\d+)", sem_name, re.I)
        if not m:
            continue
        sem_num = int(m.group(1))
        if target_sems and sem_num not in target_sems:
            continue
            
        print(f"  ⚡ Indexing {dept_name} Semester {sem_num}...")
        files = crawl_folder_recursive(sem_id, [f"Semester {sem_num}", dept_name])
        print(f"     -> Discovered {len(files)} files")
        for f in files:
            f["semester"] = sem_num
            f["department"] = dept_name
        dept_files.extend(files)
        
    return dept_files

def main():
    print("=" * 70)
    print("🏛️ CampusIQ B.Tech Google Drive Vault Crawler")
    print(f"Target Root: {BTECH_ROOT_FOLDER_ID}")
    print("=" * 70)
    
    root_items = fetch_folder_items(BTECH_ROOT_FOLDER_ID)
    branch_map = {name: fid for fid, name, is_folder in root_items if is_folder}
    print(f"Discovered {len(branch_map)} branches: {list(branch_map.keys())}")
    
    all_crawled_files = []
    
    # 1. CSE contains all 1st Year (Sem 1 & Sem 2) common subjects + Sem 3-8 CSE core
    if "CSE" in branch_map:
        files = crawl_branch_semesters("CSE", branch_map["CSE"], target_sems=[1, 2, 3, 4, 5, 6])
        all_crawled_files.extend(files)
        
    # 2. IT Sem 3 & 4
    if "IT" in branch_map:
        files = crawl_branch_semesters("IT", branch_map["IT"], target_sems=[3, 4, 5])
        all_crawled_files.extend(files)
        
    # 3. AI&DS Sem 3
    if "AI&DS" in branch_map:
        files = crawl_branch_semesters("AI&DS", branch_map["AI&DS"], target_sems=[3])
        all_crawled_files.extend(files)
        
    # 4. ECE Sem 3
    if "ECE" in branch_map:
        files = crawl_branch_semesters("ECE", branch_map["ECE"], target_sems=[3])
        all_crawled_files.extend(files)
        
    print(f"\n✅ Total academic files crawled: {len(all_crawled_files)}")
    
    # Load existing vault_drive_map.json
    existing_map = {}
    if os.path.exists(VAULT_DRIVE_MAP_FILE):
        try:
            with open(VAULT_DRIVE_MAP_FILE, "r", encoding="utf-8") as f:
                existing_map = json.load(f)
        except Exception:
            existing_map = {}
            
    files_map = existing_map.get("files", {})
    initial_count = len(files_map)
    print(f"Pre-existing verified mappings in vault_drive_map.json: {initial_count}")
    
    # Process newly crawled files and construct clean relative paths
    added_count = 0
    
    for item in all_crawled_files:
        fid = item["id"]
        fname = item["filename"]
        sem_num = item["semester"]
        path_parts = item["path_parts"]
        
        # Determine subject name: usually path_parts has [Semester X, Dept, SubjectName, SubFolder?]
        subject_raw = "General Academic"
        if len(path_parts) >= 3:
            subject_raw = path_parts[2]
        elif len(path_parts) == 2:
            subject_raw = path_parts[1]
            
        subject = normalize_subject_name(subject_raw)
        category, cat_folder = determine_category(path_parts, fname)
        
        # Clean up filename
        clean_fname = re.sub(r'[\r\n\t]+', ' ', fname).strip()
        rel_path = f"Semester {sem_num}/{subject}/{cat_folder}/{clean_fname}"
        
        if rel_path not in files_map:
            files_map[rel_path] = fid
            added_count += 1
        elif files_map[rel_path] != fid:
            alt_path = f"Semester {sem_num}/{subject} ({item['department']})/{cat_folder}/{clean_fname}"
            if alt_path not in files_map:
                files_map[alt_path] = fid
                added_count += 1
            
    existing_map["files"] = files_map
    existing_map["total_mapped"] = len(files_map)
    existing_map["updated_at"] = time.time()
    existing_map["btech_root_id"] = BTECH_ROOT_FOLDER_ID
    
    with open(VAULT_DRIVE_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(existing_map, f, indent=2)
        
    print(f"\n💾 Successfully saved {len(files_map)} total Drive mappings to {VAULT_DRIVE_MAP_FILE} (+{added_count} new)")

if __name__ == "__main__":
    main()
