---
name: baoyu-social-post
description: "Post content to Chinese & global social platforms via real Chrome (CDP, bypasses anti-bot). Three platforms: WeChat Official Account (微信公众号 — articles 图文/文章 + image-text posts, via API or Chrome CDP), Weibo (微博 — text/image/video posts + 头条文章 long-form), X/Twitter (text/image/video posts + quote tweets + X Articles long-form Markdown). Use when user mentions '发布公众号', 'post to wechat', '微信公众号', '贴图/图文/文章', '发微博', '发布微博', 'post to Weibo', '微博头条文章', 'post to X', 'tweet', 'publish to Twitter', or 'share on X'. Markdown article workflows default to converting external links to bottom citations for WeChat-friendly output."
version: 1.56.1
metadata:
  openclaw:
    homepage: https://github.com/JimLiu/baoyu-skills
    requires:
      anyBins:
        - bun
        - npx
---

# Social Post (WeChat / Weibo / X)

Posts to three platforms via real Chrome browser (bypasses anti-bot detection). Each platform has its own scripts and full workflow reference.

## Language

**Match user's language**: Respond in the same language the user uses. Chinese in → Chinese out; English in → English out.

## Routing

Identify the target platform from the request, then read that platform's full workflow reference before acting:

| Platform | Trigger words | Workflow reference | Scripts |
|---|---|---|---|
| WeChat 公众号 | 发布公众号, post to wechat, 微信公众号, 贴图/图文/文章 | [`references/wechat.md`](references/wechat.md) | `scripts/wechat/` |
| Weibo 微博 | 发微博, 发布微博, post to Weibo, 微博头条文章 | [`references/weibo.md`](references/weibo.md) | `scripts/weibo/` |
| X (Twitter) | post to X, tweet, publish to Twitter, share on X | [`references/x.md`](references/x.md) | `scripts/x/` |

## Execution

1. Determine this SKILL.md file's directory as `{baseDir}`.
2. Read the platform's workflow reference (`references/<platform>.md`) completely — it covers script selection, input formats, and the full posting workflow.
3. Scripts live at `{baseDir}/scripts/<platform>/<name>.ts`.
4. Resolve `${BUN_X}` runtime: if `bun` installed → `bun`; if `npx` available → `npx -y bun`; else suggest installing bun.
5. Each platform subdir has its own `package.json` + `bun.lock` — run `bun install` within the platform subdir if needed.

## Preferences (EXTEND.md) — preserved per platform

Each platform keeps its **original** EXTEND.md path (unchanged from the standalone skills, so existing user configs still work):

| Platform | EXTEND.md path (project / user) |
|---|---|
| WeChat | `.baoyu-skills/baoyu-post-to-wechat/EXTEND.md` / `$HOME/.baoyu-skills/baoyu-post-to-wechat/EXTEND.md` |
| Weibo | `.baoyu-skills/baoyu-post-to-weibo/EXTEND.md` / `$HOME/.baoyu-skills/baoyu-post-to-weibo/EXTEND.md` |
| X | `.baoyu-skills/baoyu-post-to-x/EXTEND.md` / `$HOME/.baoyu-skills/baoyu-post-to-x/EXTEND.md` |

Check EXTEND.md existence (priority: project → xdg → user) before posting. The platform reference docs detail the exact preference keys and behavior.

## Additional references

- WeChat: `references/wechat-ref/` (article-posting.md, image-text-posting.md, config/first-time-setup.md)
- X: `references/x-ref/` (articles.md, regular-posts.md)

## Source

Merged from `baoyu-post-to-wechat`, `baoyu-post-to-weibo`, `baoyu-post-to-x` (github.com/JimLiu/baoyu-skills). Note: this merged skill no longer tracks the upstream repo per-skill; updates must be applied manually.
