"""
HackerOne Tool — Helper functions for HackerOne platform.
Part of the Ultimate AI Agent Bug Bounty Hunter module.
"""
import os
import logging
from typing import Dict, List, Optional

try:
    import requests
    REQUESTS_OK = True
except ImportError:
    REQUESTS_OK = False

logger = logging.getLogger("HackerOneHunter")

GRAPHQL_URL = "https://hackerone.com/graphql"
API_BASE = "https://api.hackerone.com/v1"

DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; BugBountyResearcher/1.0)",
    "Content-Type": "application/json",
}


def hackerone_fetch_scope(program: str) -> str:
    """Fetch the in-scope assets for a HackerOne program.
    
    Args:
        program (str): The HackerOne program handle (e.g. 'twitter', 'security')
        
    Returns:
        str: A formatted list of in-scope domains and wildcards.
    """
    if not REQUESTS_OK:
        return "❌ requests library not installed"

    payload = {
        "query": """
        query Team_assets($handle: String!) {
          team(handle: $handle) {
            name
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
          }
        }
        """,
        "variables": {"handle": program},
    }
    
    try:
        resp = requests.post(GRAPHQL_URL, json=payload,
                             headers=DEFAULT_HEADERS, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            team = data.get("data", {}).get("team")
            if not team:
                return f"Program '{program}' not found or no public scope."
                
            scopes = team.get("in_scope_assets", {}).get("edges", [])
            if not scopes:
                return f"No public in-scope assets found for '{program}'."
                
            bounty_label = "💰 Offers Bounties" if team.get("offers_bounties") else "✓ No Bounty"
            output = [f"🎯 Target Scope for {team.get('name', program)} — {bounty_label}:"]
            for edge in scopes:
                node = edge["node"]
                bounty = "💰" if node.get("eligible_for_bounty") else "✓"
                output.append(f"  {bounty} [{node.get('asset_type')}] {node.get('asset_identifier')}")
                if node.get("instruction"):
                    output.append(f"     ℹ️  {node['instruction'][:150]}")
            
            return "\n".join(output)
        else:
            return f"Failed to fetch {program}: HTTP {resp.status_code}"
    except Exception as e:
        return f"Error fetching scope: {str(e)}"


def hackerone_list_programs(query: str = "", limit: int = 20) -> List[Dict]:
    """Search and list public HackerOne bug bounty programs.

    Uses 3-tier fallback: GraphQL → REST API (needs H1_API_TOKEN) → curated list.

    Args:
        query (str): Search query (program name filter). Empty = all.
        limit (int): Max programs to return.

    Returns:
        List[Dict]: List of program metadata dicts.
    """
    if not REQUESTS_OK:
        return []

    # Curated popular programs (offline fallback)
    _POPULAR = [
        {"handle": "security", "name": "HackerOne", "offers_bounties": True},
        {"handle": "google_bughunters", "name": "Google Bug Hunters", "offers_bounties": True},
        {"handle": "microsoft", "name": "Microsoft", "offers_bounties": True},
        {"handle": "github", "name": "GitHub", "offers_bounties": True},
        {"handle": "gitlab", "name": "GitLab", "offers_bounties": True},
        {"handle": "shopify", "name": "Shopify", "offers_bounties": True},
        {"handle": "dropbox", "name": "Dropbox", "offers_bounties": True},
        {"handle": "paypal", "name": "PayPal", "offers_bounties": True},
        {"handle": "coinbase", "name": "Coinbase", "offers_bounties": True},
        {"handle": "uber", "name": "Uber", "offers_bounties": True},
        {"handle": "twitter", "name": "Twitter (X)", "offers_bounties": True},
        {"handle": "cloudflare", "name": "Cloudflare", "offers_bounties": True},
        {"handle": "slack", "name": "Slack", "offers_bounties": True},
        {"handle": "automattic", "name": "Automattic (WordPress)", "offers_bounties": True},
        {"handle": "snapchat", "name": "Snapchat", "offers_bounties": True},
    ]

    # Tier 1: Try GraphQL
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
                submission_state
                currency
                minimum_bounty_table_value
                maximum_bounty_table_value
              }
            }
          }
        }
        """,
        "variables": {"query": query, "first": limit},
    }
    try:
        resp = requests.post(GRAPHQL_URL, json=payload,
                             headers=DEFAULT_HEADERS, timeout=15)
        if resp.status_code == 200:
            edges = resp.json().get("data", {}).get("teams", {}).get("edges", [])
            if edges:
                return [e["node"] for e in edges]
    except Exception as e:
        logger.warning(f"hackerone_list_programs GraphQL: {e}")

    # Tier 2: Try REST API with auth
    api_token = os.environ.get("H1_API_TOKEN", "")
    h1_username = os.environ.get("H1_USERNAME", "")
    if api_token and h1_username:
        try:
            resp = requests.get(
                f"{API_BASE}/hackers/programs",
                auth=(h1_username, api_token),
                params={"page[size]": limit},
                headers={"Accept": "application/json"},
                timeout=15,
            )
            if resp.status_code == 200:
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
                    })
                if programs:
                    return programs
        except Exception as e:
            logger.warning(f"hackerone_list_programs REST: {e}")

    # Tier 3: curated list
    logger.info("Using curated HackerOne programs list (live API requires auth)")
    result = _POPULAR[:]
    if query:
        q = query.lower()
        result = [p for p in result if q in p["handle"].lower() or q in p["name"].lower()]
    return result[:limit]


def hackerone_submit_report(api_token: str, program_handle: str,
                             title: str, description: str,
                             severity: str = "medium",
                             impact: str = "") -> Dict:
    """Submit a vulnerability report to HackerOne via REST API.

    Args:
        api_token (str): HackerOne API token (from H1_API_TOKEN env var)
        program_handle (str): The program handle (e.g. 'twitter')
        title (str): Report title
        description (str): Full vulnerability description / PoC
        severity (str): critical | high | medium | low
        impact (str): Impact statement (optional)

    Returns:
        Dict: {"success": True, "report_id": ..., "url": ...} or {"error": ...}
    """
    if not REQUESTS_OK:
        return {"error": "requests library not installed"}

    sev_map = {
        "critical": "critical", "high": "high",
        "medium": "medium", "low": "low", "info": "none",
    }
    url = f"{API_BASE}/hackers/reports"
    payload = {
        "data": {
            "type": "report",
            "attributes": {
                "team_handle": program_handle,
                "title": title,
                "vulnerability_information": description,
                "impact": impact or f"{severity.upper()} severity finding requiring immediate attention.",
            },
            "relationships": {
                "severity": {
                    "data": {
                        "type": "severity",
                        "attributes": {
                            "rating": sev_map.get(severity.lower(), "medium"),
                        },
                    }
                }
            },
        }
    }
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={
                "Authorization": f"Bearer {api_token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            timeout=20,
        )
        if resp.status_code in [200, 201]:
            data = resp.json().get("data", {})
            return {
                "success": True,
                "report_id": data.get("id"),
                "url": f"https://hackerone.com/reports/{data.get('id')}",
                "title": title,
            }
        return {"error": f"HTTP {resp.status_code}: {resp.text[:400]}"}
    except Exception as e:
        return {"error": str(e)}
