"""
SOS Inventory – Fully Programmatic OAuth2 Client
No browser, no manual steps.

Set your credentials in a .env file or as environment variables:
    SOS_USERNAME=your@email.com
    SOS_PASSWORD=yourpassword

Tokens are cached in sos_tokens.json and refreshed automatically.
"""


import asyncio
import httpx
import json
import os
import requests
import time

from bs4 import BeautifulSoup
from typing import Any, Dict
from urllib.parse import urlparse, parse_qs

from app.core.config import settings
from app.logging_config import get_jsonl_logger, build_jsonl_entry


# ── Configuration ──────────────────────────────────────────────────────────────

CLIENT_ID = settings.CLIENT_ID
CLIENT_SECRET = settings.CLIENT_SECRET
REDIRECT_URI = settings.REDIRECT_URI
SOS_USERNAME = settings.SOS_USERNAME
SOS_PASSWORD = settings.SOS_PASSWORD
BASE_URL = settings.BASE_URL
TOKEN_FILE = settings.TOKEN_FILE

MAX_RESULTS = 200
MAX_CONCURRENT_REQUESTS = 1

jsonl_logger = get_jsonl_logger()

# ───────────────────────────────────────────────────────────────────────────────


# ── Token persistence ───────────────────────────────────────────────────────────

def load_tokens() -> dict | None:
    if not os.path.exists(TOKEN_FILE):
        return None

    try:
        with open(TOKEN_FILE) as f:
            content = f.read().strip()

            if not content:
                return None  # empty file

            return json.loads(content)

    except json.JSONDecodeError:
        print("⚠️ Invalid JSON in token file")
        return None


def save_tokens(tokens: dict) -> None:
    tokens["saved_at"] = time.time()
    with open(TOKEN_FILE, "w") as f:
        json.dump(tokens, f, indent=2)


def is_token_expired(tokens: dict) -> bool:
    elapsed = time.time() - tokens.get("saved_at", 0)
    return elapsed >= (tokens.get("expires_in", 0) - 60)


# ── Programmatic OAuth2 authorization ──────────────────────────────────────────

def _get_auth_code() -> str:
    """
    Drives the full OAuth2 authorization_code flow programmatically:
      1. GET the authorize URL  → SOS redirects to its login page
      2. Parse + submit the login form with credentials
      3. After login, SOS may show an OAuth approval page → submit it
      4. Capture the ?code= from the final redirect to REDIRECT_URI
    """
    if not SOS_USERNAME or not SOS_PASSWORD:
        raise ValueError(
            "SOS_USERNAME and SOS_PASSWORD must be set as environment variables "
            "or in a .env file."
        )

    session = requests.Session()
    session.headers.update({"User-Agent": "sos-inventory-client/1.0"})

    authorize_url = (
        f"{BASE_URL}/oauth2/authorize"
        f"?response_type=code"
        f"&client_id={CLIENT_ID}"
        f"&redirect_uri={REDIRECT_URI}"
    )

    # ── Step 1: Hit the authorize endpoint ─────────────────────────────────────
    # SOS will redirect us to their login page (or straight to the code if
    # we already have a session cookie from a previous call).
    resp = session.get(authorize_url, allow_redirects=True)
    resp.raise_for_status()

    # Check if we landed directly on the redirect_uri with a code
    code = _extract_code_from_response(resp)
    if code:
        return code

    # ── Step 2: Submit the login form ──────────────────────────────────────────
    soup = BeautifulSoup(resp.text, "html.parser")
    login_form = soup.find("form")

    if not login_form:
        raise RuntimeError(
            "Could not find a login form on the SOS authorization page. "
            f"Page content:\n{resp.text[:500]}"
        )

    action = login_form.get("action", resp.url)
    if not action.startswith("http"):
        parsed = urlparse(resp.url)
        action = f"{parsed.scheme}://{parsed.netloc}{action}"

    # Collect all hidden fields, then inject credentials
    form_data = {}
    for inp in login_form.find_all("input"):
        name = inp.get("name")
        value = inp.get("value", "")
        if name:
            form_data[name] = value

    # Detect field names dynamically (handle username / email / user variations)
    username_field = _detect_field(
        form_data, ["username", "email", "user", "login"])
    password_field = _detect_field(form_data, ["password", "pass", "pwd"])

    if not username_field or not password_field:
        raise RuntimeError(
            f"Could not detect username/password fields in form. "
            f"Found fields: {list(form_data.keys())}"
        )

    form_data[username_field] = SOS_USERNAME
    form_data[password_field] = SOS_PASSWORD

    resp = session.post(action, data=form_data, allow_redirects=True)
    resp.raise_for_status()

    code = _extract_code_from_response(resp)
    if code:
        return code

    # ── Step 3: OAuth approval page (if SOS shows one) ─────────────────────────
    soup = BeautifulSoup(resp.text, "html.parser")
    approve_form = soup.find("form")

    if approve_form:
        action = approve_form.get("action", resp.url)
        if not action.startswith("http"):
            parsed = urlparse(resp.url)
            action = f"{parsed.scheme}://{parsed.netloc}{action}"

        form_data = {}
        for inp in approve_form.find_all("input"):
            name = inp.get("name")
            value = inp.get("value", "")
            if name:
                form_data[name] = value

        # Look for an approve/allow/authorize submit button and include it
        for btn in approve_form.find_all(["input", "button"]):
            if btn.get("type", "").lower() == "submit":
                btn_name = btn.get("name")
                btn_value = btn.get("value", "approve")
                if btn_name:
                    form_data[btn_name] = btn_value
                break

        resp = session.post(action, data=form_data, allow_redirects=False)

        code = _extract_code_from_response(resp)
        if code:
            return code

        # Follow one more redirect manually to catch the Location header
        if resp.status_code in (301, 302, 303, 307, 308):
            location = resp.headers.get("Location", "")
            code = _code_from_url(location)
            if code:
                return code

    raise RuntimeError(
        "Failed to extract the authorization code from any step of the flow. "
        "SOS may have changed their login page structure."
    )


def _extract_code_from_response(resp: requests.Response) -> str | None:
    """Check both the final URL and any Location header for ?code=."""
    code = _code_from_url(resp.url)
    if code:
        return code
    location = resp.headers.get("Location", "")
    return _code_from_url(location)


def _code_from_url(url: str) -> str | None:
    if not url:
        return None
    qs = parse_qs(urlparse(url).query)
    codes = qs.get("code", [])
    return codes[0] if codes else None


def _detect_field(form_data: dict, candidates: list[str]) -> str | None:
    """Return the first form field name that matches any candidate substring."""
    for key in form_data:
        for candidate in candidates:
            if candidate.lower() in key.lower():
                return key
    return None


# ── Token exchange & refresh ────────────────────────────────────────────────────

def _fetch_token(auth_code: str) -> dict:
    resp = requests.post(
        f"{BASE_URL}/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":    "authorization_code",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "code":          auth_code,
            "redirect_uri":  REDIRECT_URI,
        },
    )
    resp.raise_for_status()
    return resp.json()


def _refresh_token(tokens: dict) -> dict:
    resp = requests.post(
        f"{BASE_URL}/oauth2/token",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "grant_type":    "refresh_token",
            "client_id":     CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "refresh_token": tokens["refresh_token"],
        },
    )
    resp.raise_for_status()
    return resp.json()


# ── Public interface ────────────────────────────────────────────────────────────

def get_access_token() -> str:
    """
    Returns a valid access token.
    - Uses cached token if still valid.
    - Refreshes if expired.
    - Performs full programmatic login if no token exists.
    """
    tokens = load_tokens()

    if tokens is None:
        auth_code = _get_auth_code()
        tokens = _fetch_token(auth_code)
        save_tokens(tokens)

    elif is_token_expired(tokens):
        try:
            tokens = _refresh_token(tokens)
        except requests.HTTPError:
            # Refresh token also expired — redo full login
            auth_code = _get_auth_code()
            tokens = _fetch_token(auth_code)
        save_tokens(tokens)

    return tokens["access_token"]


# def api_get(endpoint: str, params: dict = None) -> dict:
#     """Authenticated GET against the SOS v2 API. e.g. api_get('/api/v2/item')"""
#     token = get_access_token()

#     resp = requests.get(
#         f"{BASE_URL}{endpoint}",
#         headers={"Authorization": f"Bearer {token}"},
#         params=params,
#     )
#     resp.raise_for_status()
#     return resp.json()


async def fetch_page(
    client: httpx.AsyncClient,
    endpoint: str,
    token: str,
    params: Dict[str, Any],
    start: int,
    maxresults: int,
):
    response = await client.get(
        f"{BASE_URL}{endpoint}",
        headers={"Authorization": f"Bearer {token}"},
        params={
            **params,
            "start": start,
            "maxresults": maxresults,
        },
    )

    # Helpful for debugging throttling
    if response.status_code != 200:
        print(response.text)

    response.raise_for_status()

    return response.json()


async def api_get(
    endpoint: str,
    params: Dict[str, Any] | None = None,
):
    """
    Fetch all paginated data from SOS API
    with limited concurrency to avoid throttling.
    """

    if params is None:
        params = {}  # default to non-archived items, adjust as needed

    token = get_access_token()

    try:

        async with httpx.AsyncClient(timeout=300.0) as client:

            # First request
            first_page = await fetch_page(
                client=client,
                endpoint=endpoint,
                token=token,
                params=params,
                start=0,
                maxresults=MAX_RESULTS,
            )

            items = first_page.get("data", []) or []
            total_count = first_page.get("totalCount", 0)

            # Remaining offsets
            starts = range(MAX_RESULTS, total_count, MAX_RESULTS)

            semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

            async def limited_fetch(start: int):
                async with semaphore:

                    # Tiny delay helps avoid SOS throttling
                    # await asyncio.sleep(0.6)

                    return await fetch_page(
                        client=client,
                        endpoint=endpoint,
                        token=token,
                        params=params,
                        start=start+1,
                        maxresults=MAX_RESULTS,
                    )

            tasks = [
                limited_fetch(start)
                for start in starts
            ]

            if tasks:
                results = await asyncio.gather(*tasks)

                for result in results:
                    # print(result)
                    items.extend(result.get("data", []) or [])

            item_map = {
                "item": "product",
                "vendor": "supplier",
                "customer": "customer",
                "location": "location",
                "salesorder": "sales order",
                "purchaseorder": "purchase order",
            }
            item_type = item_map.get(endpoint.split("/")[-1])
            jsonl_logger.info(
                build_jsonl_entry(
                    action_type=f"Fetch {item_type}s from SOS Inventory",
                    action_variant=f"fetch-{item_type}s-from-sos-inventory",
                    status="Info",
                    message=f"Fetched {len(items)} {item_type}s from SOS Inventory",
                )
            )
            return {"data": items}
    except Exception as e:
        jsonl_logger.error(
            build_jsonl_entry(
                action_type=f"Fetch {item_type}s from SOS Inventory",
                action_variant=f"fetch-{item_type}s-from-sos-inventory",
                status="Error",
                message=f"Failed to fetch {item_type}s from SOS Inventory: {str(e)}",
            )
        )


def api_post(endpoint: str, payload: dict = None) -> dict:
    """Authenticated POST against the SOS v2 API."""
    token = get_access_token()
    resp = requests.post(
        f"{BASE_URL}{endpoint}",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type":  "application/json",
        },
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


# data = api_get("/api/v2/item")
# print(json.dumps(data, indent=2))
