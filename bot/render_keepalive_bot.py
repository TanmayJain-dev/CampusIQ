#!/usr/bin/env python3
"""
render_keepalive_bot.py - Zero-Sleep Keep-Alive Heartbeat Bot for Render Services
================================================================================
Prevents Render free tier web services from spinning down (cold shut) after 15m
of inactivity by sending lightweight health pings every 10 minutes.

Author: CampusIQ Automation Core / Antigravity
License: MIT
"""

import sys
import os
import time
import json
import random
import logging
import argparse
import urllib.request
import urllib.error
from datetime import datetime
from typing import List, Dict, Any, Tuple

DEFAULT_TARGETS = [
    {
        "name": "CampusIQ",
        "url": "https://campusiq-i9aq.onrender.com/api/health",
        "critical": True
    }
]

LOG_DIR = os.path.expanduser("~/.local/state/render-keepalive")
DEFAULT_LOG_FILE = os.path.join(LOG_DIR, "bot.log")

def setup_logger(log_file: str, verbose: bool = False) -> logging.Logger:
    os.makedirs(os.path.dirname(os.path.abspath(log_file)), exist_ok=True)
    logger = logging.getLogger("RenderKeepAlive")
    logger.setLevel(logging.DEBUG if verbose else logging.INFO)
    logger.handlers.clear()

    # Console Handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.DEBUG if verbose else logging.INFO)
    c_fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
    ch.setFormatter(c_fmt)
    logger.addHandler(ch)

    # File Handler
    try:
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(logging.INFO)
        f_fmt = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fh.setFormatter(f_fmt)
        logger.addHandler(fh)
    except Exception as e:
        logger.warning(f"Could not open log file {log_file}: {e}")

    return logger

def ping_target(target: Dict[str, Any], timeout: int = 45) -> Tuple[bool, int, float, str]:
    """
    Sends an HTTP GET heartbeat to the target.
    Returns: (success, status_code, latency_seconds, response_summary)
    """
    url = target["url"]
    name = target["name"]
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "CampusIQ-KeepAlive-Bot/1.0 (+https://campusiq-i9aq.onrender.com)",
            "Accept": "application/json, text/plain, */*"
        }
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            latency = time.time() - t0
            raw = resp.read()
            body_snippet = raw.decode("utf-8", errors="ignore")[:80].replace("\n", " ").strip()
            return True, resp.status, latency, body_snippet
    except urllib.error.HTTPError as e:
        latency = time.time() - t0
        raw = e.read()
        body_snippet = raw.decode("utf-8", errors="ignore")[:80].replace("\n", " ").strip()
        # Even if 404 or 500, Render received HTTP traffic and will NOT sleep!
        return (e.code < 500), e.code, latency, f"HTTP Error {e.code}: {body_snippet}"
    except urllib.error.URLError as e:
        latency = time.time() - t0
        return False, 0, latency, f"Connection Error: {e.reason}"
    except Exception as e:
        latency = time.time() - t0
        return False, 0, latency, f"Error: {str(e)}"

def run_ping_cycle(targets: List[Dict[str, Any]], logger: logging.Logger) -> Dict[str, Any]:
    logger.info(f"--- Starting Heartbeat Ping Cycle ({len(targets)} targets) ---")
    results = {}
    all_ok = True

    for target in targets:
        name = target["name"]
        url = target["url"]
        success, code, latency, msg = ping_target(target)

        # If it failed due to timeout or cold spin-up, retry once after a short wait
        if not success and target.get("critical", False):
            logger.warning(f"[{name}] First attempt failed ({msg}). Retrying in 10s (possible cold start)...")
            time.sleep(10)
            success, code, latency, msg = ping_target(target, timeout=60)

        results[name] = {
            "url": url,
            "success": success,
            "status_code": code,
            "latency_ms": round(latency * 1000, 1),
            "summary": msg,
            "timestamp": datetime.now().isoformat()
        }

        status_icon = "🟢" if success else "🔴"
        logger.info(f"{status_icon} [{name}] HTTP {code} ({latency:.2f}s) -> {url} | {msg}")
        if not success:
            all_ok = False

    logger.info(f"--- Ping Cycle Complete: {'ALL HEALTHY' if all_ok else 'SOME WARNINGS'} ---\n")
    return results

def daemon_loop(targets: List[Dict[str, Any]], interval_sec: int, jitter_sec: int, logger: logging.Logger):
    logger.info(f"🚀 Render Keep-Alive Daemon started. Base interval: {interval_sec}s (~{interval_sec//60} min), Jitter: ±{jitter_sec}s.")
    logger.info(f"Monitoring {len(targets)} services to prevent Render free-tier cold shutdowns.")

    while True:
        try:
            run_ping_cycle(targets, logger)
        except Exception as e:
            logger.error(f"Unexpected error in ping cycle: {e}")

        # Add random jitter to mimic natural traffic and prevent synchronized lockstep
        sleep_time = interval_sec + random.randint(-jitter_sec, jitter_sec)
        sleep_time = max(300, sleep_time) # Minimum 5 minutes
        logger.info(f"Sleeping for {sleep_time}s (~{sleep_time / 60:.1f} min) until next heartbeat...")
        time.sleep(sleep_time)

def main():
    parser = argparse.ArgumentParser(description="Render Keep-Alive Heartbeat Bot")
    parser.add_argument("--once", action="store_true", help="Run a single ping cycle and exit")
    parser.add_argument("--daemon", action="store_true", help="Run continuously in background daemon mode")
    parser.add_argument("--interval", type=int, default=600, help="Interval between pings in seconds (default: 600 = 10 min)")
    parser.add_argument("--jitter", type=int, default=30, help="Random interval jitter in seconds (default: 30)")
    parser.add_argument("--log-file", type=str, default=DEFAULT_LOG_FILE, help="Path to log file")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose debug logging")
    parser.add_argument("--targets-json", type=str, help="Optional JSON file with custom targets list")

    args = parser.parse_args()

    targets = DEFAULT_TARGETS
    if args.targets_json and os.path.exists(args.targets_json):
        try:
            with open(args.targets_json, "r") as f:
                targets = json.load(f)
        except Exception as e:
            print(f"Error loading custom targets JSON: {e}", file=sys.stderr)

    logger = setup_logger(args.log_file, args.verbose)

    if args.once or not args.daemon:
        results = run_ping_cycle(targets, logger)
        sys.exit(0 if all(r["success"] for r in results.values()) else 1)
    else:
        daemon_loop(targets, args.interval, args.jitter, logger)

if __name__ == "__main__":
    main()
