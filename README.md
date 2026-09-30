# Agent Skills 仓库

从多来源统一收拢、去重、归类的 AI Agent Skill 集合。

## 是什么

本仓库收录了 **232 个 Agent Skill**（AI 编程助手的能力扩展包），经过系统性的整合——从最初的 196 个来源去重、合并、归档了 78 个冗余项，再经全盘同步补入 112 个散落各处的 skill，最终归入 **15 个分类子目录**。

每个 skill 都是一个独立目录，内含 `SKILL.md`（技能描述/触发逻辑），以及可选的 `references/`、`scripts/`、示例文件等。

## 分类概览

```
agent-skills/
├── lark/          (30) 飞书/Lark 全套（审批/文档/表格/日历/即时通讯/云盘/应用开发…）
├── dingtalk/      (23) 钉钉全套（dws cli 管理：文档/表格/日历/群聊/审批/考勤…）
├── baoyu/         (16) 宝玉工具集（图像生成/社媒分发/内容转换/翻译…）
├── design/        (22) 设计参考与前端（58 品牌设计系统 + 设计提取 + 前端品味）
├── devflow/       (57) 开发流程（规划/审查/分支/Skill 创建/输出控制/工程脚手架）
├── office/        (16) Office/文档（docx/xlsx/pptx/PDF/LaTeX/Obsidian/图表/网页PPT）
├── writing/        (8) 写作/文风（公众号长文/去 AI 味/Sepia 文体改写）
├── business/      (14) 业务/行业（财务模型/合同审查/中国税务/招聘发布/协作平台）
├── testing/       (18) 测试与质量（TDD/调试/回归/用例生成/缺陷提交/UI 自动化）
├── infra/          (8) 基础设施（定时任务/快照/AionUi/Remotion/存储清理…）
├── browser/        (4) 浏览器自动化（Computer Use/Chrome 控制）
├── mobile/         (2) 移动开发（Android/iOS 模拟器）
├── meta/           (3) 元 skill（如何发现/使用/管理 skill）
├── security/       (1) 安全研究（团队模式漏洞审计）
└── misc/          (10) 其他（AI 资讯/主题皮肤/微信文章转换…）
```

每个分类目录下的各子目录即为独立的 skill。

## 怎么用

### 在 OpenCode / Codex CLI 中使用

将本仓库路径加入你的 agent 配置：

```jsonc
// opencode.json
{
  "skills": [
    {
      "source": "D:\\agent-skills\\skills",
      "name": "agent-skills"
    }
  ]
}
```

> **注意**：若你在其他 AI Agent 框架（如 Claude Code、Cursor、Windsurf）中使用，请参考对应框架的 skill/plugin 配置文档。

### 直接引用某个 Skill

```
D:\agent-skills\skills\lark\lark-im\SKILL.md
```

每个 skill 目录包含该技能的全部描述和触发规则。

## 来源

本仓库的 skill 收拢自以下来源：

| 来源 | 说明 |
|---|---|
| hub-managed | OpenCode Skill Hub 安装的公开 skill |
| user-or-tool-global | 用户/工具全局安装 |
| source-repo | 从 GitHub 仓库直接克隆 |
| app-user-config | 应用用户配置中的 skill |
| project-tool-entry | 项目中嵌入的 tool 配置 |

详见 [`catalog/manifest.md`](catalog/manifest.md)。

## 整合记录

| 动作 | 详情 |
|---|---|
| 品牌设计系统 58→1 | 58 个独立品牌壳合并为 1 个参数化 design-md skill |
| LaTeX 3→1 | latex-compile + latex-doctor + texlive-runtime-installer 合并 |
| Obsidian 2→1 | obsidian-bases + obsidian-markdown 合并 |
| 社媒发布 3→1 | baoyu-post-to-wechat + weibo + x 合并 |
| 内置/重复归档 | taste-skill、security-review、VS Code 内部 8 个等共 ~20 个归档 |
| 子目录归类 | 118 个 skill 从根目录平铺归入 13 个分类子目录 |
| 全盘同步 | 从整机扫描补入 112 个未收录 skill（新增 dingtalk/、writing/ 两个分类），lark 20 个 + officecli 跟随上游更新 |

## 许可

本仓库收录的 skill 遵循各自上游的许可证。详见各 skill 目录内的 `SKILL.md`。
