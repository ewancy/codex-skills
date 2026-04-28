# 安装与使用说明

## 适用对象

适用于需要在 Codex 中复用产品部需求编写、需求知识库、禅道流转和 HTML 原型生成流程的成员。

## 前置条件

- 已安装 Codex 桌面端或 Codex CLI。
- 本机可以访问 GitHub 私有仓库 `ewancy/codex-skills`。
- 如需操作禅道，需先完成禅道 CLI 登录或配置禅道账号环境变量。

## 首次安装

克隆仓库：

```bash
git clone https://github.com/ewancy/codex-skills.git
cd codex-skills
```

安装 Codex 技能：

```bash
mkdir -p ~/.codex/skills ~/.agents/skills
rsync -a skills/ ~/.codex/skills/
rsync -a agents-skills/ ~/.agents/skills/
```

安装后重启 Codex，让技能被重新加载。

## 更新本地技能

进入本仓库并拉取最新版本：

```bash
cd codex-skills
git pull --ff-only
rsync -a skills/ ~/.codex/skills/
rsync -a agents-skills/ ~/.agents/skills/
```

更新后建议重启 Codex。

## 禅道配置

`zentao` 相关技能会读取禅道 CLI 或环境变量中的配置。常见方式：

```bash
zentao login --zentao-url="https://zentao.example.com/zentao" --zentao-account="your-account" --zentao-password="your-password"
zentao whoami
```

也可以使用环境变量：

```bash
export ZENTAO_URL="https://zentao.example.com/zentao"
export ZENTAO_ACCOUNT="your-account"
export ZENTAO_PASSWORD="your-password"
```

注意：不要把真实账号、密码、Token 或 Cookie 写入本仓库。

## 常用触发方式

在 Codex 中可以直接描述目标，也可以点名技能：

```text
帮我基于这个禅道需求建立需求知识库
```

```text
$requirement-prd-writer 基于知识库写一份需求说明
```

```text
帮我把这份 PRD 提交到禅道，需求来源客户，版本号 AI伴侣 3.4.0
```

```text
从这个禅道需求创建主任务和前端/后端/测试子任务
```

```text
基于这份需求说明生成可交互 HTML 原型
```

## 推荐使用流程

### 新需求从 0 到禅道

1. `requirement-kb-creator`：建立需求知识库。
2. `requirement-prd-writer`：生成 PRD/需求说明。
3. `html-interactive-prototype`：按需生成 HTML 交互原型。
4. `zentao-requirement-submit`：提交到禅道。
5. `zentao-task-creator`：从禅道需求创建主任务和子任务。

### 已有需求变更

1. `requirement-kb-updater`：同步最新事实到知识库。
2. `requirement-prd-writer`：更新本地需求说明。
3. `zentao-story-change`：变更已有禅道需求。
4. `zentao-task-creator`：按需补充或调整任务。

### 未下单需求处理

1. `zentao-unordered-demands`：查询未下单需求。
2. 选定需求后进入知识库、PRD、提交或任务创建流程。

## 目录说明

```text
agents-skills/
  zentao/
    SKILL.md
skills/
  requirement-kb-creator/
  requirement-kb-updater/
  requirement-prd-writer/
  html-interactive-prototype/
  zentao-requirement-submit/
  zentao-story-change/
  zentao-task-creator/
  zentao-unordered-demands/
```

## 维护和提交流程

修改本地技能后，在仓库中同步并提交：

```bash
rsync -a ~/.codex/skills/requirement-prd-writer/ skills/requirement-prd-writer/
git status
git add .
git commit -m "Update requirement PRD writer skill"
git push
```

如果修改的是 agent 技能：

```bash
rsync -a ~/.agents/skills/zentao/ agents-skills/zentao/
git status
git add .
git commit -m "Update zentao skill"
git push
```

提交前检查不要包含敏感信息或临时产物：

```bash
rg -n -i "password|token|cookie|secret|authorization|bearer" .
git status --short
```
