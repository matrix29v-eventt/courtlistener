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
    return os.getenv(
        "COURTLISTENER_UA",
        "CourtListenerDemo/1.0 (set COURTLISTENER_UA with name/email)"
    )


class CourtListenerClient:
    def __init__(self, token: Optional[str] = None, user_agent: Optional[str] = None):
        self.session = requests.Session()

        # Set User-Agent
        self.session.headers.update({
            "User-Agent": user_agent or _get_user_agent()
        })

        # Set Authorization token
        token_to_use = token or os.getenv("COURTLISTENER_TOKEN")
        if token_to_use:
            self.session.headers.update({
                "Authorization": f"Token {token_to_use}"
            })

    def _get_with_retries(
        self,
        url: str,
        params: Optional[Dict[str, Any]] = None
    ) -> requests.Response:
        attempt = 0

        while True:
            attempt += 1
            try:
                print(f"\nRequesting (attempt {attempt}): {url}")
                print(f"Params: {params}")

                resp = self.session.get(
                    url,
                    params=params,
                    timeout=REQUEST_TIMEOUT
                )

                # ---- DEBUG / VERIFICATION OUTPUT ----
                print("HTTP STATUS:", resp.status_code)

                # Retryable status codes
                if resp.status_code in (429, 500, 502, 503, 504):
                    print(f"Transient HTTP {resp.status_code}; retrying...")
                    raise requests.HTTPError(
                        f"HTTP {resp.status_code}", response=resp
                    )

                resp.raise_for_status()

                # Confirm JSON structure
                data = resp.json()
                print("Response keys:", data.keys())
                print("Records in this page:", len(data.get("results", [])))

                return resp

            except requests.exceptions.ReadTimeout as e:
                print(f"ReadTimeout on attempt {attempt}/{MAX_RETRIES}: {e}")

            except requests.exceptions.ConnectionError as e:
                print(f"ConnectionError on attempt {attempt}/{MAX_RETRIES}: {e}")

            except requests.HTTPError as e:
                status = getattr(e.response, "status_code", None)
                if status in (429, 500, 502, 503, 504):
                    print(f"Retryable HTTP error {status}")
                else:
                    print(f"Non-retryable HTTP error {status}; aborting.")
                    raise

            except requests.RequestException as e:
                print(f"RequestException: {e}")
                raise

            if attempt >= MAX_RETRIES:
                raise requests.exceptions.RetryError(
                    f"Failed after {MAX_RETRIES} attempts to GET {url}"
                )

            sleep_for = BACKOFF_FACTOR * (2 ** (attempt - 1))
            print(f"Sleeping {sleep_for:.1f}s before retry...")
            time.sleep(sleep_for)

    def fetch_paginated(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None
    ) -> Iterator[Dict[str, Any]]:

        url = f"{BASE_URL.rstrip('/')}/{endpoint.lstrip('/')}"
        first_request = True

        while url:
            resp = self._get_with_retries(
                url,
                params if first_request else None
            )

            try:
                data = resp.json()
            except Exception:
                print("Failed to parse JSON response:")
                print(resp.text[:1000])
                raise

            for item in data.get("results", []):
                yield item

            first_request = False
            params = None
            url = data.get("next")

    def opinions(self, **filters) -> Iterator[Dict[str, Any]]:
        """
        Fetch court opinions using CourtListener API.
        """
        return self.fetch_paginated("/opinions/", filters)
