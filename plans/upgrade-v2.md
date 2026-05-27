# Bilingual Reader v2 升级方案（最简版）

## 一、核心思路

**砍掉 MD → JSON → HTML 的复杂流程**。MD 本身就是数据源，翻译后的 MD 就是对照源。浏览器端用 marked.js 实时解析双栏渲染。

```
v1（现状）：手动写 Python 脚本 → JSON → 正则嵌入 HTML → 部署
v2（目标）：MD 原文 → Claude 翻译（保留格式）→ Python 构建 → 单 HTML 输出
```

## 二、整体架构

```
输入层: 给 Agent 文章名/URL → Agent 抓取 → articles/{slug}/en.md
翻译层: en.md → Claude API（保留全部 MD 格式）→ articles/{slug}/zh.md
构建层: python builder.py {slug} → 读取 MD + 模板注入 → output/{slug}.html
展示层: 浏览器打开 HTML → marked.js 解析双栏 MD → 点击高亮对照
```

## 三、最小文件清单（2 个源文件）

| # | 文件 | 职责 |
|---|------|------|
| 1 | `builder.py` | 一键构建脚本（~150 行），完成翻译 + HTML 生成 |
| 2 | `template.html` | HTML 骨架（~100 行），含 CSS 双栏布局 + marked.js + JS 交互逻辑 |

加上文章目录约定：
```
articles/
  fix-life/
    en.md    ← 英文原文（MD）
    zh.md    ← 中文译文（MD，格式完全保留）
  agent-survey/
    en.md
    zh.md
output/
  fix-life.html          ← 构建产出
  agent-survey.html
  index.html             ← 文章列表（从 builder.py 自动生成）
```

## 四、各文件核心逻辑

### 4.1 builder.py

```python
#!/usr/bin/env python3
"""bilingual-reader builder — 翻译 + 构建单文件 HTML"""

import sys, os, json, subprocess

TEMPLATE_PATH = "template.html"
ARTICLES_DIR  = "articles"
OUTPUT_DIR    = "output"

# ============ 翻译（通过 Claude CLI） ============

SYSTEM_PROMPT = """You are a translator. Translate the following Markdown to Chinese.
CRITICAL RULES:
1. Preserve ALL Markdown formatting EXACTLY — **bold**, *italic*, `code`, > blockquote, lists, code blocks, links, tables.
2. Do NOT change any Markdown syntax characters.
3. Output ONLY the translated Markdown, no explanations."""

def translate(slug):
    """调用 Claude CLI 翻译 en.md → zh.md"""
    en_path = f"{ARTICLES_DIR}/{slug}/en.md"
    zh_path = f"{ARTICLES_DIR}/{slug}/zh.md"
    os.makedirs(f"{ARTICLES_DIR}/{slug}", exist_ok=True)
    # 使用 claude CLI 或 Anthropic API 翻译
    # 实际使用时替换为真实 API 调用
    with open(en_path) as f:
        en_text = f.read()
    # 调用 Claude: en_text → zh_text（保留所有 MD 格式）
    # zh_text = call_claude(en_text, system=SYSTEM_PROMPT)
    with open(zh_path, 'w') as f:
        f.write(zh_text)  # placeholder
    print(f"Translated: {zh_path}")

# ============ 构建 HTML ============

def build(slug, title, author=""):
    """将 en.md + zh.md 注入模板，生成单文件 HTML"""
    en_path = f"{ARTICLES_DIR}/{slug}/en.md"
    zh_path = f"{ARTICLES_DIR}/{slug}/zh.md"

    with open(en_path) as f:
        en_md = f.read()
    with open(zh_path) as f:
        zh_md = f.read()
    with open(TEMPLATE_PATH) as f:
        template = f.read()

    # 安全嵌入 MD（JSON.stringify 处理所有特殊字符）
    html = template.replace("{{TITLE}}", title)
    html = html.replace("{{AUTHOR}}", author)
    html = html.replace("{{EN_MD_JSON}}", json.dumps(en_md, ensure_ascii=False))
    html = html.replace("{{ZH_MD_JSON}}", json.dumps(zh_md, ensure_ascii=False))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = f"{OUTPUT_DIR}/{slug}.html"
    with open(out_path, 'w') as f:
        f.write(html)
    print(f"Built: {out_path}")

# ============ CLI ============

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "build":
        slug = sys.argv[2]
        title = sys.argv[3] if len(sys.argv) > 3 else slug
        build(slug, title)
    elif cmd == "translate":
        translate(sys.argv[2])
    elif cmd == "all":
        # build-all: 遍历 articles/ 下所有目录
        for slug in os.listdir(ARTICLES_DIR):
            build(slug, slug)
    else:
        print("Usage: python builder.py {build|translate|all} [args]")
```

### 4.2 template.html（伪代码级）

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{{TITLE}} · Bilingual Reader</title>
<style>
  /* === CSS 变量（亮/暗双主题） === */
  :root {
    --bg: #ffffff; --text: #1a1a2e; --text-secondary: #52525b;
    --accent: #4f46e5; --border: #e5e5e7;
    --highlight-bg: rgba(79,70,229,0.06);
  }
  body.dark {
    --bg: #0f0f13; --text: #e4e4ec; --text-secondary: #9898a8;
    --accent: #818cf8; --border: #2a2a35;
    --highlight-bg: rgba(129,140,248,0.08);
  }

  /* === 双栏布局 === */
  body { max-width: 1040px; margin: 0 auto; padding: 40px 24px; font-family: -apple-system, sans-serif; background: var(--bg); color: var(--text); }

  .pair { display: flex; gap: 32px; padding: 12px 16px; margin: 0 -16px;
          border-radius: 6px; cursor: pointer; border-left: 2px solid transparent;
          transition: background 0.15s, border-color 0.15s; }
  .pair:hover { background: var(--highlight-bg); }
  .pair.active { background: var(--highlight-bg); border-left-color: var(--accent); }
  .pair + .pair { border-top: 1px solid var(--border); }

  .col-en, .col-zh { flex: 0 0 50%; min-width: 0; line-height: 1.7; color: var(--text-secondary); }
  .pair.active .col-en, .pair.active .col-zh { color: var(--text); }

  /* 全宽标题行 */
  .section-header { text-align: center; font-weight: 600; color: var(--accent);
                    margin: 40px 0 16px; padding-top: 40px; border-top: 1px solid var(--border); }
  .section-header:first-child { border-top: none; margin-top: 0; }

  /* MD 渲染内容样式 */
  .col-en strong, .col-zh strong { color: var(--text); }
  .col-en em, .col-zh em { font-style: italic; }
  .col-en code, .col-zh code { font-size: 0.875em; background: var(--highlight-bg); padding: 2px 6px; border-radius: 3px; }
  .col-en pre, .col-zh pre { background: var(--highlight-bg); padding: 12px 16px; border-radius: 6px; overflow-x: auto; font-size: 0.8125rem; }
  .col-en blockquote, .col-zh blockquote { border-left: 2px solid var(--accent); padding-left: 12px; margin: 8px 0; }
  .col-en ul, .col-zh ul, .col-en ol, .col-zh ol { padding-left: 20px; margin: 6px 0; }
  .col-en a, .col-zh a { color: var(--accent); }

  /* 响应式 */
  @media (max-width: 768px) {
    .pair { flex-direction: column; gap: 8px; }
    .col-zh { border-top: 1px solid var(--border); padding-top: 8px; }
  }

  /* 按钮 */
  .toolbar { display: flex; gap: 8px; margin: 12px 0 32px; flex-wrap: wrap; }
  .toolbar button { padding: 6px 16px; border: 1px solid var(--border); border-radius: 6px;
                    background: var(--bg); color: var(--accent); cursor: pointer; font-size: 0.8rem; }
  .toolbar button:hover { background: var(--highlight-bg); }
</style>
</head>
<body>

<div class="toolbar">
  <button id="swapBtn">⇄ 英中互换</button>
  <button id="darkBtn">🌙 关灯</button>
  <button id="langBtn">📖 双语</button>
</div>

<h1>{{TITLE}}</h1>
<p style="color:var(--text-secondary);font-size:0.875rem;margin-bottom:32px">{{AUTHOR}}</p>

<div id="content"></div>

<!-- marked.js CDN（或内嵌） -->
<script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
<!-- marked 配置 -->
<script>
  // 初始化 marked
  marked.setOptions({ breaks: true, gfm: true });
</script>

<script>
  // 数据注入（builder.py 替换）
  var EN_MD = {{EN_MD_JSON}};
  var ZH_MD = {{ZH_MD_JSON}};

  // ====== 段落切分与配对 ======
  // 按连续空行切分 block
  function splitBlocks(md) {
    return md.split(/\n\n+/).filter(function(b) { return b.trim(); });
  }

  var enBlocks = splitBlocks(EN_MD);
  var zhBlocks = splitBlocks(ZH_MD);
  var len = Math.min(enBlocks.length, zhBlocks.length);

  // ====== 渲染 ======
  var content = document.getElementById('content');
  var activeIdx = -1;

  for (var i = 0; i < len; i++) {
    var enHTML = marked.parse(enBlocks[i]);
    var zhHTML = marked.parse(zhBlocks[i]);

    // 判断是否为标题（h1-h6）
    var isHeader = /^<h[1-6]/.test(enHTML.trim()) || /^<h[1-6]/.test(zhHTML.trim());

    if (isHeader) {
      // 标题全宽渲染
      var h = document.createElement('div');
      h.className = 'section-header';
      h.innerHTML = (enHTML + ' / ' + zhHTML).replace(/<\/?h[1-6]>/g, '');
      content.appendChild(h);
    } else {
      // 正文双栏
      var pair = document.createElement('div');
      pair.className = 'pair';
      pair.dataset.idx = i;

      var enCol = document.createElement('div');
      enCol.className = 'col-en';
      enCol.innerHTML = enHTML;

      var zhCol = document.createElement('div');
      zhCol.className = 'col-zh';
      zhCol.innerHTML = zhHTML;

      pair.appendChild(zhCol);  // 中文在左
      pair.appendChild(enCol);  // 英文在右
      content.appendChild(pair);
    }
  }

  // 超出部分单独显示
  for (var j = len; j < enBlocks.length; j++) {
    var div = document.createElement('div');
    div.className = 'col-en';
    div.innerHTML = marked.parse(enBlocks[j]);
    content.appendChild(div);
  }
  for (var j = len; j < zhBlocks.length; j++) {
    var div = document.createElement('div');
    div.className = 'col-zh';
    div.innerHTML = marked.parse(zhBlocks[j]);
    content.appendChild(div);
  }

  // ====== 点击高亮 ======
  content.addEventListener('click', function(e) {
    var pair = e.target.closest('.pair');
    if (!pair) return;

    // 清除上一个
    var prev = document.querySelector('.pair.active');
    if (prev) prev.classList.remove('active');

    var idx = pair.dataset.idx;
    if (String(activeIdx) === idx) {
      activeIdx = -1;
      return;
    }
    pair.classList.add('active');
    activeIdx = parseInt(idx);
  });

  // Esc 清除
  document.addEventListener('keydown', function(e) {
    if (e.key === 'Escape') {
      var prev = document.querySelector('.pair.active');
      if (prev) prev.classList.remove('active');
      activeIdx = -1;
    }
    if (e.key === 'j') { /* 下一段 */ }
    if (e.key === 'k') { /* 上一段 */ }
  });

  // ====== 工具栏按钮 ======
  // 英中互换
  var swapped = false;
  document.getElementById('swapBtn').onclick = function() {
    swapped = !swapped;
    document.querySelectorAll('.pair').forEach(function(p) {
      p.style.flexDirection = swapped ? 'row-reverse' : '';
    });
  };

  // 暗色模式
  var dark = false;
  document.getElementById('darkBtn').onclick = function() {
    dark = !dark;
    document.body.classList.toggle('dark', dark);
    this.textContent = dark ? '☀️ 开灯' : '🌙 关灯';
    localStorage.setItem('dark', dark ? '1' : '0');
  };
  if (localStorage.getItem('dark') === '1') {
    document.getElementById('darkBtn').click();
  }

  // 语言切换（双语 / 仅中文 / 仅英文）
  var langIdx = 0;
  document.getElementById('langBtn').onclick = function() {
    langIdx = (langIdx + 1) % 3;
    document.body.classList.remove('lang-zh', 'lang-en');
    if (langIdx === 1) document.body.classList.add('lang-zh');
    if (langIdx === 2) document.body.classList.add('lang-en');
    this.textContent = ['📖 双语', '🇨🇳 中文', '🇬🇧 English'][langIdx];
  };
</script>

<style>
  body.lang-zh .col-en { display: none; }
  body.lang-zh .col-zh { flex: 1 1 auto; }
  body.lang-en .col-zh { display: none; }
  body.lang-en .col-en { flex: 1 1 auto; }
</style>

</body>
</html>
```

## 五、与现有代码的关系

### 5.1 迁移策略

现有 `data-*.json` 中的双语数据需要逆向导出为 `en.md` + `zh.md` 对：

```python
# 一次性迁移脚本（跑完即弃）
for s in data['sections']:
    for p in s['pairs']:
        en_md += strip_html(p['en']) + '\n\n'
        zh_md += strip_html(p['zh']) + '\n\n'
```

更实际的做法：直接用 Claude 从 JSON 还原 MD（因为 JSON 中的 en/zh 已经是 HTML 格式，需要反向转为 MD）。

### 5.2 现有文件处理

| 现有文件 | 处理方式 |
|----------|----------|
| `html/LLM-Powered-Autonomous-Agents.html` | 弃用。重建：获取原文 MD → 翻译 → builder.py 构建 |
| `html/How-to-Fix-Your-Entire-Life-in-1-Day.html` | 弃用。同 Agent 文章流程，但可使用 `如何在一天之内修复你的人生.md` 作为 en-MD 起点 |
| `html/index.html` | 替换为 `output/index.html`（builder.py 自动生成） |
| `data-*.json` | 归档（`archive/` 目录）。v2 不再使用 JSON 中间格式 |
| `generate_data_agent.py` | 归档 |
| `regenerate_fix_life.py` | 归档 |
| `embed_data.py` | 被 `builder.py` 替代，归档 |
| `fix_en_formatting.py` | 不再需要（格式保留由 Claude 翻译 prompt 保证），归档 |
| `如何在一天之内修复你的人生.md` | 保留作为 articles/fix-life/ 的源文件 |
| `index.html`（根目录） | 被 builder.py 自动生成的索引页替代 |
| `TEMPLATE.md` | 更新为 v2 说明 |

### 5.3 v2 新目录结构

```
bilingual-reader/
├── builder.py              ← 唯一脚本
├── template.html           ← HTML 骨架
├── archive/                ← v1 旧文件归档
│   ├── data-agent.json
│   ├── data-fix-life.json
│   ├── generate_data_agent.py
│   ├── regenerate_fix_life.py
│   ├── embed_data.py
│   └── fix_en_formatting.py
├── articles/
│   ├── fix-life/
│   │   ├── en.md
│   │   └── zh.md
│   └── agent-survey/
│       ├── en.md
│       └── zh.md
├── output/
│   ├── index.html
│   ├── fix-life.html
│   └── agent-survey.html
└── TEMPLATE.md
```

## 六、关键设计决策

### 6.1 为什么不用 Jinja2

**用原生字符串替换。** 只有 3 个替换点（`{{TITLE}}`、`{{EN_MD_JSON}}`、`{{ZH_MD_JSON}}`），`str.replace()` 足够。不引入额外依赖。

### 6.2 为什么不在 Python 端解析 MD

**在浏览器端解析。** Python 端解析 → JSON → HTML 的流程正是 v1 的痛点。v2 中 MD 原样传入 HTML，marked.js 直接在浏览器渲染。优势：
- 零格式损失（MD → MD，翻译过程不需要理解 MD 结构）
- 段落对应天然（按空行切分，按索引配对）
- 不需要维护 Python MD 解析器

### 6.3 为什么用 marked.js 而不是自己写渲染

marked.js 压缩后 ~30KB，可以 CDN 引入也可以内嵌。完整的 GFM 支持（表格、任务列表、代码高亮等）。如果对包大小敏感，可以只引入 marked 的 parser 部分（~15KB）。

### 6.4 段落配对策略

按 `\n\n+` 切分 MD 为 blocks → 按索引逐一配对 `en_blocks[i] ↔ zh_blocks[i]`。

- **标题检测**：marked 渲染后如果以 `<h1`–`<h6` 开头，渲染为全宽标题行
- **数量不匹配**：较短的优先配对，超出的部分单独显示
- **黄金法则**：Claude 翻译 prompt 要求"保持段落数量完全一致"，这保证了 99% 的情况下一一对应

## 七、未来 MCP 封装

builder.py 的核心逻辑可包装为 MCP 工具：

```python
# mcp_tool.py（未来文件）
def bilingual_build(url: str) -> str:
    """输入文章 URL，返回 HTML 文件路径"""
    slug = url_to_slug(url)
    fetch_article(url, f"articles/{slug}/en.md")
    translate(slug)          # Claude API
    build(slug, slug)        # 生成 HTML
    return f"output/{slug}.html"
```

MCP Server 暴露一个 endpoint：接收 URL → 返回 HTML 路径或 HTML 内容。Agent 可以直接调用。

## 八、实施步骤（Phase 1 完成全部）

| 步骤 | 内容 | 预计时间 |
|------|------|----------|
| 1 | 创建 `template.html`（双栏布局 + marked.js + JS 交互） | 1 小时 |
| 2 | 创建 `builder.py`（MD 读取 + 模板注入 + CLI） | 1 小时 |
| 3 | 测试：将 Fix Life 的 MD 原文转为 en.md，手动翻译 zh.md，执行构建 | 30 分钟 |
| 4 | 测试：用 Claude 翻译 Agent 综述（验证格式保留） | 30 分钟 |
| 5 | 迁移现有 2 篇文章 → articles/ + 构建 HTML | 30 分钟 |
| 6 | 归档 v1 旧文件到 archive/ | 10 分钟 |
| 7 | 更新 `TEMPLATE.md` 说明文档 | 15 分钟 |
| 8 | 验证：浏览器打开 output/*.html，测试高亮/切换/暗色模式/响应式 | 15 分钟 |

**总计：约 4 小时。**

## 九、风险

| 风险 | 缓解 |
|------|------|
| Claude 翻译时丢失 MD 格式 | System prompt 强调 + 输出后校验（检测 `**` 数量是否一致） |
| 中英段落数不一致 | builder.py 提示警告，标记不配对段落 |
| marked.js 渲染与原文意图偏差 | 所有 inline 格式（bold/italic/code/link）是标准 MD，marked 原生支持 |
