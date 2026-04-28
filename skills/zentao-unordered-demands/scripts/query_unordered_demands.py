#!/usr/bin/env python3
"""Query ZenTao pool rows whose state is 未下单 for the current account.

The script uses the same web login flow as the ZenTao page because the custom
`pool` module is usually not exposed through the standard REST API.
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import parse_qsl, urlencode, urljoin, urlparse, urlunparse
from urllib.request import HTTPCookieProcessor, Request, build_opener
from http.cookiejar import CookieJar

DEFAULT_PARAMS = {
    "m": "pool",
    "f": "browse",
    "version": "",
    "mode": "3",
    "title": "",
    "category": "",
    "isShowMoreSearch": "0",
    "pm": "",
    "tester": "0",
    "status": "1",
    "phpGroup": "",
    "pri": "",
    "desc": "",
    "reviewPool": "",
    "skins": "",
    "deptCenter": "",
    "timeType": "timeType1",
    "begin": "",
    "end": "",
    "orderBy": "",
    "stateType": "",
    "tag": "",
    "onlyWeeklyShow": "0",
    "recTotal": "",
    "recPerPage": "",
    "pageID": "",
    "projectSearch": "",
    "t": "html",
}

CONFIG_RE = re.compile(r'^(zentaoUrl|zentaoAccount|zentaoPassword)\s*=\s*"(.*)"\s*$')


def read_config(path: Optional[str]) -> Dict[str, str]:
    config_path = Path(path or os.environ.get("ZENTAO_CONFIG", "~/.config/zentao/config.toml")).expanduser()
    data: Dict[str, str] = {}
    if config_path.exists():
        for line in config_path.read_text(encoding="utf-8").splitlines():
            match = CONFIG_RE.match(line.strip())
            if match:
                data[match.group(1)] = bytes(match.group(2), "utf-8").decode("unicode_escape")
    env_map = {
        "zentaoUrl": "ZENTAO_URL",
        "zentaoAccount": "ZENTAO_ACCOUNT",
        "zentaoPassword": "ZENTAO_PASSWORD",
    }
    for key, env_name in env_map.items():
        if os.environ.get(env_name):
            data[key] = os.environ[env_name]
    missing = [key for key in env_map if not data.get(key)]
    if missing:
        raise SystemExit(f"Missing ZenTao config: {', '.join(missing)}. Run zentao login first or set env vars.")
    data["zentaoUrl"] = data["zentaoUrl"].rstrip("/")
    return data


def make_url(base_url: str, source_url: Optional[str], version: Optional[str], account: str, all_accounts: bool, project: Optional[str]) -> str:
    if source_url:
        parsed = urlparse(source_url)
        base = urlunparse((parsed.scheme, parsed.netloc, parsed.path, "", "", ""))
        params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    else:
        base = f"{base_url}/index.php"
        params = dict(DEFAULT_PARAMS)

    params.setdefault("m", "pool")
    params.setdefault("f", "browse")
    params.setdefault("mode", "3")
    params.setdefault("t", "html")
    params["status"] = "1"  # 未下单 in this customized pool module.
    if version is not None:
        params["version"] = str(version)
    elif "version" not in params:
        params["version"] = ""
    if not all_accounts:
        params["pm"] = params.get("pm") or account
    elif "pm" in params and not source_url:
        params["pm"] = ""
    if project is not None:
        params["projectSearch"] = project
    params.pop("onlybody", None)
    return base + "?" + urlencode(params, doseq=False)


def replace_query_param(url: str, key: str, value: str) -> str:
    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    params[key] = value
    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, parsed.params, urlencode(params), ""))


def fetch_text(opener, url: str, *, data: Optional[bytes] = None, headers: Optional[Dict[str, str]] = None) -> str:
    req = Request(url, data=data, headers=headers or {})
    with opener.open(req, timeout=30) as resp:
        raw = resp.read()
        content_type = resp.headers.get("Content-Type", "")
        charset_match = re.search(r"charset=([^;]+)", content_type, re.I)
        charset = charset_match.group(1) if charset_match else "utf-8"
        return raw.decode(charset, errors="replace")


def login(config: Dict[str, str]):
    jar = CookieJar()
    opener = build_opener(HTTPCookieProcessor(jar))
    login_url = f"{config['zentaoUrl']}/index.php?m=user&f=login"
    fetch_text(opener, login_url)
    body = urlencode({"account": config["zentaoAccount"], "password": config["zentaoPassword"], "keepLogin": "on"}).encode()
    fetch_text(opener, login_url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": login_url})
    names = {cookie.name for cookie in jar}
    if "za" not in names and "zentaosid" not in names:
        raise SystemExit("ZenTao web login failed: no session cookie received.")
    return opener


@dataclass
class Cell:
    text: str = ""
    links: List[Dict[str, str]] = field(default_factory=list)


class PoolTableParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.in_pool_table = False
        self.in_row = False
        self.in_cell = False
        self.cell_name: Optional[str] = None
        self.cell_text: List[str] = []
        self.cell_links: List[Dict[str, str]] = []
        self.current_attrs: Dict[str, str] = {}
        self.current_cells: Dict[str, Cell] = {}
        self.rows: List[Dict[str, object]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "table" and attrs.get("id") == "poolList":
            self.in_pool_table = True
        if not self.in_pool_table:
            return
        if tag == "tr":
            self.in_row = True
            self.current_attrs = attrs
            self.current_cells = {}
        elif self.in_row and tag == "td":
            self.in_cell = True
            self.cell_name = attrs.get("data-name")
            self.cell_text = []
            self.cell_links = []
        elif self.in_cell and tag == "a" and attrs.get("href"):
            self.cell_links.append({"href": attrs.get("href", ""), "title": attrs.get("title", "")})
        elif self.in_cell and tag == "br":
            self.cell_text.append("\n")

    def handle_data(self, data):
        if self.in_cell:
            self.cell_text.append(data)

    def handle_endtag(self, tag):
        if not self.in_pool_table:
            return
        if tag == "td" and self.in_cell:
            if self.cell_name:
                text = html.unescape("".join(self.cell_text))
                text = re.sub(r"[ \t\r\f\v]+", " ", text)
                text = re.sub(r"\n\s*", "\n", text).strip()
                self.current_cells[self.cell_name] = Cell(text=text, links=self.cell_links)
            self.in_cell = False
            self.cell_name = None
        elif tag == "tr" and self.in_row:
            if self.current_cells:
                self.rows.append({"attrs": self.current_attrs, "cells": self.current_cells})
            self.in_row = False
        elif tag == "table":
            self.in_pool_table = False


class FilterParser(HTMLParser):
    """Extract version choices from the custom pool filter area."""

    def __init__(self):
        super().__init__()
        self.in_version_select = False
        self.in_option = False
        self.option_value = ""
        self.option_text: List[str] = []
        self.versions: List[Dict[str, str]] = []

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "select" and attrs.get("name") == "version":
            self.in_version_select = True
        elif self.in_version_select and tag == "option":
            self.in_option = True
            self.option_value = attrs.get("value", "")
            self.option_text = []
        elif tag == "a" and attrs.get("class") and "poolBrowseVersion" in attrs.get("class", ""):
            value = attrs.get("data-version", "")
            if value:
                self.versions.append({"value": value, "name": ""})

    def handle_data(self, data):
        if self.in_option:
            self.option_text.append(data)
        elif self.versions and not self.versions[-1].get("name"):
            self.versions[-1]["name"] = data.strip()

    def handle_endtag(self, tag):
        if tag == "option" and self.in_option:
            if self.option_value:
                self.versions.append({"value": self.option_value, "name": html.unescape("".join(self.option_text)).strip()})
            self.in_option = False
        elif tag == "select" and self.in_version_select:
            self.in_version_select = False


def extract_versions(page_html: str) -> List[Dict[str, str]]:
    parser = FilterParser()
    parser.feed(page_html)
    seen = set()
    versions = []
    for version in parser.versions:
        value = version.get("value", "")
        if not value or value in seen:
            continue
        seen.add(value)
        versions.append(version)
    return versions


def extract_rows(page_html: str, base_url: str) -> List[Dict[str, object]]:
    parser = PoolTableParser()
    parser.feed(page_html)
    rows = []
    for row in parser.rows:
        attrs: Dict[str, str] = row["attrs"]  # type: ignore[assignment]
        cells: Dict[str, Cell] = row["cells"]  # type: ignore[assignment]
        def txt(name: str) -> str:
            return cells.get(name, Cell()).text
        task_links = []
        for cell_name in ("taskID", "title"):
            for link in cells.get(cell_name, Cell()).links:
                href = link.get("href", "")
                if href:
                    task_links.append({"url": urljoin(base_url, href), "title": link.get("title", "")})
        demand_id = attrs.get("data-id", "")
        rows.append({
            "id": demand_id,
            "detailUrl": urljoin(base_url, f"/index.php?m=pool&f=view&id={demand_id}&onlybody=yes") if demand_id else "",
            "taskID": attrs.get("data-taskid", attrs.get("data-taskID", "")),
            "order": txt("versionOrder"),
            "category": txt("category"),
            "title": txt("title"),
            "description": txt("desc"),
            "status": txt("status"),
            "pm": txt("pm"),
            "tester": txt("tester"),
            "phpGroup": txt("phpGroup"),
            "submitter": txt("submitter"),
            "priority": txt("priority"),
            "review": txt("reviewStory"),
            "skins": txt("skins"),
            "taskOpenedDate": txt("taskOpenedDate"),
            "deliveryDate": txt("deliveryDate"),
            "taskTitle": txt("taskID"),
            "remark": txt("remark"),
            "taskLinks": task_links,
        })
    return rows


def print_table(rows: List[Dict[str, object]], query_url: str):
    print(f"queryUrl: {query_url}")
    print(f"count: {len(rows)}")
    if not rows:
        return
    headers = ["ID", "版本", "序号", "需求名称", "类别", "状态", "PHP组", "皮肤", "优先级", "提出人", "交付", "禅道"]
    print("\t".join(headers))
    for r in rows:
        print("\t".join(str(r.get(k, "")) for k in ["id", "versionName", "order", "title", "category", "status", "phpGroup", "skins", "priority", "submitter", "deliveryDate", "taskTitle"]))


def main() -> int:
    ap = argparse.ArgumentParser(description="Query current ZenTao account's 未下单 demand rows from the custom pool page.")
    ap.add_argument("--url", help="Full ZenTao pool browse URL to reuse; status is forced to 未下单.")
    ap.add_argument("--version", help="Version id, e.g. 412. Overrides or supplies the version query parameter.")
    ap.add_argument("--project", help="Optional projectSearch value. Use empty string to clear when your shell supports it.")
    ap.add_argument("--single-page", action="store_true", help="Do not auto-scan versions when neither --url nor --version is provided.")
    ap.add_argument("--all-accounts", action="store_true", help="Do not force pm=current account; query all PMs allowed by the page/search filters.")
    ap.add_argument("--config", help="Path to zentao config.toml. Defaults to ~/.config/zentao/config.toml.")
    ap.add_argument("--json", action="store_true", help="Output structured JSON.")
    ap.add_argument("--save-html", help="Save the fetched page HTML for debugging.")
    args = ap.parse_args()

    config = read_config(args.config)
    query_url = make_url(config["zentaoUrl"], args.url, args.version, config["zentaoAccount"], args.all_accounts, args.project)
    opener = login(config)
    headers = {"Referer": f"{config['zentaoUrl']}/index.php?m=index&f=index", "X-Requested-With": "XMLHttpRequest"}
    page_html = fetch_text(opener, query_url, headers=headers)
    if args.save_html:
        Path(args.save_html).write_text(page_html, encoding="utf-8")

    scanned_versions: List[Dict[str, str]] = []
    if args.url or args.version or args.single_page:
        rows = extract_rows(page_html, config["zentaoUrl"])
        version_label = args.version or dict(parse_qsl(urlparse(query_url).query, keep_blank_values=True)).get("version", "")
        for row in rows:
            row["version"] = version_label
            row["versionName"] = version_label
    else:
        # A blank version page is not an "all versions" query in this ZenTao customization.
        # Discover visible version filters, query each version, then deduplicate demand IDs.
        versions = extract_versions(page_html)
        rows = []
        seen_ids = set()
        for version in versions:
            version_url = replace_query_param(query_url, "version", version["value"])
            version_html = fetch_text(opener, version_url, headers=headers)
            for row in extract_rows(version_html, config["zentaoUrl"]):
                row_id = str(row.get("id", ""))
                dedupe_key = row_id or f"{version['value']}:{row.get('title', '')}"
                if dedupe_key in seen_ids:
                    continue
                seen_ids.add(dedupe_key)
                row["version"] = version["value"]
                row["versionName"] = version.get("name") or version["value"]
                rows.append(row)
        scanned_versions = versions

    result = {"account": config["zentaoAccount"], "queryUrl": query_url, "scannedVersions": scanned_versions, "count": len(rows), "items": rows}
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print_table(rows, query_url)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
