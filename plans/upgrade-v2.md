# Bilingual Reader v2 升级方案

## 一、现状分析

### 当前架构

```
手动编写 Python 脚本（硬编码段落+翻译）
  → 生成 data-*.json
    → embed_data.py 嵌入 HTML（正则替换 var data = {...}）
      → 单文件 HTML + GitHub Pages 部署
```

### 核心痛点

| 痛点 | 现状 | 影响 |
|------|------|------|
| 手动配 JSON | 每个段落手动写 `{"en": "...", "zh": "..."}`，百行以上的 Python 脚本 | 效率低，易出错 |
| 硬编码格式化 | 英文加粗、斜体、换行需要手动插 `<strong>`/`<em>`/`<br>` 标签 | 维护困难，`fix_en_formatting.py` 是补丁式修复 |
| 翻译需人工 | 英文原文需人工翻译为中文，无机器辅助 | 耗时长，门槛高 |
| 原文获取繁琐 | 先手动复制原文 → 手动分段 → 手动翻译 | 整个流程全靠手 |
| 数据与模板耦合 | 数据和 HTML 模板通过正则嵌入，无模板引擎 | 改样式需操作带数据的 HTML |

### 当前技术栈

- **前端**：纯 HTML + CSS + JS（零依赖，~8KB 模板 + JSON 数据内嵌）
- **后端**：Python 脚本（`generate_data_agent.py`、`regenerate_fix_life.py`、`embed_data.py`、`fix_en_formatting.py`）
- **数据格式**：JSON，结构为 `{title, author, sections: [{id, title, pairs: [{en, zh}]}]}`
- **部署**：GitHub Pages，静态文件直接托管

---

## 二、功能方案分析

### 2.1 模板化（数据与展示分离）

**目标**：将 HTML 中的 CSS/JS 框架抽离为模板，数据独立注入，一键构建。

**技术方案**：**Jinja2**（Python 原生模板引擎）

理由：
- 与现有 Python 工具链无缝集成
- 语法简洁（`{{ var }}`、`{% for %}`），学习成本低
- 自带 autoescape，防止 XSS（HTML 格式化内容安全输出）
- 支持模板继承，多文章可共享同一套布局

**替代方案对比**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| Jinja2 | Python 原生，与现有脚本统一 | 需 `pip install jinja2` |
| Nunjucks | JS 版 Jinja2，可在浏览器端渲染 | 需要 Node.js 运行时 |
| Mustache/Handlebars | 跨语言，逻辑少 | 功能弱，无模板继承 |
| 纯 JS 模板字面量 | 零依赖 | 可维护性差 |

**实现要点**：

1. 创建 `templates/reader.html.j2`，提取当前 HTML 的结构部分
2. 数据注入点：`{{ title }}`、`{{ author }}`，`{% for section in sections %}` 循环
3. CSS/JS 保留在模板中（不抽离），保持单文件部署能力
4. `builder.py` 作为统一构建入口：读 JSON + 数据 → 渲染模板 → 输出 HTML
5. 保留内嵌数据方式（`var data = {{ data_json }};`），确保单文件可离线使用

### 2.2 Markdown 解析器

**目标**：自动解析原文 Markdown → 提取段落、保留格式 → 生成结构化 JSON 数据。

**技术方案**：**mistune**（Python Markdown 解析器）

理由：
- 纯 Python，与工具链一致
- AST 遍历模式，可精确控制输出
- 支持 GFM 表格、脚注、任务列表
- 插件系统（highlight、math 等）

**替代方案对比**：

| 方案 | 优点 | 缺点 |
|------|------|------|
| mistune | 轻量，AST 可遍历，Python | 生态不如 markdown-it |
| markdown-it-py | JS markdown-it 的 Python 移植 | 稍重 |
| marked.js (JS) | 最流行的 JS MD 解析器 | 需要 Node，与 Python 链割裂 |
| Python-Markdown | 老牌方案 | API 较旧，AST 操作不直观 |

**段落映射策略（核心难点）**：

```
输入：英文 MD + 中文 MD
  ↓ mistune 解析为 AST
  ↓ 按标题层级分段（h1 → section, h2 → sub-section）
  ↓ 逐段配对：按段落序号对齐 en[i] ↔ zh[i]
  ↓ 保留内联格式：bold → <strong>、italic → <em>、code → <code>
  ↓ 输出：标准 JSON（{title, author, sections: [{id, title, pairs: [{en, zh}]}]}）
```

**格式保留对照表**：

| Markdown | HTML 输出 | 用途 |
|----------|-----------|------|
| `**bold**` | `<strong>bold</strong>` | 强调关键词 |
| `*italic*` / `_italic_` | `<em>italic</em>` | 术语标注 |
| `` `code` `` | `<code>code</code>` | 代码/变量名 |
| `> quote` | `<blockquote>quote</blockquote>` | 引用 |
| `1. list` / `- list` | `<ol><li>` / `<ul><li>` | 列表 |
| `\| table \|` | `<table>` | 表格数据 |
| `---` / `***` | `<hr>` | 分隔线 |
| `[text](url)` | `<a href="url">text</a>` | 超链接 |

### 2.3 智能翻译

**目标**：自动将英文段落翻译为中文，保留 HTML 格式标签，产出可直接使用的双语对照数据。

**技术方案**：**分层翻译策略**

```
第一层：DeepL API（主力）
  - EN→ZH 翻译质量业界最佳
  - 支持 HTML 标签保留（tag_handling=html）
  - 成本：$25/百万字符（Pro 版）

第二层：Anthropic Claude API（兜底 + 复杂段落）
  - 上下文理解强，可处理长段落
  - 可在 prompt 中指定术语表、风格
  - 成本：$15/百万 token（Opus 4）

第三层：缓存层（本地 JSON）
  - 已翻译段落持久化缓存
  - 相同原文命中缓存直接返回
  - 人工校对后标记 verified: true
```

**实施方案**：

```python
# translate.py 核心流程
def translate_article(md_path: str, target_lang: str = "zh"):
    segments = parse_markdown(md_path)  # 复用 2.2 的解析器
    cache = load_cache(md_path)          # 加载本地翻译缓存

    for seg in segments:
        if seg.hash in cache:
            seg.translation = cache[seg.hash]  # 命中缓存
        else:
            seg.translation = call_deepl(seg.text)  # 或 call_claude(seg.text)
            cache[seg.hash] = seg.translation

    save_cache(md_path, cache)           # 持久化缓存
    return segments
```

**关键设计决策**：

- **翻译粒度**：按段落翻译（非逐句、非全文），在速度和质量间取得平衡
- **上下文窗口**：将前后各 1 段作为上下文传入（翻译时更连贯）
- **格式保护**：DeepL 的 `tag_handling=html` 模式，或 Claude prompt 中明确要求保留 HTML 标签
- **人工审查**：最终输出标记 `verified: false`，提供 diff 视图供人工校对

**成本估算**（以 Agent 综述为例，约 8000 词）：

| 方案 | 成本 | 质量 | 速度 |
|------|------|------|------|
| DeepL | ~$0.50 | 良好 | 5-10 秒 |
| Claude Opus | ~$0.30 | 优秀 | 15-30 秒 |
| Claude Haiku | ~$0.02 | 可接受 | 3-5 秒 |
| DeepL + 人工校对 | ~$0.50 + 30min | 最佳 | — |

推荐默认使用 **DeepL** 作为主力引擎，Claude Opus 处理 DeepL 返回低置信度的段落。

### 2.4 点击变色增强

**目标**：点击段落时更流畅的视觉反馈，增强阅读体验。

**技术方案**：纯 CSS 动画 + 少量 JS

当前实现：
```css
.pair.active {
  border-left: 3px solid var(--accent);
  background: var(--highlight-bg);
}
.pair.active .line {
  font-weight: 500;
  color: var(--accent);
}
```

**增强方案**（零依赖，纯 CSS）：

```css
/* 1. 过渡动画 */
.pair {
  transition: background 0.3s ease, border-color 0.3s ease;
}

/* 2. 左右滑入指示条 */
.pair.active::before {
  content: '';
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 3px;
  background: var(--accent);
  animation: slideIn 0.25s ease-out;
}
@keyframes slideIn {
  from { transform: scaleY(0); }
  to   { transform: scaleY(1); }
}

/* 3. 点击波纹 */
.pair.active::after {
  animation: ripple 0.6s ease-out;
}
@keyframes ripple {
  0%   { box-shadow: 0 0 0 0 var(--accent-glow); }
  100% { box-shadow: 0 0 0 12px transparent; }
}

/* 4. 未读/已读状态 */
.pair.read .line { opacity: 0.6; }
.pair.read.active .line { opacity: 1; }
```

**JS 增强**：

```javascript
// 点击自动滚动到视口中央（已有 scrollIntoView）
// 增加：键盘导航 j/k 上下移动激活段落
document.addEventListener('keydown', (e) => {
  if (e.key === 'j') moveHighlight(1);   // 下一段
  if (e.key === 'k') moveHighlight(-1);  // 上一段
  if (e.key === 'm') markAsRead();       // 标记已读
});
```

注意：所有增强保持 CSS 变量驱动，深色模式下自动适配。

### 2.5 原文自动获取

**目标**：从 URL（公众号文章、博客、Medium 等）自动抓取正文，输出干净的 Markdown。

**技术方案**：**trafilatura**（Python 网页正文提取）

理由：
- 专业正文提取库，自动过滤导航/广告/评论区
- 输出格式可选：Markdown、XML、TXT
- 支持中文网页优化
- 比 newspaper3k 更活跃维护（2024 年仍有更新）

**平台适配**：

| 平台 | 方案 | 备注 |
|------|------|------|
| 通用博客/Medium | trafilatura 直接抓取 | 90% 场景可用 |
| 微信公众号 | 需要特殊处理 | 公众号文章常需 Cookie，建议手动复制粘贴 |
| Substack | trafilatura + 邮件原文 | Substack 网页版正文提取良好 |
| 知乎专栏 | trafilatura | 中等效果，部分反爬 |
| RSS/Atom Feed | feedparser 解析 | 最稳定的方式 |

**CLI 设计**：

```bash
# 从 URL 抓取
python fetch.py --url "https://lilianweng.github.io/posts/2023-06-23-agent/" --output article-en.md

# 从本地文件（公众号复制粘贴的场景）
python fetch.py --file article.txt --output article-en.md

# 交互式：打开编辑器人工整理
python fetch.py --url "..." --interactive
```

**实现架构**：

```
URL 输入
  → trafilatura.fetch_url() 下载 HTML
    → trafilatura.extract() 提取正文（Markdown 格式）
      → 后处理：清理残留广告、规范化空行、统一标点
        → 输出 article-en.md
```

**局限性与应对**：

1. **JS 渲染页面**：trafilatura 不走 JS，如页面完全 SPA 渲染则需 playwright 降级方案
2. **微信公众号限制**：通常需要 Cookies + User-Agent，建议提供"手动粘贴原文"的降级路径
3. **图片处理**：正文中的图片默认保留 `![](url)` 引用，可选本地化下载

---

## 三、完整工具链设计

### 3.1 新工具链

```
                        ┌─────────────────┐
                        │   原文获取       │
                        │  fetch.py       │
                        │  URL → MD       │
                        └────────┬────────┘
                                 │ article-en.md
                                 ▼
┌─────────────────┐    ┌─────────────────┐
│  中文翻译稿      │    │  Markdown 解析   │
│  article-zh.md  │    │  parse.py       │
│  (可选，人工)    │    │  MD → segments  │
└────────┬────────┘    └────────┬────────┘
         │                      │ segments (list[Segment])
         ▼                      ▼
┌─────────────────────────────────────────┐
│           翻译引擎                       │
│  translate.py                           │
│  segments → translated segments         │
│  (DeepL / Claude / 缓存 / 人工校对)      │
└────────────────────┬────────────────────┘
                     │ bilingual segments
                     ▼
┌─────────────────────────────────────────┐
│           数据组装                       │
│  assemble.py                            │
│  segments → data.json                   │
│  (标准格式，含 en/zh/formatting)         │
└────────────────────┬────────────────────┘
                     │ data.json
                     ▼
┌─────────────────────────────────────────┐
│           构建输出                       │
│  builder.py                             │
│  data.json + template → index.html      │
│           + template → html/*.html      │
└────────────────────┬────────────────────┘
                     │ html/
                     ▼
              GitHub Pages 部署
```

### 3.2 目录结构演进

```
bilingual-reader/
├── builder.py              # 统一构建入口（替代 embed_data.py）
├── fetch.py                # 原文获取 CLI
├── parse.py                # Markdown 解析器
├── translate.py            # 智能翻译引擎
├── assemble.py             # 数据组装器
├── config.yaml             # 项目配置（翻译引擎、路径等）
├── requirements.txt        # Python 依赖
│
├── templates/
│   ├── base.html.j2        # 基础布局模板（CSS + JS 框架）
│   ├── reader.html.j2      # 阅读页模板（继承 base）
│   └── index.html.j2       # 文章索引页模板
│
├── articles/               # 文章源文件
│   └── agent-survey/
│       ├── article-en.md   # 英文原文（fetch 或手写）
│       ├── article-zh.md   # 中文翻译（可选，人工或机翻）
│       ├── metadata.yaml   # 元数据（标题、作者、日期）
│       └── cache.json      # 翻译缓存
│
├── data/                   # 构建中间产物
│   ├── data-agent.json     # 组装后的双语数据
│   └── data-fix-life.json
│
├── output/                 # 构建输出
│   ├── index.html          # 文章索引页
│   └── html/
│       ├── agent-survey.html
│       └── fix-life.html
│
├── plans/                  # 升级方案文档
│   └── upgrade-v2.md
│
└── .github/workflows/
    └── deploy.yml          # CI：自动构建 + 部署
```

### 3.3 单命令构建

```bash
# 完整流程：从 MD 到 HTML
python builder.py build articles/agent-survey/

# 仅重新构建（使用已有 data.json）
python builder.py build articles/agent-survey/ --skip-translate

# 构建全部文章
python builder.py build-all

# 新建文章脚手架
python builder.py new "My Article Title"
```

---

## 四、兼容性分析

### 4.1 现有 HTML 输出保持

| 现有文件 | v2 对应 | 兼容策略 |
|----------|---------|----------|
| `html/LLM-Powered-Autonomous-Agents.html` | `output/html/agent-survey.html` | 内容保持一致，模板渲染后 CSS/JS 行为不变 |
| `html/How-to-Fix-Your-Entire-Life-in-1-Day.html` | `output/html/fix-life.html` | 同上 |
| `index.html` | `output/index.html` | 卡片列表增加元数据展示 |

### 4.2 JSON 数据格式

v1 格式保持不变，v2 作为超集向后兼容：

```json
// v1 兼容字段
{
  "title": "...",
  "author": "...",
  "sections": [
    {
      "id": "part1",
      "title": "...",
      "pairs": [
        {"en": "...", "zh": "..."}
      ]
    }
  ],
  // v2 新增字段（可选）
  "_meta": {
    "version": "2.0",
    "source_url": "https://...",
    "translated_by": "deepel",
    "translated_at": "2026-05-27",
    "verified": false
  }
}
```

### 4.3 CSS/JS 行为不变

模板化后，CSS 变量名、类名、DOM 结构保持完全一致，确保：
- 深色模式切换：`body.dark` 类不变
- 语言切换：`body.lang-zh` / `body.lang-en` 类不变
- 高亮逻辑：`.pair.active` 类不变
- 英文在前/中文在前：`body.swapped` 类不变
- localStorage 持久化逻辑不变

### 4.4 URL 路由不变

GitHub Pages 部署路径保持不变：
- `https://xxx.github.io/bilingual-reader/` → 索引页
- `https://xxx.github.io/bilingual-reader/html/xxx.html` → 文章页

---

## 五、优先级排序

### 优先级矩阵

```
                高影响
                  │
     Phase 2     │   Phase 1
    Markdown     │   模板化
    解析器       │
                  │
  ───────────────┼────────────────
                  │
     Phase 4     │   Phase 3
    智能翻译     │   点击增强
                  │
     Phase 5     │
    URL 抓取     │
                  │
                低影响
   高成本                    低成本
```

### 最终排序

| 优先级 | Phase | 名称 | 理由 |
|--------|-------|------|------|
| **P0** | Phase 1 | 模板化 | 低风险、高回报，是所有后续 Phase 的基础；不改变用户体验，纯工程优化 |
| **P1** | Phase 2 | Markdown 解析器 | 解决最大痛点（手动配 JSON），直接提效 5-10x |
| **P2** | Phase 3 | 点击增强 | 低成本、纯前端改动，独立性强，可并行开发 |
| **P3** | Phase 4 | 智能翻译 | 需要 API key 和预算，需在 Phase 2 稳定后再接入 |
| **P4** | Phase 5 | URL 抓取 | 技术最复杂、外部依赖最多，放在最后 |

---

## 六、分 Phase 实施计划

### Phase 1：模板化（预计 1-2 天）

**目标**：将 HTML 结构抽离为 Jinja2 模板，统一构建流程。

**Checklist**：

- [ ] 安装 Jinja2：`pip install jinja2 pyyaml`
- [ ] 创建 `requirements.txt`
- [ ] 创建 `templates/base.html.j2`：
  - 提取当前文章页的 `<head>`（meta、字体、CSS 变量、全局样式）
  - 提取 `.header`、按钮栏（swap / dark / lang）
  - 提取 `<script type="module">` 中的渲染逻辑（`renderAll`、`toggleHighlight` 等）
  - 数据注入点：`{{ data_json }}`（内嵌到 `var data = {{ data_json }};`）
- [ ] 创建 `templates/index.html.j2`：
  - 提取当前 `index.html` 结构
  - 文章列表数据注入：`{% for article in articles %}`
- [ ] 创建 `builder.py`：
  - `build_article(json_path, output_path)`：读 JSON → 渲染 reader 模板 → 输出 HTML
  - `build_index(articles_meta, output_path)`：读元数据列表 → 渲染 index 模板 → 输出 HTML
  - `build_all()`：遍历 `data/` 目录批量构建
- [ ] 创建 `config.yaml` 配置文件
- [ ] 验证：用现有 `data-agent.json` 构建，对比输出 HTML 与现有 HTML 的 diff（功能无回归）
- [ ] 更新 `TEMPLATE.md` 文档

**产出物**：

```
templates/base.html.j2
templates/reader.html.j2
templates/index.html.j2
builder.py
config.yaml
requirements.txt
```

---

### Phase 2：Markdown 解析器（预计 3-5 天）

**目标**：从 Markdown 原文自动生成结构化 JSON 数据。

**Checklist**：

- [ ] 安装 mistune：`pip install mistune`
- [ ] 创建 `parse.py`：
  - `parse_markdown(file_path)` → 返回段落列表
  - AST 遍历：识别 h1-h6（标题层级）、p（段落）、blockquote（引用）、list（列表）、code_block（代码块）、table（表格）
  - 标题映射规则：h2 → section，h3 → sub-section title pair（en 为空）
  - 内联格式保留：strong → `<strong>`，em → `<em>`，codespan → `<code>`，link → `<a href>`
  - 列表项合并：连续 li 项合并为一个 HTML 字符串（`<ul><li>...</li></ul>`）
  - 代码块映射：`<pre><code>...</code></pre>`
  - 输出格式：标准 JSON（`{title, author, sections: [{id, title, pairs: [{en, zh}]}]}`）
- [ ] 创建段落对齐算法：
  - 同时解析 `article-en.md` 和 `article-zh.md`
  - 按标题层级对齐 section
  - section 内按段落序号对齐 pairs
  - 处理不匹配情况（标记 `_align_warning: true`）
- [ ] 测试：用 Fix Life 的原始 MD 和现有 JSON 做对比，校验段落映射正确率
- [ ] 迁移现有文章：
  - 将 Fix Life 数据转为 `articles/fix-life/article-en.md` + `article-zh.md`
  - 将 Agent 综述数据转为 `articles/agent-survey/article-en.md` + `article-zh.md`
  - 验证 `parse.py` 生成的 JSON 与原有 `data-*.json` 内容一致

**产出物**：

```
parse.py
articles/fix-life/article-en.md
articles/fix-life/article-zh.md
articles/fix-life/metadata.yaml
articles/agent-survey/article-en.md
articles/agent-survey/article-zh.md
articles/agent-survey/metadata.yaml
```

---

### Phase 3：点击增强（预计 1 天）

**目标**：增强阅读交互体验，纯前端改动。

**Checklist**：

- [ ] CSS 过渡动画：
  - `.pair` 添加 `transition: background 0.3s ease, border-color 0.3s ease`
  - `.pair.active::before` 添加 `slideIn` 动画（指示条从中间向两端展开）
  - `.pair.active::after` 添加 `ripple` 效果（可选，保持节制）
- [ ] 已读状态：
  - 点击段落自动添加 `.read` 类
  - localStorage 持久化已读段落列表
  - 页面加载时恢复已读状态
  - 已读段落文字 opacity 降低，激活时恢复
- [ ] 键盘导航：
  - `j` / `↓`：下一段
  - `k` / `↑`：上一段
  - `Escape`：清除高亮（已有此逻辑，保留）
  - 导航时自动 `scrollIntoView({behavior: 'smooth', block: 'center'})`
- [ ] 进度指示：
  - 页面顶部添加细进度条 `width: (readCount / totalPairs) * 100%`
  - CSS 变量 `--progress` 驱动
- [ ] 移动端适配：触摸点击动画保持一致
- [ ] 深色模式验证：所有新增动画在 dark 模式下颜色正确

**产出物**：

```
templates/base.html.j2（CSS 和 JS 增强部分）
```

---

### Phase 4：智能翻译（预计 3-5 天）

**目标**：自动翻译英文段落为中文，产出可校对的双语数据。

**Checklist**：

- [ ] 获取 API Key：
  - DeepL API（注册 DeepL Developer，免费额度 50 万字符/月）
  - 或 Anthropic API（已有的话可直接用）
- [ ] 创建 `translate.py`：
  - `translate_text(text, engine="deepel")`：单段翻译
  - `translate_article(en_segments, zh_segments=None)`：全文翻译
  - 上下文传递：翻译当前段时携带前一段的译文作为 context
  - HTML 标签保留：DeepL 使用 `tag_handling=html`，Claude 使用 system prompt 约束
  - 速率控制：DeepL 限流，增加 `time.sleep(0.5)` 间隔
- [ ] 缓存层：
  - 翻译结果存入 `articles/{name}/cache.json`
  - key = `hashlib.md5(segment.text.encode()).hexdigest()[:12]`
  - 相同原文命中缓存直接返回
  - 人工校对后标记 `verified: true`
- [ ] 标记逻辑：
  - 机翻段落自动标记 `_translated: true, _verified: false`
  - 人工校对后改为 `_verified: true`
  - 构建时可选仅输出已校对段落（`--only-verified`）
- [ ] 降级策略：
  - DeepL 不可用时自动切换 Claude Haiku（最便宜）
  - 全部不可用时提示用户手动翻译
- [ ] 测试：
  - 用已有人工翻译的 Fix Life 数据做回译测试（ZH→EN），评估翻译质量
  - 对比机翻 vs 人工翻译的 BLEU 分（参考值，不作为硬性门槛）

**产出物**：

```
translate.py
articles/*/cache.json
```

---

### Phase 5：URL 抓取（预计 2-3 天）

**目标**：从网页 URL 自动提取正文为 Markdown 原文。

**Checklist**：

- [ ] 安装依赖：`pip install trafilatura feedparser readability-lxml`
- [ ] 创建 `fetch.py`：
  - `fetch_url(url)` → 下载 HTML → trafilatura 提取正文 → 输出 Markdown
  - `fetch_file(file_path)` → 纯文本/Markdown 文件规范化
  - `fetch_rss(feed_url)` → 解析 RSS feed，列出文章列表
- [ ] URL 智能识别：
  - 检测 URL 域名，选择策略：
    - `medium.com` / `substack.com` → trafilatura（高置信度）
    - `mp.weixin.qq.com` → 提示手动复制粘贴（公众号限制多）
    - `zhihu.com` → trafilatura + 额外 CSS selector
    - 其他 → trafilatura 默认策略
- [ ] 后处理管道：
  - 清理残留广告文本
  - 统一空行（连续 3+ 空行合并为 2 行）
  - 全半角标点规范化
  - 去除社交分享按钮文本
  - 图片 alt 文本补全
- [ ] 交互模式：
  - `python fetch.py --url "..." --interactive`
  - 打开 `$EDITOR` 让用户编辑提取结果
  - 保存到 `articles/{slug}/article-en.md`
- [ ] 脚手架命令：
  - `python builder.py new --url "..."` 一键：fetch → 保存 MD → 创建目录
  - 或 `python builder.py new --title "..."` 仅创建空目录结构

**产出物**：

```
fetch.py
```

---

## 七、风险与缓解

| 风险 | 概率 | 影响 | 缓解措施 |
|------|------|------|----------|
| Markdown 段落对齐错误 | 中 | 高 | 对齐算法加人工校验步骤，生成 diff 报告 |
| 翻译质量不达标 | 中 | 中 | 默认标记 `verified: false`，提供 diff 校对视图，关键文章人工翻译 |
| 微信公众平台反爬升级 | 高 | 低 | 提供手动粘贴原文的降级路径，不依赖全自动 |
| Jinja2 模板迁移遗漏细节 | 低 | 中 | 构建后自动对比新老 HTML 的 DOM 结构 diff |
| API 费用超预期 | 低 | 中 | 本地缓存 + 速率限制 + 支持低成本模型切换 |
| trafilatura 提取正文不完整 | 中 | 中 | 交互模式人工编辑，支持手动粘贴原文 |

---

## 八、总结

### 从 v1 到 v2 的核心变化

```
v1：手动一切                     v2：自动流水线
─────────────────────────────────────────────────
手写 Python 生成 JSON    →    Markdown 自动解析 + 段落对齐
人工逐段翻译             →    DeepL / Claude 自动翻译 + 人工校对
正则嵌入 HTML            →    Jinja2 模板引擎 + 构建命令
各脚本独立零散           →    统一 CLI：fetch → parse → translate → build
新文章从头写脚本         →    一个命令脚手架 + 逐步填充
```

### 不变的部分

- 单文件 HTML 输出（内嵌数据，离线可用）
- CSS 变量主题系统
- GitHub Pages 零成本部署
- 50/50 双语对照布局
- 所有现有交互行为（高亮、切换、深色模式）

### 下一步

1. 评审本方案，确认优先级
2. 从 **Phase 1 模板化** 开始实施
3. 每完成一个 Phase，用现有 2 篇文章验证无回归
4. Phase 2 完成后即可用新流程产出一篇新文章，端到端验证工具链
