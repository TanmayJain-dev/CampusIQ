#!/usr/bin/env python3
"""
sync_drive_vault.py - Automated Google Drive Crawler & Vault Mapper for CampusIQ
=============================================================================
Recursively indexes Google Drive folders, extracts every file's unique ID,
and maps it to CampusIQ Study Vault relative paths for headless PDF streaming.
"""

import sys
import os
import re
import html
import json
import time
import urllib.request
from typing import Dict, List, Tuple

PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
OUTPUT_MAP_FILE = os.path.join(DATA_DIR, "vault_drive_map.json")
CATALOG_CACHE_FILE = os.path.join(DATA_DIR, "catalog_cache.json")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "*/*"
}

def fetch_folder_items(folder_id: str) -> List[Tuple[str, str, bool]]:
    """
    Fetches items inside a Google Drive folder.
    Returns a list of tuples: (item_id, item_name, is_folder)
    """
    url = f"https://drive.google.com/drive/folders/{folder_id}"
    req = urllib.request.Request(url, headers=HEADERS)
    try:
        content = urllib.request.urlopen(req, timeout=15).read().decode("utf-8", errors="ignore")
    except Exception as e:
        print(f"[!] Error loading folder {folder_id}: {e}", file=sys.stderr)
        return []

    # Extract all items using data-id and title/strong tags
    # In Google Drive table row: data-id="ID" ... <strong class="DNoYtb">NAME</strong>
    matches = re.findall(r'data-id=\"([a-zA-Z0-9_-]{28,40})\".*?<strong class=\"DNoYtb\">([^<]+)</strong>', content, re.DOTALL)
    items = []
    seen = set()
    for fid, raw_name in matches:
        if fid in seen or fid == folder_id:
            continue
        seen.add(fid)
        name = html.unescape(raw_name).strip()
        
        # Check if folder or file
        # Find the block around fid to check mime type
        idx = content.find(fid)
        block = content[max(0, idx-100):idx+300]
        is_folder = "application/vnd.google-apps.folder" in block or not ("." in name and any(name.lower().endswith(ext) for ext in [".pdf", ".docx", ".pptx", ".zip", ".png", ".jpg"]))
        items.append((fid, name, is_folder))
    return items

def crawl_drive_tree(root_folder_id: str, current_path: str = "") -> Dict[str, str]:
    """
    Recursively crawls the Google Drive folder tree.
    Returns mapping: { "relative/path/to/file.pdf": "file_id", ... }
    """
    file_map: Dict[str, str] = {}
    print(f"[*] Crawling: {current_path or 'ROOT'} (ID: {root_folder_id})")
    
    items = fetch_folder_items(root_folder_id)
    time.sleep(0.3)  # Gentle crawl rate
    
    for item_id, item_name, is_folder in items:
        sub_path = f"{current_path}/{item_name}".strip("/") if current_path else item_name
        if is_folder:
            sub_files = crawl_drive_tree(item_id, sub_path)
            file_map.update(sub_files)
        else:
            file_map[sub_path] = item_id
            print(f"  📄 [PDF] {sub_path} -> {item_id}")
            
    return file_map

def main():
    root_id = "1xL3cYaVt8YdV1gvYgtVJJ-_6D7oJhXBN"
    if len(sys.argv) > 1:
        root_id = sys.argv[1].split("/")[-1].split("?")[0]
        
    print(f"🚀 Starting Google Drive crawl for root: {root_id}")
    file_map = crawl_drive_tree(root_id)
    print(f"✅ Total files discovered in Google Drive: {len(file_map)}")

    # Load existing map if any
    existing = {}
    if os.path.exists(OUTPUT_MAP_FILE):
        try:
            with open(OUTPUT_MAP_FILE, "r", encoding="utf-8") as f:
                existing = json.load(f)
        except Exception:
            existing = {}

    existing_files = existing.get("files", {})
    existing_files.update(file_map)
    existing["files"] = existing_files
    existing["root_folder_id"] = root_id
    existing["updated_at"] = time.time()

    with open(OUTPUT_MAP_FILE, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    print(f"💾 Saved {len(existing_files)} file mappings to {OUTPUT_MAP_FILE}")

    # Now correlate with catalog_cache.json if present
    if os.path.exists(CATALOG_CACHE_FILE):
        try:
            with open(CATALOG_CACHE_FILE, "r", encoding="utf-8") as f:
                cat = json.load(f)

            # Match items by filename
            matched = 0
            name_to_id = {os.path.basename(p): fid for p, fid in existing_files.items()}
            
            def tag_tree(node):
                nonlocal matched
                if isinstance(node, dict):
                    if "filename" in node and node.get("filename") in name_to_id:
                        node["drive_file_id"] = name_to_id[node["filename"]]
                        matched += 1
                    for v in node.values():
                        tag_tree(v)
                elif isinstance(node, list):
                    for el in node:
                        tag_tree(el)

            tag_tree(cat)
            with open(CATALOG_CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump(cat, f, indent=2)
            print(f"🎯 Correlated and tagged {matched} files in {CATALOG_CACHE_FILE}")
        except Exception as e:
            print(f"[!] Error updating catalog cache: {e}", file=sys.stderr)

if __name__ == "__main__":
    main()
