#!/usr/bin/env python3
"""bilingual-reader v2 builder — 翻译 + 构建单文件 HTML"""

import sys, os, json, re, subprocess, shutil

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE, "template.html")
ARTICLES_DIR  = os.path.join(BASE, "articles")
OUTPUT_DIR    = os.path.join(BASE, ".")

# ============ 翻译 ============

TRANSLATE_PROMPT = """Translate the following Markdown to Chinese.

CRITICAL RULES:
1. Preserve ALL Markdown formatting EXACTLY — **bold**, *italic*, `code`, > blockquote, lists, code blocks, links, tables, images.
2. Do NOT change any Markdown syntax characters.
3. Keep the EXACT same number of paragraphs (separated by blank lines).
4. Output ONLY the translated Markdown. No explanations, no notes."""

def translate(slug, engine="claude"):
    """翻译 en.md → zh.md，保留全部 MD 格式"""
    articles_dir = os.path.join(ARTICLES_DIR, slug)
    en_path = os.path.join(articles_dir, "en.md")
    zh_path = os.path.join(articles_dir, "zh.md")

    if not os.path.exists(en_path):
        print(f"ERROR: {en_path} not found")
        return False

    with open(en_path, encoding="utf-8") as f:
        en_text = f.read()

    print(f"Translating {slug} ({len(en_text)} chars)...")

    if engine == "claude":
        # 使用 Anthropic API 直接调用（更可靠）
        try:
            import anthropic
            api_key = os.environ.get("ANTHROPIC_API_KEY")
            if not api_key:
                print("WARNING: ANTHROPIC_API_KEY not set, trying claude CLI...")
                raise ImportError

            client = anthropic.Anthropic(api_key=api_key)
            msg = client.messages.create(
                model="claude-sonnet-4-20250514",
                max_tokens=16000,
                system=TRANSLATE_PROMPT,
                messages=[{"role": "user", "content": en_text}]
            )
            zh_text = msg.content[0].text
        except (ImportError, Exception) as e:
            print(f"API fallback: using claude CLI ({e})")
            # Fallback to CLI
            with open(en_path) as f:
                en_text = f.read()
            proc = subprocess.run(
                ["claude", "-p", "--dangerously-skip-permissions", "--output-format", "text",
                 TRANSLATE_PROMPT + "\n\n" + en_text],
                capture_output=True, text=True, timeout=300,
                cwd=BASE, env={**os.environ, "ANTHROPIC_API_KEY": os.environ.get("ANTHROPIC_API_KEY", "")}
            )
            zh_text = proc.stdout.strip()
            if proc.returncode != 0:
                print(f"Claude CLI error: {proc.stderr[:200]}")
                return False
    else:
        print(f"Unknown engine: {engine}")
        return False

    with open(zh_path, "w", encoding="utf-8") as f:
        f.write(zh_text)
    print(f"Translated: {zh_path} ({len(zh_text)} chars)")
    return True

# ============ 构建 ============

def build(slug, title, author=""):
    """将 en.md + zh.md 注入模板，生成单文件 HTML"""
    articles_dir = os.path.join(ARTICLES_DIR, slug)
    en_path = os.path.join(articles_dir, "en.md")
    zh_path = os.path.join(articles_dir, "zh.md")

    for p in [en_path, zh_path]:
        if not os.path.exists(p):
            print(f"ERROR: {p} not found. Run 'python builder.py translate {slug}' first.")
            return False

    with open(en_path, encoding="utf-8") as f: en_md = f.read()
    with open(zh_path, encoding="utf-8") as f: zh_md = f.read()
    with open(TEMPLATE_PATH, encoding="utf-8") as f: template = f.read()

    html = template.replace("{{TITLE}}", title)
    html = html.replace("{{AUTHOR}}", author)
    html = html.replace("{{EN_MD_JSON}}", json.dumps(en_md, ensure_ascii=False))
    html = html.replace("{{ZH_MD_JSON}}", json.dumps(zh_md, ensure_ascii=False))

    os.makedirs(OUTPUT_DIR, exist_ok=True)
    out_path = os.path.join(OUTPUT_DIR, f"{slug}.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Built: {out_path} ({len(html):,} bytes)")
    return True

def build_index():
    """生成文章索引页"""
    articles = []
    if os.path.isdir(ARTICLES_DIR):
        for slug in sorted(os.listdir(ARTICLES_DIR)):
            meta_path = os.path.join(ARTICLES_DIR, slug, "metadata.yaml")
            title = slug
            author = ""
            desc = ""
            if os.path.exists(meta_path):
                try:
                    import yaml
                    with open(meta_path) as f:
                        meta = yaml.safe_load(f)
                    title = meta.get("title", slug)
                    author = meta.get("author", "")
                    desc = meta.get("description", "")
                except:
                    pass
            articles.append({"slug": slug, "title": title, "author": author, "desc": desc})

    index_html = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bilingual Reader · 双语阅读</title>
<style>
  :root{--bg:#fff;--text:#1a1a2e;--accent:#4f46e5;--border:#e5e5e7;--hl:rgba(79,70,229,.06)}
  body.dark{--bg:#0f0f13;--text:#e4e4ec;--accent:#818cf8;--border:#2a2a35;--hl:rgba(129,140,248,.08)}
  *{box-sizing:border-box;margin:0;padding:0}
  body{background:var(--bg);color:var(--text);font-family:-apple-system,'PingFang SC',sans-serif;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:80px 32px}
  h1{font-size:1.5rem;margin-bottom:6px}
  .sub{color:var(--accent);font-size:.875rem;margin-bottom:48px}
  .card{width:100%;max-width:600px;border:1px solid var(--border);border-radius:10px;padding:24px 28px;margin-bottom:14px;transition:all .15s;text-decoration:none;color:inherit;display:block}
  .card:hover{border-color:var(--accent);box-shadow:0 2px 12px rgba(79,70,229,.08)}
  .card h2{font-size:1.1rem;margin-bottom:6px}
  .card p{font-size:.84rem;color:#71717a;line-height:1.5}
  .dark-btn{position:fixed;top:20px;right:20px;padding:6px 16px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--accent);cursor:pointer;font-size:.8rem}
</style>
</head>
<body>
<button class="dark-btn" onclick="document.body.classList.toggle('dark')">🌙</button>
<h1>📖 Bilingual Reader</h1>
<p class="sub">中英双语对照阅读 · 点击高亮 · 深色模式</p>
"""
    for a in articles:
        index_html += f'<a class="card" href="{a["slug"]}.html"><h2>{a["title"]}</h2><p>{a["author"]}{" · " + a["desc"] if a["desc"] else ""}</p></a>\n'
    index_html += '<p style="margin-top:32px;color:#a1a1aa;font-size:.78rem"><a href="https://github.com/guocongcongcong/bilingual-reader" style="color:inherit">GitHub</a></p>\n</body>\n</html>'

    out_path = os.path.join(OUTPUT_DIR, "index.html")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(index_html)
    print(f"Built index: {out_path} ({len(articles)} articles)")

# ============ CLI ============

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"

    if cmd == "build":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        title = sys.argv[3] if len(sys.argv) > 3 else slug
        author = sys.argv[4] if len(sys.argv) > 4 else ""
        if not slug:
            print("Usage: python builder.py build <slug> [title] [author]")
            sys.exit(1)
        build(slug, title, author)
        build_index()

    elif cmd == "translate":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        engine = sys.argv[3] if len(sys.argv) > 3 else "claude"
        if not slug:
            print("Usage: python builder.py translate <slug> [engine]")
            sys.exit(1)
        translate(slug, engine)

    elif cmd == "all":
        for slug in sorted(os.listdir(ARTICLES_DIR)):
            meta_path = os.path.join(ARTICLES_DIR, slug, "metadata.yaml")
            title = slug
            author = ""
            if os.path.exists(meta_path):
                try:
                    import yaml
                    with open(meta_path) as f:
                        meta = yaml.safe_load(f)
                    title = meta.get("title", slug)
                    author = meta.get("author", "")
                except:
                    pass
            if not os.path.exists(os.path.join(ARTICLES_DIR, slug, "zh.md")):
                translate(slug)
            build(slug, title, author)
        build_index()

    elif cmd == "new":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        title = sys.argv[3] if len(sys.argv) > 3 else slug
        if not slug:
            print("Usage: python builder.py new <slug> [title]")
            sys.exit(1)
        os.makedirs(os.path.join(ARTICLES_DIR, slug), exist_ok=True)
        en_path = os.path.join(ARTICLES_DIR, slug, "en.md")
        if not os.path.exists(en_path):
            with open(en_path, "w") as f:
                f.write(f"# {title}\n\n")
            print(f"Created: {en_path}")
        print(f"Ready: articles/{slug}/ (add en.md, then 'python builder.py translate {slug}')")

    else:
        print("bilingual-reader v2 builder")
        print("  python builder.py new <slug> [title]       Create new article directory")
        print("  python builder.py translate <slug>           Translate en.md → zh.md")
        print("  python builder.py build <slug> [title] [author]  Build HTML")
        print("  python builder.py all                        Translate + build all articles")
