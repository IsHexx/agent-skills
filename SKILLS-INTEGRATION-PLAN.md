# Skills 整合方案（已执行）

> ✅ **已执行完成**。196 → 121 个 skill（减 75）。归档在 `_archive/`，可回滚。
> 权威记录见 `skills/SKILLS-INDEX.md`（分类索引 + 变更记录 + 剩余去重候选）。
> 盘点范围：`D:\agent-skills\skills` 原 197 个目录，其中 196 个有效 skill（`.codegraph` 非 skill）。
>
> 决策记录：D1=先对比能力→后定保留4归档3 | D2=只删重复 taste-skill | D3=移除 VS Code 内部 | D4=做 LaTeX+Obsidian 合并 | D5=合并 baoyu 社媒 | D6=归档待确认后删

---

## 一、现状总览

### 1.1 数量分布

| 类别 | 数量 | 来源 | 更新机制 |
|---|---|---|---|
| `design-md-*` | 58 | getdesign.md 静态参考 | 无 openclaw metadata，手动放置，**不活跃更新** |
| `baoyu-*` | 18 | github.com/JimLiu/baoyu-skills | openclaw 管理，**活跃上游** |
| `lark-*` | 27 | lark-cli | lark-cli 管理，**随 cli 更新** |
| 飞书补充（非 lark-cli） | 2 | feishu-docx-extractor / feishu-native-kb-export | 独立 |
| 散落独立 skill | 91 | 各来源不一 | 各异 |
| **合计** | **196** | | |

### 1.2 核心问题

1. **同源零碎**：design-md 58 个壳子结构完全相同（SKILL.md 16 行 + references/DESIGN.md + agents/openai.yaml 3 行），只是品牌数据不同 → 纯粹的目录膨胀。
2. **功能重叠冗余**：散落 skill 中存在多套做同一件事的 skill（Office 文档 9 个、前端设计品味 10+ 个、find-skill/find-skills 重名、security-research/security-review 互为别名）。
3. **发现性差**：196 个平铺目录，无分类索引，找 skill 靠记前缀。

---

## 二、整合原则（判定标准）

**能否物理合并，取决于上游更新机制**：

| 判定 | 条件 | 处理 |
|---|---|---|
| ✅ 物理合并 | 静态数据、无活跃上游、结构同质 | 合并成 1 个 skill |
| ⚠️ 保留独立 + 索引 | 活跃上游、openclaw/cli 管理更新 | 不动目录，归入分类索引 |
| 🔧 去重 | 功能重叠的多套 skill | 理清边界，保留最优一套，其余归档 |
| 📌 保留 | 功能独特无重叠 | 不动，归入索引 |

> skill 加载器扫描 `skills/` 下一层子目录（每个含 SKILL.md 即一个 skill），**不能用嵌套子目录分类**（会破坏发现）。所以"分类"只能靠：命名前缀（已有）+ 索引文档，不能用文件夹分组。

---

## 三、三大同源系列处理方案

### 3.1 ✅ design-md-*：58 → 1（物理合并）

**理由**：静态设计参考数据，无 openclaw metadata，结构完全同质，合并不破坏任何更新链路。合并后总体积约 1MB（58 × 15.8KB），完全可控。

**合并后结构**：
```
design-md/
├── SKILL.md                      # 统一入口，description 含全部 58 个品牌名作为触发词
├── references/
│   ├── brands/
│   │   ├── apple.md              # 原 design-md-apple/references/DESIGN.md
│   │   ├── stripe.md             # 原 design-md-stripe/references/DESIGN.md
│   │   └── ... (58 个)
│   └── brands-index.md           # 品牌清单 + traits 摘要（从各 agents/openai.yaml 收拢）
└── agents/
    └── openai.yaml               # 统一界面元数据
```

**触发机制**（你选的"统一 skill + 品牌参数"）：
- SKILL.md 的 description 列出全部 58 个品牌名 + "inspired by / 风格 / design language"等触发词
- body 说明：识别用户提到的品牌 → 读 `references/brands/<brand>.md` → 提取 tokens（color/typography/spacing/radii/shadows/motion）→ 套用到项目
- 品牌名匹配用 `references/brands-index.md` 做归一化（处理 linear-app→linear、x-ai→x.ai 等别名）

**brands-index.md 示例**：
```markdown
| 品牌 | 文件 | Traits |
|---|---|---|
| apple | brands/apple.md | 消费电子。留白、SF Pro、电影感影像 |
| stripe | brands/stripe.md | 支付基建。紫色渐变、weight-300 优雅 |
| linear | brands/linear-app.md | ... |
| x.ai | brands/x-ai.md | ... |
```

**收益**：196 → 139 个 skill，目录减少 57 个。

---

### 3.2 ⚠️ baoyu-*：18 个保留独立 + 归类索引

**理由**：全部带 `metadata.openclaw.homepage` 指向 `github.com/JimLiu/baoyu-skills`，是活跃上游。物理合并会破坏 openclaw 的更新链路（上游更新后无法整体替换）。每个 baoyu skill 有独立 `scripts/`（main.ts 等），合并会让单 skill 膨胀且难维护。

**处理**：保留 18 个独立目录，在全局索引中归为一类并细分功能子组。

**功能子组（用于索引，非物理合并）**：
| 子组 | skill |
|---|---|
| 通用图像引擎 | baoyu-image-gen |
| 专题图生成 | baoyu-comic, baoyu-infographic, baoyu-cover-image, baoyu-xhs-images, baoyu-slide-deck, baoyu-article-illustrator |
| 社媒分发 | baoyu-post-to-wechat, baoyu-post-to-weibo, baoyu-post-to-x |
| 内容转换 | baoyu-url-to-markdown, baoyu-danger-x-to-markdown, baoyu-markdown-to-html, baoyu-format-markdown, baoyu-youtube-transcript |
| 翻译 | baoyu-translate |
| 工具 | baoyu-compress-image |
| 危险/逆向 | baoyu-danger-gemini-web |

**可选轻量归并**（需你确认，会破坏该子项的 openclaw 单项更新）：
- 社媒分发 3 个 → 1 个 `baoyu-social-post`（3 个都用 Chrome CDP，结构相似）
- 仅当你明确"不再跟上游同步这几个"时才做。默认**不做**。

---

### 3.3 ⚠️ lark-*：27 个保留独立 + 归类索引

**理由**：lark-cli 管理，随 cli 版本更新。每个对应飞书一个产品模块，触发条件各异，物理合并会让 SKILL.md 巨型化且破坏 cli 更新。

**处理**：保留 27 个独立目录，在全局索引中按飞书产品线分组。

**功能分组（用于索引）**：
| 子组 | skill |
|---|---|
| 文档/内容 | lark-doc, lark-sheets, lark-base, lark-slides, lark-whiteboard, lark-markdown, lark-drive, lark-wiki |
| 通讯 | lark-im, lark-mail, lark-contact |
| 日程/会议 | lark-calendar, lark-vc, lark-vc-agent, lark-minutes, lark-note, lark-event |
| 任务/效率 | lark-task, lark-okr, lark-approval, lark-attendance |
| 应用开发 | lark-apps, lark-openapi-explorer, lark-skill-maker |
| 工作流编排 | lark-workflow-meeting-summary, lark-workflow-standup-report |
| 元/共享 | lark-shared |

**飞书补充**（非 lark-cli，归入飞书索引同一类）：feishu-docx-extractor, feishu-native-kb-export

---

## 四、散落 skill 冗余去重清单

这是零碎感的主要来源。以下是需要你拍板去重的重叠群组。

### 4.1 🔧 Office 文档处理（9 个，重叠严重）

| skill | 处理格式 | 实现 | 备注 |
|---|---|---|---|
| `officecli` | .docx/.xlsx/.pptx | officecli CLI | **统一入口**，三格式通吃 |
| `docx` | .docx | python-docx 类 | 综合文档库 |
| `documents` | .docx/Word/Google Docs | 容器内渲染 | 偏 Google Docs |
| `xlsx` | .xlsx | openpyxl 类 | 综合 |
| `spreadsheets` | .xlsx/.xls/.csv/.tsv | | 覆盖更广格式 |
| `pptx` | .pptx | python-pptx 类 | 综合 |
| `presentations` | PowerPoint/Google Slides | | 偏 Google Slides |
| `pdf` | .pdf | | 独立，无重叠 |
| `kami` | 排版产 PDF/简历/PPT | LaTeX | 偏排版，无重叠 |

**建议**：
- 保留 `officecli` 作为 Office 三格式统一入口
- 保留 `pdf`、`kami`（功能独立）
- `docx`/`documents`、`xlsx`/`spreadsheets`、`pptx`/`presentations` 三组重叠 → **需你决定每组装哪套**（officecli 够用就归档旧的；若旧的有 officecli 没有的能力则保留）
- ❓ 决策点 D1

### 4.2 🔧 前端设计品味（10+ 个，高度重叠）

| skill | name | 定位 |
|---|---|---|
| `design-taste-frontend` | design-taste-frontend | 反 slop 前端，落地页/作品集/重设计 |
| `taste-skill` | **design-taste-frontend** | **与上行同 name！疑似重复安装** |
| `taste-skill-v1` | design-taste-frontend-v1 | v1 旧版保留 |
| `frontend-design` | frontend-design | 生产级前端组件 |
| `redesign-skill` | redesign-existing-projects | 升级现有网站 |
| `soft-skill` | high-end-visual-design | 高端代理商风格教学 |
| `brutalist-skill` | industrial-brutalist-ui | 粗野主义 UI |
| `minimalist-skill` | minimalist-ui | 极简 UI |
| `gpt-tasteskill` | gpt-taste | UX/UI + GSAP 动效 |
| `stitch-skill` | stitch-design-taste | Google Stitch 设计系统 |
| `dark-page-animations` | (解析失败) | 暗色页面动画 |
| `image-to-code-skill` | image-to-code | 图转码 |
| `imagegen-frontend-web` | imagegen-frontend-web | 前端网页设计图 |
| `imagegen-frontend-mobile` | imagegen-frontend-mobile | 移动端设计图 |
| `brandkit` | brandkit | 品牌 kit 图 |
| `desktop-skill-manager-style` | (解析失败) | 待查 frontmatter |

**确定去重**：
- `taste-skill` 与 `design-taste-frontend` 同 name 同描述 → **二选一删除**（保留 `design-taste-frontend`，归档 `taste-skill`）

**需决策**：
- 风格流派 skill（brutalist/minimalist/高端/GSAP/Stitch）是不同设计语言，**建议保留各自独立**，但归入"前端设计"索引类
- `image-to-code` / `imagegen-frontend-*` / `brandkit` 偏"图生成用于前端"，与 baoyu 图像生成有交集 → 归索引
- `dark-page-animations` / `desktop-skill-manager-style` frontmatter 解析失败 → 执行前需单独检查
- ❓ 决策点 D2

### 4.3 🔧 确定去重项（无争议）

| 重叠对 | 处理 | 依据 |
|---|---|---|
| `security-research` / `security-review` | 保留 `security-research`，`security-review` 是其 alias（SKILL.md 明写"Alias for security-research"） | description 自述 |
| `find-skill` / `find-skills` | 二选一（中文版 vs 英文版，功能同义） | 同名单复数，描述同义 |
| `writing-skills` / `skill-creator` / `template-creator` | 三者都"创建 skill"，边界需理清 | 可能各有侧重，需看 body |

### 4.4 📌 可合并的小族（低风险，需确认）

| 群组 | skill | 建议 |
|---|---|---|
| LaTeX 工具链 | latex-compile, latex-doctor, texlive-runtime-installer | 合并成 `latex`（编译/诊断/装环境三子命令）|
| Obsidian | obsidian-bases, obsidian-markdown | 合并成 `obsidian`（.base + markdown 两子命令）|
| 代码审查 | requesting-code-review, receiving-code-review | 保留独立（发/收是不同场景）|
| 测试运行 | run-e2e-tests, run-integration-tests, run-smoke-tests, run-pre-commit-checks | 保留独立（触发条件不同）|
| 招聘发布 | x-recruiter, xiaohongshu-recruiter | 保留独立（平台不同）|

### 4.5 📌 VS Code 扩展内部 skill（疑似不属于通用集）

以下 skill 描述提到 "VS Code extension / ZCode / Codex extension"，疑似某个 VS Code 扩展项目的内部 skill，混进了通用 skills 目录：
- `cross-platform-paths`, `settings-precedence`, `python-manager-discovery`, `restore-legacy-sessions`, `run-e2e-tests`, `run-integration-tests`, `run-smoke-tests`, `run-pre-commit-checks`

**建议**：确认这些是否你真正在用的通用 skill。若是某扩展专用，可移出 skills 目录或归档。
- ❓ 决策点 D3

---

## 五、全局索引设计

新增一个 `SKILLS-INDEX.md`（放在 `D:\agent-skills\skills\` 下），作为全局分类索引。结构：

```markdown
# Skills 索引（196 项）

## 设计参考
- design-md（58 品牌设计系统，按品牌名触发）

## 前端设计 / 品味
- design-taste-frontend, frontend-design, redesign-skill, soft-skill,
  brutalist-skill, minimalist-skill, gpt-tasteskill, stitch-skill,
  dark-page-animations, image-to-code-skill, imagegen-frontend-web,
  imagegen-frontend-mobile, brandkit

## 飞书 / Lark
### 文档内容: lark-doc, lark-sheets, ...
### 通讯: lark-im, lark-mail, lark-contact
### ...（按 3.3 分组）
### 补充工具: feishu-docx-extractor, feishu-native-kb-export

## 宝玉工具集（baoyu-skills）
### 图像: baoyu-image-gen, baoyu-comic, ...
### 社媒: baoyu-post-to-wechat/weibo/x
### ...

## Office / 文档
- officecli, pdf, kami, docx, xlsx, pptx, ...

## 开发流程
- brainstorming, writing-plans, executing-plans, ...

## 测试 / 质量
- run-*-tests, regression-test-planner, ...

## 安全
- security-research

## 业务 / 行业
- contract-review, creating-financial-models, ...

## 基础设施
- cron, generate-snapshot, ...

## 元 skill
- skill-creator, find-skill, using-superpowers, ...
```

索引是**纯文档**，不影响 skill 加载，只是给你和我快速定位用。

---

## 六、最终目标结构

| 动作 | 数量变化 |
|---|---|
| design-md 58 → 1 | -57 |
| 去重 security-review(alias) | -1 |
| 去重 taste-skill(重复) | -1 |
| 去重 find-skill/find-skills 二选一 | -1 |
| LaTeX 3 → 1（若你同意） | -2 |
| Obsidian 2 → 1（若你同意） | -1 |
| VS Code 内部 skill 移出（若 D3 确认） | -7 |
| **合计** | **196 → 约 126** |

目录数从 197 降到约 127，零碎感大幅降低，且不破坏 baoyu/lark 的上游更新链路。

---

## 七、迁移步骤（确认后执行）

### 阶段 1：design-md 合并（最大收益，零风险）
1. 新建 `design-md/` 目录及子结构
2. 迁移 58 个 `references/DESIGN.md` → `design-md/references/brands/<brand>.md`
3. 从 58 个 `agents/openai.yaml` 生成 `references/brands-index.md`
4. 写统一 `design-md/SKILL.md`（含 58 品牌触发词 + 加载机制说明）
5. 验证：测试几个品牌名触发能正确加载对应 DESIGN.md
6. 确认无误后，归档原 58 个目录到 `_archive/design-md-old/`（不直接删，留回滚）

### 阶段 2：无争议去重
7. 归档 `security-review`（alias）
8. 归档 `taste-skill`（与 design-taste-frontend 重复）
9. 归档 find-skill/find-skills 之一

### 阶段 3：可选小族合并（需你确认）
10. LaTeX 3 → 1（若同意）
11. Obsidian 2 → 1（若同意）

### 阶段 4：Office 去重（需 D1 决策）
12. 按你的决策归档冗余的 docx/xlsx/pptx/documents/spreadsheets/presentations

### 阶段 5：生成全局索引
13. 写 `SKILLS-INDEX.md`
14. 更新本方案文档记录最终状态

### 阶段 6：清理（最后，确认一切正常后）
15. 删除 `_archive/`（或长期保留作为备份）

> 每阶段独立可回滚。归档而非直接删除，确保任何阶段出问题都能恢复。

---

## 八、风险与回滚

| 风险 | 应对 |
|---|---|
| design-md 合并后某品牌触发不到 | brands-index.md 做别名归一化；合并后逐一测试 58 个品牌名 |
| 误删非重复 skill | 全程归档到 `_archive/` 不直接删，可恢复 |
| baoyu/lark 误合并破坏更新 | 方案明确不合并这两类，只做索引 |
| Office 去重误删有用能力 | D1 决策前先对比各 skill 的 body 能力差异，再定保留集 |
| 加载器不识别合并后的 design-md | 合并后 SKILL.md 保持标准 frontmatter 格式，兼容加载器扫描 |

---

## 九、需要你拍板的决策点

| 编号 | 决策 | 选项 |
|---|---|---|
| **D1** | Office 文档 9 个怎么去重？ | A) 全用 officecli，归档 docx/xlsx/pptx/documents/spreadsheets/presentations；B) 保留旧套（docx/xlsx/pptx），只归档 documents/spreadsheets/presentations；C) 先对比能力再定 |
| **D2** | 前端设计品味类如何处理？ | A) 只删 taste-skill 重复项，其余全保留+索引；B) 进一步合并风格流派；C) 让我先对比各 skill body 再建议 |
| **D3** | VS Code 扩展内部 skill（cross-platform-paths 等 7 个）是否通用？ | A) 是通用 skill，保留+索引；B) 是某扩展专用，移出 skills 目录；C) 不确定，先保留 |
| **D4** | LaTeX 3→1、Obsidian 2→1 的小族合并做不做？ | A) 做；B) 不做，只索引；C) 只做 LaTeX |
| **D5** | baoyu 社媒分发 3→1 的轻量归并做不做？ | A) 不做（默认，保 openclaw 更新）；B) 做（不再跟上游同步这 3 个） |
| **D6** | 归档的原目录保留多久？ | A) 长期保留 _archive/；B) 确认正常后删除 |

---

## 附：完整 196 skill 分类表

（见 `C:\Users\win10\AppData\Local\Temp\opencode\skills-inventory.txt`，已生成）
