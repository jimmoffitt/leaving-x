import fcntl
import json
import os
from contextlib import contextmanager

POSTED_RECORDS_FILE = "posted_records.json"
LOCK_FILE = POSTED_RECORDS_FILE + ".lock"

"""
The Tweet ID -> Bluesky post mapping. The archive backfill (leaving_x.py) and the "On this day"
timer (on_this_day.py) can run at the same time, so writes are made under a file lock.
"""

@contextmanager
def _locked():
    with open(LOCK_FILE, "w") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(lock, fcntl.LOCK_UN)

def _read():
    try:
        with open(POSTED_RECORDS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def load_posted_records():
    """
    Loads the Tweet ID -> Bluesky post mapping, or returns an empty dict if not found.

    Each entry looks like: {"uri": "at://...", "cid": "...", "kind": "archive" | "on_this_day", "year": 2026}
    'year' is only set for "on_this_day" posts.
    """
    with _locked():
        return _read()

def save_posted_record(tweet_id, record):
    """Saves (or replaces) the Bluesky post for a Tweet. Writes to a temp file first so a crash can't corrupt the file."""
    with _locked():
        records = _read()
        records[tweet_id] = record
        tmp_file = POSTED_RECORDS_FILE + ".tmp"
        with open(tmp_file, "w") as f:
            json.dump(records, f, indent=1)
        os.replace(tmp_file, POSTED_RECORDS_FILE)
