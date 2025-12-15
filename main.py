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
    return {k: record[k] for k in fields if k in record}


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
    df = opinion.get("date_filed")
    return str(df)[:10] if df else None


def print_summary(records: List[Dict[str, Any]]):
    print("\nSummary:")
    print(f"- Records saved: {len(records)}")

    if not records:
        print("- No records to summarize")
        return

    r = records[0]

    print(f"- Opinion ID: {r.get('id', 'N/A')}")
    print(f"- Case URL: {r.get('absolute_url', 'N/A')}")
    print(f"- Date filed: {r.get('date_filed', 'N/A')}")

    text = r.get("plain_text")
    if isinstance(text, str):
        print(f"- Opinion length: {len(text)} characters")
    else:
        print("- Opinion text not included (possibly filtered)")


def main():
    parser = argparse.ArgumentParser(
        description="CourtListener Demo Project (with --fields, --since-file, and summary output)"
    )
    parser.add_argument("--user", required=True, help="Username to store data under")
    parser.add_argument("--limit", type=int, default=10, help="How many records to fetch")
    parser.add_argument("--date_min", help="Filter: date_filed_min (YYYY-MM-DD)")
    parser.add_argument("--token", help="CourtListener API token")
    parser.add_argument("--ua", help="User-Agent string")
    parser.add_argument("--fields", help="Comma-separated fields to save")
    parser.add_argument("--since-file", help="Path to since-file for incremental sync")
    args = parser.parse_args()

    token = args.token or os.getenv("COURTLISTENER_TOKEN")
    ua = args.ua or os.getenv("COURTLISTENER_UA")
    client = CourtListenerClient(token=token, user_agent=ua)

    date_min = args.date_min
    since_path = Path(args.since_file) if args.since_file else None
    if not date_min and since_path:
        stored = read_since_file(since_path)
        if stored:
            date_min = stored
            print(f"Using since-file date_filed_min from {since_path}: {date_min}")

    fields_list = None
    if args.fields:
        fields_list = [f.strip() for f in args.fields.split(",") if f.strip()]
        print(f"Saving only fields: {fields_list}")

    filters = {}
    if date_min:
        filters["date_filed_min"] = date_min

    print(f"Fetching up to {args.limit} opinions ...")

    collected: List[Dict[str, Any]] = []
    newest_date = None

    try:
        for i, rec in enumerate(client.opinions(**filters), start=1):
            d = extract_date_filed(rec)
            if d and (newest_date is None or d > newest_date):
                newest_date = d

            collected.append(filter_fields(rec, fields_list))

            if i >= args.limit:
                break
    except Exception as e:
        print("Error while fetching:", e)
        if not collected:
            raise

    output_file = DATA_DIR / f"{args.user}_opinions.jsonl"
    save_jsonl(output_file, collected)
    add_user_record(args.user, output_file)

    print(f"Saved {len(collected)} records to {output_file}")
    print(f"User data index updated: {USERS_FILE}")

    if since_path and newest_date:
        try:
            write_since_file(since_path, newest_date)
            print(f"Wrote newest date_filed '{newest_date}' to since-file: {since_path}")
        except Exception as e:
            print(f"Failed to write since-file {since_path}: {e}")

    # 🔹 NEW: print terminal summary
    print_summary(collected)


if __name__ == "__main__":
    main()
