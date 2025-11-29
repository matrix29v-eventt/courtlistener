CourtListener Bulk Fetch Demo

A small Python project to fetch U.S. court opinions using the CourtListener REST API with pagination, retries, incremental sync, and selective field saving.

📌 Features

This demo project includes:

Pagination — Automatically fetches multiple pages from CourtListener.

Retry logic with backoff — Handles timeouts and unstable network conditions.

Selective field saving (--fields) — Reduce file size by saving only the fields you need.

Incremental sync (--since-file) — Fetch only newer opinions on each run.

User data index — Tracks what each user fetched and when.

Configurable — Pass API token, User-Agent, timeout, retries, fields, and filters via CLI.

JSONL output — Saves results into newline-delimited JSON (.jsonl) for easy ML/data use.

📂 Project Structure
courtlistener/
│
├── client.py            # API client with retries + pagination
├── storage.py           # JSONL write & user data index management
├── main.py              # CLI entry point
├── README.md            # Project documentation
│
├── data/                # Saved opinion records (gitignored)
│     ├── alice_opinions.jsonl
│     └── users.json
│
└── state/               # Incremental sync state (gitignored)
      └── alice_since.txt


Both data/ and state/ are already ignored in .gitignore for safety.

🛠 Requirements

Python 3.10+

requests library

A valid CourtListener API token

A valid User-Agent string (must include your name + an email)

🔧 Installation
git clone https://github.com/<your-user>/courtlistener-demo.git
cd courtlistener-demo

# create virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1   # Windows PowerShell

# install dependencies
pip install -r requirements.txt


If you do not have a requirements.txt, create one:

requests

🔐 CourtListener API Setup
1. Get an API Token

Go to:

https://www.courtlistener.com/account/api/

Click Generate Token.

2. Your User-Agent MUST follow their rules

The UA must contain:

App name

Version

Your name

Your email

Example:

CourtListenerDemo/1.0 (Anzer Farooq; matrix29v@gmail.com)


CourtListener blocks generic UAs.

3. Pass token + UA at runtime (recommended)
python main.py --token YOUR_TOKEN --ua "CourtListenerDemo/1.0 (Your Name; you@example.com)" ...

▶️ Basic Usage
Fetch 10 latest opinions after a given date:
python main.py --user alice --limit 10 --date_min 2024-01-01 ^
  --token YOUR_TOKEN ^
  --ua "CourtListenerDemo/1.0 (Your Name; you@example.com)"


Output will save into:

data/alice_opinions.jsonl

⚙️ Selective Fields (--fields)

To keep output small, save only selected fields:

python main.py --user alice --limit 50 --fields id,date_filed,absolute_url ^
  --token YOUR_TOKEN ^
  --ua "CourtListenerDemo/1.0 (Your Name; you@example.com)"


Example fields you may want:

id,date_filed,absolute_url,cluster_id,author_str,page_count,download_url,resource_uri

🔁 Incremental Sync (--since-file)

Fetch only newer records each time.

First run (bootstrap)
python main.py --user alice --limit 50 --date_min 2024-01-01 ^
  --since-file state/alice_since.txt ^
  --fields id,date_filed,absolute_url ^
  --token YOUR_TOKEN ^
  --ua "CourtListenerDemo/1.0 (Your Name; you@example.com)"

Next run (incremental)
python main.py --user alice --limit 50 ^
  --since-file state/alice_since.txt ^
  --fields id,date_filed,absolute_url ^
  --token YOUR_TOKEN ^
  --ua "CourtListenerDemo/1.0 (Your Name; you@example.com)"


The script automatically updates state/alice_since.txt with the newest date.

🔄 Retry + Backoff

The client automatically handles:

Timeouts

Slow server responses

Temporary network interruption

Retry sequence example:

Attempt 1 → fail → sleep 1.5s
Attempt 2 → fail → sleep 3s
Attempt 3 → succeed

📁 Output Format

The output is JSONL (one JSON object per line):

Example:

{
  "id": 11210457,
  "date_filed": "2025-11-29",
  "absolute_url": "/opinion/10743872/example-case/",
  "page_count": 10,
  "resource_uri": "https://www.courtlistener.com/api/rest/v3/opinions/11210457/"
}


This format is perfect for:

ML ingestion

Data pipelines

Spark / Pandas / DuckDB

Easy incremental updates

🧪 Preview Saved Data

Show first 3 records:

Get-Content data/alice_opinions.jsonl -TotalCount 3


Pretty-print first record:

python -c "import json;print(json.dumps(json.loads(open('data/alice_opinions.jsonl').read().splitlines()[0]),indent=2))"

🛡 Security
IMPORTANT:

Never expose your API token in GitHub, screenshots, or commits.

If a token is ever leaked:

Go to profile → API Token → Revoke

Generate a new one

The project does not store tokens anywhere except environment variables or CLI arguments.

🔺 Troubleshooting
1. 401 Unauthorized

Fix:

Ensure token is correct

Ensure User-Agent includes real name + email

Do not use generic UA like "python-requests"

2. ReadTimeout

The script retries automatically.
You can increase timeout:

--timeout 90

3. VS Code shows “Import requests unresolved”

Select the correct virtual environment:

Ctrl+Shift+P → Python: Select Interpreter → choose venv
