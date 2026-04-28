---
name: zentao-story-change
description: Update or change an existing ZenTao/禅道 story from a local PRD or requirement Markdown. Use when the user asks to 变更禅道需求, 更新已有需求, 同步本地 PRD 到 story, 修改 storyID, 更新需求描述/验收/注意事项, or gives a ZenTao storyView/storyID URL and wants the original requirement changed rather than creating a new story.
---

# ZenTao Story Change / 禅道已有需求变更

## Core Rule / 核心规则

Update existing stories only. Do not create a new story unless the user explicitly asks.

中文说明：本技能只用于“变更已有禅道需求”，默认不新建需求；除非用户明确说要新建。

Prefer local `zentao` CLI for read/verify and use the bundled script for web-form story changes. Do not use Playwright unless the user explicitly requests browser automation.

中文说明：优先用 `zentao` CLI 读取和复核，用内置脚本提交禅道变更表单；除非用户明确要求浏览器自动化，否则不要用 Playwright。

## Inputs / 输入信息

Collect or infer:

中文说明：执行前需要收集或推断以下信息。

- Story ID: from `storyID=8903`, `story-view-8903`, or user text.
- PRD file: prefer the latest local `...需求说明.md` the user references or the closest matching feature directory.
- Change comment: short, concrete summary of what changed.
- Verify/注意事项: use user-provided text, or generate a concise standard verify block from the PRD.

## Workflow / 标准流程

中文说明：按以下顺序执行，避免直接覆盖需求或误建新需求。

1. Read source PRD and confirm it is the intended latest version.
2. Run `zentao whoami` and `zentao story get --id <id> --json` to confirm access and current story metadata.
3. Convert the PRD Markdown to HTML and submit through ZenTao's `story change` form, not just REST `PUT`, so ZenTao creates a real story version/change record.
4. Preserve story identity: title, product/module/execution links and assignee. Preserve unrelated attachments, but clean old/duplicate/unreferenced generated attachments after the latest PRD and images are synced.
5. Update `spec` from the PRD. Update `verify` with concise 注意事项. Keep `customDemandSpec` unchanged unless the user provides a new background field.
6. Re-read the story with `zentao story get --id <id> --json` and verify key phrases from the new PRD exist in `spec` and 注意事项 exist in `verify`.
7. Final response: include story link, status, version, execution link status, and what was changed. Never print credentials, cookies, or tokens.

## Formatting Rules / 正文格式规则

The changed `spec` must preserve the PRD's visual structure in ZenTao. Do not submit the whole Markdown file inside `<pre>`.

中文说明：变更禅道需求时，正文是给产品、研发、测试直接阅读的；Markdown 表格必须转成禅道可展示的真实 HTML 表格，而不是纯文本。

- Convert headings to HTML headings, lists to HTML lists, and inline code to `<code>`.
- Convert Markdown tables to `<table><thead><tbody>` with `<th>` and `<td>`.
- Preserve table rows for 改动范围、验收标准、版本记录、字段说明等 PRD sections.
- After changing a story, verify `spec` contains `<table` when the source PRD has Markdown tables.
- If `spec` still contains `<pre>` wrapping the PRD or raw Markdown separators such as `| --- |`, treat it as a failed formatting update and resubmit using `scripts/change_story.py`.

## Attachment Reference Rules / 附件引用规则

When syncing a local PRD to ZenTao, the ZenTao `spec` must not contain local prototype paths.

中文说明：本地需求文档可以记录绝对路径方便当前电脑维护，但同步到禅道时，正文必须面向所有研发/测试可读；默认同步最新需求 `.md` 源文件。如果 PRD 有页面截图，默认禅道正文直接显示图片：上传图片附件，并用禅道附件 `webPath` 写入 `<img>`。原型 ZIP、知识库附件仍不上传，除非用户明确要求。

- Replace local prototype references with wording like `需求文档：查看禅道附件 <需求说明>.md`.
- Do not keep `/Users/...`, `/home/...`, `C:\...`, `file://...`, `localhost`, or `127.0.0.1` in ZenTao `spec`.
- If the PRD embeds a local flowchart/image path, default behavior is to show it directly in ZenTao正文: upload the image attachment, read `files[].webPath`, and write `<img src="https://<禅道域名><webPath>" ... />` into `spec`.
- Upload or replace only the latest `.md` requirement source by default; ZenTao may display `.md` as `.txt`, but the content/title should still identify the requirement source. After syncing, delete old requirement-source attachments with the same purpose/version lineage unless the user asks to keep them.
- Do not wrap `<img>` with `<a>` because this ZenTao editor rewrites image links to `/data/upload/...`, which may download on click. For large preview, add a separate `m=file&f=download&fileID=<fileID>&mouse=left` link below the image.
- After changing a story, verify the ZenTao `spec` has no local path and still references the uploaded attachment.

## Attachment Cleanup Rules / 附件清理规则

中文说明：变更已有需求时，经常会多次上传 `.md` 和截图。每次变更完成后都要把附件列表整理干净，只保留当前正文需要的附件。

- 先计算保留清单：最新需求说明 `.md`、正文 `<img src=...>` 引用的图片、正文“点击查看大图”引用的 fileID、用户明确要求保留的其他附件。
- 删除清单包括：旧版需求源文件、旧版截图、重复上传但未被正文引用的图片、临时调试附件、已经被最新正文替代的附件。
- 不删除无法判断用途的历史附件；如附件不是本次需求生成且用途不明，先向用户确认。
- 默认正文需要展示 PRD 页面截图；这些图片附件必须保留，否则图片会失效。只能删除未被最新正文引用的旧图片。
- 删除方式：登录后请求 `/index.php?m=file&f=delete&fileID=<id>&confirm=yes`；删除后重新 `zentao story get --id <id> --json` 复核 `files`。
- 最终回复必须说明附件清理结果；如没有权限删除或删除失败，明确列出残留附件和原因。

## Bundled Script / 内置脚本

Use `scripts/change_story.py` for the fragile ZenTao web-form update.

中文说明：禅道变更表单字段较多，容易遗漏 `lastEditedDate`、`uid/kuid` 等隐藏字段，因此统一使用内置脚本处理。

Typical command:

```bash
python3 /Users/bsg/.codex/skills/zentao-story-change/scripts/change_story.py \
  --story-id 8903 \
  --prd "/path/to/需求说明.md" \
  --comment "按最新 PRD 同步需求描述和注意事项" \
  --verify-auto
```

Dry run without writing:

```bash
python3 /Users/bsg/.codex/skills/zentao-story-change/scripts/change_story.py \
  --story-id 8903 --prd "/path/to/需求说明.md" --verify-auto --dry-run
```

Script behavior:

- Reads credentials from `ZENTAO_URL/ZENTAO_ACCOUNT/ZENTAO_PASSWORD` or `~/.config/zentao/config.toml`.
- Logs in via `/index.php?m=user&f=login` and posts to `/index.php?m=story&f=change&storyID=<id>`.
- Converts basic Markdown headings, bullets, tables, and inline code to HTML; Markdown tables are rendered as real `<table><thead><tbody>` structures.
- Extracts `lastEditedDate` and `uid/kuid` from the change form.
- Preserves `customDemandSpec` unless `--custom-demand-spec` is passed.
- Prints only safe metadata and validation booleans.

## Verify Block Template / 注意事项模板

If `--verify-auto` is not sufficient, write a concise block matching this shape:

```text
【影响范围】影响哪些后台配置、前端页面、接口或旧数据。
【需求边界】本次只改哪些内容；不涉及哪些内容。
【是否存在新旧版本兼容问题】是/否，并说明兼容点。
【是否需要性能测试】是/否，并说明原因。
【是否需要脚本】是/否，并说明原因。
```

## Validation Checklist / 提交后复核

After submitting, verify:

中文说明：提交后必须复核以下内容，确认禅道确实保存了变更。

- `status` remains expected, usually `active`.
- `version` increases after a real change-form submit.
- `executions` still contains the target execution if the original story was linked.
- `spec` contains latest PRD anchors, such as new section names or version record.
- `spec` preserves formatting: no whole-document `<pre>`, Markdown tables become HTML tables, and raw `| --- |` separators are absent.
- `spec` references the `.md` requirement attachment by default and does not contain local paths, temporary local URLs, or download-style image links.
- `verify` contains `影响范围` and `需求边界`.
- Attachment list is clean: only the latest `.md`, currently referenced images, and user-requested extras remain; old/duplicate/unreferenced generated attachments are deleted, while unrelated unknown attachments are preserved unless confirmed removable.

## Failure Handling / 异常处理

- If REST `PUT` appears to update but `version` does not increase or `spec` remains old, use the change form script.
- If the story content displays Markdown tables as plain text, rerun the change script and validate `<table>` exists in `spec`.
- If the story content contains local prototype paths, replace them with “查看需求文档附件” wording and upload only the latest `.md` requirement source unless the user explicitly asks for extra attachments.
- If the change page says the story was edited by someone else, re-fetch the page and retry once with the latest `lastEditedDate`; do not overwrite if content changed unexpectedly.
- If HTML prototype attachments need updating, only zip and upload HTML files when the user explicitly requests uploading the prototype package.
- If duplicate or obsolete attachments remain after a change, delete them with `m=file&f=delete&fileID=<id>&confirm=yes`, then re-read the story to verify the attachment list.


- Current ZenTao strips `data:image/png;base64` from story spec, so inline images without file records are not reliable. Default behavior is to show screenshots directly in ZenTao正文 by uploading image attachments and using their `webPath` in width-constrained `<img>` thumbnails plus separate `mouse=left` preview links.
- Avoid CSS background thumbnails for PRD screenshots because ZenTao may strip `background-size`, causing cropped/incomplete display.

## Skill Writing Note / 技能编写要求

- Any future script or workflow added to this skill should include Chinese comments or Chinese explanations for key steps.
- 中文说明：后续新增或修改技能内容时，关键流程、脚本参数、易错点都要配中文注释，方便团队成员和后续 AI 阅读。
