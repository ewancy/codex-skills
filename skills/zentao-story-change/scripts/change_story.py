#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Change an existing ZenTao story from a local PRD Markdown file.

中文说明：把本地 PRD Markdown 同步到已有禅道需求，并通过禅道“变更”表单生成正式变更记录。
"""
from __future__ import annotations

import argparse
import html
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from dataclasses import dataclass
from http.cookiejar import CookieJar
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    tomllib = None


@dataclass
class Config:
    url: str
    account: str
    password: str


# 读取禅道登录配置：优先环境变量，其次 zentao CLI 保存的本地配置。
def load_config() -> Config:
    url = os.environ.get("ZENTAO_URL")
    account = os.environ.get("ZENTAO_ACCOUNT")
    password = os.environ.get("ZENTAO_PASSWORD")
    cfg_path = Path.home() / ".config" / "zentao" / "config.toml"
    if (not url or not account or not password) and cfg_path.exists():
        raw = cfg_path.read_text(encoding="utf-8")
        if tomllib:
            data = tomllib.loads(raw)
        else:
            data = dict(re.findall(r'^(zentaoUrl|zentaoAccount|zentaoPassword)\s*=\s*"(.*)"\s*$', raw, flags=re.M))
        url = url or data.get("zentaoUrl")
        account = account or data.get("zentaoAccount")
        password = password or data.get("zentaoPassword")
    if not url or not account or not password:
        raise SystemExit("Missing ZenTao credentials: set env vars or login with zentao CLI first.")
    return Config(url=url.rstrip("/"), account=account, password=password)


# 处理 Markdown 行内格式：反引号字段、加粗文本等。
def inline(text: str) -> str:
    text = html.escape(text.strip())
    text = re.sub(r"`([^`]+)`", r"<code>\1</code>", text)
    text = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", text)
    return text


# 将精简 Markdown 转成禅道编辑器可识别的基础 HTML。
def parse_table_align(separator_line: str) -> list[str]:
    """解析 Markdown 表格分隔行的对齐方式。

    中文说明：禅道编辑器可以直接展示 HTML 表格，因此这里把 `:---`、`---:`、
    `:---:` 转成对应的 `text-align`，避免表格退化成纯文本。
    """
    aligns: list[str] = []
    for cell in separator_line.strip().strip("|").split("|"):
        token = cell.strip()
        if token.startswith(":") and token.endswith(":"):
            aligns.append("center")
        elif token.endswith(":"):
            aligns.append("right")
        elif token.startswith(":"):
            aligns.append("left")
        else:
            aligns.append("")
    return aligns


def is_table_separator(line: str) -> bool:
    cells = [c.strip() for c in line.strip().strip("|").split("|")]
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", c or "") for c in cells)


def render_table(rows: list[list[str]], aligns: list[str]) -> str:
    """把 Markdown 表格渲染为规范 HTML 表格。

    中文说明：提交禅道需求时必须保留表格结构，不能把整份 PRD 放进 `<pre>`。
    这里输出 `<thead>`/`<tbody>`，让禅道详情页以真实表格展示“改动范围”
    “验收标准”“版本记录”等内容。
    """
    if not rows:
        return ""
    col_count = max(len(row) for row in rows)

    def cell_style(index: int) -> str:
        align = aligns[index] if index < len(aligns) else ""
        return f' style="text-align:{align};"' if align else ""

    def normalize(row: list[str]) -> list[str]:
        return row + [""] * (col_count - len(row))

    header = normalize(rows[0])
    body_rows = [normalize(row) for row in rows[1:]]
    html_rows = [
        '<table border="1" cellspacing="0" cellpadding="6" style="border-collapse:collapse; width:100%;">',
        "<thead>",
        "<tr>" + "".join(f"<th{cell_style(i)}>{inline(cell)}</th>" for i, cell in enumerate(header)) + "</tr>",
        "</thead>",
        "<tbody>",
    ]
    for row in body_rows:
        html_rows.append("<tr>" + "".join(f"<td{cell_style(i)}>{inline(cell)}</td>" for i, cell in enumerate(row)) + "</tr>")
    html_rows.extend(["</tbody>", "</table>"])
    return "\n".join(html_rows)


def md_to_html(md: str) -> str:
    out: list[str] = []
    in_ul = False
    table_rows: list[list[str]] = []
    table_aligns: list[str] = []

    # 关闭列表标签，避免生成不完整 HTML。
    def close_ul() -> None:
        nonlocal in_ul
        if in_ul:
            out.append("</ul>")
            in_ul = False

    # 关闭表格并输出规范 HTML，确保禅道详情页按表格显示。
    def flush_table() -> None:
        nonlocal table_rows, table_aligns
        if table_rows:
            out.append(render_table(table_rows, table_aligns))
            table_rows = []
            table_aligns = []

    for raw in md.splitlines():
        line = raw.rstrip()
        if not line.strip():
            close_ul(); flush_table(); continue
        if line.startswith("|") and line.endswith("|"):
            close_ul()
            if is_table_separator(line):
                table_aligns = parse_table_align(line)
                continue
            table_rows.append([c.strip() for c in line.strip("|").split("|")])
            continue
        flush_table()
        if line.startswith("#"):
            close_ul()
            level = min(len(line) - len(line.lstrip("#")), 4)
            out.append(f"<h{level}>{inline(line[level:])}</h{level}>")
        elif line.lstrip().startswith("- "):
            if not in_ul:
                out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(line.lstrip()[2:])}</li>")
        else:
            close_ul()
            out.append(f"<p>{inline(line)}</p>")
    close_ul(); flush_table()
    return "\n".join(out)


def auto_verify(md: str) -> str:
    # 自动生成禅道“注意事项”；如需精确口径，可用 --verify-file 传入人工编写版本。
    title = next((l.lstrip("# ").strip() for l in md.splitlines() if l.startswith("# ")), "需求")
    text = re.sub(r"[#`*|>-]", "", md)
    has_frontend = any(k in text for k in ["前端", "PC", "H5", "客户端", "展示"])
    has_backend = any(k in text for k in ["后端", "后台", "配置", "接口", "保存", "校验"])
    scope = []
    if has_backend: scope.append("后台配置/校验")
    if has_frontend: scope.append("前端展示/交互")
    scope_text = "、".join(scope) or "需求描述中的相关模块"
    items = [
        ("影响范围", f"影响{scope_text}；具体以《{title}》需求描述中的前端改动、后端改动和验收标准为准。"),
        ("需求边界", "仅变更本次 PRD 明确列出的改动项；不包含/非改动范围内的旧逻辑不做调整。"),
        ("是否存在新旧版本兼容问题", "是。需按 PRD 中兼容要求验证历史配置、旧数据或旧展示逻辑。"),
        ("是否需要性能测试", "否。若研发实现涉及高频接口、大数据量或视频加载性能改造，再另行评估。"),
        ("是否需要脚本", "否。若研发实现涉及数据迁移、字段初始化或历史数据修复，再另行评估。"),
    ]
    return "".join(
        f'<p style="border-left: 3px solid #3b82f6; padding-left: 8px; margin: 2px 0;">【{html.escape(k)}】{html.escape(v)}</p>'
        for k, v in items
    )


def unescape_textarea(value: str) -> str:
    return html.unescape(value or "")


# 统一封装 HTTP 请求，复用同一个 cookie jar 保持禅道登录态。
def request(opener, url: str, data=None, headers=None):
    req = urllib.request.Request(url, data=data, headers=headers or {})
    return opener.open(req, timeout=30)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--story-id", required=True, type=int)
    ap.add_argument("--prd", required=True, help="Local Markdown PRD path")
    ap.add_argument("--comment", default="按最新 PRD 同步变更需求。")
    ap.add_argument("--verify-file", help="HTML or text file for ZenTao verify/注意事项")
    ap.add_argument("--verify-auto", action="store_true", help="Generate standard verify block from PRD")
    ap.add_argument("--custom-demand-spec", default=None, help="Optional replacement for customDemandSpec")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    cfg = load_config()
    md = Path(args.prd).read_text(encoding="utf-8")
    spec_html = md_to_html(md)
    if args.verify_file:
        verify_html = Path(args.verify_file).read_text(encoding="utf-8")
    elif args.verify_auto:
        verify_html = auto_verify(md)
    else:
        verify_html = ""

    # 使用传统表单登录，因为 story change 需要 cookie 会话而不是纯 REST token。
    jar = CookieJar()
    opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    login_url = f"{cfg.url}/index.php?m=user&f=login"
    request(opener, login_url).read()
    login_data = urllib.parse.urlencode({"account": cfg.account, "password": cfg.password, "keepLogin": "on"}).encode()
    request(opener, login_url, data=login_data, headers={"Content-Type": "application/x-www-form-urlencoded", "Referer": login_url}).read()

    # 打开“变更需求”页面，提取 lastEditedDate 和 uid/kuid 等隐藏字段。
    change_url = f"{cfg.url}/index.php?m=story&f=change&storyID={args.story_id}"
    page = request(opener, change_url, headers={"Referer": f"{cfg.url}/index.php?m=story&f=view&storyID={args.story_id}"}).read().decode("utf-8", "replace")
    last = re.search(r"name='lastEditedDate'[^>]*value='([^']*)'", page)
    kuid = re.search(r"var kuid = '([^']+)'", page)
    title = re.search(r"name='title'[^>]*value='([^']*)'", page)
    custom = re.search(r"<textarea name='customDemandSpec'[^>]*>([\s\S]*?)</textarea>", page)
    if not last or not kuid or not title:
        raise SystemExit("Could not parse ZenTao change form; check login, permissions, and story ID.")

    # 提交字段：保留标题和 customDemandSpec，替换 spec/verify，并写入变更备注。
    form = {
        "title": html.unescape(title.group(1)),
        "color": "",
        "customDemandSpec": args.custom_demand_spec if args.custom_demand_spec is not None else unescape_textarea(custom.group(1) if custom else ""),
        "spec": spec_html,
        "verify": verify_html,
        "comment": args.comment,
        "needNotReview[]": "0",
        "lastEditedDate": last.group(1),
        "uid": kuid.group(1),
    }

    safe = {"story_id": args.story_id, "title": form["title"], "lastEditedDate": form["lastEditedDate"], "uid_present": bool(form["uid"]), "spec_chars": len(spec_html), "verify_chars": len(verify_html), "dry_run": args.dry_run}
    if args.dry_run:
        print(json.dumps(safe, ensure_ascii=False, indent=2))
        return 0

    # 禅道表单使用 multipart/form-data，手动组装可避免引入额外依赖。
    boundary = "---------------------------codexzentao"
    body = bytearray()
    for k, v in form.items():
        body.extend(f"--{boundary}\r\n".encode())
        body.extend(f'Content-Disposition: form-data; name="{k}"\r\n\r\n'.encode())
        body.extend(str(v).encode("utf-8"))
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    res_text = request(opener, change_url, data=bytes(body), headers={"Content-Type": f"multipart/form-data; boundary={boundary}", "Referer": change_url}).read().decode("utf-8", "replace")
    ok = "保存成功" in res_text or "story&f=view" in res_text or "parent.location" in res_text or "self.location" in res_text
    safe["submitted"] = ok
    safe["response_preview"] = re.sub(r"<[^>]+>", " ", res_text)[:200]
    print(json.dumps(safe, ensure_ascii=False, indent=2))
    return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
