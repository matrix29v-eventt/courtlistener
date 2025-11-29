# main.py
import argparse
import json
import os
from pathlib import Path
from typing import Iterable, Dict, Any, List, Optional
from client import CourtListenerClient

DATA_DIR = Path("data")
USERS_FILE = DATA_DIR / "users.json"

def ensure_users_file():
    DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        USERS_FILE.write_text(json.dumps({"users": []}, indent=2), encoding="utf-8")

def add_user_record(username: str, file_path: Path):
    ensure_users_file()
    db = json.loads(USERS_FILE.read_text(encoding="utf-8"))
    user = next((u for u in db["users"] if u["username"] == username), None)
    if not user:
        user = {"username": username, "saved_files": []}
        db["users"].append(user)
    user["saved_files"].append(str(file_path))
    USERS_FILE.write_text(json.dumps(db, indent=2), encoding="utf-8")

def save_jsonl(path: Path, items: Iterable[Dict[str, Any]]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for item in items:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

def filter_fields(record: Dict[str, Any], fields: Optional[List[str]]) -> Dict[str, Any]:
    if not fields:
        return record
    out = {}
    for k in fields:
        if k in record:
            out[k] = record[k]
    return out

def read_since_file(path: Path) -> Optional[str]:
    if not path.exists():
        return None
    try:
        txt = path.read_text(encoding="utf-8").strip()
        return txt if txt else None
    except Exception:
        return None

def write_since_file(path: Path, date_str: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(date_str.strip(), encoding="utf-8")

def extract_date_filed(opinion: Dict[str, Any]) -> Optional[str]:
    # CourtListener uses "date_filed" in many opinion records; try to extract first 10 chars (YYYY-MM-DD)
    df = opinion.get("date_filed")
    if not df:
        return None
    return str(df)[:10]

def main():
    parser = argparse.ArgumentParser(description="CourtListener Demo Project (with --fields and --since-file)")
    parser.add_argument("--user", required=True, help="Username to store data under")
    parser.add_argument("--limit", type=int, default=10, help="How many records to fetch (demo limit)")
    parser.add_argument("--date_min", help="Filter: date_filed_min (YYYY-MM-DD)")
    parser.add_argument("--token", help="CourtListener API token (optional; falls back to COURTLISTENER_TOKEN env var)")
    parser.add_argument("--ua", help="User-Agent string (optional; falls back to COURTLISTENER_UA env var)")
    parser.add_argument("--fields", help="Comma-separated top-level fields to save (e.g. id,date_filed,absolute_url)")
    parser.add_argument("--since-file", help="Path to since-file for incremental sync (will read/write last date_filed)")
    args = parser.parse_args()

    # Prepare token/ua and client
    token = args.token or os.getenv("COURTLISTENER_TOKEN")
    ua = args.ua or os.getenv("COURTLISTENER_UA")
    client = CourtListenerClient(token=token, user_agent=ua)

    # Determine date_filed_min via precedence:
    # 1) explicit --date_min
    # 2) since-file contents (if exists and --date_min not provided)
    date_min = args.date_min
    since_path = Path(args.since_file) if args.since_file else None
    if not date_min and since_path:
        stored = read_since_file(since_path)
        if stored:
            date_min = stored
            print(f"Using since-file date_filed_min from {since_path}: {date_min}")

    # Prepare fields
    fields_list = None
    if args.fields:
        # simple split and strip
        fields_list = [f.strip() for f in args.fields.split(",") if f.strip()]
        print(f"Saving only fields: {fields_list}")

    # Build filters for API
    filters = {}
    if date_min:
        filters["date_filed_min"] = date_min

    print(f"Fetching up to {args.limit} opinions ...")
    collected: List[Dict[str, Any]] = []
    newest_date = None  # track max date_filed among fetched

    try:
        for i, rec in enumerate(client.opinions(**filters), start=1):
            # track newest date_filed (YYYY-MM-DD)
            d = extract_date_filed(rec)
            if d:
                if (newest_date is None) or (d > newest_date):
                    newest_date = d
            # apply fields filter
            out = filter_fields(rec, fields_list)
            collected.append(out)
            if i >= args.limit:
                break
    except Exception as e:
        print("Error while fetching:", e)
        # If fetch failed and we have no items, exit with error (don't update since-file)
        if not collected:
            raise

    output_file = DATA_DIR / f"{args.user}_opinions.jsonl"
    save_jsonl(output_file, collected)
    add_user_record(args.user, output_file)
    print(f"Saved {len(collected)} records to {output_file}")
    print(f"User data index updated: {USERS_FILE}")

    # Update since-file if provided and we found a newest_date
    if since_path and newest_date:
        try:
            write_since_file(since_path, newest_date)
            print(f"Wrote newest date_filed '{newest_date}' to since-file: {since_path}")
        except Exception as e:
            print(f"Failed to write since-file {since_path}: {e}")

if __name__ == "__main__":
    main()
