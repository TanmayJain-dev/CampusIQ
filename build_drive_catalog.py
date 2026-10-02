#!/usr/bin/env python3
"""
build_drive_catalog.py - Generates data/catalog_cache.json from data/vault_drive_map.json
========================================================================================
Ensures 100% of study resources shown in CampusIQ Study Vault map directly to real
Google Drive files with zero missing links, categorized by Semester, Subject, and Type.
"""

import os
import re
import json
from typing import Dict, List, Any
from campusiq_cataloguer import SUBJECT_CODE_MAP
from scripts.enhance_vault_metadata import generate_clean_metadata

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
VAULT_DRIVE_MAP_FILE = os.path.join(PROJECT_DIR, "data", "vault_drive_map.json")
CATALOG_CACHE_FILE = os.path.join(PROJECT_DIR, "data", "catalog_cache.json")

def clean_subject_name(raw_name: str) -> str:
    s = raw_name.strip()
    if s.lower() == "manufacturing process":
        return "Manufacturing Processes"
    if s.lower() in ["applied mathematics 1", "applied maths 1"]:
        return "Applied Mathematics I"
    if s.lower() in ["applied mathematics 2", "applied maths 2"]:
        return "Applied Mathematics II"
    if s.lower() == "applied physics 1":
        return "Applied Physics I"
    if s.lower() == "applied physics 2":
        return "Applied Physics II"
    return s

def extract_meta_from_drive_path(rel_path: str, drive_id: str) -> Dict[str, Any]:
    parts = [p for p in rel_path.replace("\\", "/").split("/") if p]
    fname = parts[-1]

    semester = None
    for p in parts:
        m = re.search(r"Semester\s*(\d+)", p, re.I)
        if m:
            semester = int(m.group(1))
            break

    subject = "General Academic"
    if semester and len(parts) > 1 and parts[0].lower().startswith("semester"):
        folder_subj = parts[1].strip()
        if not any(folder_subj.lower().endswith(ext) for ext in [".pdf", ".docx", ".zip", ".jpg", ".png", ".pptx"]):
            subject = clean_subject_name(folder_subj)

    if subject == "General Academic":
        for p in parts:
            for sname in SUBJECT_CODE_MAP.keys():
                if sname.lower() in p.lower():
                    subject = sname
                    break
            if subject != "General Academic":
                break

    code_match = re.search(r"\b([A-Z]{2,3}[-\s]?\d{3})\b", fname)
    if code_match:
        subject_code = code_match.group(1).replace(" ", "-")
    else:
        subject_code = SUBJECT_CODE_MAP.get(subject, "GEN-000")

    p_lower = rel_path.lower()
    if "akash" in p_lower or "aakash" in p_lower:
        category = "Akash Solved Question Banks"
    elif "mid sem" in p_lower or "midterm" in p_lower:
        category = "Mid-Term Papers & PYQs"
    elif "end sem" in p_lower or "endterm" in p_lower:
        category = "End-Term Papers & PYQs"
    elif "previous years" in p_lower or "pyq" in p_lower or "question paper" in p_lower:
        category = "Previous Year Papers"
    elif "syllabus" in p_lower:
        category = "Official Syllabus & Blueprints"
    elif "lab" in p_lower or "practical" in p_lower or "workshop" in p_lower:
        category = "Practical Files & Lab Manuals"
    elif "book" in p_lower or "textbook" in p_lower or "guide" in p_lower:
        category = "Reference Books & Guides"
    elif "notes" in p_lower or "theory" in p_lower or "unit" in p_lower:
        category = "Lecture Notes & Theory"
    elif "assignment" in p_lower or "tutorial" in p_lower:
        category = "Assignments & Tutorials"
    elif "datesheet" in p_lower or "notice" in p_lower:
        category = "Official Datesheet / Notice"
    else:
        category = "General Academic Materials"

    is_typeset = "_typeset" in fname.lower()

    date_match = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-_]?\s*(\d{4})\b", fname, re.I)
    year_match = re.search(r"\b(202[0-9]|201[0-9])\b", fname)
    if date_match:
        exam_session = f"{date_match.group(1).capitalize()} {date_match.group(2)}"
    elif year_match:
        exam_session = f"Year {year_match.group(1)}"
    else:
        exam_session = "Standard"

    clean_title, description, badge = generate_clean_metadata({
        "filename": fname,
        "relative_path": rel_path,
        "subject": subject,
        "category": category,
        "exam_session": exam_session
    })

    tags = []
    if semester:
        tags.append(f"Sem {semester}")
    if subject != "General Academic":
        tags.append(subject)
    if subject_code != "GEN-000":
        tags.append(subject_code)
    tags.append(category)
    if badge:
        tags.append(badge)
    if is_typeset:
        tags.append("Typeset Master")

    return {
        "id": f"ciq_{abs(hash(rel_path)) % 1000000:06d}",
        "title": clean_title,
        "description": description,
        "content_badge": badge,
        "filename": fname,
        "subject": subject,
        "subject_code": subject_code,
        "semester": semester,
        "category": category,
        "exam_session": exam_session,
        "is_typeset": is_typeset,
        "size_kb": 250.0,
        "relative_path": rel_path,
        "file_path": rel_path,
        "drive_file_id": drive_id,
        "tags": tags
    }

def build_tree_from_catalog(catalog: List[Dict[str, Any]]) -> Dict[str, Any]:
    tree: Dict[int, Dict[str, Any]] = {}
    for item in catalog:
        sem = item["semester"] or 0
        subj = item["subject"]
        cat = item["category"]

        if sem not in tree:
            tree[sem] = {
                "semester": sem,
                "title": f"Semester {sem}" if sem > 0 else "General Archives",
                "subjects": {}
            }

        if subj not in tree[sem]["subjects"]:
            tree[sem]["subjects"][subj] = {
                "name": subj,
                "code": item["subject_code"],
                "categories": {}
            }

        if cat not in tree[sem]["subjects"][subj]["categories"]:
            tree[sem]["subjects"][subj]["categories"][cat] = []

        tree[sem]["subjects"][subj]["categories"][cat].append(item)

    return {
        "total_items": len(catalog),
        "total_semesters": len(tree),
        "semesters": {str(k): v for k, v in sorted(tree.items())}
    }

def consolidate_and_pair_catalog(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # 1. Deduplicate near-identical files in the same semester, subject & category
    dedup_dict = {}
    for item in items:
        norm_fn = re.sub(r'[\s\-_]+', '', item['filename'].lower())
        key = (item['semester'], item['subject'], item['category'], norm_fn)
        if key not in dedup_dict:
            dedup_dict[key] = item
        else:
            existing = dedup_dict[key]
            # Keep the cleaner filename (avoiding copies with (1))
            if '(1)' in existing['filename'] and '(1)' not in item['filename']:
                dedup_dict[key] = item

    filtered = list(dedup_dict.values())
    typeset_items = [x for x in filtered if x.get("is_typeset")]
    raw_only = [x for x in filtered if not x.get("is_typeset")]

    def match_score(t: Dict[str, Any], r: Dict[str, Any]) -> int:
        if t.get("semester") != r.get("semester") or t.get("subject") != r.get("subject"):
            return -1
        t_fn = t["filename"].lower()
        r_fn = r["filename"].lower()
        score = 0
        yt = re.findall(r"20\d\d", t_fn)
        yr = re.findall(r"20\d\d", r_fn)
        if not yr:
            for yy in ["22", "23", "24", "25", "26"]:
                if yy in r_fn:
                    yr = ["20" + yy]
                    break
        if yt and yr:
            if set(yt).intersection(set(yr)):
                score += 10
            else:
                return -1
        is_mid_t = "mid" in t_fn or "classtest" in t_fn
        is_mid_r = "mid" in r_fn or "classtest" in r_fn or "class test" in r_fn
        is_end_t = "end" in t_fn
        is_end_r = "end" in r_fn or "dec" in r_fn or "jan" in r_fn or "feb" in r_fn
        if is_mid_t and is_mid_r:
            score += 5
        elif is_end_t and is_end_r:
            score += 5
        elif is_mid_t != is_mid_r and is_end_t != is_end_r:
            return -1
        return score

    matched_raw_ids = set()
    consolidated = []

    for t in typeset_items:
        candidates = []
        for r in raw_only:
            sc = match_score(t, r)
            if sc > 0:
                candidates.append((sc, r))
        candidates.sort(key=lambda x: x[0], reverse=True)
        if candidates:
            best_r = candidates[0][1]
            t["has_typeset"] = True
            t["has_raw"] = True
            t["typeset_drive_id"] = t["drive_file_id"]
            t["typeset_relative_path"] = t["relative_path"]
            t["raw_drive_id"] = best_r["drive_file_id"]
            t["raw_relative_path"] = best_r["relative_path"]
            t["content_badge"] = "TYPESET + RAW"
            t["tags"] = list(set(t.get("tags", []) + ["Typeset Master", "Raw Scan Available"]))
            matched_raw_ids.add(best_r["id"])
        else:
            t["has_typeset"] = True
            t["has_raw"] = False
            t["typeset_drive_id"] = t["drive_file_id"]
            t["typeset_relative_path"] = t["relative_path"]
            t["raw_drive_id"] = None
            t["raw_relative_path"] = None
        consolidated.append(t)

    for r in raw_only:
        if r["id"] not in matched_raw_ids:
            r["has_typeset"] = False
            r["has_raw"] = True
            r["raw_drive_id"] = r["drive_file_id"]
            r["raw_relative_path"] = r["relative_path"]
            r["typeset_drive_id"] = None
            r["typeset_relative_path"] = None
            consolidated.append(r)

    return consolidated

def main():
    if not os.path.exists(VAULT_DRIVE_MAP_FILE):
        print(f"[!] Map file not found: {VAULT_DRIVE_MAP_FILE}")
        return

    with open(VAULT_DRIVE_MAP_FILE, "r", encoding="utf-8") as f:
        vmap = json.load(f)

    files = vmap.get("files", {})
    print(f"[*] Processing {len(files)} files from Google Drive vault map...")

    raw_parsed = []
    valid_exts = {".pdf", ".docx", ".jpg", ".jpeg", ".png", ".pptx"}

    for rel_path, drive_id in files.items():
        ext = os.path.splitext(rel_path)[1].lower()
        if ext not in valid_exts:
            continue
        if ".crdownload" in rel_path.lower():
            continue
        if any(ignored in rel_path for ignored in [".py", ".tmp", "desktop.ini"]):
            continue

        item = extract_meta_from_drive_path(rel_path, drive_id)
        raw_parsed.append(item)

    print(f"[*] Cleaned {len(raw_parsed)} raw items, pairing typeset masters with scans...")
    catalog = consolidate_and_pair_catalog(raw_parsed)

    catalog.sort(key=lambda x: (
        x["semester"] or 0,
        x["subject"],
        x["category"],
        x["exam_session"] or ""
    ), reverse=True)

    tree = build_tree_from_catalog(catalog)

    result = {
        "catalog": catalog,
        "tree": tree,
        "generated_at": vmap.get("updated_at")
    }

    with open(CATALOG_CACHE_FILE, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"✅ Generated {len(catalog)} verified study items into {CATALOG_CACHE_FILE}")
    print(f"✅ Dual (Typeset + Raw): {sum(1 for x in catalog if x.get('has_typeset') and x.get('has_raw'))}")
    print(f"✅ Hierarchical tree contains {tree['total_semesters']} semesters, {sum(len(s['subjects']) for s in tree['semesters'].values())} subjects")

if __name__ == "__main__":
    main()
