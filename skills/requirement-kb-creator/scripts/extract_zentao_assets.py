#!/usr/bin/env python3
"""List image/file references from a ZenTao JSON payload saved from `zentao ... --json`."""
from __future__ import annotations
import html, json, re, sys
from pathlib import Path
from typing import Any
IMAGE_RE = re.compile(r"<img[^>]+src=[\"']([^\"']+)[\"']", re.I)
FILE_ID_RE = re.compile(r"fileID=(\d+)|\{(\d+)\.(?:png|jpg|jpeg|gif|webp)\}", re.I)
FIELDS = ("desc", "spec", "verify", "customDemandSpec", "selfTest", "testDemo", "onlineFeedback", "optimizationResults")
def walk_records(obj: Any):
    if isinstance(obj, dict):
        yield obj
        for value in obj.values(): yield from walk_records(value)
    elif isinstance(obj, list):
        for item in obj: yield from walk_records(item)
def main() -> int:
    if len(sys.argv) != 2:
        print("usage: extract_zentao_assets.py /tmp/zentao_payload.json", file=sys.stderr); return 2
    payload = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
    seen = set()
    for record in walk_records(payload.get("result", payload)):
        owner = record.get("id") or record.get("title") or record.get("name") or "unknown"
        for field in FIELDS:
            value = record.get(field)
            if not isinstance(value, str) or not value: continue
            value = html.unescape(value)
            refs = IMAGE_RE.findall(value)
            refs += [m.group(0) for m in FILE_ID_RE.finditer(value) if not m.group(0).startswith("fileID=")]
            for ref in refs:
                file_ids = [x for match in FILE_ID_RE.findall(ref) for x in match if x]
                key = (str(owner), field, ref)
                if key in seen: continue
                seen.add(key)
                print(f"owner={owner}\tfield={field}\tfile_ids={','.join(file_ids) or '-'}\tref={ref}")
    return 0
if __name__ == "__main__": raise SystemExit(main())
