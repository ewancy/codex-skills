---
name: zentao-unordered-demands
description: Query customized ZenTao/禅道 demand-pool pages for 当前用户/指定账号的未下单需求. Use when the user asks to 查询未下单需求、还未下单的需求、按禅道链接筛选未下单、按版本号查询未下单, or directly query all unsubmitted/unordered demand-pool items for the current ZenTao account.
---

# ZenTao Unordered Demands

## Overview

Use this skill to query the customized ZenTao `pool` demand page for rows whose state is `未下单`. It supports:

- A full pool browse URL from the user.
- A specific version id, such as `412`.
- No explicit version/link: scan the visible version filters for the current saved ZenTao account as PM, then deduplicate results.

The bundled script logs into the ZenTao web UI with the saved `zentao` config, fetches the pool table, and extracts structured rows.

## Prerequisites

- Confirm `zentao whoami` works when needed. The script reads `~/.config/zentao/config.toml` by default, or `ZENTAO_URL`, `ZENTAO_ACCOUNT`, and `ZENTAO_PASSWORD`.
- If network is sandboxed and requests fail with DNS or connection errors, rerun the script with approval/escalation.
- Do not print passwords or config file contents in the final answer.

## Quick Commands

Run the script from this skill directory:

```bash
python3 /Users/bsg/.codex/skills/zentao-unordered-demands/scripts/query_unordered_demands.py --json
```

### Query From A User-Provided Link

Use the full URL exactly as provided. The script preserves its filters but forces `status=1` (`未下单`).

```bash
python3 /Users/bsg/.codex/skills/zentao-unordered-demands/scripts/query_unordered_demands.py \
  --url 'https://cd.baa360.cc:20088/index.php?m=pool&f=browse&version=412&mode=3&pm=cheny&t=html' \
  --json
```

### Query By Version Id

Use `--version` when the user provides only a version number.

```bash
python3 /Users/bsg/.codex/skills/zentao-unordered-demands/scripts/query_unordered_demands.py --version 412 --json
```

### Query Current Account Across All Versions

Omit `--url` and `--version`. The script first opens the pool page with the current saved ZenTao account as PM, discovers available version filters, queries each version with `status=1`, then deduplicates demand IDs. This is necessary because this customized ZenTao page treats a blank `version` as “no version selected”, not as “all versions”.

```bash
python3 /Users/bsg/.codex/skills/zentao-unordered-demands/scripts/query_unordered_demands.py --json
```

### Query All PMs Allowed By The Page

Only use this if the user explicitly asks for all accounts instead of the current account.

```bash
python3 /Users/bsg/.codex/skills/zentao-unordered-demands/scripts/query_unordered_demands.py --all-accounts --json
```

## Output Guidance

Summarize results as a compact table with these columns when available: `ID`, `版本`, `需求名称`, `类别`, `状态`, `PHP组`, `皮肤`, `优先级`, `提出人`, `交付时间`, `禅道任务`.

After the table, include `需求描述` for short lists or when the user asks for details. Link each row to `detailUrl` if the environment supports Markdown links.

If count is zero, state the exact filter used: current account, version/link or cross-version scan, projectSearch if present, and `未下单`.

## Downstream Requirement Design

- If the user asks to design or document one of the returned demand-pool rows, switch to the `zentao-requirement-docs` workflow.
- Pass along the demand-pool `id`, title, description, version, skins, submitter, priority, and detail URL as source material.
- Before drafting, split involved feature points and check/create `功能点/<功能点名称>/<功能点名称>需求知识库.md`.
- Put the new requirement under the primary owning feature point, e.g. `功能点/内链跳转/内链跳转新增锦标赛/`, not a top-level mixed feature directory.
- If implementation choices need product confirmation, list options with descriptions and recommendations before locking the PRD.

## Script Notes

- `--url` preserves query parameters from the provided URL, then forces `status=1`.
- `--version` overrides the URL/default `version` parameter.
- When neither `--url` nor `--version` is provided, blank version is not trusted as all versions; the script scans discovered versions and fills each result with `version`/`versionName`.
- `--project` sets `projectSearch` when the user asks for a project-specific filter.
- `--single-page` disables automatic cross-version scanning and returns only the currently requested page.
- `--save-html /tmp/file.html` is available for debugging parser issues.
- `--json` is preferred for reliable downstream summarization.
