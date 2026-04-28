# 使用说明

本文说明产品部 Codex 技能的使用场景、推荐流程和常用提示词。安装步骤见 [`INSTALL.md`](INSTALL.md)。

## 技能分组

### 需求知识库

- `requirement-kb-creator`：创建新的需求知识库。
- `requirement-kb-updater`：更新已有需求知识库。

适用场景：

- 从禅道需求、任务、Bug、附件或备注沉淀知识库。
- 从本地 Markdown、Word、PDF、Excel、截图、原型或会议记录沉淀知识库。
- 把用户口头补充、测试反馈、方案变更同步到已有知识库。

常用提示词：

```text
帮我基于这个禅道需求建立需求知识库
```

```text
基于这份本地需求文档更新现有需求知识库，并补充版本变更记录
```

### PRD / 需求说明

- `requirement-prd-writer`：编写或更新中文 PRD/需求说明。

使用规则：

- 正式写 PRD 前先检查是否存在需求知识库。
- 需要先输出待确认问题，等用户确认后再输出写作方案。
- 写作方案确认后，才生成或更新正式需求说明。

常用提示词：

```text
基于这个需求知识库写一份需求说明
```

```text
更新这份需求说明，把最新规则补进去
```

### HTML 交互原型

- `html-interactive-prototype`：基于 PRD、知识库、截图或现有页面生成可交互 HTML 原型/demo。

适用场景：

- 需要给研发、测试或业务确认交互流程。
- 需要把后台配置、前端页面、弹窗、列表筛选等流程做成可点击 demo。
- 需要根据已有页面截图或当前 UI 风格生成原型。

常用提示词：

```text
基于这份需求说明生成一个可交互 HTML 原型
```

```text
按照现有页面风格，把这个后台配置流程做成 htmldemo
```

### 禅道需求流转

- `zentao`：禅道 CLI 通用查询和操作能力。
- `zentao-requirement-submit`：提交本地 PRD 到禅道，创建或更新需求。
- `zentao-story-change`：变更已有禅道需求。
- `zentao-task-creator`：从已有需求创建主任务和子任务。
- `zentao-unordered-demands`：查询未下单需求。

常用提示词：

```text
帮我把这份 PRD 提交到禅道，需求来源客户，版本号 AI伴侣 3.4.0
```

```text
把这个本地 PRD 同步变更到已有禅道需求 storyID 1234
```

```text
从这个禅道需求创建主任务和前端/后端/测试子任务
```

```text
查询我当前账号还未下单的需求
```

## 推荐端到端流程

### 新需求

1. 收集输入：禅道链接、本地文档、截图、原型或用户描述。
2. 创建知识库：使用 `requirement-kb-creator`。
3. 编写 PRD：使用 `requirement-prd-writer`，完成问题确认和方案确认。
4. 制作原型：如需 demo，使用 `html-interactive-prototype`。
5. 提交禅道：使用 `zentao-requirement-submit`。
6. 创建任务：使用 `zentao-task-creator`。

### 需求变更

1. 更新知识库：使用 `requirement-kb-updater`。
2. 更新 PRD：使用 `requirement-prd-writer`。
3. 同步禅道：使用 `zentao-story-change`。
4. 调整任务：需要时使用 `zentao-task-creator`。

### 未下单需求

1. 查询未下单：使用 `zentao-unordered-demands`。
2. 选定需求：确认产品、版本、来源、模块和负责人。
3. 后续处理：进入知识库、PRD、禅道提交或任务创建流程。

## 使用注意事项

- 不要在对话、文档或提交中暴露账号、密码、Token、Cookie。
- 涉及禅道提交或变更时，先确认产品、版本、需求来源、模块、执行和指派人。
- 涉及任务创建时，先确认是否需要后端、前端、测试、美术子任务。
- 平台部、AI 项目等不同项目的负责人和子类型规则，以技能内最新说明为准。
- 生成 PRD 或原型前，优先复用已有知识库、截图和当前页面资料。

## 维护建议

- 每次流程规则变化后，同步更新对应技能和本说明。
- 修改技能后先在本地跑一遍真实或脱敏案例。
- 提交前执行敏感信息扫描：

```bash
rg -n -i "password|token|cookie|secret|authorization|bearer" .
```
