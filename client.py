# client.py
import os
import time
import requests
from typing import Iterator, Dict, Any, Optional

BASE_URL = "https://www.courtlistener.com/api/rest/v3"

# Config via environment variables (optional)
MAX_RETRIES = int(os.getenv("COURTLISTENER_MAX_RETRIES", "6"))
REQUEST_TIMEOUT = float(os.getenv("COURTLISTENER_TIMEOUT", "60"))  # seconds
BACKOFF_FACTOR = float(os.getenv("COURTLISTENER_BACKOFF_FACTOR", "1.5"))

def _get_user_agent() -> str:
    return os.getenv("COURTLISTENER_UA", "CourtListenerDemo/1.0 (please-set-COURTLISTENER_UA-with-your-name-and-email)")

class CourtListenerClient:
    def __init__(self, token: Optional[str] = None, user_agent: Optional[str] = None):
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent or _get_user_agent()})
        token_to_use = token or os.getenv("COURTLISTENER_TOKEN")
        if token_to_use:
            self.session.headers.update({"Authorization": f"Token {token_to_use}"})

    def _get_with_retries(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        attempt = 0
        while True:
            attempt += 1
            try:
                print(f"Requesting (attempt {attempt}): {url} params={params}")
                resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT)
                # Treat certain status codes as transient
                if resp.status_code in (429, 500, 502, 503, 504):
                    print(f"Transient HTTP {resp.status_code} received; will retry if attempts remain.")
                    raise requests.HTTPError(f"HTTP {resp.status_code}", response=resp)
                resp.raise_for_status()
                return resp
            except requests.exceptions.ReadTimeout as e:
                print(f"ReadTimeout on attempt {attempt}/{MAX_RETRIES}: {e}")
            except requests.exceptions.ConnectionError as e:
                print(f"ConnectionError on attempt {attempt}/{MAX_RETRIES}: {e}")
            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status in (429, 500, 502, 503, 504):
                    print(f"Transient HTTP {status} on attempt {attempt}/{MAX_RETRIES}")
                else:
                    print(f"Non-retryable HTTP error {status}; re-raising.")
                    raise
            except requests.RequestException as e:
                print(f"RequestException on attempt {attempt}: {e}")
                raise

            if attempt >= MAX_RETRIES:
                raise requests.exceptions.RetryError(f"Failed after {MAX_RETRIES} attempts to GET {url}")

            sleep_for = BACKOFF_FACTOR * (2 ** (attempt - 1))
            print(f"Sleeping {sleep_for:.1f}s before retry...")
            time.sleep(sleep_for)

    def fetch_paginated(self, endpoint: str, params: Optional[Dict[str, Any]] = None) -> Iterator[Dict[str, Any]]:
        url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        first_request = True
        while url:
            resp = self._get_with_retries(url, params if first_request else None)
            try:
                data = resp.json()
            except Exception:
                text = resp.text[:1000]
                print("Failed to parse JSON response (truncated body):")
                print(text)
                raise
            for item in data.get("results", []):
                yield item
            params = None
            first_request = False
            url = data.get("next")

    def opinions(self, **filters):
        return self.fetch_paginated("/opinions/", filters)
