# Skills 全局索引

> **119 个 skill，按 13 个分类子目录组织。**
> 整合记录：原 196 个 → 合并/去重减 78 → 118 个 → 归入 13 个分类子目录。
> 新增：test-board（测试任务看板生成）。
> 引用路径：`D:\agent-skills\skills\<分类>\<skill名>\SKILL.md`

---

## 目录结构

```
skills/
├── lark/          (29) 飞书/Lark 全套 + 飞书补充工具
├── baoyu/         (16) 宝玉工具集
├── design/        (15) 设计参考 + 前端设计/品味
├── devflow/       (14) 开发流程 + skill 创建 + 输出控制
├── office/        (10) Office/文档/LaTeX/Obsidian/图表
├── business/       (9) 业务/行业/财务/招聘
├── testing/        (8) 测试/质量/用例
├── infra/          (6) 基础设施/环境/框架
├── browser/        (4) 浏览器/自动化
├── mobile/         (2) 移动开发
├── meta/           (2) 元 skill（发现/入门）
├── security/       (1) 安全
├── misc/           (2) 其他
└── SKILLS-INDEX.md 本文件
```

---

## lark/ — 飞书/Lark（29）

### 文档/内容
lark-doc, lark-sheets, lark-base, lark-slides, lark-whiteboard, lark-markdown, lark-drive, lark-wiki

### 通讯
lark-im, lark-mail, lark-contact

### 日程/会议
lark-calendar, lark-vc, lark-vc-agent, lark-minutes, lark-note, lark-event

### 任务/效率
lark-task, lark-okr, lark-approval, lark-attendance

### 应用开发
lark-apps, lark-openapi-explorer, lark-skill-maker

### 工作流编排
lark-workflow-meeting-summary, lark-workflow-standup-report

### 元/共享
lark-shared

### 补充工具（非 lark-cli）
feishu-docx-extractor, feishu-native-kb-export

## baoyu/ — 宝玉工具集（16）

> 活跃上游 github.com/JimLiu/baoyu-skills。baoyu-social-post 已合并不再跟上游，其余保留独立。

### 通用图像引擎
baoyu-image-gen

### 专题图生成
baoyu-comic, baoyu-infographic, baoyu-cover-image, baoyu-xhs-images, baoyu-slide-deck, baoyu-article-illustrator

### 社媒分发（已合并）
baoyu-social-post — WeChat 公众号 / 微博 / X 三平台

### 内容转换
baoyu-url-to-markdown, baoyu-danger-x-to-markdown, baoyu-markdown-to-html, baoyu-format-markdown, baoyu-youtube-transcript

### 翻译
baoyu-translate

### 工具
baoyu-compress-image

### 危险/逆向
baoyu-danger-gemini-web

## design/ — 设计参考与前端（15）

### 品牌设计系统
design-md — 58 品牌设计系统参考库（apple/stripe/linear/notion/vercel...），按品牌名触发

### 前端设计/品味
design-taste-frontend, taste-skill-v1, frontend-design, redesign-skill, soft-skill, brutalist-skill, minimalist-skill, gpt-tasteskill, stitch-skill, image-to-code-skill, imagegen-frontend-web, imagegen-frontend-mobile, brandkit, dark-page-animations

## office/ — Office/文档（10）

### Office 三格式
officecli（统一 CLI 入口）, docx（Word 深度/redlining）, xlsx（Excel 深度/金融建模）, pptx（PPT 深度/html2pptx）, pdf

### 排版
kami — 排版产 PDF/简历/PPT（LaTeX）

### LaTeX
latex — 编译/诊断/装环境三合一

### 笔记/格式
obsidian — Bases(.base) + Flavored Markdown, json-canvas, mermaid

## devflow/ — 开发流程与元 skill（14）

### 规划/执行
brainstorming, writing-plans, executing-plans, dispatching-parallel-agents, subagent-driven-development

### 代码审查
requesting-code-review, receiving-code-review

### 分支/发布
finishing-a-development-branch, using-git-worktrees, release-skills

### Skill 创建
writing-skills, skill-creator, template-creator

### 输出控制
output-skill

## business/ — 业务/行业（9）

### 财务/金融
creating-financial-models, defect-excel-analysis-pipeline, market-research-reports

### 合同/法务
contract-review

### 中国业务
cn-tax-employee-import, dingtalk-overtime-application, menu-module-sheet-grouper

### 招聘发布
x-recruiter, xiaohongshu-recruiter

## testing/ — 测试/质量（9）

### 测试方法
test-driven-development, systematic-debugging, debug-failing-test, verification-before-completion, regression-test-planner

### 金融/Excel 用例
excel-testcase-reviewer, finance-testcase-reviewer, finance-testcase-writer

### 任务看板
test-board — 根据人员分工描述自动更新测试任务总表并生成 HTML/Excel 看板

## infra/ — 基础设施/环境（6）

cron, generate-snapshot, aionui-webui-setup, openclaw-setup, fastapi, remotion-best-practices

## browser/ — 浏览器/自动化（4）

browser-use, computer-use, control-chrome, control-in-app-browser

## mobile/ — 移动开发（2）

android-dev, ios-dev

## meta/ — 元 skill（2）

using-superpowers, find-skill

## security/ — 安全（1）

security-research

## misc/ — 其他（2）

moltbook, story-roleplay

---

## 整合变更记录

| 动作 | 详情 |
|---|---|
| design-md 58→1 | 58 个品牌壳合并为 1 个带品牌参数的 skill |
| taste-skill 归档 | 与 design-taste-frontend 逐字节相同 |
| security-review 归档 | security-research 的 alias |
| find-skills 归档 | 与 find-skill 同义，保留中文版 |
| documents/spreadsheets/presentations 归档 | Codex 容器专用 |
| VS Code 扩展内部 8 个归档 | cross-platform-paths 等 |
| latex 3→1 | latex-compile+latex-doctor+texlive-runtime-installer |
| obsidian 2→1 | obsidian-bases+obsidian-markdown |
| baoyu 社媒 3→1 | baoyu-post-to-wechat+weibo+x |
| desktop-skill-manager-style + tauri-delivery-checklist 归档 | 项目种子数据 |
| dark-page-animations 修复 | 补 frontmatter |
| 子目录归类 | 118 skill 归入 13 个分类子目录，根目录从 118 目录降至 13 |
