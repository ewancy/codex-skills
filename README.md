# 产品部 Codex 技能管理

本仓库用于版本管理产品部在 Codex 中沉淀的本地技能，聚焦需求知识库、PRD 编写、禅道需求/任务流转，以及基于需求生成 HTML 交互原型。

## 当前技能范围

| 技能 | 路径 | 主要用途 |
| --- | --- | --- |
| `zentao` | `agents-skills/zentao` | 禅道 CLI 通用能力，支持查询和操作需求、任务、Bug、项目、执行、版本、用户等。 |
| `requirement-kb-creator` | `skills/requirement-kb-creator` | 从禅道、本地文档、截图、原型、会议记录或用户描述创建需求知识库。 |
| `requirement-kb-updater` | `skills/requirement-kb-updater` | 更新已有需求知识库，保留结构和版本变更记录。 |
| `requirement-prd-writer` | `skills/requirement-prd-writer` | 编写或更新中文 PRD/需求说明，要求先完成知识库、待确认问题和写作方案确认。 |
| `html-interactive-prototype` | `skills/html-interactive-prototype` | 基于 PRD、知识库、截图或现有页面生成可交互 HTML 原型/demo。 |
| `zentao-requirement-submit` | `skills/zentao-requirement-submit` | 将本地 PRD/需求 Markdown 提交到禅道，创建或更新需求并上传附件。 |
| `zentao-story-change` | `skills/zentao-story-change` | 从本地 PRD 或需求 Markdown 变更已有禅道需求。 |
| `zentao-task-creator` | `skills/zentao-task-creator` | 从已有禅道需求创建产品主任务和后端/前端/测试/美术子任务。 |
| `zentao-unordered-demands` | `skills/zentao-unordered-demands` | 查询当前用户或指定账号的禅道未下单需求。 |

## 推荐工作流

1. 建立或更新需求知识库：使用 `requirement-kb-creator` 或 `requirement-kb-updater`。
2. 编写需求说明：使用 `requirement-prd-writer`，先确认问题口径和写作方案。
3. 制作交互原型：需要 HTML demo 时使用 `html-interactive-prototype`。
4. 提交禅道需求：使用 `zentao-requirement-submit`。
5. 变更已有需求：使用 `zentao-story-change`。
6. 创建主任务和子任务：使用 `zentao-task-creator`。
7. 查询未下单需求：使用 `zentao-unordered-demands`。

## 安装

详见 [`INSTALL.md`](INSTALL.md)。

## 使用说明

详见 [`USAGE.md`](USAGE.md)。

## 维护规范

- 修改技能前先在本地验证完整流程，避免只改文案不验证命令。
- 不要提交账号、密码、Token、Cookie、禅道登录态或临时导出文件。
- 不要提交本地业务需求文档、禅道附件、截图产物和 `.playwright-mcp` 临时文件。
- 新增技能时，必须包含清晰的触发场景、前置条件、执行步骤、失败处理和最终回复规范。

## 未纳入范围

以下本地技能或文件不纳入本仓库：

- `产品部AI技能-0427.zip`
- `extract-axure-data`
- `extract-page-data`
- `genie-editor-client`
- `genie-editor-workflow`
- `clone-page`
- `generate-theme`
- `react-to-axure`
- `react-to-figma-make`
- `mcp-installer`
- `codex-primary-runtime/slides`
- `codex-primary-runtime/spreadsheets`
