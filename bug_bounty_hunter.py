"""
Bug Bounty Hunter — Multi-platform bug bounty integration for the Ultimate AI Agent.
Supports: HackerOne, Bugcrowd, Intigriti

Features:
  • Browse & search public programs on all 3 platforms (no API key needed)
  • Fetch in-scope assets for any program
  • Passive recon — subdomain enum (crt.sh), security header audit, tech fingerprinting
  • Active vulnerability scan — XSS, SQLi, open redirect, CORS, path traversal, secrets exposure
  • Finding tracker — save, categorize, and list findings
  • PoC report generator — formatted Markdown ready to paste
  • Report submission via HackerOne REST API (needs H1_API_TOKEN)
"""

import os
import re
import json
import logging
import hashlib
from typing import Dict, List, Optional, Any
from datetime import datetime
from urllib.parse import urlparse, urljoin, urlencode

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

try:
    from curl_cffi import requests as curl_requests
    CURL_CFFI_OK = True
except ImportError:
    CURL_CFFI_OK = False

logger = logging.getLogger("BugBountyHunter")

# ── Constants ─────────────────────────────────────────────────────────────────

SEVERITY_LEVELS = ["critical", "high", "medium", "low", "informational"]

PLATFORMS = {
    "hackerone": {
        "name": "HackerOne",
        "url": "https://hackerone.com",
        "icon": "🔴",
        "programs_url": "https://hackerone.com/programs",
        "api_base": "https://api.hackerone.com/v1",
    },
    "bugcrowd": {
        "name": "Bugcrowd",
        "url": "https://bugcrowd.com",
        "icon": "🟠",
        "programs_url": "https://bugcrowd.com/programs",
        "api_base": "https://bugcrowd.com",
    },
    "intigriti": {
        "name": "Intigriti",
        "url": "https://app.intigriti.com",
        "icon": "🟡",
        "programs_url": "https://app.intigriti.com/researcher/programs",
        "api_base": "https://app.intigriti.com/api/core/public",
    },
    "yeswehack": {
        "name": "YesWeHack",
        "url": "https://yeswehack.com",
        "icon": "🟢",
        "programs_url": "https://yeswehack.com/programs",
        "api_base": "https://api.yeswehack.com",
    },
    "immunefi": {
        "name": "Immunefi",
        "url": "https://immunefi.com",
        "icon": "💜",
        "programs_url": "https://immunefi.com/explore/",
        "api_base": "https://immunefi.com/v2",
        "note": "Web3/Crypto — bounties up to $10M",
    },
    "synack": {
        "name": "Synack Red Team",
        "url": "https://www.synack.com/red-team",
        "icon": "🔵",
        "programs_url": "https://www.synack.com/red-team",
        "api_base": None,
        "note": "Invite-only program — apply at synack.com/red-team",
    },
    "openbugbounty": {
        "name": "Open Bug Bounty",
        "url": "https://www.openbugbounty.org",
        "icon": "⚪",
        "programs_url": "https://www.openbugbounty.org/programs/",
        "api_base": "https://www.openbugbounty.org/api/1",
    },
}

# Default browser-like headers to bypass basic WAFs (Cloudflare)
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "none",
    "Sec-Fetch-User": "?1",
    "X-Bug-Bounty": "yuvaraj030_agent",
    "X-Test-Account-Email": "test_yuvaraj030@example.com"
}

# ── Security header checks ────────────────────────────────────────────────────

SECURITY_HEADERS = {
    "Strict-Transport-Security": ("MISSING HSTS", "HIGH"),
    "X-Frame-Options": ("Clickjacking risk (no X-Frame-Options)", "MEDIUM"),
    "X-Content-Type-Options": ("MIME sniffing risk (no X-Content-Type-Options)", "LOW"),
    "Content-Security-Policy": ("No CSP — XSS risk", "MEDIUM"),
    "X-XSS-Protection": ("No X-XSS-Protection header", "LOW"),
    "Referrer-Policy": ("No Referrer-Policy", "LOW"),
    "Permissions-Policy": ("No Permissions-Policy", "LOW"),
}

# ── XSS / SQLi / Traversal payloads ──────────────────────────────────────────

XSS_PAYLOADS = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "javascript:alert(1)",
    "'><svg/onload=alert(1)>",
]

SQLI_PAYLOADS = [
    "'",
    "1' OR '1'='1",
    '" OR "1"="1',
    "1; DROP TABLE users--",
    "1 UNION SELECT NULL--",
]

OPEN_REDIRECT_PAYLOADS = [
    "https://evil.com",
    "//evil.com",
    "\\\\evil.com",
    "/\\evil.com",
    "https://evil.com%00.example.com",
]

SQLI_ERROR_PATTERNS = [
    "SQL syntax", "mysql_fetch", "ORA-", "SQLite",
    "Warning: mysql", "Unclosed quotation mark",
    "syntax error", "pg_query", "SQLSTATE",
]


# Global rate limiter state (1 req/sec per domain by default)
import time as _time_mod
_RATE_LIMIT_DELAY: float = 0.0   # Fast scanning for this task
_RATE_LIMIT_ENABLED: bool = False

def _get(url: str, timeout: int = 10, headers: Dict = None, allow_redirects: bool = True,
         _delay: bool = True) -> Optional[Any]:
    """Safe GET wrapper. Uses curl_cffi (Chrome TLS) if available, falls back to requests.
    Includes configurable rate limiting to avoid WAF bans."""
    h = {**DEFAULT_HEADERS, **(headers or {})}
    if _RATE_LIMIT_ENABLED and _delay:
        _time_mod.sleep(_RATE_LIMIT_DELAY)
    try:
        if CURL_CFFI_OK:
            return curl_requests.get(url, headers=h, timeout=timeout,
                                     allow_redirects=allow_redirects,
                                     impersonate="chrome110")
        elif REQUESTS_OK:
            return requests.get(url, headers=h, timeout=timeout, allow_redirects=allow_redirects)
        return None
    except Exception as e:
        logger.debug(f"GET {url}: {e}")
        return None


def _post(url: str, json_data: Dict = None, data: Dict = None,
          headers: Dict = None, timeout: int = 15) -> Optional[Any]:
    """Safe POST wrapper. Uses curl_cffi (Chrome TLS) if available, falls back to requests."""
    h = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        if CURL_CFFI_OK:
            return curl_requests.post(url, json=json_data, data=data, headers=h,
                                      timeout=timeout, impersonate="chrome110")
        elif REQUESTS_OK:
            return requests.post(url, json=json_data, data=data, headers=h, timeout=timeout)
        return None
    except Exception as e:
        logger.debug(f"POST {url}: {e}")
        return None


# ── Platform scope fetchers ───────────────────────────────────────────────────

def _fetch_h1_scope(handle: str) -> Dict:
    """Fetch HackerOne program scope via GraphQL."""
    url = "https://hackerone.com/graphql"
    payload = {
        "query": """
        query Team_assets($handle: String!) {
          team(handle: $handle) {
            name
            url
            submission_state
            offers_bounties
            in_scope_assets: structured_scopes(
              first: 100
              archived: false
              eligible_for_submission: true
            ) {
              edges {
                node {
                  asset_identifier
                  asset_type
                  eligible_for_bounty
                  instruction
                }
              }
            }
            out_of_scope_assets: structured_scopes(
              first: 50
              archived: false
              eligible_for_submission: false
            ) {
              edges {
                node {
                  asset_identifier
                  asset_type
                }
              }
            }
          }
        }
        """,
        "variables": {"handle": handle},
    }
    resp = _post(url, json_data=payload, headers={"Content-Type": "application/json"})
    if not resp or resp.status_code != 200:
        return {"error": f"HTTP {getattr(resp,'status_code','timeout')}"}
    data = resp.json().get("data", {})
    team = data.get("team")
    if not team:
        return {"error": f"Program '{handle}' not found or not public"}
    return {
        "platform": "hackerone",
        "handle": handle,
        "name": team.get("name", handle),
        "offers_bounties": team.get("offers_bounties", False),
        "submission_state": team.get("submission_state", "?"),
        "in_scope": [
            {
                "identifier": e["node"]["asset_identifier"],
                "type": e["node"]["asset_type"],
                "bounty": e["node"].get("eligible_for_bounty", False),
                "instruction": (e["node"].get("instruction") or "")[:200],
            }
            for e in (team.get("in_scope_assets", {}).get("edges") or [])
        ],
        "out_of_scope": [
            {
                "identifier": e["node"]["asset_identifier"],
                "type": e["node"]["asset_type"],
            }
            for e in (team.get("out_of_scope_assets", {}).get("edges") or [])
        ],
    }


def _fetch_bugcrowd_programs(query: str = "") -> List[Dict]:
    """Fetch Bugcrowd public programs list."""
    url = "https://bugcrowd.com/programs.json"
    resp = _get(url)
    if not resp or resp.status_code != 200:
        return []
    try:
        programs = resp.json()
        if query:
            q = query.lower()
            programs = [p for p in programs if q in (p.get("name") or "").lower()
                        or q in (p.get("tagline") or "").lower()]
        return programs[:30]
    except Exception:
        return []


def _fetch_intigriti_programs(query: str = "") -> List[Dict]:
    """Fetch Intigriti public programs."""
    url = "https://app.intigriti.com/api/core/public/programs"
    resp = _get(url)
    if not resp or resp.status_code != 200:
        resp = _get("https://app.intigriti.com/api/core/public/program")
    if not resp or resp.status_code != 200:
        return []
    try:
        data = resp.json()
        programs = data if isinstance(data, list) else data.get("programs", data.get("data", []))
        if query:
            q = query.lower()
            programs = [p for p in programs
                        if q in str(p.get("name", p.get("companyHandle", ""))).lower()]
        return programs[:30]
    except Exception:
        return []


# Curated list of popular HackerOne bug bounty programs (offline fallback)
_H1_POPULAR_PROGRAMS = [
    {"handle": "security", "name": "HackerOne", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 25000},
    {"handle": "google_bughunters", "name": "Google Bug Hunters", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 31337},
    {"handle": "microsoft", "name": "Microsoft", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 100000},
    {"handle": "github", "name": "GitHub", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 30000},
    {"handle": "gitlab", "name": "GitLab", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 35000},
    {"handle": "shopify", "name": "Shopify", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 50000},
    {"handle": "dropbox", "name": "Dropbox", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 32768},
    {"handle": "paypal", "name": "PayPal", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 30000},
    {"handle": "twitter", "name": "Twitter (X)", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 15000},
    {"handle": "coinbase", "name": "Coinbase", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 50000},
    {"handle": "uber", "name": "Uber", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 15000},
    {"handle": "yahoo", "name": "Yahoo", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 15000},
    {"handle": "automattic", "name": "Automattic (WordPress)", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 25000},
    {"handle": "cloudflare", "name": "Cloudflare", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 3000},
    {"handle": "slack", "name": "Slack", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 15000},
    {"handle": "snapchat", "name": "Snapchat", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 15000},
    {"handle": "nodejs-ecosystem", "name": "Node.js Ecosystem", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 2500},
    {"handle": "ruby", "name": "Ruby", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 5000},
    {"handle": "hyatt", "name": "Hyatt", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 4000},
    {"handle": "basecamp", "name": "Basecamp", "offers_bounties": True, "submission_state": "open", "maximum_bounty_table_value": 5000},
]


def _fetch_h1_programs_graphql(query: str = "") -> List[Dict]:
    """Attempt to fetch HackerOne programs via GraphQL (may require auth)."""
    url = "https://hackerone.com/graphql"
    payload = {
        "query": """
        query DirectoryQuery($query: String, $first: Int) {
          teams(
            first: $first
            secure_or_public: true
            product_type: "bug-bounty"
            query: $query
            order_by: { field: name, direction: ASC }
          ) {
            edges {
              node {
                handle
                name
                url
                offers_bounties
                state
                submission_state
                currency
                minimum_bounty_table_value
                maximum_bounty_table_value
              }
            }
          }
        }
        """,
        "variables": {"query": query or "", "first": 25},
    }
    resp = _post(url, json_data=payload, headers={"Content-Type": "application/json"})
    if not resp or resp.status_code != 200:
        return []
    try:
        edges = resp.json().get("data", {}).get("teams", {}).get("edges", [])
        return [e["node"] for e in edges]
    except Exception:
        return []


def _fetch_h1_programs_rest(query: str = "") -> List[Dict]:
    """Fetch HackerOne programs via REST API (requires H1_API_TOKEN)."""
    api_token = os.environ.get("H1_API_TOKEN", "")
    h1_username = os.environ.get("H1_USERNAME", "")
    if not api_token or not h1_username:
        return []
    url = "https://api.hackerone.com/v1/hackers/programs"
    try:
        resp = requests.get(
            url,
            auth=(h1_username, api_token),
            params={"page[size]": 25},
            headers={"Accept": "application/json"},
            timeout=15,
        )
        if resp.status_code != 200:
            return []
        data = resp.json().get("data", [])
        programs = []
        for item in data:
            attrs = item.get("attributes", {})
            handle = attrs.get("handle", "")
            if query and query.lower() not in handle.lower() and query.lower() not in attrs.get("name", "").lower():
                continue
            programs.append({
                "handle": handle,
                "name": attrs.get("name", handle),
                "offers_bounties": attrs.get("offers_bounties", False),
                "submission_state": attrs.get("submission_state", "?"),
                "maximum_bounty_table_value": None,
            })
        return programs
    except Exception as e:
        logger.debug(f"H1 REST API failed: {e}")
        return []


def _fetch_h1_programs(query: str = "") -> List[Dict]:
    """Fetch HackerOne programs with 3-tier fallback: GraphQL → REST API → curated list."""
    programs = _fetch_h1_programs_graphql(query)
    if programs:
        return programs
    programs = _fetch_h1_programs_rest(query)
    if programs:
        return programs
    logger.info("Using curated HackerOne programs list (GraphQL/REST auth required for live data)")
    result = _H1_POPULAR_PROGRAMS[:]
    if query:
        q = query.lower()
        result = [p for p in result if q in p["handle"].lower() or q in p["name"].lower()]
    return result


# ── Passive recon engine ──────────────────────────────────────────────────────

def _recon_crtsh(domain: str) -> List[str]:
    """Query crt.sh for certificate-based subdomain enumeration."""
    url = f"https://crt.sh/?q=%.{domain}&output=json"
    resp = _get(url, timeout=20)
    if not resp or resp.status_code != 200:
        return []
    try:
        data = resp.json()
        subs = set()
        for entry in data:
            name_val = entry.get("name_value", "")
            for line in name_val.splitlines():
                line = line.strip().lstrip("*.")
                if line.endswith(domain) and line != domain:
                    subs.add(line.lower())
        return sorted(subs)[:50]
    except Exception:
        return []


def _audit_headers(resp) -> List[Dict]:
    """Audit HTTP response headers for security issues."""
    findings = []
    headers_lower = {k.lower(): v for k, v in resp.headers.items()}
    for header, (message, severity) in SECURITY_HEADERS.items():
        if header.lower() not in headers_lower:
            findings.append({
                "type": "missing_header",
                "header": header,
                "message": message,
                "severity": severity,
            })
    hsts = headers_lower.get("strict-transport-security", "")
    if hsts:
        age_match = re.search(r"max-age=(\d+)", hsts)
        age = int(age_match.group(1)) if age_match else 0
        if age < 31536000:
            findings.append({
                "type": "weak_hsts",
                "header": "Strict-Transport-Security",
                "message": f"HSTS max-age too short ({age}s, should be ≥31536000)",
                "severity": "MEDIUM",
            })
    server = headers_lower.get("server", "")
    x_powered = headers_lower.get("x-powered-by", "")
    if server:
        findings.append({
            "type": "info_leak",
            "header": "Server",
            "message": f"Server version disclosed: {server}",
            "severity": "LOW",
        })
    if x_powered:
        findings.append({
            "type": "info_leak",
            "header": "X-Powered-By",
            "message": f"Tech stack disclosed: {x_powered}",
            "severity": "LOW",
        })
    return findings


def _check_cors(url: str) -> Optional[Dict]:
    """Check for CORS misconfiguration."""
    resp = _get(url, headers={"Origin": "https://evil.com"})
    if not resp:
        return None
    acao = resp.headers.get("Access-Control-Allow-Origin", "")
    acac = resp.headers.get("Access-Control-Allow-Credentials", "false").lower()
    if acao == "https://evil.com" or (acao == "*" and acac == "true"):
        return {
            "type": "cors_misconfiguration",
            "message": f"CORS reflects arbitrary Origin ({acao}) with credentials={acac}",
            "severity": "HIGH",
            "url": url,
        }
    if acao == "*":
        return {
            "type": "cors_wildcard",
            "message": "CORS allows all origins (*)",
            "severity": "MEDIUM",
            "url": url,
        }
    return None


# ── Sensitive file scanner (with false positive reduction) ────────────────────

# Sensitive paths with content validation signatures to reduce false positives.
# Each entry: (path, severity, content_signatures, content_type_hint, max_expected_size)
#   - content_signatures: list of strings; at least one must appear in body for a true positive
#   - content_type_hint: expected Content-Type substring (None = any)
#   - max_expected_size: if response is larger than this, likely a full HTML page (soft 404)
SENSITIVE_PATHS_V2 = [
    ("/.git/HEAD",       "CRITICAL", ["ref: refs/", "ref:refs/"],
     None, 1000),
    ("/.env",            "CRITICAL", ["=", "DB_", "APP_", "SECRET", "KEY",
                                      "PASSWORD", "DATABASE", "MAIL_", "AWS_"],
     None, 10000),
    ("/wp-config.php",   "CRITICAL", ["DB_NAME", "DB_USER", "DB_PASSWORD",
                                      "table_prefix", "wp-settings.php"],
     None, 15000),
    ("/config.php",      "HIGH",     ["<?php", "password", "db_host", "database",
                                      "config[", "define("],
     None, 15000),
    ("/phpinfo.php",     "HIGH",     ["phpinfo()", "PHP Version", "php.ini",
                                      "Configuration File"],
     "text/html", 500000),
    ("/.DS_Store",       "HIGH",     [b"\x00\x00\x00\x01Bud1"],   # binary magic bytes
     None, 100000),
    ("/backup.zip",      "HIGH",     [b"PK\x03\x04"],             # ZIP magic bytes
     None, None),
    ("/server-status",   "HIGH",     ["Apache Server Status", "Server Version:",
                                      "Current Time:", "Restart Time:"],
     "text/html", None),
    ("/.well-known/security.txt", "LOW", ["Contact:", "Expires:",
                                           "Policy:", "Acknowledgments:"],
     "text/plain", 5000),
]

# Paths that are useful to check but don't have reliable signatures
# (only reported if they look genuinely different from baseline)
SENSITIVE_PATHS_HEURISTIC = [
    ("/admin",           "MEDIUM"),
    ("/api/v1/users",    "MEDIUM"),
]


def _body_fingerprint(content: bytes, max_len: int = 2000) -> str:
    """Create a simple fingerprint of response body for comparison."""
    return hashlib.md5(content[:max_len]).hexdigest()


def _check_sensitive_files(base_url: str) -> List[Dict]:
    """Check for exposed sensitive files with soft-404 detection and content validation."""
    findings = []
    base = base_url.rstrip("/")

    # ── Step 1: Get a soft-404 baseline ──────────────────────────────────
    # Fetch a path that should never exist to capture the site's 404 behavior
    baseline_url = f"{base}/bb_probe_nonexistent_8f3a2b1c.html"
    baseline_resp = _get(baseline_url, timeout=8, allow_redirects=False)

    baseline_status = getattr(baseline_resp, "status_code", 0) if baseline_resp else 0
    baseline_fp = ""
    baseline_size = 0
    if baseline_resp and baseline_status == 200:
        baseline_fp = _body_fingerprint(baseline_resp.content)
        baseline_size = len(baseline_resp.content)
        logger.info(f"Soft-404 detected: {base} returns 200 for nonexistent paths "
                    f"(size={baseline_size})")

    # ── Step 2: Check paths with content signatures ─────────────────────
    for entry in SENSITIVE_PATHS_V2:
        path, sev, signatures, ct_hint, max_size = entry
        url = base + path
        resp = _get(url, timeout=8, allow_redirects=False)
        if not resp:
            continue

        if resp.status_code == 200 and len(resp.content) > 10:
            body = resp.content
            body_text = ""
            try:
                body_text = body.decode("utf-8", errors="replace")
            except Exception:
                pass

            # Skip if response matches the soft-404 baseline
            if baseline_fp and _body_fingerprint(body) == baseline_fp:
                logger.debug(f"Skipping {path} — matches soft-404 baseline")
                continue

            # Skip if response size is suspiciously close to baseline (within 5%)
            if baseline_size > 100 and abs(len(body) - baseline_size) < baseline_size * 0.05:
                logger.debug(f"Skipping {path} — size similar to soft-404 baseline")
                continue

            # Check content-type hint if specified
            if ct_hint:
                actual_ct = resp.headers.get("Content-Type", "").lower()
                if ct_hint.lower() not in actual_ct:
                    continue

            # Check max expected size (if response is way too large, it's probably a page)
            if max_size and len(body) > max_size:
                continue

            # Validate against content signatures
            matched = False
            for sig in signatures:
                if isinstance(sig, bytes):
                    if sig in body:
                        matched = True
                        break
                elif isinstance(sig, str):
                    if sig.lower() in body_text.lower():
                        matched = True
                        break

            if matched:
                # Additional confidence: check that it's NOT an HTML error page
                is_html_page = ("<html" in body_text.lower()[:500]
                                and "</html>" in body_text.lower()[-500:])
                # Allow HTML for phpinfo and server-status (they ARE html)
                if is_html_page and path not in ["/phpinfo.php", "/server-status"]:
                    # For files like .env, .git/HEAD — they should NOT be full HTML
                    if len(body) > 5000:
                        logger.debug(f"Skipping {path} — looks like HTML page, not a raw file")
                        continue

                findings.append({
                    "type": "sensitive_file",
                    "url": url,
                    "status_code": resp.status_code,
                    "size": len(body),
                    "message": f"Sensitive file exposed: {path}",
                    "severity": sev,
                    "verified": True,
                })

        elif resp.status_code in [301, 302]:
            location = resp.headers.get("Location", "")
            if "login" not in location.lower():
                findings.append({
                    "type": "redirect_target",
                    "url": url,
                    "status_code": resp.status_code,
                    "location": location,
                    "message": f"Path {path} redirects to {location}",
                    "severity": "LOW",
                })

    # ── Step 3: Heuristic paths (compare against baseline) ──────────────
    for path, sev in SENSITIVE_PATHS_HEURISTIC:
        url = base + path
        resp = _get(url, timeout=8, allow_redirects=False)
        if not resp or resp.status_code != 200 or len(resp.content) < 50:
            continue
        # Only flag if response is clearly different from soft-404
        if baseline_fp and _body_fingerprint(resp.content) == baseline_fp:
            continue
        if baseline_size > 100 and abs(len(resp.content) - baseline_size) < baseline_size * 0.05:
            continue
        # Extra: if it returns JSON, it's more interesting
        ct = resp.headers.get("Content-Type", "").lower()
        if "json" in ct or "api" in path:
            findings.append({
                "type": "sensitive_endpoint",
                "url": url,
                "status_code": resp.status_code,
                "size": len(resp.content),
                "message": f"Interesting endpoint accessible: {path}",
                "severity": sev,
            })

    return findings


def _probe_xss(base_url: str, param: str = "q") -> List[Dict]:
    """Basic reflected XSS probe."""
    findings = []
    for payload in XSS_PAYLOADS[:2]:  # Keep it quick
        encoded = urlencode({param: payload})
        url = f"{base_url}?{encoded}"
        resp = _get(url, timeout=8)
        if resp and payload in (resp.text or ""):
            findings.append({
                "type": "xss_reflected",
                "url": url,
                "parameter": param,
                "payload": payload,
                "message": f"Reflected XSS via parameter '{param}'",
                "severity": "HIGH",
            })
    return findings


def _probe_sqli(base_url: str, param: str = "id") -> List[Dict]:
    """Basic SQLi error-based probe."""
    findings = []
    for payload in SQLI_PAYLOADS[:3]:
        encoded = urlencode({param: payload})
        url = f"{base_url}?{encoded}"
        resp = _get(url, timeout=8)
        if resp:
            body = resp.text or ""
            for err in SQLI_ERROR_PATTERNS:
                if err.lower() in body.lower():
                    findings.append({
                        "type": "sql_injection",
                        "url": url,
                        "parameter": param,
                        "payload": payload,
                        "error_pattern": err,
                        "message": f"Possible SQL Injection via '{param}' (error: {err})",
                        "severity": "CRITICAL",
                    })
                    break
    return findings


def _probe_open_redirect(base_url: str, param: str = "redirect") -> List[Dict]:
    """Check for open redirect vulnerability."""
    findings = []
    for payload in OPEN_REDIRECT_PAYLOADS[:3]:
        encoded = urlencode({param: payload})
        url = f"{base_url}?{encoded}"
        resp = _get(url, timeout=8, allow_redirects=False)
        if resp and resp.status_code in [301, 302, 303, 307, 308]:
            location = resp.headers.get("Location", "")
            if "evil.com" in location:
                findings.append({
                    "type": "open_redirect",
                    "url": url,
                    "parameter": param,
                    "location": location,
                    "message": f"Open Redirect via '{param}' → {location}",
                    "severity": "MEDIUM",
                })
    return findings


# ── Report submission (HackerOne REST API) ────────────────────────────────────

def _submit_h1_report(api_token: str, h1_username: str, program_handle: str,
                      title: str, description: str, severity: str = "medium",
                      impact: str = "") -> Dict:
    """Submit a vulnerability report to HackerOne via REST API."""
    url = "https://api.hackerone.com/v1/hackers/reports"
    sev_map = {
        "critical": "critical", "high": "high",
        "medium": "medium", "low": "low", "info": "none",
    }
    payload = {
        "data": {
            "type": "report",
            "attributes": {
                "team_handle": program_handle,
                "title": title,
                "vulnerability_information": description,
                "impact": impact or f"Security impact: {severity.upper()} severity finding",
                "structured_scope_attributes": None,
            },
            "relationships": {
                "severity": {
                    "data": {
                        "type": "severity",
                        "attributes": {
                            "rating": sev_map.get(severity.lower(), "medium")
                        }
                    }
                }
            }
        }
    }
    resp = _post(url, json_data=payload,
                 headers={
                     "Authorization": f"Bearer {api_token}",
                     "Content-Type": "application/json",
                     "Accept": "application/json",
                 })
    if not resp:
        return {"error": "Request failed / network error"}
    if resp.status_code in [200, 201]:
        data = resp.json().get("data", {})
        return {
            "success": True,
            "report_id": data.get("id"),
            "url": f"https://hackerone.com/reports/{data.get('id')}",
            "title": title,
        }
    return {"error": f"HTTP {resp.status_code}: {resp.text[:400]}"}


# ── Main class ────────────────────────────────────────────────────────────────

class BugBountyHunter:
    """
    Multi-platform bug bounty hunter.
    Integrates HackerOne, Bugcrowd, Intigriti.
    """

    FINDINGS_FILE = "bug_bounty_findings.json"

    def __init__(self, llm_provider=None):
        self.llm = llm_provider
        self.findings: List[Dict] = []
        self._scope: List[str] = []   # set via set_scope()
        self._load_findings()

    # ── Scope enforcement ─────────────────────────────────────────────────────

    def set_scope(self, domains: List[str]) -> str:
        """
        Define in-scope domains for active scanning.
        Accepts exact hostnames and wildcard prefixes (e.g. '*.example.com').

        Example:
            hunter.set_scope(['example.com', '*.example.com', 'api.example.com'])
        """
        self._scope = [d.lower().strip() for d in domains if d.strip()]
        return (f"  ✅ Scope set: {len(self._scope)} domain(s)\n"
                + "\n".join(f"    • {d}" for d in self._scope))

    def _in_scope(self, url: str) -> bool:
        """Return True if url's hostname is within the defined scope (or no scope set)."""
        if not self._scope:
            return True  # No scope configured → everything is allowed
        try:
            from urllib.parse import urlparse
            host = urlparse(url).hostname or ""
        except Exception:
            host = url.split("/")[0].split(":")[0]
        host = host.lower()
        for entry in self._scope:
            if entry.startswith("*."):
                base = entry[2:]  # strip '*.'  
                if host == base or host.endswith("." + base):
                    return True
            elif host == entry:
                return True
        return False

    # ── Platform helpers ──────────────────────────────────────────────────────

    def list_platforms(self) -> str:
        """Return a formatted table of all supported platforms."""
        lines = [
            "🎯 Supported Bug Bounty Platforms",
            "─" * 55,
        ]
        for key, info in PLATFORMS.items():
            lines.append(f"  {info['icon']}  {info['name']:<14} → {info['url']}")
            lines.append(f"      Programs: {info['programs_url']}")
        lines.append("─" * 55)
        lines.append("  Usage: /bugbounty programs <platform> [search]")
        return "\n".join(lines)

    def list_programs(self, platform: str, query: str = "") -> str:
        """Browse programs on a given platform."""
        platform = platform.lower()
        if platform not in PLATFORMS:
            return f"❌ Unknown platform: {platform}. Use: {', '.join(PLATFORMS)}"

        info = PLATFORMS[platform]
        lines = [f"{info['icon']} {info['name']} Programs" + (f" — '{query}'" if query else "")]

        if platform == "hackerone":
            programs = _fetch_h1_programs(query)
            if not programs:
                return (f"  ⚠️ No HackerOne programs found for '{query}'.\n"
                        f"  💡 Try a broader search or set H1_API_TOKEN + H1_USERNAME env vars for live data.\n"
                        f"  🌐 Browse all: {info['programs_url']}")
            lines.append(f"  Found {len(programs)} program(s)\n")
            for p in programs:
                bounty = "💰" if p.get("offers_bounties") else "✓"
                state = p.get("submission_state", "?")
                max_b = p.get("maximum_bounty_table_value")
                b_str = f" (up to ${max_b:,.0f})" if max_b else ""
                lines.append(f"  {bounty} [{state}] {p.get('handle'):<30} {p.get('name','')}{b_str}")

        elif platform == "bugcrowd":
            programs = _fetch_bugcrowd_programs(query)
            if not programs:
                return f"  ⚠️ Could not fetch Bugcrowd programs. Visit: {info['programs_url']}"
            lines.append(f"  Found {len(programs)} program(s)\n")
            for p in programs:
                name = p.get("name", "?")
                slug = p.get("program_url", p.get("code", ""))
                reward = p.get("max_payout", "")
                b_str = f" (${reward})" if reward else ""
                lines.append(f"  💰 {name:<35} → bugcrowd.com{slug}{b_str}")

        elif platform == "intigriti":
            programs = _fetch_intigriti_programs(query)
            if not programs:
                return f"  ⚠️ Could not fetch Intigriti programs. Visit: {info['programs_url']}"
            lines.append(f"  Found {len(programs)} program(s)\n")
            for p in programs:
                name = p.get("name") or p.get("companyHandle", "?")
                handle = p.get("handle") or p.get("companyHandle", "")
                status = p.get("status", {})
                if isinstance(status, dict):
                    state = status.get("value", "?")
                else:
                    state = str(status)
                lines.append(f"  🟡 [{state}] {name:<35} ({handle})")

        return "\n".join(lines)

    def get_scope(self, platform: str, handle: str) -> str:
        """Fetch in-scope assets for a program."""
        platform = platform.lower()
        if platform == "hackerone":
            data = _fetch_h1_scope(handle)
            if "error" in data:
                return f"  ❌ {data['error']}"
            bounties = "💰 Offers Bounties" if data.get("offers_bounties") else "✓ No Bounty"
            lines = [
                f"🎯 Scope for {data['name']} ({handle}) — {data['submission_state']} — {bounties}",
                f"  Platform: HackerOne | https://hackerone.com/{handle}",
                "",
                f"  IN SCOPE ({len(data['in_scope'])} assets):",
            ]
            for asset in data["in_scope"]:
                b = "💰" if asset["bounty"] else "✓"
                lines.append(f"    {b} [{asset['type']}] {asset['identifier']}")
                if asset.get("instruction"):
                    lines.append(f"        ℹ️  {asset['instruction']}")
            if data.get("out_of_scope"):
                lines.append(f"\n  OUT OF SCOPE ({len(data['out_of_scope'])} assets):")
                for asset in data["out_of_scope"][:10]:
                    lines.append(f"    ✗ [{asset['type']}] {asset['identifier']}")
            return "\n".join(lines)

        elif platform == "bugcrowd":
            url = f"https://bugcrowd.com/{handle}/target_groups.json"
            resp = _get(url, timeout=12)
            if not resp or resp.status_code != 200:
                return f"  ⚠️ Could not fetch Bugcrowd scope for '{handle}'. Visit: https://bugcrowd.com/{handle}"
            try:
                data = resp.json()
                groups = data.get("groups", [])
                lines = [f"🎯 Bugcrowd Scope for: {handle}"]
                for g in groups:
                    name = g.get("name", "Default")
                    targets = g.get("in_scope_targets", [])
                    oos = g.get("out_of_scope_targets", [])
                    lines.append(f"\n  📂 {name} — {len(targets)} in-scope, {len(oos)} OOS")
                    for t in targets[:20]:
                        lines.append(f"    ✓ [{t.get('category','?')}] {t.get('name','?')}")
                return "\n".join(lines)
            except Exception as e:
                return f"  ❌ Parse error: {e}"

        elif platform == "intigriti":
            url = f"https://app.intigriti.com/api/core/public/program/{handle}"
            resp = _get(url, timeout=12)
            if not resp or resp.status_code != 200:
                return f"  ⚠️ Could not fetch Intigriti scope for '{handle}'. Visit: https://app.intigriti.com/researcher/programs/{handle}"
            try:
                data = resp.json()
                domains = data.get("domains", data.get("targets", []))
                lines = [f"🎯 Intigriti Scope for: {data.get('name', handle)}"]
                in_scope = [d for d in domains if d.get("type") != "outofscope"]
                oos = [d for d in domains if d.get("type") == "outofscope"]
                lines.append(f"  IN SCOPE ({len(in_scope)}):")
                for d in in_scope[:20]:
                    lines.append(f"    ✓ {d.get('endpoint', d.get('value', '?'))}")
                if oos:
                    lines.append(f"  OUT OF SCOPE ({len(oos)}):")
                    for d in oos[:10]:
                        lines.append(f"    ✗ {d.get('endpoint', d.get('value', '?'))}")
                return "\n".join(lines)
            except Exception as e:
                return f"  ❌ Parse error: {e}"

        return f"❌ Unknown platform: {platform}"

    # ── Passive recon ─────────────────────────────────────────────────────────

    def passive_recon(self, domain: str) -> str:
        """Perform passive recon on a domain (no active scanning)."""
        import re
        domain = re.sub(r'^https?://', '', domain.strip()).split("/")[0]
        if self._scope and not self._in_scope(f"https://{domain}"):
            return (f"  ⛔ SCOPE VIOLATION: '{domain}' is not in the defined scope.\n"
                    f"  Configured scope: {self._scope}")
        lines = [f"🔍 Passive Recon: {domain}", "─" * 55]

        # 1. Subdomain enum via crt.sh
        lines.append("\n  📜 Subdomain Enumeration (crt.sh):")
        subs = _recon_crtsh(domain)
        if subs:
            for sub in subs[:20]:
                lines.append(f"    • {sub}")
            if len(subs) > 20:
                lines.append(f"    ... and {len(subs) - 20} more")
        else:
            lines.append("    ⚠️  crt.sh returned no results (or rate limited)")

        # 2. Security headers on main domain
        lines.append(f"\n  🛡️  Security Headers: https://{domain}")
        import socket
        try:
            resp = _get(f"https://{domain}", timeout=12)
        except Exception:
            resp = None
        if resp and resp.status_code == 200:
            header_issues = _audit_headers(resp)
            if header_issues:
                for h in header_issues:
                    icon = {"HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(h["severity"], "•")
                    lines.append(f"    {icon} [{h['severity']}] {h['message']}")
            else:
                lines.append("    ✅ All key security headers present")

            # 3. Tech fingerprinting
            lines.append(f"\n  🖥️  Tech Fingerprint:")
            server = resp.headers.get("Server", "")
            powered = resp.headers.get("X-Powered-By", "")
            framework = resp.headers.get("X-Framework", "")
            cf = resp.headers.get("cf-ray", "")
            content_type = resp.headers.get("Content-Type", "")
            if server:
                lines.append(f"    Server      : {server}")
            if powered:
                lines.append(f"    Powered By  : {powered}")
            if framework:
                lines.append(f"    Framework   : {framework}")
            if cf:
                lines.append(f"    CDN         : Cloudflare ✓")
            if "wordpress" in (resp.text or "").lower():
                lines.append(f"    CMS         : WordPress detected")
            if "react" in (resp.text or "").lower()[:5000]:
                lines.append(f"    Frontend    : React likely")
            if "angular" in (resp.text or "").lower()[:5000]:
                lines.append(f"    Frontend    : Angular likely")
            if "next" in (resp.text or "").lower()[:5000] or "__NEXT_DATA__" in (resp.text or ""):
                lines.append(f"    Frontend    : Next.js detected")

            # 4. CORS check
            cors = _check_cors(f"https://{domain}")
            if cors:
                lines.append(f"\n  🌐 CORS Issue:")
                lines.append(f"    🟠 [{cors['severity']}] {cors['message']}")
        elif resp:
            # Got a response but non-200 (WAF block, redirect, etc.)
            status_hints = {
                403: "🔴 403 Forbidden — WAF/auth block",
                429: "🟡 429 Too Many Requests — rate limited",
                503: "🟡 503 Service Unavailable",
                521: "🔴 521 Cloudflare — origin unreachable",
                403: "🔴 403 — blocked by WAF",
                407: "🟡 407 Proxy Authentication Required",
            }
            hint = status_hints.get(resp.status_code, f"HTTP {resp.status_code}")
            lines.append(f"    ⚠️  {hint} — try via VPN or manually in browser")
            # Still try to audit any headers present
            if resp.headers:
                header_issues = _audit_headers(resp)
                for h in header_issues[:3]:
                    icon = {"HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(h["severity"], "•")
                    lines.append(f"    {icon} [{h['severity']}] {h['message']}")
        else:
            lines.append(f"    ❌ Connection timed out / refused for https://{domain}")
            lines.append(f"    💡 Likely cause: geo-restriction or network block (try VPN)")

        # Shodan InternetDB — port / CVE intel (free, no key needed)
        lines.append(f"\n  🔌 Shodan InternetDB:")
        try:
            from bb_engines import ShodanEngine
            shodan = ShodanEngine()
            shodan_result = shodan.lookup(domain)
            lines.append(shodan.format_report(shodan_result))
        except Exception as e:
            lines.append(f"    ⚠️  Shodan lookup error: {e}")

        lines.append("\n─" * 55)
        lines.append("  ➜ Next: /bugbounty scan <url> for active vulnerability scan")
        return "\n".join(lines)

    # ── Active vulnerability scan ─────────────────────────────────────────────

    def active_scan(self, url: str) -> str:
        """Active vulnerability scan on a URL (only use on in-scope targets!)."""
        if not url.startswith("http"):
            url = "https://" + url
        if not self._in_scope(url):
            return (f"  ⛔ SCOPE VIOLATION: '{url}' is not in the defined scope.\n"
                    f"  In-scope: {self._scope or ['(no scope set — allow all)']}.\n"
                    f"  Use /bugbounty scope or hunter.set_scope([...]) first.")
        parsed = urlparse(url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        lines = [
            f"⚔️  Active Scan: {url}",
            "  ⚠️  Only run this on targets you're authorized to test!",
            "─" * 55,
        ]
        all_findings = []

        # 0. Parameter discovery — find hidden params before probing
        lines.append(f"\n  🔎 Parameter Discovery:")
        try:
            from bb_engines import ParameterDiscovery
            pd = ParameterDiscovery()
            pd_result = pd.run(url)
            discovered_params = pd_result.get("params", [])
            discovered_endpoints = pd_result.get("endpoints", [])
            if discovered_params:
                lines.append(f"    Found {len(discovered_params)} hidden param(s): {', '.join(discovered_params[:10])}")
            if discovered_endpoints:
                lines.append(f"    Found {len(discovered_endpoints)} endpoint(s): {', '.join(str(e) for e in discovered_endpoints[:5])}")
            if not discovered_params and not discovered_endpoints:
                lines.append("    ℹ️  No hidden parameters discovered")
            # Merge discovered params with URL params for later probes
            extra_params = list(dict.fromkeys(discovered_params[:5]))
        except Exception as e:
            lines.append(f"    ⚠️  Param discovery error: {e}")
            extra_params = []

        # 1. Header audit
        resp = _get(url, timeout=12)
        if not resp:
            return f"❌ Could not reach {url}"
        header_issues = _audit_headers(resp)
        if header_issues:
            lines.append(f"\n  🛡️  Header Issues ({len(header_issues)}):")
            for h in header_issues:
                icon = {"HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(h["severity"], "•")
                lines.append(f"    {icon} {h['message']}")
            all_findings.extend(header_issues)

        # 2. Sensitive file exposure
        lines.append(f"\n  📁 Sensitive File Probe:")
        sf = _check_sensitive_files(base)
        if sf:
            for f in sf:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠"}.get(f["severity"], "🟡")
                lines.append(f"    {icon} [{f['severity']}] {f['url']}")
                lines.append(f"       {f['message']}")
            all_findings.extend(sf)
        else:
            lines.append("    ✅ No exposed sensitive files found")

        # 3. CORS check
        lines.append(f"\n  🌐 CORS:")
        cors = _check_cors(url)
        if cors:
            lines.append(f"    🟠 [{cors['severity']}] {cors['message']}")
            all_findings.append(cors)
        else:
            lines.append("    ✅ CORS appears safe")

        # 4. XSS probe (on query params if any, else add test param)
        lines.append(f"\n  💉 XSS Probe:")
        xss_base = url.split("?")[0]
        test_params = re.findall(r"[?&](\w+)=", url) or ["q", "search", "s"]
        # Merge with discovered params
        try:
            all_test_params = list(dict.fromkeys(test_params + extra_params))
        except Exception:
            all_test_params = test_params
        xss_findings = []
        for param in all_test_params[:5]:
            xss_findings.extend(_probe_xss(xss_base, param))
        if xss_findings:
            for f in xss_findings:
                lines.append(f"    🟠 [{f['severity']}] {f['message']}")
                lines.append(f"       Param: {f['parameter']} | Payload: {f['payload'][:60]}")
            all_findings.extend(xss_findings)
            # ExploitConfirmEngine — canary XSS confirmation on first hit
            try:
                from bb_engines import ExploitConfirmEngine
                ece = ExploitConfirmEngine()
                first_xss = xss_findings[0]
                conf = ece.confirm_xss(xss_base, first_xss.get("parameter", "q"))
                if conf.get("confirmed"):
                    lines.append(f"    ✅ XSS CONFIRMED via canary token: {conf.get('evidence', '')}")
                    all_findings[all_findings.index(first_xss)]["confirmed"] = True
            except Exception:
                pass
        else:
            lines.append("    ✅ No reflected XSS found (basic probe)")

        # 5. SQLi probe
        lines.append(f"\n  🗄️  SQL Injection Probe:")
        sqli_findings = []
        for param in all_test_params[:5]:
            sqli_findings.extend(_probe_sqli(xss_base, param))
        if sqli_findings:
            for f in sqli_findings:
                lines.append(f"    🔴 [{f['severity']}] {f['message']}")
            all_findings.extend(sqli_findings)
            # ExploitConfirmEngine — time-based blind SQLi confirmation on first hit
            try:
                from bb_engines import ExploitConfirmEngine
                ece = ExploitConfirmEngine()
                first_sqli = sqli_findings[0]
                conf = ece.confirm_sqli(xss_base, first_sqli.get("parameter", "id"))
                if conf.get("confirmed"):
                    lines.append(f"    ✅ SQLi CONFIRMED via time-based blind: {conf.get('evidence', '')}")
                    sqli_findings[0]["confirmed"] = True
            except Exception:
                pass
        else:
            lines.append("    ✅ No SQL injection errors found (basic probe)")

        # 6. Open Redirect probe
        lines.append(f"\n  🔁 Open Redirect Probe:")
        redir_params = ["redirect", "url", "next", "return", "returnUrl", "redir"]
        redir_findings = []
        for param in redir_params[:4]:
            redir_findings.extend(_probe_open_redirect(xss_base, param))
        if redir_findings:
            for f in redir_findings:
                lines.append(f"    \U0001f7e1 [{f['severity']}] {f['message']}")
            all_findings.extend(redir_findings)
        else:
            lines.append("    ✅ No open redirects found (common params)")

        # 7. SSRF probe
        lines.append(f"\n  \U0001f310 SSRF Probe:")
        ssrf_params = [p for p in test_params if any(
            kw in p.lower() for kw in ["url", "uri", "path", "redirect", "fetch",
                                        "webhook", "callback", "src", "href", "link"]
        )] or ["url", "redirect", "fetch"]
        ssrf_payloads = [
            ("http://127.0.0.1",                     "loopback"),
            ("http://169.254.169.254/latest/meta-data/", "AWS metadata"),
        ]
        ssrf_findings = []
        for param in ssrf_params[:2]:
            for payload, label in ssrf_payloads:
                from urllib.parse import urlencode as _ue
                test_url_ssrf = f"{xss_base}?{_ue({param: payload})}"
                try:
                    r = _get(test_url_ssrf, timeout=6)
                    if r:
                        body = (r.text or "").lower()
                        if any(kw in body for kw in [
                            "ami-id", "instance-id", "computemetadata",
                            "ec2", "iam", "169.254",
                        ]):
                            ssrf_findings.append({
                                "type": "ssrf", "severity": "CRITICAL",
                                "param": param, "payload": payload,
                                "label": label,
                                "message": f"SSRF confirmed: {label} metadata via {param}={payload}",
                            })
                        elif r.status_code == 200 and len(r.text or "") > 100:
                            ssrf_findings.append({
                                "type": "ssrf_possible", "severity": "HIGH",
                                "param": param, "payload": payload,
                                "label": label,
                                "message": f"SSRF possible: {label} probe got HTTP 200 on {param}",
                            })
                except Exception:
                    pass
        if ssrf_findings:
            for f in ssrf_findings:
                icon = "\U0001f534" if f["severity"] == "CRITICAL" else "\U0001f7e0"
                lines.append(f"    {icon} [{f['severity']}] {f['message']}")
            all_findings.extend(ssrf_findings)
        else:
            lines.append("    ✅ No SSRF indicators found (basic probe)")

        # 8. SSTI probe
        lines.append(f"\n  \U0001f4a5 SSTI Probe:")
        ssti_payloads = ["{{7*7}}", "${7*7}", "<%= 7*7 %>", "#{7*7}", "*{7*7}"]
        ssti_findings = []
        for param in test_params[:3]:
            for payload in ssti_payloads[:2]:
                from urllib.parse import urlencode as _ue2
                test_url_ssti = f"{xss_base}?{_ue2({param: payload})}"
                try:
                    r = _get(test_url_ssti, timeout=6)
                    if r and "49" in (r.text or ""):
                        ssti_findings.append({
                            "type": "ssti", "severity": "CRITICAL",
                            "param": param, "payload": payload,
                            "message": f"SSTI confirmed: '{payload}' evaluated to 49 in {param}",
                        })
                        break
                except Exception:
                    pass
        if ssti_findings:
            for f in ssti_findings:
                lines.append(f"    \U0001f534 [{f['severity']}] {f['message']}")
            all_findings.extend(ssti_findings)
        else:
            lines.append("    ✅ No SSTI indicators found")

        # 9. Path traversal probe
        lines.append(f"\n  \U0001f4c2 Path Traversal Probe:")
        trav_params = [p for p in test_params if any(
            kw in p.lower() for kw in ["file", "path", "filename", "doc", "page",
                                        "template", "dir", "folder"]
        )] or ["file", "path", "filename"]
        trav_payloads = [
            "../../../../etc/passwd",
            "..%2F..%2F..%2Fetc%2Fpasswd",
            "....//....//etc/passwd",
        ]
        trav_findings = []
        for param in trav_params[:2]:
            for payload in trav_payloads[:2]:
                from urllib.parse import urlencode as _ue3
                test_url_trav = f"{xss_base}?{_ue3({param: payload})}"
                try:
                    r = _get(test_url_trav, timeout=6)
                    if r and "root:" in (r.text or "").lower():
                        trav_findings.append({
                            "type": "path_traversal", "severity": "CRITICAL",
                            "param": param, "payload": payload,
                            "message": f"Path traversal: /etc/passwd exposed via {param}={payload}",
                        })
                        break
                except Exception:
                    pass
        if trav_findings:
            for f in trav_findings:
                lines.append(f"    \U0001f534 [{f['severity']}] {f['message']}")
            all_findings.extend(trav_findings)
        else:
            lines.append("    ✅ No path traversal found (common file params)")

        # 10. CRLF injection probe
        lines.append(f"\n  🔀 CRLF Injection Probe:")
        try:
            from bb_engines import CRLFProbe
            crlf = CRLFProbe()
            for param in all_test_params[:3]:
                crlf_results = crlf.probe(xss_base, param)
                if crlf_results:
                    lines.append(crlf.format_report(crlf_results))
                    all_findings.extend(crlf_results)
                    break
            else:
                lines.append("    ✅ No CRLF injection found (common params)")
        except Exception as e:
            lines.append(f"    ⚠️  CRLF probe error: {e}")

        # 11. Prototype Pollution probe
        lines.append(f"\n  ⚡ Prototype Pollution Probe:")
        try:
            from bb_engines import PrototypePollutionProbe
            ppp = PrototypePollutionProbe()
            pp_results = ppp.probe(xss_base)
            if pp_results:
                lines.append(ppp.format_report(pp_results))
                all_findings.extend(pp_results)
            else:
                lines.append("    ✅ No prototype pollution indicators found")
        except Exception as e:
            lines.append(f"    ⚠️  Prototype pollution probe error: {e}")

        # Summary
        critical = sum(1 for f in all_findings if f.get("severity") in ["CRITICAL", "critical"])
        high = sum(1 for f in all_findings if f.get("severity") in ["HIGH", "high"])
        medium = sum(1 for f in all_findings if f.get("severity") in ["MEDIUM", "medium"])
        low = sum(1 for f in all_findings if f.get("severity") in ["LOW", "low"])

        lines.append(f"\n─" * 55)
        lines.append(f"  📊 Scan Complete: {len(all_findings)} total issues")
        lines.append(f"     🔴 Critical: {critical}  🟠 High: {high}  🟡 Medium: {medium}  🟢 Low: {low}")
        lines.append(f"  ➜ Use /bugbounty add <url> <severity> <title> to log a finding")
        return "\n".join(lines)

    # ── Finding tracker ───────────────────────────────────────────────────────

    def _load_findings(self):
        if os.path.exists(self.FINDINGS_FILE):
            try:
                with open(self.FINDINGS_FILE, "r") as f:
                    self.findings = json.load(f)
            except Exception:
                self.findings = []

    def _save_findings(self):
        try:
            with open(self.FINDINGS_FILE, "w") as f:
                json.dump(self.findings, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save findings: {e}")

    def add_finding(self, url: str, severity: str, title: str,
                    description: str = "", platform: str = "", program: str = "") -> Dict:
        """Manually log a bug bounty finding."""
        severity = severity.lower()
        if severity not in SEVERITY_LEVELS:
            severity = "medium"
        finding = {
            "id": len(self.findings) + 1,
            "url": url,
            "title": title,
            "severity": severity,
            "description": description or f"{severity.title()} severity vulnerability at {url}",
            "platform": platform,
            "program": program,
            "status": "new",
            "found_at": datetime.now().isoformat(),
            "poc": "",
        }
        self.findings.append(finding)
        self._save_findings()
        # Send webhook notification for Critical/High findings
        if severity in ["critical", "high"]:
            try:
                from bb_engines import WebhookNotifier
                WebhookNotifier().notify_finding({**finding, "severity": severity.upper()})
            except Exception:
                pass
        return finding

    def list_findings(self) -> str:
        """List all saved findings."""
        if not self.findings:
            return "  📋 No findings logged yet.\n  Use: /bugbounty add <url> <severity> <title>"
        SEV_ICONS = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "informational": "ℹ️"}
        lines = [f"📋 Bug Bounty Findings ({len(self.findings)} total):", "─" * 55]
        for f in sorted(self.findings, key=lambda x: SEVERITY_LEVELS.index(x.get("severity","medium"))):
            icon = SEV_ICONS.get(f["severity"], "•")
            platform_str = f" [{f['platform']}/{f['program']}]" if f.get("platform") else ""
            lines.append(f"  [{f['id']}] {icon} [{f['severity'].upper()}] {f['title']}{platform_str}")
            lines.append(f"       {f['url']}")
            lines.append(f"       Status: {f['status']} | Found: {f['found_at'][:10]}")
        return "\n".join(lines)

    def generate_report(self, finding_id: Optional[int] = None,
                         export_path: Optional[str] = None) -> str:
        """Generate a formatted PoC report for a finding.

        If export_path is given, write the report .md to that path and
        append the save location to the returned string.
        """
        if not self.findings:
            return "  ❌ No findings logged. Use /bugbounty add first."

        if finding_id:
            finding = next((f for f in self.findings if f["id"] == finding_id), None)
            if not finding:
                return f"  ❌ Finding #{finding_id} not found"
        else:
            # Sort by severity, pick most critical
            finding = sorted(self.findings,
                             key=lambda x: SEVERITY_LEVELS.index(x.get("severity", "medium")))[0]

        # LLM-enhanced report if available
        llm_impact = ""
        llm_remediation = ""
        if self.llm:
            try:
                llm_impact = self.llm.call(
                    f"Write a 2-sentence business impact statement for: [{finding['severity'].upper()}] "
                    f"{finding['title']} at {finding['url']}. Be concise and professional.",
                    max_tokens=100
                )
                llm_remediation = self.llm.call(
                    f"Write 2-3 bullet point remediation steps for: {finding['title']}. Be specific and technical.",
                    max_tokens=120
                )
            except Exception:
                pass

        report = f"""# Bug Report: {finding['title']}

**Severity:** {finding['severity'].upper()}
**URL:** {finding['url']}
**Platform:** {finding.get('platform', 'N/A')} / {finding.get('program', 'N/A')}
**Reported:** {finding['found_at'][:10]}

---

## Summary

{finding['description']}

## Vulnerability Details

**Type:** {finding['title']}
**Affected Endpoint:** `{finding['url']}`
**CVSS Severity:** {finding['severity'].upper()}

## Steps to Reproduce

1. Navigate to: `{finding['url']}`
2. {finding.get('poc') or 'Observe the vulnerability as described.'}
3. Note the impact described below.

## Impact

{llm_impact or f"This {finding['severity']} severity vulnerability could allow an attacker to compromise affected users or the application."}

## Remediation

{llm_remediation or f"- Review and fix the identified vulnerability at {finding['url']}\n- Apply security headers and input validation\n- Conduct a thorough code review of similar endpoints"}

---

*Report generated by Ultimate AI Agent — Bug Bounty Hunter*
*Finding ID: #{finding['id']}*
"""
        if export_path:
            try:
                os.makedirs(os.path.dirname(export_path) if os.path.dirname(export_path) else ".", exist_ok=True)
                with open(export_path, "w", encoding="utf-8") as fh:
                    fh.write(report)
                report += f"\n\n---\n*Saved to: `{export_path}`*"
            except Exception as e:
                report += f"\n\n⚠️ Could not save to {export_path}: {e}"
        return report

    def export_markdown_report(self, finding_id: Optional[int] = None,
                               output_dir: str = "reports/") -> str:
        """
        Generate a Markdown PoC report and save it to output_dir.
        Returns the file path on success.
        """
        import re as _re
        if not self.findings:
            return "  ❌ No findings. Use /bugbounty add first."
        if finding_id:
            finding = next((f for f in self.findings if f["id"] == finding_id), None)
            if not finding:
                return f"  ❌ Finding #{finding_id} not found"
        else:
            finding = sorted(self.findings,
                             key=lambda x: SEVERITY_LEVELS.index(x.get("severity", "medium")))[0]
        safe_title = _re.sub(r'[^\w\- ]', '_', finding.get("title", "finding"))[:50]
        filename = f"{output_dir.rstrip('/')}/finding_{finding['id']}_{safe_title}.md"
        self.generate_report(finding_id=finding["id"], export_path=filename)
        return filename

    def submit_report(self, platform: str, program: str,
                      finding_id: Optional[int] = None,
                      skip_dedup_check: bool = False) -> str:
        """Submit a finding to a bug bounty platform via API."""
        platform = platform.lower()
        if not self.findings:
            return "  ❌ No findings to submit. Log a finding first with /bugbounty add"

        if finding_id:
            finding = next((f for f in self.findings if f["id"] == finding_id), None)
        else:
            finding = sorted(self.findings,
                             key=lambda x: SEVERITY_LEVELS.index(x.get("severity", "medium")))[0]

        if not finding:
            return "  ❌ Finding not found"

        # Auto-dedup check before submitting
        if not skip_dedup_check:
            try:
                from bb_engines import DuplicateFinder
                df = DuplicateFinder()
                dup_result = df.check_duplicate(finding)
                if "similar disclosed report" in dup_result:
                    return (
                        f"  ⚠️  Duplicate check flagged similar public reports!\n"
                        f"{dup_result}\n\n"
                        f"  To submit anyway: /bugbounty submit {platform} {program} {finding['id']} --force"
                    )
            except Exception:
                pass

        if platform == "hackerone" or platform == "h1":
            token = os.getenv("H1_API_TOKEN") or os.getenv("HACKERONE_API_TOKEN")
            username = os.getenv("H1_USERNAME") or os.getenv("HACKERONE_USERNAME")
            if not token:
                return ("  ❌ Set environment variable H1_API_TOKEN (and optionally H1_USERNAME)\n"
                        "  Get it at: https://hackerone.com/settings/api_token/edit")
            report = self.generate_report(finding["id"])
            result = _submit_h1_report(
                api_token=token,
                h1_username=username or "researcher",
                program_handle=program,
                title=finding["title"],
                description=report,
                severity=finding["severity"],
            )
            if result.get("success"):
                finding["status"] = "submitted"
                finding["platform"] = "hackerone"
                finding["program"] = program
                self._save_findings()
                return (f"  ✅ Report submitted to HackerOne!\n"
                        f"  ID: #{result['report_id']}\n"
                        f"  URL: {result['url']}")
            return f"  ❌ Submission failed: {result.get('error', 'Unknown')}"

        elif platform == "bugcrowd":
            token = os.getenv("BUGCROWD_TOKEN")
            if token:
                # Basic Bugcrowd submission via API
                submit_url = f"https://bugcrowd.com/api/v1/engagements/{program}/submissions"
                report_text = self.generate_report(finding["id"])
                payload = {
                    "submission": {
                        "title": finding["title"],
                        "description": report_text,
                        "severity": finding["severity"],
                        "vulnerability_references": finding["url"],
                    }
                }
                resp = _post(submit_url, json_data=payload,
                             headers={"Authorization": f"Token {token}",
                                      "Content-Type": "application/json"})
                if resp and resp.status_code in [200, 201]:
                    finding["status"] = "submitted"
                    finding["platform"] = "bugcrowd"
                    finding["program"] = program
                    self._save_findings()
                    return f"  ✅ Submitted to Bugcrowd program: {program}"
                return (f"  ⚠️ Bugcrowd API returned {getattr(resp,'status_code','?')}.\n"
                        f"  Check https://bugcrowd.com/{program} to submit manually.\n"
                        f"  Run /bugbounty report {finding['id']} for formatted PoC.")
            else:
                report_text = self.generate_report(finding["id"])
                return (f"  💡 Bugcrowd submission — set BUGCROWD_TOKEN for API submit.\n"
                        f"  Web UI: https://bugcrowd.com/{program}/report\n"
                        f"  PoC Report:\n{report_text}")

        elif platform == "intigriti":
            token = os.getenv("INTIGRITI_TOKEN")
            if token:
                # Intigriti submission endpoint
                submit_url = f"https://app.intigriti.com/api/core/researcher/submissions"
                report_text = self.generate_report(finding["id"])
                payload = {
                    "programId": program,
                    "title": finding["title"],
                    "description": report_text,
                    "severity": {"critical": 5, "high": 4, "medium": 3,
                                  "low": 2, "informational": 1}.get(finding["severity"], 3),
                    "endpoint": finding["url"],
                }
                resp = _post(submit_url, json_data=payload,
                             headers={"Authorization": f"Bearer {token}",
                                      "Content-Type": "application/json"})
                if resp and resp.status_code in [200, 201]:
                    finding["status"] = "submitted"
                    finding["platform"] = "intigriti"
                    finding["program"] = program
                    self._save_findings()
                    return f"  ✅ Submitted to Intigriti program: {program}"
                return (f"  ⚠️ Intigriti API returned {getattr(resp,'status_code','?')}.\n"
                        f"  Web UI: https://app.intigriti.com/researcher/programs/{program}\n"
                        f"  Run /bugbounty report {finding['id']} for formatted PoC.")
            else:
                report_text = self.generate_report(finding["id"])
                return (f"  💡 Intigriti submission — set INTIGRITI_TOKEN for API submit.\n"
                        f"  Web UI: https://app.intigriti.com/researcher/programs/{program}/report\n"
                        f"  PoC Report:\n{report_text}")

        return f"  ❌ Unknown platform: {platform}. Use: hackerone, bugcrowd, intigriti"

    # ── Nuclei CLI integration ────────────────────────────────────────────────

    def run_nuclei(self, target: str, severity: str = "medium,high,critical",
                   output_dir: str = "reports/", dry_run: bool = False) -> str:
        """
        Run Nuclei against a target and ingest results as findings.

        Looks for nuclei.exe (Windows) or nuclei (Linux/Mac) in:
          1. Current working directory
          2. PATH

        Args:
            target:     URL or domain to scan
            severity:   Comma-separated severity filter (default: medium,high,critical)
            output_dir: Directory to write nuclei JSON output
            dry_run:    If True, only check availability and return the command that would run

        Returns formatted result string.
        """
        import shutil, subprocess, json as _json

        # Locate nuclei binary
        nuclei_bin = None
        for candidate in ["nuclei.exe", "nuclei"]:
            if os.path.exists(candidate):
                nuclei_bin = candidate
                break
            found = shutil.which(candidate)
            if found:
                nuclei_bin = found
                break

        if not nuclei_bin:
            return ("  ⚠️  Nuclei not found. Download from https://github.com/projectdiscovery/nuclei/releases\n"
                    "  Place nuclei.exe in the agent directory or add to PATH.")

        os.makedirs(output_dir, exist_ok=True)
        safe_target = re.sub(r"[^\w\-.]", "_", target)[:40]
        out_file = os.path.join(output_dir, f"nuclei_{safe_target}.json")

        cmd = [nuclei_bin, "-u", target, "-severity", severity,
               "-json", "-o", out_file, "-silent", "-no-color"]

        if dry_run:
            return f"  🔍 Nuclei available: {nuclei_bin}\n  Would run: {' '.join(cmd)}"

        lines = [f"⚡ Nuclei Scan: {target}", f"   Severity: {severity}", "─" * 55]
        try:
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        except subprocess.TimeoutExpired:
            return "  ⚠️  Nuclei timed out after 5 minutes."
        except Exception as e:
            return f"  ❌ Nuclei execution error: {e}"

        new_findings = []
        if os.path.exists(out_file):
            try:
                with open(out_file, "r") as fh:
                    for line in fh:
                        line = line.strip()
                        if not line:
                            continue
                        hit = _json.loads(line)
                        info = hit.get("info", {})
                        sev = info.get("severity", "medium").lower()
                        if sev not in SEVERITY_LEVELS:
                            sev = "medium"
                        finding = self.add_finding(
                            url=hit.get("matched-at") or hit.get("host") or target,
                            severity=sev,
                            title=info.get("name", "Nuclei finding"),
                            description=(info.get("description") or
                                         f"Template: {hit.get('template-id','?')} | "
                                         f"Matcher: {hit.get('matcher-name','')}"),
                            platform="nuclei",
                            program=target,
                        )
                        new_findings.append(finding)
            except Exception as e:
                lines.append(f"  ⚠️  Parse error: {e}")

        if new_findings:
            lines.append(f"  ✅ {len(new_findings)} finding(s) found and saved:")
            counts = {}
            for f in new_findings:
                counts[f["severity"]] = counts.get(f["severity"], 0) + 1
            for sev, n in sorted(counts.items(), key=lambda x: SEVERITY_LEVELS.index(x[0])):
                icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢"}
                lines.append(f"     {icons.get(sev,'•')} {sev.upper()}: {n}")
            lines.append(f"  📄 Output: {out_file}")
            lines.append(f"  ➜ /bugbounty findings | /bugbounty report")
        else:
            lines.append("  ✅ No vulnerabilities found by Nuclei (or output empty).")

        return "\n".join(lines)

    # ── Autopilot — end-to-end chain ─────────────────────────────────────────


    # ── Triage Dashboard ────────────────────────────────────────────────────

    def triage_dashboard(self) -> str:
        """
        Rank all findings by exploitability and estimated bounty.
        Uses AIImpactAnalyzer.score_priority().
        """
        from bb_engines import AIImpactAnalyzer
        if not self.findings:
            return "  ℹ️  No findings yet. Run /bugbounty scan or /bugbounty autopilot first."
        analyzer = AIImpactAnalyzer()
        ranked = analyzer.score_priority(self.findings)

        from bb_engines import DuplicateFinder
        dup_finder = DuplicateFinder()

        lines = [
            "🏆 TRIAGE DASHBOARD — Ranked by Exploit Priority",
            "═" * 60,
            f"  {'#':<4} {'SEV':<12} {'TYPE':<22} {'BOUNTY EST.':<16} TITLE",
            "─" * 60,
        ]
        bounty_ranges = {
            "critical": "$5K–$50K", "high": "$1K–$10K",
            "medium": "$200–$2K", "low": "$50–$500", "informational": "$0–$150",
        }
        for i, f in enumerate(ranked, 1):
            sev = f.get("severity", "low").lower()
            icons = {"critical": "🔴", "high": "🟠", "medium": "🟡",
                     "low": "🟢", "informational": "ℹ️ "}
            icon = icons.get(sev, "•")
            bounty = bounty_ranges.get(sev, "?")
            title = f.get("title", "Untitled")[:35]
            vuln_type = f.get("type", "?")[:20]
            status = f.get("status", "new")
            status_icon = "✅" if status == "submitted" else "🆕"
            lines.append(f"  {i:<4} {icon} {sev:<10} {vuln_type:<22} {bounty:<16} {title}")

        lines.append("─" * 60)
        lines.append(f"  TOTAL: {len(ranked)} finding(s) — prioritized by impact × exploitability")
        lines.append(f"  ➜ /bugbounty report <id>  to generate submission-ready PoC")
        lines.append(f"  ➜ /bugbounty html         to export full HTML report")
        return "\n".join(lines)

    # ── Finding Status Workflow ──────────────────────────────────────────────

    def update_finding_status(self, finding_id: str, new_status: str, note: str = "") -> str:
        """
        Update the status of a finding with timestamp tracking.
        Valid statuses: new, triaged, needs_poc, submitted, waiting_response,
                        closed, duplicate, wont_fix, bounty_paid
        """
        VALID_STATUSES = [
            "new", "triaged", "needs_poc", "submitted", "waiting_response",
            "closed", "duplicate", "wont_fix", "bounty_paid", "informational",
        ]
        f = self._get_finding_by_id(finding_id) if hasattr(self, '_get_finding_by_id') else None
        if not f:
            # Find by partial match
            for finding in self.findings:
                if (str(finding.get("id", "")).startswith(finding_id) or
                        finding.get("id") == finding_id):
                    f = finding
                    break
        if not f:
            return f"  ❌ Finding ID '{finding_id}' not found. Use /bugbounty findings to list."

        new_status = new_status.lower()
        if new_status not in VALID_STATUSES:
            return f"  ❌ Invalid status. Valid: {', '.join(VALID_STATUSES)}"

        old_status = f.get("status", "new")
        f["status"] = new_status

        # Track status history
        if "status_history" not in f:
            f["status_history"] = []
        f["status_history"].append({
            "from": old_status,
            "to": new_status,
            "timestamp": datetime.now().isoformat(),
            "note": note,
        })

        if note:
            f["notes"] = f.get("notes", [])
            f["notes"].append({"timestamp": datetime.now().isoformat(), "text": note})

        self._save_findings()
        return (f"  ✅ Finding #{finding_id} status: {old_status} → {new_status}"
                + (f"\n  📝 Note: {note}" if note else ""))

    def _save_findings(self) -> None:
        """Save findings to disk."""
        try:
            with open(self.findings_file, "w", encoding="utf-8") as fh:
                import json as _json
                _json.dump(self.findings, fh, indent=2)
        except Exception as e:
            logger.debug(f"Save findings error: {e}")

    # ── Webhook Configuration ────────────────────────────────────────────────

    def configure_webhook(self, webhook_url: str) -> str:
        """
        Configure and test a Slack or Discord webhook URL for real-time notifications.
        Auto-detects platform from URL.
        """
        from bb_engines import WebhookNotifier
        notifier = WebhookNotifier()

        # Detect platform
        if "hooks.slack.com" in webhook_url:
            platform = "Slack"
            test_msg = "🔔 Bug Bounty webhook configured successfully! You'll receive alerts for Critical/High findings."
            ok = notifier._send_slack(webhook_url, test_msg, "#36a64f")
        elif "discord.com/api/webhooks" in webhook_url or "discordapp.com/api/webhooks" in webhook_url:
            platform = "Discord"
            test_msg = "🔔 Bug Bounty webhook configured! Critical/High finding alerts enabled."
            ok = notifier._send_discord(webhook_url, test_msg)
        else:
            return ("  ❌ Unrecognized webhook URL format.\n"
                    "  Slack:   https://hooks.slack.com/services/...\n"
                    "  Discord: https://discord.com/api/webhooks/...")

        if ok:
            # Persist to environment for this session
            env_key = "SLACK_WEBHOOK_URL" if platform == "Slack" else "DISCORD_WEBHOOK_URL"
            os.environ[env_key] = webhook_url
            return (f"  ✅ {platform} webhook configured and tested successfully!\n"
                    f"  Env var set: {env_key} (session only — export in your shell profile to persist)\n"
                    f"  You'll receive alerts for all Critical and High severity findings.")
        else:
            return f"  ❌ Test message to {platform} webhook failed — check the URL is correct."

    # ── DOM XSS Scan ────────────────────────────────────────────────────────

    def dom_xss_scan(self, url: str) -> str:
        """Scan a URL for DOM-based XSS vulnerabilities."""
        try:
            from bb_engines import DOMXSSEngine
            engine = DOMXSSEngine()
            return engine.scan_url(url)
        except ImportError as e:
            return f"  ❌ DOMXSSEngine not available: {e}"

    # ── WebSocket Scan ───────────────────────────────────────────────────────

    def ws_scan(self, url: str) -> str:
        """Scan a URL for WebSocket endpoints and test their security."""
        try:
            from bb_engines import WebSocketEngine
            engine = WebSocketEngine()
            return engine.scan(url)
        except ImportError as e:
            return f"  ❌ WebSocketEngine not available: {e}"

    # ── Request Smuggling Scan ───────────────────────────────────────────────

    def smuggling_scan(self, url: str) -> str:
        """Test a URL for HTTP request smuggling (CL.TE / TE.CL)."""
        try:
            from bb_engines import RequestSmugglingEngine
            engine = RequestSmugglingEngine()
            return engine.scan(url)
        except ImportError as e:
            return f"  ❌ RequestSmugglingEngine not available: {e}"

    # ── XXE Probe Scan ───────────────────────────────────────────────────────

    def xxe_scan(self, url: str) -> str:
        """Test a URL for XML External Entity (XXE) injection."""
        try:
            from bb_engines import XXEProbeEngine
            engine = XXEProbeEngine()
            findings = engine.probe(url)
            report = engine.format_report(findings)
            # Add high-severity findings to tracker
            for f_data in findings:
                if f_data.get("confirmed") and f_data.get("severity") in ["HIGH", "CRITICAL"]:
                    self.add_finding(
                        url=url,
                        severity=f_data["severity"].lower(),
                        title=f"XXE Injection at {url}",
                        description=f_data.get("message", ""),
                        vuln_type="xxe",
                    )
            return report
        except ImportError as e:
            return f"  ❌ XXEProbeEngine not available: {e}"

    # ── Hunt Session ─────────────────────────────────────────────────────────

    def save_hunt_session(self) -> str:
        """Save current hunt state (scope, findings, subdomains) to disk."""
        try:
            from bb_engines import HuntSession
            domain = self.scope[0] if self.scope else "unknown"
            session = HuntSession(domain=domain)
            session.scope = list(self.scope)
            session.findings = self.findings
            session.subdomains = list(getattr(self, '_discovered_subdomains', []))
            session.metadata = {
                "program": getattr(self, 'program', ""),
                "platform": getattr(self, 'platform', ""),
            }
            return session.save()
        except Exception as e:
            return f"  ❌ Save failed: {e}"

    def load_hunt_session(self, domain: str) -> str:
        """Load a previously saved hunt session."""
        try:
            from bb_engines import HuntSession
            session = HuntSession()
            ok = session.load(domain)
            if not ok:
                return f"  ❌ No saved session for '{domain}'. Use /bugbounty session list to see available."
            self.scope = set(session.scope)
            self.findings = session.findings
            self._discovered_subdomains = session.subdomains
            return (f"  ✅ Hunt session loaded for {domain}\n"
                    f"     {len(session.scope)} scope domains\n"
                    f"     {len(session.findings)} findings\n"
                    f"     {len(session.subdomains)} subdomains")
        except Exception as e:
            return f"  ❌ Load failed: {e}"

    def list_hunt_sessions(self) -> str:
        """List all saved hunt sessions."""
        try:
            from bb_engines import HuntSession
            return HuntSession.list_sessions()
        except Exception as e:
            return f"  ❌ Error: {e}"

    # ── Rate Limit Configuration ─────────────────────────────────────────────

    def set_rate_limit(self, delay_seconds: float = 0.5) -> str:
        """Configure HTTP request rate limiting (delay between requests)."""
        import bug_bounty_hunter as _bbh
        _bbh._RATE_LIMIT_DELAY = max(0.0, delay_seconds)
        _bbh._RATE_LIMIT_ENABLED = delay_seconds > 0
        if delay_seconds > 0:
            return (f"  ✅ Rate limiting: {delay_seconds}s between requests "
                    f"(≈ {1/delay_seconds:.1f} req/s)\n"
                    f"  💡 Recommended: 0.5s (safe), 1.0s (very polite), 0.1s (aggressive)")
        return "  ⚠️  Rate limiting disabled — be careful not to trigger WAF/IP bans"

    # ── CVSS Auto-Suggest ────────────────────────────────────────────────────

    def cvss_suggest(self, vuln_type: str) -> str:
        """Suggest a CVSS 3.1 vector for a given vulnerability type."""
        try:
            from bb_engines import CVSS31Calculator
            calc = CVSS31Calculator()
            return calc.suggest_vector(vuln_type)
        except ImportError as e:
            return f"  ❌ CVSS calculator not available: {e}"

    def autopilot(self, domain: str, scope: List[str] = None,
                  run_nuclei_scan: bool = True,
                  output_dir: str = "reports/") -> str:
        """
        Full autopilot: chains all active engines end-to-end.

        Steps:
          1. Scope setup
          2. Passive recon (crt.sh subdomains, headers, CORS)
          3. JS secret scanning on discovered JS files
          4. Subdomain takeover check
          5. Tech fingerprint + CVE matching
          6. Active scan (headers, CORS, SQLi, XSS, redirects)
          7. Host header injection test
          8. Nuclei scan (if enabled and available)
          9. Markdown report export
        """
        lines = [
            "╔══════════════════════════════════════════════════════════╗",
            f"║  🚀 BUG BOUNTY AUTOPILOT: {domain:<32}║",
            "╚══════════════════════════════════════════════════════════╝",
            "",
        ]

        # ── 1. Scope ─────────────────────────────────────────────────
        scope_domains = scope or [domain, f"*.{domain}"]
        lines.append("  [1/8] 🎯 Setting scope...")
        lines.append(self.set_scope(scope_domains))

        # ── 2. Passive recon ─────────────────────────────────────────
        lines.append("\n  [2/8] 🔍 Passive recon...")
        try:
            recon_out = self.passive_recon(domain)
            # Extract subdomain list from crt.sh for later takeover check
            discovered_subs = []
            for line in recon_out.splitlines():
                if line.strip().startswith("•") and domain in line:
                    sub = line.strip().lstrip("• ").strip()
                    if sub and sub != domain:
                        discovered_subs.append(sub)
            lines.append(recon_out)
        except Exception as e:
            lines.append(f"  ⚠️  Recon error: {e}")
            discovered_subs = []

        # ── 3. JS secret scanning ────────────────────────────────────
        lines.append("\n  [3/8] 🔑 JS Secret Scanning...")
        try:
            from js_secret_scanner import JSSecretScanner
            from bb_engines import PassiveReconEngine
            pre = PassiveReconEngine()
            js_urls = pre.find_js_files(f"https://{domain}")
            if js_urls:
                scanner = JSSecretScanner()
                secrets = scanner.scan_urls(js_urls)
                lines.append(scanner.format_report(secrets))
                for s in secrets:
                    if s["severity"] in ["CRITICAL", "HIGH"]:
                        self.add_finding(
                            url=s["source"], severity=s["severity"].lower(),
                            title=f"Hardcoded {s['name']}",
                            description=f"Found in JS: {s['context'][:200]}",
                        )
            else:
                lines.append("  ℹ️  No JS files detected.")
        except Exception as e:
            lines.append(f"  ⚠️  JS scan error: {e}")

        # ── 4. Subdomain takeover ────────────────────────────────────
        lines.append("\n  [4/8] 🎯 Subdomain Takeover Check...")
        try:
            from bb_engines import TakeoverEngine
            to_engine = TakeoverEngine()
            takeover_out = to_engine.scan_domain(domain, discovered_subs or None)
            lines.append(takeover_out)
            # Auto-log confirmed takeovers
            for line in takeover_out.splitlines():
                if "[HIGH]" in line or "[CRITICAL]" in line:
                    sub = line.split("]")[-1].strip()
                    if sub:
                        self.add_finding(url=f"http://{sub}", severity="medium",
                                         title=f"Subdomain Takeover: {sub}")
        except Exception as e:
            lines.append(f"  ⚠️  Takeover scan error: {e}")

        # ── 5. Tech fingerprint + CVEs ───────────────────────────────
        lines.append("\n  [5/8] 🖥️  Tech Fingerprinting + CVE Match...")
        try:
            from fingerprint_engine import FingerprintEngine
            fe = FingerprintEngine()
            profile = fe.fingerprint(f"https://{domain}")
            cves = fe.match_cves(profile)
            lines.append(fe.format_report(profile, cves))
            # Add CVE findings
            for tech, cve_list in cves.items():
                for cve in cve_list[:2]:
                    self.add_finding(
                        url=f"https://{domain}", severity="high" if cve["cvss"] >= 9.0 else "medium",
                        title=f"Known CVE: {cve['id']} ({tech})",
                        description=cve["summary"],
                    )
        except Exception as e:
            lines.append(f"  ⚠️  Fingerprint error: {e}")

        # ── 6. Active scan ───────────────────────────────────────────
        lines.append("\n  [6/8] ⚔️  Active Vulnerability Scan...")
        try:
            scan_out = self.active_scan(f"https://{domain}")
            lines.append(scan_out)
        except Exception as e:
            lines.append(f"  ⚠️  Active scan error: {e}")

        # ── 7. Host header injection ─────────────────────────────────
        lines.append("\n  [7/8] 🌐 Host Header Injection Test...")
        try:
            from bb_engines import PayloadMutationEngine
            pme = PayloadMutationEngine()
            hh_findings = pme.test_host_header_injection(f"https://{domain}")
            lines.append(pme.format_host_injection_report(hh_findings))
            for hf in hh_findings:
                if hf.get("severity") in ["HIGH", "CRITICAL"]:
                    self.add_finding(
                        url=f"https://{domain}", severity=hf["severity"].lower(),
                        title=f"Host Header Injection: {hf['type']}",
                        description=hf["evidence"],
                    )
        except Exception as e:
            lines.append(f"  ⚠️  Host header test error: {e}")

        # ── 8. Nuclei ────────────────────────────────────────────────
        if run_nuclei_scan:
            lines.append("\n  [8/8] ⚡ Nuclei Scan...")
            try:
                lines.append(self.run_nuclei(f"https://{domain}", output_dir=output_dir))
            except Exception as e:
                lines.append(f"  ⚠️  Nuclei error: {e}")
        else:
            lines.append("\n  [8/8] ⚡ Nuclei — skipped (run_nuclei_scan=False)")

        # ── Summary & report ─────────────────────────────────────────
        lines.append("\n" + "═" * 60)
        lines.append(f"  📊 AUTOPILOT COMPLETE — {len(self.findings)} total finding(s)")
        os.makedirs(output_dir, exist_ok=True)
        report_path = self.export_markdown_report(output_dir=output_dir)
        lines.append(f"  📄 Report saved: {report_path}")
        lines.append(f"  ➜ /bugbounty findings  |  /bugbounty submit h1 <program>")
        lines.append("═" * 60)

        return "\n".join(lines)

    def export_html_report(self, finding_id: Optional[int] = None,
                           output_dir: str = "reports/") -> str:
        """
        Generate a professional HTML report and save it to output_dir.
        Returns the file path on success.

        Args:
            finding_id: If provided, export only that finding. Otherwise export all.
            output_dir: Directory to write the HTML file.
        """
        try:
            from bb_html_report import export as _html_export
        except ImportError:
            return "  \u274c bb_html_report.py not found. Ensure it is in the same directory."

        if not self.findings:
            return "  \u274c No findings to export. Use /bugbounty add first."

        if finding_id:
            finding = next((f for f in self.findings if f["id"] == finding_id), None)
            if not finding:
                return f"  \u274c Finding #{finding_id} not found"
            findings_to_export = [finding]
        else:
            findings_to_export = self.findings

        os.makedirs(output_dir, exist_ok=True)
        path = _html_export(
            findings=findings_to_export,
            path=None,  # auto-generate filename
            program=getattr(self, '_current_program', ''),
            platform=getattr(self, '_current_platform', ''),
        )
        return f"  \u2705 HTML Report exported: {path}\n  \U0001f4c4 Open in browser to view"

    # ── JWT Scanner ───────────────────────────────────────────────────────────

    def scan_jwt(self, token_or_url: str) -> str:
        """
        JWT vulnerability scanner.
        Pass either:
          - A raw JWT token (eyJ...) to scan directly
          - A URL to auto-detect and scan any JWT in the response
        """
        from bb_engines import JWTScanner
        scanner = JWTScanner()
        # If it looks like a URL, auto-detect JWTs from the response
        if token_or_url.startswith("http"):
            return scanner.scan_url(token_or_url)
        # Otherwise treat it as a raw token
        result = scanner.scan_token(token_or_url)
        return scanner.format_report(result)

    # ── CVSS 3.1 Calculator ───────────────────────────────────────────────────

    def calculate_cvss(self, vector: str = "") -> str:
        """
        CVSS 3.1 base score calculator.
        Pass a vector string like: AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
        Leave empty for interactive builder guide.
        """
        from bb_engines import CVSS31Calculator
        calc = CVSS31Calculator()
        if not vector:
            return calc.interactive_build()
        result = calc.calculate(vector)
        return calc.format_report(result)

    # ── GitHub Secret Leakage Recon ──────────────────────────────────────────

    def github_recon(self, domain: str) -> str:
        """
        Search public GitHub repos for secrets, passwords, and API keys
        related to a target domain. Set GITHUB_TOKEN env var for full rate limit.
        """
        from bb_engines import GitHubReconEngine
        return GitHubReconEngine().recon(domain)

    # ── CRLF Probe ────────────────────────────────────────────────────────────

    def probe_crlf(self, url: str, param: str = None) -> str:
        """Test a URL for CRLF / HTTP response splitting injection."""
        from bb_engines import CRLFProbe
        probe = CRLFProbe()
        findings = probe.probe(url, param)
        if findings:
            for f in findings:
                self.add_finding(
                    url=f["url"], severity="medium",
                    title=f"CRLF Injection: {f.get('type','?')}",
                    description=f["message"],
                )
        return probe.format_report(findings)

    # ── Prototype Pollution Probe ─────────────────────────────────────────────

    def probe_prototype_pollution(self, url: str) -> str:
        """Test a URL for JavaScript prototype pollution via GET parameters."""
        from bb_engines import PrototypePollutionProbe
        probe = PrototypePollutionProbe()
        findings = probe.probe(url)
        if findings:
            for f in findings:
                self.add_finding(
                    url=f["url"], severity="high",
                    title="Prototype Pollution",
                    description=f["message"],
                )
        return probe.format_report(findings)

    # ── Blind XSS ────────────────────────────────────────────────────────────

    def probe_blind_xss(self, url: str, param: str, wait_seconds: int = 10) -> str:
        """Inject blind XSS payloads and wait for Interactsh OOB callback."""
        from bb_engines import BlindXSSEngine
        engine = BlindXSSEngine()
        result = engine.probe(url, param, wait_seconds)
        if result.get("confirmed"):
            self.add_finding(
                url=url, severity="high",
                title=f"Blind XSS in parameter '{param}'",
                description=result.get("message", ""),
            )
        return engine.format_report(result)

