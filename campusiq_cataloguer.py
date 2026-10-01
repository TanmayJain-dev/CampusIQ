#!/usr/bin/env python3
"""
CampusIQ - Academic Study Resource Cataloguer & Indexer
======================================================
Scans and indexes all university academic papers, typeset PYQs, syllabi,
and lecture materials across semesters into a structured manifest and
searchable index for CampusIQ web & mobile interfaces.

Author: CampusIQ Automation Core / Antigravity
License: MIT
"""

import sys
import os
import re
import json
import argparse
from typing import Dict, List, Optional, Any

SUBJECT_CODE_MAP = {
    # Semester 1
    "Applied Mathematics I": "BS-111",
    "Applied Physics I": "BS-105",
    "Applied Chemistry": "BS-103",
    "Electrical Science": "ES-107",
    "Manufacturing Processes": "ES-119",
    "Human Values & Ethics": "HS-115",
    "Workshop Practice": "ES-164",
    # Semester 2
    "Applied Mathematics II": "BS-112",
    "Applied Physics II": "BS-106",
    "Programming in C": "ES-102",
    "Environmental Studies": "BS-110",
    "Communication Skills": "HS-114",
    "Engineering Mechanics": "ES-114",
    # Semester 3
    "Computational Methods": "ES-201",
    "Discrete Mathematics": "CIC-205",
    "Digital Logic and Circuit Design": "ECC-207",
    "Digital Logic and Computer Design": "ECC-207",
    "Data Structures": "CIC-209",
    "Object Oriented Programming": "CIC-211",
}


class CampusIQResourceCataloguer:
    """Discovers, parses metadata, and catalogues academic files."""

    def __init__(self, root_dir: str, cache_file: Optional[str] = None):
        self.root_dir = os.path.abspath(root_dir) if root_dir else ""
        self.cache_file = os.path.abspath(cache_file) if cache_file else os.path.join(os.path.dirname(__file__), "data", "catalog_cache.json")
        self.has_root = bool(self.root_dir and os.path.exists(self.root_dir))

        if not self.has_root and not os.path.exists(self.cache_file):
            raise FileNotFoundError(f"Root academic directory does not exist: {self.root_dir} and cache file not found: {self.cache_file}")

    def scan(self, semester_filter: Optional[int] = None, typeset_only: bool = True) -> List[Dict[str, Any]]:
        # If running on cloud without local file mount, load from pre-indexed cache
        if not self.has_root and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    items = cached_data.get("catalog", [])
                    if semester_filter is not None:
                        items = [x for x in items if x.get("semester") == semester_filter]
                    if typeset_only:
                        items = [x for x in items if x.get("is_typeset")]
                    return items
            except Exception as e:
                print(f"[!] Warning reading catalog cache: {e}", file=sys.stderr)

        catalog = []
        if self.has_root:
            for root, dirs, files in os.walk(self.root_dir):
                for fname in files:
                    if not fname.endswith(".pdf"):
                        continue

                    full_path = os.path.join(root, fname)
                    rel_path = os.path.relpath(full_path, self.root_dir)
                    size_kb = round(os.path.getsize(full_path) / 1024, 1)

                    meta = self._extract_metadata(rel_path, fname, full_path, size_kb)

                    if semester_filter is not None and meta["semester"] != semester_filter:
                        continue
                    if typeset_only and not meta["is_typeset"]:
                        continue

                    catalog.append(meta)

        # Sort logically: Semester -> Subject -> Category -> Year
        catalog.sort(key=lambda x: (
            x["semester"] or 0,
            x["subject"],
            x["category"],
            x["exam_session"] or ""
        ), reverse=True)
        return catalog

    def build_tree(self) -> Dict[str, Any]:
        """Builds a 3-tier hierarchical study tree: Semester -> Subject -> Category -> Items."""
        if not self.has_root and os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    cached_data = json.load(f)
                    if "tree" in cached_data and cached_data["tree"]:
                        return cached_data["tree"]
            except Exception as e:
                print(f"[!] Warning reading tree from cache: {e}", file=sys.stderr)

        catalog = self.scan(typeset_only=True)
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
            "typeset_count": len([x for x in catalog if x.get("is_typeset", False)]),
            "semesters": {str(k): v for k, v in sorted(tree.items())}
        }

    def _extract_metadata(self, rel_path: str, fname: str, full_path: str, size_kb: float) -> Dict[str, Any]:
        parts = rel_path.split(os.sep)

        # 1. Semester Extraction
        semester = None
        for p in parts:
            sem_m = re.search(r"Semester\s*(\d+)", p, re.I)
            if sem_m:
                semester = int(sem_m.group(1))
                break

        # 2. Subject Extraction (Hierarchical folder preferred, fallback to string map)
        subject = "General Academic"
        if semester and len(parts) > 1 and parts[0].lower().startswith("semester"):
            folder_subj = parts[1].strip()
            if not folder_subj.endswith(".pdf"):
                subject = folder_subj

        if subject == "General Academic":
            for p in parts:
                for sname in SUBJECT_CODE_MAP.keys():
                    if sname.lower() in p.lower():
                        subject = sname
                        break
                if subject != "General Academic":
                    break

        # 3. Subject Code
        code_match = re.search(r"\b([A-Z]{2,3}[-\s]?\d{3})\b", fname)
        if code_match:
            subject_code = code_match.group(1).replace(" ", "-")
        else:
            subject_code = SUBJECT_CODE_MAP.get(subject, "GEN-000")

        # 4. Standardized Category Grouping
        p_lower = rel_path.lower()
        if "mid sem" in p_lower or "midterm" in p_lower:
            category = "Mid-Term Papers & PYQs"
        elif "end sem" in p_lower or "endterm" in p_lower:
            category = "End-Term Papers & PYQs"
        elif "syllabus" in p_lower:
            category = "Official Syllabus & Blueprints"
        elif "lab" in p_lower or "practical" in p_lower or "workshop" in p_lower:
            category = "Practical Files & Lab Manuals"
        elif "book" in p_lower or "textbook" in p_lower or "guide" in p_lower:
            category = "Reference Books & Guides"
        elif "notes" in p_lower or "theory" in p_lower or "unit" in p_lower or "quiz" in p_lower:
            category = "Lecture Notes & Theory"
        elif "assignment" in p_lower:
            category = "Assignments & Tutorials"
        elif "datesheet" in p_lower or "notice" in p_lower:
            category = "Official Datesheet / Notice"
            subject = "Examination Division"
        else:
            category = "General Academic Materials"

        # Typeset Flag
        is_typeset = "_typeset" in fname.lower()

        # Exam Session / Date
        date_match = re.search(r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*[-_]?\s*(\d{4})\b", fname, re.I)
        year_match = re.search(r"\b(202[0-9])\b", fname)
        if date_match:
            exam_session = f"{date_match.group(1).capitalize()} {date_match.group(2)}"
        elif year_match:
            exam_session = f"Year {year_match.group(1)}"
        else:
            exam_session = "Standard"

        # Pretty Display Title (No 'Typeset' prefix)
        title_base = os.path.splitext(fname)[0].replace("_Typeset", "").replace("_typeset", "").replace("_", " ").strip()
        display_title = title_base

        tags = []
        if semester:
            tags.append(f"Sem {semester}")
        if subject != "General Academic":
            tags.append(subject)
        if subject_code != "GEN-000":
            tags.append(subject_code)
        tags.append(category)
        if is_typeset:
            tags.append("Typeset Master")

        return {
            "id": f"ciq_{abs(hash(rel_path)) % 1000000:06d}",
            "title": display_title,
            "filename": fname,
            "subject": subject,
            "subject_code": subject_code,
            "semester": semester,
            "category": category,
            "exam_session": exam_session,
            "is_typeset": is_typeset,
            "size_kb": size_kb,
            "relative_path": rel_path,
            "file_path": full_path,
            "tags": tags
        }


def generate_markdown_catalog(catalog: List[Dict[str, Any]]) -> str:
    """Generate a clean, structured Markdown study catalog."""
    md = [
        "# 📚 CampusIQ Unified Academic Resource Catalog",
        "> Curated, typeset, and indexed previous year papers, syllabi, and study resources for GGSIPU students.",
        "",
        f"**Total Indexed Resources:** {len(catalog)} documents  ",
        f"**Typeset High-Yield Papers:** {len([c for c in catalog if c['is_typeset']])} documents  ",
        "",
        "---",
        ""
    ]

    # Group by Semester -> Subject
    grouped: Dict[str, Dict[str, List[Dict[str, Any]]]] = {}
    for item in catalog:
        s_key = f"Semester {item['semester']}" if item['semester'] else "General Resources"
        subj = item["subject"]
        if s_key not in grouped:
            grouped[s_key] = {}
        if subj not in grouped[s_key]:
            grouped[s_key][subj] = []
        grouped[s_key][subj].append(item)

    for sem, subjects in sorted(grouped.items()):
        md.append(f"## 🏛️ {sem}\n")
        for subj, items in sorted(subjects.items()):
            subj_code = items[0]["subject_code"]
            md.append(f"### 📖 {subj} (`{subj_code}`)\n")
            md.append("| Type | Title | Session | Quality | Size | Location |")
            md.append("| :--- | :--- | :---: | :---: | :---: | :--- |")
            for it in items:
                q_badge = "💎 **Typeset**" if it["is_typeset"] else "📄 Standard PDF"
                md.append(f"| {it['category']} | **{it['title']}** | {it['exam_session']} | {q_badge} | {it['size_kb']} KB | `{it['relative_path']}` |")
            md.append("")
        md.append("---\n")

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="CampusIQ - Academic Study Resource Cataloguer & Manifest Generator"
    )
    default_vault = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "vault")
    parser.add_argument("--dir", type=str, default=default_vault, help="Root directory of academic resources")
    parser.add_argument("--semester", type=int, help="Filter by specific semester (e.g. 3)")
    parser.add_argument("--subject", type=str, help="Filter by subject name")
    parser.add_argument("--typeset-only", action="store_true", default=True, help="Include only verified typeset documents (Default: True)")
    parser.add_argument("--include-all", action="store_true", help="Include non-typeset reference documents")
    parser.add_argument("--export-json", type=str, help="File path to save JSON manifest")
    parser.add_argument("--export-markdown", type=str, help="File path to save Markdown catalog")

    args = parser.parse_args()

    cataloguer = CampusIQResourceCataloguer(args.dir)
    typeset_flag = False if args.include_all else True
    items = cataloguer.scan(semester_filter=args.semester, typeset_only=typeset_flag)

    if args.subject:
        items = [i for i in items if args.subject.lower() in i["subject"].lower()]

    print(f"\n[+] Catalogued {len(items)} academic resources from: {args.dir}")
    typeset_count = len([i for i in items if i["is_typeset"]])
    print(f"    ⭐ Typeset PYQ Master Papers: {typeset_count}")
    print(f"    📄 Standard Reference Papers & Notes: {len(items) - typeset_count}\n")

    # Preview sample
    print("=" * 80)
    print(f"{'Subject':<32} {'Type':<22} {'Session':<12} {'Quality'}")
    print("-" * 80)
    for it in items[:10]:
        q = "TYPESET" if it["is_typeset"] else "PDF"
        print(f"{it['subject'][:30]:<32} {it['category'][:20]:<22} {it['exam_session'][:10]:<12} {q}")
    print("=" * 80)
    if len(items) > 10:
        print(f"... and {len(items) - 10} more documents.\n")

    if args.export_json:
        with open(args.export_json, "w") as f:
            json.dump(items, f, indent=2)
        print(f"[✓] Saved JSON manifest to: {args.export_json}")

    if args.export_markdown:
        md_content = generate_markdown_catalog(items)
        with open(args.export_markdown, "w") as f:
            f.write(md_content)
        print(f"[✓] Saved Markdown catalog to: {args.export_markdown}")


if __name__ == "__main__":
    main()
