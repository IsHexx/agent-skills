# 云效提缺陷工具包（yunxiao-defect-submitter）

把 bug 截图 + 一句话描述发给 AI Agent，自动生成缺陷单（缺陷标题/模块路径/复现步骤/实际结果/预期结果），**你确认后**创建到云效，截图自动贴进缺陷描述。也支持命令行单条创建和 Excel 批量导入。

适用 Agent：**Kimi Code / Codex / Claude Code / Trae / Qoder / CodeBuddy / OpenCode** 等能读写文件、执行命令行的 AI 编程助手。

---

## 一、快速开始（5 分钟）

### 第 1 步：克隆仓库

```bash
git clone https://codeup.aliyun.com/68b7f9a6349fe2cce7f7fe9a/caibaoTest/cb_QA_skills.git
cd cb_QA_skills/yunxiao-defect-submitter
```

### 第 2 步：把工具包交给你的 AI Agent

用你的 AI 助手打开 `yunxiao-defect-submitter` 目录（作为工作目录/项目目录），然后发一句话：

> **「按 SKILL.md 安装并配置这个工具」**

### 第 3 步：Agent 自动完成安装配置

Agent 会按 SKILL.md 依次执行（全程自动，不需要你操作）：

```bash
python -m venv .venv                                     # ① 建虚拟环境
.venv/Scripts/python.exe -m pip install -r scripts/requirements.txt   # ② 装依赖（仅 openpyxl）
cp scripts/config.example.json scripts/config.json       # ③ 生成配置文件
```

然后自动调云效接口完成：获取你的组织ID → 列出你有权限的项目让你挑 → 拉取缺陷类型ID → 拉取严重程度/优先级字段映射 → 自检。

### 第 4 步：你只需提供一样东西——云效令牌

Agent 会向你要**个人访问令牌**，按这个路径申请（1 分钟）：

```
云效页面 → 右上角头像 → 个人设置 → 个人访问令牌 → 新建令牌
→ 勾选「项目协作」的读、写权限 → 复制 pt- 开头的字符串
```

把令牌发给 Agent 即可（令牌只写入你本地的 `scripts/config.json`，不会上传仓库）。

### 第 5 步：开始提单

直接发：

> 「[贴 bug 截图] 客户管理联系人维度，VIP1~4 筛选数量加起来比全部还多，提个缺陷」

Agent 返回缺陷草稿 → 你回复「确认」→ 创建完成，返回缺陷ID。

---

## 二、三种提单方式

| 方式 | 怎么用 | 适合场景 |
|---|---|---|
| AI 对话提单（推荐） | 发「截图 + 一句话描述」给 Agent | 日常迭代中发现 bug，自动生成规范缺陷单 |
| 用户反馈原样提单 | 说「这是用户反馈的 bug，原样提上去」 | 客服/用户反馈，描述不改写，支持 docx/清单批量 |
| Excel 批量导入 | 填 `scripts/缺陷导入模板.xlsx` 后跑 `import_defects.py` | 存量缺陷清单一次性入库 |

命令行详细用法见 `references/使用手册.md`。

---

## 三、目录说明

| 路径 | 说明 |
|---|---|
| `SKILL.md` | Agent 的安装与使用指引（**Agent 读这个**） |
| `scripts/` | 全部脚本 + 配置模板 + 模块人员映射表 + 批量导入模板 |
| `references/使用手册.md` | 面向测试同学的使用手册（**人读这个**） |
| `references/bug_draft_prompt.md` | AI 生成缺陷草稿的规范（两种提单场景的模板） |

---

## 四、注意事项

1. `scripts/config.json` 含你的个人令牌，已在 `.gitignore` 中排除，**严禁提交到仓库、严禁发群**
2. 每位使用者在本地由 Agent 生成自己的 `config.json`（各自填各自的令牌）
3. 模块归属变动时，直接改 `scripts/模块人员映射.csv`（格式：项目,模块,负责人,验证者）
4. 提单默认项目由 Agent 配置时确定，提单时可随时说「提到 xx 项目」切换
5. 缺陷创建后如提错项目/内容有误，在云效中删除即可（只进回收站，可恢复）

---

*维护：测试部 · 问题反馈给何祥*
