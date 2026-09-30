# Skills 全局索引

> **232 个 skill，按 15 个分类子目录组织。**
> 整合记录：原 196 个 → 合并/去重减 78 → 118 个 → 归入分类子目录 → 全盘同步新增 112 个、更新 21 个（lark 跟随 cli 上游 + officecli）。
> 引用路径：`D:\agent-skills\skills\<分类>\<skill名>\SKILL.md`

---

## 目录结构

```
skills/
├── lark/          (30) 飞书/Lark 全套 + 飞书补充工具
├── dingtalk/      (23) 钉钉全套（dws cli 管理，镜像 lark 规则）
├── baoyu/         (16) 宝玉工具集
├── design/        (22) 设计参考 + 前端设计/品味
├── devflow/       (57) 开发流程 + skill 创建 + 输出控制
├── office/        (16) Office/文档/LaTeX/Obsidian/图表/演示
├── writing/        (8) 写作/文风（长文/去 AI 味/文体改写）
├── business/      (14) 业务/行业/财务/招聘/发版/协作平台
├── testing/       (18) 测试/质量/用例/缺陷
├── infra/          (8) 基础设施/环境/框架
├── browser/        (4) 浏览器/自动化
├── mobile/         (2) 移动开发
├── meta/           (3) 元 skill（发现/入门/目录管理）
├── security/       (1) 安全
├── misc/          (10) 其他
└── SKILLS-INDEX.md 本文件
```

---

## lark/ — 飞书/Lark（30）

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
feishu-docx-extractor, feishu-native-kb-export, feishu-weekly-report

## dingtalk/ — 钉钉（23）

> dws cli 管理的活跃上游（`~/.dws/skills/multi/`），与 lark 同规则：保留独立 + 索引，不物理合并。

### 入口/共享
dws（统一入口）, dws-shared

### 文档/内容
dingtalk-doc, dingtalk-sheet, dingtalk-aitable, dingtalk-drive, dingtalk-wiki, dingtalk-devdoc

### 通讯
dingtalk-chat, dingtalk-mail, dingtalk-contact, dingtalk-ding, dingtalk-aisearch

### 日程/会议
dingtalk-calendar, dingtalk-live, dingtalk-minutes

### 任务/效率
dingtalk-todo, dingtalk-oa（审批）, dingtalk-attendance（考勤）, dingtalk-report（日志）, dingtalk-profile

### 应用开发
dingtalk-dev, dingtalk-skill

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

## design/ — 设计参考与前端（22）

### 品牌设计系统
design-md — 58 品牌设计系统参考库（apple/stripe/linear/notion/vercel...），按品牌名触发

### 设计提取
extract-design — 从网站 URL 提取完整设计语言（tokens/Tailwind/Figma 变量等 8 种产物）
web-to-design-md — 把网站视觉提取为 Stitch 规范的 DESIGN.md

### 设计语言/规范
apple-design — Apple 流体界面设计哲学（WWDC）转译到 Web
design-system — 品牌级视觉工艺 + 反 AI slop 规则（.kun）
shadcn-ui — shadcn/ui 组件体系指导

### 前端设计/品味
design-taste-frontend, taste-skill-v1, frontend-design, frontend-dev, impeccable, redesign-skill, soft-skill, brutalist-skill, minimalist-skill, gpt-tasteskill, stitch-skill, image-to-code-skill, imagegen-frontend-web, imagegen-frontend-mobile, brandkit, dark-page-animations

## office/ — Office/文档/演示（16）

### Office 三格式
officecli（统一 CLI 入口）, docx（Word 深度/redlining）, xlsx（Excel 深度/金融建模）, pptx（PPT 深度/html2pptx）, pdf

### 演示/网页 PPT
guizang-ppt-skill — 横向翻页网页 PPT（杂志风/瑞士风）
deckhtml — HTML 演示文稿生成

### 排版
kami — 排版产 PDF/简历/PPT（LaTeX）

### LaTeX
latex — 编译/诊断/装环境三合一

### 图表/可视化
archify — 架构/流程/时序图（交互式 HTML/SVG）, mermaid, mermaid-visualizer, excalidraw-diagram

### 笔记/格式
obsidian — Bases(.base) + Flavored Markdown, json-canvas, obsidian-canvas-creator

## writing/ — 写作/文风（8）

### 长文写作
khazix-writer — 数字生命卡兹克公众号长文写作

### 文体改写（Sepia 家族，5 个需同目录共存）
sepia — 小说/职业文本拟人化改写主入口
sepia-recreate, sepia-refactor, sepia-review, sepia-write — 四个显式操作入口（依赖同级 sepia/）

### 去 AI 味
humanizer-zh — 维基"AI 写作特征"规则去 AI 痕迹
lieflat-less-ai-tone — 白名单规则改写 AI 痕迹，未命中不动

## devflow/ — 开发流程与元 skill（57）

### 规划/执行
brainstorming, writing-plans, executing-plans, dispatching-parallel-agents, subagent-driven-development, hyperplan, prototype, implement, to-spec, to-tickets, triage, wizard, wayfinder, ask-matt, research

### 代码理解/架构
codebase-reader, codebase-design, domain-modeling, improve-codebase-architecture, tech-debt-audit, remove-deadcode

### 调试/修复
diagnosing-bugs

### 代码审查
requesting-code-review, receiving-code-review, code-review, pre-publish-review

### 分支/发布
finishing-a-development-branch, using-git-worktrees, release-skills, publish, get-unpublished-changes, resolving-merge-conflicts, git-guardrails-claude-code, setup-pre-commit

### 需求澄清/交接（访谈式）
grill-me, grilling, grill-with-docs, teach, handoff, to-questionnaire, wait-what

### Skill 创建
writing-skills, skill-creator, template-creator, writing-for-agents

### 工程脚手架/杂项
dev-start-scripts, scaffold-exercises, migrate-to-shoehorn, i18n-translate, vercel-react-best-practices, omomomo, opencode-qa, github-triage, leader, neat-freak

### 输出控制
output-skill

## business/ — 业务/行业（14）

### 财务/金融
creating-financial-models, defect-excel-analysis-pipeline, market-research-reports, hv-analysis

### 合同/法务
contract-review

### 中国业务
cn-tax-employee-import, dingtalk-overtime-application, menu-module-sheet-grouper

### 招聘发布
x-recruiter, xiaohongshu-recruiter, boss-zhipin-scraper

### 发版流程
feishu-release — 创建蓝绿或停服发版单、PDF 缺陷单，归档飞书 Wiki 并按需发送通知

### 协作平台/团队管理
tapd-openapi — TAPD 全量 OpenAPI 命令行
task-scheduler — 团队任务排期 + 人员看板/甘特图

## testing/ — 测试/质量（18）

### 测试方法
test-driven-development, systematic-debugging, debug-failing-test, verification-before-completion, regression-test-planner

### 金融/Excel 用例
excel-testcase-reviewer, finance-testcase-reviewer, finance-testcase-writer

### 任务看板
test-board — 根据人员分工描述自动更新测试任务总表并生成 HTML/Excel 看板

### 缺陷提交
yunxiao-defect-submitter — 云效缺陷提交工具包
defect-submitter — 通用缺陷平台（禅道/Jira/云效/TAPD）提交工具包

### API 测试（cb-api-test-engine 项目）
api-test, case-design, failure-triage, yaml-gen

### UI 自动化测试（plawright-ai-ui-framework 项目）
ui-element-builder, ui-failure-analyzer, ui-test-generator

## infra/ — 基础设施/环境（8）

cron, generate-snapshot, aionui-webui-setup, openclaw-setup, fastapi, remotion-best-practices, storage-analyzer, claude-cleanup

## browser/ — 浏览器/自动化（4）

browser-use, computer-use, control-chrome, control-in-app-browser

## mobile/ — 移动开发（2）

android-dev, ios-dev

## meta/ — 元 skill（3）

using-superpowers, find-skill, skill-catalog

## security/ — 安全（1）

security-research

## misc/ — 其他（10）

moltbook, story-roleplay, aihot, follow-builders, follow-builders-lite, i-have-adhd, wechat-to-md, codedrobe-codex-theme, classic-to-default-sync, termy-obsidian-context

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
| 子目录归类 | 118 skill 归入 13 个分类子目录 |
| 全盘同步（本次） | 新增 112 个 skill，15 个分类（新增 dingtalk/、writing/）；lark 20 个 + officecli 跟随上游更新 |

### 本次同步的排除项（沿用既定规则）

| 排除 | 依据 |
|---|---|
| design-md-* 单品牌壳、obsidian-bases/markdown、baoyu-post-to-*、latex-* | 已合并，不重复收录 |
| taste-skill / security-review / find-skills / documents / spreadsheets / presentations | 已归档的重复/容器专用项 |
| VS Code 扩展内部（含 .antigravity 里的同套）| 已归档的工具内部 skill |
| desktop-skill-manager-style / tauri-delivery-checklist / task-scheduler.legacy_20260805 | 种子数据/历史备份 |
| .codex/.system、.workbuddy、.codebuddy marketplace、/tmp/codebuddy-marketplace-install-*、.qoder/.qwenworkcn 插件缓存 | 工具内部/市场缓存/临时解压，非用户 skill |
| awesome-design-md / agent-reach 空目录 / sepia-repo（本体）| design-md 源仓库、无 SKILL.md、源仓库（内容已按 5 个 skill 收录） |
| portable-skills-artifacts 备份中的其余 148 个 | 均为已有 skill 的备份副本（extract-design、web-to-design-md 仅存在于该处，已收录） |
| mattpocock in-progress 8 个 + setup-matt-pocock-skills | 作者 WIP / 集合安装器 |
| dws mono 变体 / dingtalk-devapp | 与 dws 入口同名重复 / 无 SKILL.md |
| playwright/fastapi 包内 SKILL.md、hello-ai-cli 示例、$RECYCLE.BIN | 库内部文件/示例/回收站 |
