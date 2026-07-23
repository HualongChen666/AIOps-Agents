#!/usr/bin/env python3
"""Local GitLab API search helper for the gitlab-search skill.

This script acts as a fallback when the current agent session does not expose
`mcp_call_tool`. It reads the GitLab token from Devin's MCP config and calls
the gitlab.dell.com API directly.
"""

import argparse
import base64
import json
import os
import ssl
import sys
import urllib.parse
import urllib.request


def load_credential():
    """Load GitLab token and API URL from the Devin MCP config."""
    config_path = os.path.expandvars(r"%APPDATA%\devin\mcp_config.json")
    if not os.path.exists(config_path):
        config_path = r"C:\AIOps_Agent_bak\.devin\config.local.json"
    if not os.path.exists(config_path):
        raise FileNotFoundError("Cannot find GitLab token config")

    with open(config_path, encoding="utf-8") as f:
        cfg = json.load(f)
    env = cfg.get("mcpServers", {}).get("gitlab", {}).get("env", {})
    token = env.get("GITLAB_PERSONAL_ACCESS_TOKEN", "")
    url = env.get("GITLAB_API_URL", "https://gitlab.dell.com/api/v4")
    if not token:
        raise RuntimeError("GITLAB_PERSONAL_ACCESS_TOKEN is empty")
    return token, url.rstrip("/")


def build_ssl_context():
    """Disable certificate validation for internal self-signed GitLab certs."""
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def api_get(token, api_url, path, params=None):
    """Make a GET request to the GitLab API."""
    query = urllib.parse.urlencode(params or {})
    url = f"{api_url}{path}?{query}" if query else f"{api_url}{path}"
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "User-Agent": "aiops-gitlab-search/1.0",
        },
    )
    with urllib.request.urlopen(req, context=build_ssl_context(), timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def format_project(item):
    """Format a project search result."""
    lines = [
        f"- {item.get('name_with_namespace')} ({item.get('path_with_namespace')})",
        f"  web_url: {item.get('web_url')}",
    ]
    branch = item.get("default_branch")
    if branch:
        lines.append(f"  default_branch: {branch}")
    desc = (item.get("description") or "").strip()
    if desc:
        lines.append(f"  description: {desc[:120]}")
    lines.append("")
    return "\n".join(lines)


def format_blob(item):
    """Format a code/blob search result."""
    lines = [
        f"- file: {item.get('filename')} / {item.get('path')}",
        f"  project_id: {item.get('project_id')}",
        f"  ref: {item.get('ref')}",
    ]
    data = item.get("data") or ""
    if data:
        preview = data.strip().splitlines()[0][:120]
        lines.append(f"  preview: {preview}")
    lines.append("")
    return "\n".join(lines)


def format_issue(item):
    """Format an issue search result."""
    lines = [
        f"- #{item.get('iid')} {item.get('title')} ({item.get('state')})",
        f"  project: {item.get('project_id')}",
    ]
    web_url = item.get("web_url") or item.get("_links", {}).get("self", "")
    if web_url:
        lines.append(f"  url: {web_url}")
    desc = (item.get("description") or "").strip()
    if desc:
        lines.append(f"  description: {desc[:120]}")
    labels = item.get("labels") or []
    if labels:
        lines.append(f"  labels: {', '.join(str(label) for label in labels)}")
    lines.append("")
    return "\n".join(lines)


def cmd_search(args):
    """Run a project/blob/issue search."""
    token, api_url = load_credential()
    scope = args.scope or "projects"
    per_page = args.limit or args.per_page

    if scope == "projects":
        params = {"search": args.query, "per_page": per_page}
        results = api_get(token, api_url, "/projects", params)
        print(f"Found {len(results)} projects for '{args.query}':\n")
        for item in results:
            print(format_project(item), end="")
        return 0

    params = {"search": args.query, "per_page": per_page}
    if args.project:
        project_id = urllib.parse.quote(args.project, safe="")
        path = f"/projects/{project_id}/search"
        params["scope"] = scope
    else:
        path = "/search"
        params["scope"] = scope

    results = api_get(token, api_url, path, params)
    print(f"Found {len(results)} {scope} results for '{args.query}':\n")
    if scope == "blobs":
        for item in results:
            print(format_blob(item), end="")
    elif scope == "issues":
        for item in results:
            print(format_issue(item), end="")
    else:
        for item in results:
            print(json.dumps(item, ensure_ascii=False, indent=2)[:500])
    return 0


def cmd_file(args):
    """Fetch and decode a single file from a GitLab project."""
    token, api_url = load_credential()
    project_id = urllib.parse.quote(args.project, safe="")
    file_path = urllib.parse.quote(args.path.strip("/"), safe="")
    ref = args.ref or "HEAD"
    result = api_get(
        token,
        api_url,
        f"/projects/{project_id}/repository/files/{file_path}",
        {"ref": ref},
    )
    content = result.get("content", "")
    if content:
        decoded = base64.b64decode(content).decode("utf-8", errors="replace")
        print(decoded)
    else:
        print("No content returned", file=sys.stderr)
        return 1
    return 0


def main():
    parser = argparse.ArgumentParser(description="GitLab search helper for gitlab-search skill")
    sub = parser.add_subparsers(dest="command", required=True)

    search_parser = sub.add_parser("search", help="Search projects, code or issues")
    search_parser.add_argument("query")
    search_parser.add_argument(
        "--scope",
        choices=["projects", "blobs", "issues"],
        default="projects",
    )
    search_parser.add_argument("--project", help="Project path (scope blobs/issues)")
    search_parser.add_argument("--limit", "--per-page", dest="limit", type=int, default=10)

    file_parser = sub.add_parser("file", help="Read a file from a project")
    file_parser.add_argument("project", help="Project path, e.g. Hualong_Chen/repo")
    file_parser.add_argument("path", help="File path in repository")
    file_parser.add_argument("--ref", default="HEAD")

    args = parser.parse_args()
    try:
        if args.command == "search":
            return cmd_search(args)
        if args.command == "file":
            return cmd_file(args)
    except Exception as exc:
        print(f"GitLab API error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
