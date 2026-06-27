---
name: dark-page-animations
description: "Dark-themed page animation component library: starfield, canvas meteors, card border-light (hover), input border-light (focus), slide-in entrance, shake feedback. 6 ready-to-copy CSS/JS components with key params and common pitfalls. Use when building dark/black-background login pages, landing pages, marketing pages, or any UI needing starfield backgrounds, meteor particles, border-light sweep effects, or dark UI motion (CSS/Canvas animations). Triggers: '暗色页面', '星空背景', '流星动画', '粒子背景', '边框光', 'border light', '扫光', 'dark UI 动效', 'starfield', 'meteor canvas'."
---

# Skill: Dark Page Animations

## 触发条件

当任务涉及以下任意一项时，自动加载本 skill：

- 暗色/黑色背景的登录页、落地页、营销页
- 星空背景、流星动画、粒子背景
- 卡片/输入框的边框光（border light）扫光效果
- 深色 UI 的动效设计（CSS 动画、Canvas 动画）

---

## 核心原则

1. **组件库优先**：`v-minimax-full/animation-components.html` 是所有技术的权威实现参考，优先从中复制代码，不要凭记忆重写。
2. **方案选型正确**：每种效果有唯一推荐方案，不要混用或随意替换。
3. **纯 HTML 约束**：`v-minimax-full/` 下无构建工具，所有动画必须用原生 CSS + JS 实现。

---

## 动画组件目录

| 组件 | 方案 | 关键文件位置 |
|------|------|-------------|
| 星空点阵 | CSS keyframes + JS DOM | 组件 1 |
| 流星 Canvas | Canvas 2D requestAnimationFrame | 组件 2 |
| 卡片边框光（hover） | `@property` + CSS hover | 组件 3 |
| 输入框边框光（focus） | 旋转正方形 + JS class toggle | 组件 4 |
| 入场滑入 | CSS keyframes | 组件 5 |
| 抖动反馈 | CSS keyframes + JS class toggle | 组件 6 |

---

## 组件 1：星空点阵

**方案**：预定义 STARS 数组 → JS 生成绝对定位 span → CSS 动画驱动漂浮+闪烁

**关键参数**：
- 每颗星 4 个属性：`{ top, left, size, opacity }`
- 4 条 drift 路径（a/b/c/d），用 index 错开时长和延迟
- `--star-opacity` CSS 变量让 twinkle 动画基于各自的初始透明度

```css
@keyframes star-drift-a {
  0%,100% { transform: translate(0,0); }
  50%     { transform: translate(6px,-4px); }
}
@keyframes star-twinkle {
  0%,100% { opacity: var(--star-opacity); }
  50%     { opacity: calc(var(--star-opacity) * 0.35); }
}
```

```js
STARS.forEach((s, i) => {
  const el = document.createElement('span');
  const driftDur   = ((14 + (i*7)%13) / 3).toFixed(2);  // 4.7~8.7s
  const twinkleDur = (( 4 + (i*5)%7)  / 3).toFixed(2);  // 1.3~3.3s
  el.style.cssText = `
    position:absolute; border-radius:50%; background:#fff;
    top:${s.top}; left:${s.left};
    width:${s.size}px; height:${s.size}px;
    --star-opacity:${s.opacity};
    box-shadow:0 0 ${s.size*2}px rgba(255,255,255,0.6);
    animation:
      ${DRIFTS[i%4]} ${driftDur}s ease-in-out ${-((i*3)%11)}s infinite,
      star-twinkle   ${twinkleDur}s ease-in-out ${-((i*2)%9)}s infinite;
  `;
  container.appendChild(el);
});
```

---

## 组件 2：流星 Canvas

**方案**：Canvas 2D + `requestAnimationFrame` + Meteor 类

**关键参数**：
- 6 条流星，初始延迟错开（`i * 50 + random * 80` ms）
- 起点：右侧 60%~110% 宽，上方 40% 高
- 飞行角度：165°~175°（近水平向左，轻微下倾）
- 速度：7~12 px/frame
- Alpha 生命周期：前 20% 淡入，20~70% 全亮，后 30% 淡出
- 结束后延迟 300~800 帧重置（控制频率，不要太密集）
- 颜色：`HUES = [210, 200, 220, 190, 60]`（蓝、青、黄）
- 渐变拖尾 + 发光头部 + 3 个粒子点缀尾部

**canvas 必须随窗口 resize**：
```js
function resize() {
  canvas.width  = canvas.offsetWidth;   // 或 window.innerWidth
  canvas.height = canvas.offsetHeight;
}
window.addEventListener('resize', resize);
```

---

## 组件 3：卡片边框光（hover 触发）

**方案**：`@property` 注册角度变量 + `conic-gradient` + mask 裁切 + CSS hover

**适用**：hover 触发的静态容器（卡片、panel）
**不适用**：需要 focus/blur 动态切换的场景（用组件 4）

```css
@property --bl-angle {
  syntax: '<angle>';
  inherits: false;
  initial-value: 0deg;
}
@keyframes bl-spin { to { --bl-angle: 360deg; } }

.bl-card {
  position: absolute; inset: 0; padding: 1px;
  border-radius: inherit;
  background: conic-gradient(
    from var(--bl-angle),
    transparent 0deg, rgba(255,255,255,0.85) 20deg,
    transparent 50deg, transparent 360deg
  );
  /* 双层 mask：只显示 padding 区域（1px 环）*/
  -webkit-mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  -webkit-mask-composite: xor;
  mask: linear-gradient(#fff 0 0) content-box, linear-gradient(#fff 0 0);
  mask-composite: exclude;
  opacity: 0; transition: opacity 0.5s;
}
.card:hover .bl-card {
  opacity: 1;
  animation: bl-spin 3s linear infinite;
}
```

**注意**：`mask` 和 `-webkit-mask` 都要写，缺一不可。

---

## 组件 4：输入框边框光（focus 触发）

**方案**：旋转正方形 conic-gradient + JS class toggle

**为什么不用 `@property`**：在 focus/blur 动态切换时，`@property` 动画链路（自定义属性 → conic-gradient 重绘）在部分场景下不触发重绘，效果消失。旋转正方形方案用标准 `transform: rotate()` 驱动，完全可靠。

**HTML 结构**：
```html
<!-- 父容器：padding:1px 充当边框 -->
<div class="inp-wrap">
  <!-- .bl-ring 由 JS 注入 -->
  <span class="input-icon"> ... </span>  <!-- z-index: 2 -->
  <input type="text" ...>                <!-- z-index: 1 -->
</div>
```

```css
.inp-wrap {
  position: relative; overflow: hidden; border-radius: 6px;
  padding: 1px;
  background: #262626;   /* 静止时边框色，光圈覆盖时被遮住 */
}
input { border: none; border-radius: 5px; position: relative; z-index: 1; }

.input-icon {
  position: absolute; left: 12px; top: 50%; transform: translateY(-50%);
  z-index: 2;   /* 必须高于 input 的 z-index:1，否则图标被遮 */
  pointer-events: none;
}

@keyframes bl-rotate { to { transform: rotate(360deg); } }
.bl-ring {
  position: absolute;
  background: conic-gradient(from 0deg,
    transparent          0deg,
    rgba(96,200,255,0.15) 10deg,
    rgba(96,200,255,0.80) 25deg,
    rgba(96,200,255,0.95) 35deg,
    rgba(96,200,255,0.60) 55deg,
    rgba(96,200,255,0.15) 80deg,
    transparent         110deg,
    transparent         360deg
  );
  opacity: 0; transition: opacity 0.3s;
  animation: bl-rotate 3s linear infinite;
  animation-play-state: paused;
  pointer-events: none;
}
.bl-ring.active { opacity: 1; animation-play-state: running; }
```

```js
function createRing(wrap) {
  const ring = document.createElement('span');
  ring.className = 'bl-ring';
  const w = wrap.offsetWidth || 320;
  const h = wrap.offsetHeight || 46;
  // 尺寸必须用对角线，否则旋转时四角渐变被裁掉
  const size = Math.ceil(Math.hypot(w, h)) + 8;
  ring.style.width  = size + 'px';
  ring.style.height = size + 'px';
  ring.style.left   = ((w - size) / 2) + 'px';
  ring.style.top    = ((h - size) / 2) + 'px';
  wrap.insertBefore(ring, wrap.firstChild);
  return ring;
}

const ring = createRing(inputWrap);
input.addEventListener('focus', () => ring.classList.add('active'));
input.addEventListener('blur',  () => ring.classList.remove('active'));
```

**光弧参数说明**：
- `0→35deg`：渐进淡入（避免硬边急促感）
- `35deg` 峰值：最亮点
- `35→110deg`：缓慢衰减拖尾（越长越柔和）
- `110→360deg`：透明
- 速度 `3s`：2/3 圈速，不急促

---

## 组件 5：入场滑入

```css
@keyframes slideUp {
  from { opacity: 0; transform: translateY(16px); }
  to   { opacity: 1; transform: translateY(0); }
}
.card { animation: slideUp 0.4s cubic-bezier(0.16, 1, 0.3, 1); }
```

`cubic-bezier(0.16,1,0.3,1)` = "spring out"：快速升起后轻微过冲，比 ease-out 更有弹性感。

---

## 组件 6：抖动反馈

```css
@keyframes shake {
  0%,100% { transform: translateX(0); }
  20%     { transform: translateX(-6px); }
  40%     { transform: translateX( 6px); }
  60%     { transform: translateX(-4px); }
  80%     { transform: translateX( 4px); }
}
```

```js
// 用完立刻移除，确保下次点击能重播
element.classList.add('shake');
setTimeout(() => element.classList.remove('shake'), 400);
```

---

## 常见陷阱

| 陷阱 | 正确做法 |
|------|---------|
| 输入框图标被遮挡 | `input-icon` 必须设 `z-index: 2`，input 设 `z-index: 1` |
| 输入框 border light 旋转时四角消失 | ring 尺寸用 `Math.hypot(w,h)`，不能用 `max(w,h)` |
| border light 完全无效 | 检查 `mask` 是否同时写了 `-webkit-mask` 和标准 `mask` |
| `@property` 动画在 focus/blur 时失效 | 输入框改用旋转正方形方案（组件 4） |
| 流星频率太高/太低 | 调整 `reset(delay)` 的 delay 值：300~800 = 5~13s 间隔 |
| 星星动画完全同步/呆板 | drift 和 twinkle 的时长/延迟必须用 index 错开，不能用同一固定值 |
| 光弧旋转感觉急促 | 延长光弧的尾部渐变（扩大 `transparent` 前的区间），加长旋转周期 |

---

## 参考文件

- 完整 demo + 可复制代码片段：`D:/project/loginPage/v-minimax-full/animation-components.html`
- 生产实现参考：`D:/project/loginPage/v-minimax-full/01-login.html`
- 原版 React 实现：`D:/project/loginPage/login-page-redesign/app/page.tsx`
- 原版星空组件：`D:/project/loginPage/login-page-redesign/components/starfield.tsx`
