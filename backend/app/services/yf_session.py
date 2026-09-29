"""Shared yfinance HTTP session that impersonates a real Chrome browser.

Yahoo Finance blocks the plain `requests` sessions that yfinance uses by
default -- every call comes back with an empty body, which yfinance then
fails to parse as JSON (`Expecting value: line 1 column 1 (char 0)`) and
reports as "possibly delisted". Routing calls through a `curl_cffi` session
with Chrome TLS/HTTP fingerprint impersonation avoids that block.
"""
from __future__ import annotations

from curl_cffi import requests as curl_requests

_session: curl_requests.Session | None = None


def get_yf_session() -> curl_requests.Session:
    """Module-level singleton session, reused across all yfinance calls."""
    global _session
    if _session is None:
        _session = curl_requests.Session(impersonate="chrome")
    return _session
