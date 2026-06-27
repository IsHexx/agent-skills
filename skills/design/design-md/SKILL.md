---
name: design-md
description: "Apply brand-inspired DESIGN.md design systems to frontend work. 58 brands available — apple, stripe, linear (linear-app), notion, vercel, spotify, tesla, nvidia, figma, framer, cursor, claude, airbnb, uber, bmw, ferrari, lamborghini, renault, spacex, ibm, hashicorp, mongodb, clickhouse, supabase, coinbase, kraken, revolut, wise, zapier, webflow, sanity, miro, airtable, cal, clay, cohere, mistral-ai, together-ai, x-ai, ollama, voltagent, composio, opencode-ai, mintlify, posthog, raycast, resend, replicate, runwayml, elevenlabs, superhuman, warp, lovable, minimax, pinterest, intercom, figma, framer. Use when the user asks for a UI inspired by a specific brand or wants a visual direction matching a design language. Triggers: 'inspired by <brand>', '<brand> 风格', '<brand> style', 'design language like <brand>', 'make it look like <brand>', '用 <brand> 的设计'. Also triggers on 'design-md', 'DESIGN.md brand', or any brand name listed in references/brands-index.md."
---

# design-md — 品牌设计系统参考库

58 个品牌的设计系统参考（源自 getdesign.md）。每个品牌一份 `references/brands/<brand>.md`，内含该品牌的设计 tokens：color roles、typography、spacing、radii、borders、shadows、layout density、motion。

## 工作流程

1. **识别品牌**：从用户请求中提取品牌名。若不确定，查 `references/brands-index.md` 做归一化（处理别名，如 linear→linear-app、x.ai→x-ai、mistral→mistral-ai）。
2. **读参考**：读 `references/brands/<brand>.md`，提取具体 tokens：color roles、typography、spacing、radii、borders、shadows、layout density、motion。
3. **翻译到项目**：把参考翻译进项目现有结构和组件体系，不要盲目克隆截图。
4. **优先复用**：优先用共享主题变量或可复用组件，而非一次性样式。
5. **保留可达性**：适配视觉语言时保留 accessibility 和 responsiveness。

## 品牌清单

完整 58 个品牌 + traits 见 `references/brands-index.md`。常用品牌：

| 品牌 | 定位 |
|---|---|
| apple | 消费电子，留白、SF Pro、电影感 |
| stripe | 支付基建，紫色渐变、weight-300 优雅 |
| linear / linear-app | 项目管理，极简、精准、紫色点缀 |
| notion | 全能工作区，暖色极简、serif 标题 |
| vercel | 前端部署，黑白精准、Geist 字体 |
| spotify | 音乐流媒体，深色亮绿、粗体字 |
| tesla | 电动汽車，激进减法、全屏摄影 |
| claude | Anthropic AI，暖赤陶点缀、编辑式排版 |

## 多品牌

用户同时提到多个品牌时，先读每份参考，明确主品牌（主导视觉方向）与次品牌（仅取特定 token 如配色或字体），在交付前向用户确认主次关系。

## 来源

各品牌原始来源：`https://getdesign.md/<brand>/design-md`
