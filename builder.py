#!/usr/bin/env python3
"""bilingual-reader v2 builder — MD or JSON → single-file HTML"""

import sys, os, json, re, subprocess

BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_PATH = os.path.join(BASE, "template.html")
ARTICLES_DIR  = os.path.join(BASE, "articles")

TRANSLATE_PROMPT = """Translate the following Markdown to Chinese.
CRITICAL: Preserve ALL Markdown formatting EXACTLY. Keep the same number of paragraphs.
Output ONLY the translated Markdown. No explanations."""

def translate(slug):
    """Translate en.md → zh.md via Claude API"""
    en_path = os.path.join(ARTICLES_DIR, slug, "en.md")
    zh_path = os.path.join(ARTICLES_DIR, slug, "zh.md")
    if not os.path.exists(en_path):
        print(f"ERROR: {en_path} not found")
        return False
    with open(en_path, encoding="utf-8") as f:
        en_text = f.read()
    print(f"Translating {slug} ({len(en_text)} chars)...")
    try:
        import anthropic
        client = anthropic.Anthropic()
        msg = client.messages.create(model="claude-sonnet-4-20250514", max_tokens=16000,
            system=TRANSLATE_PROMPT, messages=[{"role":"user","content":en_text}])
        zh_text = msg.content[0].text
    except:
        proc = subprocess.run(["claude","-p","--dangerously-skip-permissions","--output-format","text",
            TRANSLATE_PROMPT+"\n\n"+en_text], capture_output=True, text=True, timeout=300,
            env={**os.environ})
        zh_text = proc.stdout.strip()
    with open(zh_path, "w", encoding="utf-8") as f:
        f.write(zh_text)
    print(f"Translated: {zh_path} ({len(zh_text)} chars)")
    return True

def build(slug, title, author=""):
    """Build single-file HTML from JSON or MD source"""
    adir = os.path.join(ARTICLES_DIR, slug)
    json_path = os.path.join(adir, "data.json")
    
    # Determine format
    if os.path.exists(json_path):
        with open(json_path) as f:
            data = json.load(f)
        data["title"] = title
        data["author"] = author
    else:
        en_path = os.path.join(adir, "en.md")
        zh_path = os.path.join(adir, "zh.md")
        if not os.path.exists(en_path) or not os.path.exists(zh_path):
            print(f"ERROR: Need {en_path} and {zh_path} (or data.json). Run 'python builder.py translate {slug}' first.")
            return False
        with open(en_path) as f: en_md = f.read()
        with open(zh_path) as f: zh_md = f.read()
        # Strip YAML frontmatter
        en_md = re.sub(r'^---\n.*?\n---\n\n', '', en_md, flags=re.DOTALL)
        zh_md = re.sub(r'^---\n.*?\n---\n\n', '', zh_md, flags=re.DOTALL)
        data = {"title": title, "author": author, "en_md": en_md, "zh_md": zh_md}

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    html = template.replace("{{TITLE}}", title)
    html = html.replace("{{AUTHOR}}", author)
    html = html.replace("{{DATA_JSON}}", json.dumps(data, ensure_ascii=False))

    out = f"{slug}.html"
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Built: {out} ({len(html):,} bytes)")
    return True

def build_index():
    articles = []
    if os.path.isdir(ARTICLES_DIR):
        for slug in sorted(os.listdir(ARTICLES_DIR)):
            meta = os.path.join(ARTICLES_DIR, slug, "metadata.yaml")
            title = slug; author = ""; desc = ""
            if os.path.exists(meta):
                try:
                    import yaml
                    with open(meta) as f: m = yaml.safe_load(f)
                    title = m.get("title", slug); author = m.get("author", ""); desc = m.get("description", "")
                except: pass
            articles.append({"slug":slug,"title":title,"author":author,"desc":desc})
    html = """<!DOCTYPE html><html lang="zh-CN"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"><title>Bilingual Reader</title>
<style>:root{--bg:#fff;--text:#1a1a2e;--accent:#4f46e5;--border:#e5e5e7;--hl:rgba(79,70,229,.06)}
body.dark{--bg:#0f0f13;--text:#e4e4ec;--accent:#818cf8;--border:#2a2a35}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--text);font-family:-apple-system,'PingFang SC',sans-serif;min-height:100vh;display:flex;flex-direction:column;align-items:center;padding:80px 32px}
h1{font-size:1.5rem;margin-bottom:6px}.sub{color:var(--accent);font-size:.875rem;margin-bottom:48px}
.card{width:100%;max-width:600px;border:1px solid var(--border);border-radius:10px;padding:24px 28px;margin-bottom:14px;transition:all .15s;text-decoration:none;color:inherit;display:block}
.card:hover{border-color:var(--accent);box-shadow:0 2px 12px rgba(79,70,229,.08)}
.card h2{font-size:1.1rem;margin-bottom:6px}.card p{font-size:.84rem;color:#71717a;line-height:1.5}
.dark-btn{position:fixed;top:20px;right:20px;padding:6px 16px;border:1px solid var(--border);border-radius:6px;background:var(--bg);color:var(--accent);cursor:pointer;font-size:.8rem}
</style></head><body><button class="dark-btn" onclick="document.body.classList.toggle('dark')">🌙</button><h1>📖 Bilingual Reader</h1><p class="sub">中英双语对照阅读 · 点击高亮 · 深色模式</p>"""
    for a in articles:
        html += f'<a class="card" href="{a["slug"]}.html"><h2>{a["title"]}</h2><p>{a["author"]}{" · "+a["desc"] if a["desc"] else ""}</p></a>\n'
    html += '<p style="margin-top:32px;color:#a1a1aa;font-size:.78rem"><a href="https://github.com/guocongcongcong/bilingual-reader" style="color:inherit">GitHub</a></p></body></html>'
    with open("index.html","w") as f: f.write(html)
    print(f"Built index ({len(articles)} articles)")

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "help"
    if cmd == "build":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        title = sys.argv[3] if len(sys.argv) > 3 else slug
        author = sys.argv[4] if len(sys.argv) > 4 else ""
        if slug: build(slug, title, author); build_index()
    elif cmd == "translate":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        if slug: translate(slug)
    elif cmd == "all":
        for slug in sorted(os.listdir(ARTICLES_DIR)):
            meta = os.path.join(ARTICLES_DIR, slug, "metadata.yaml")
            title = slug; author = ""
            if os.path.exists(meta):
                try:
                    import yaml
                    with open(meta) as f: m = yaml.safe_load(f)
                    title = m.get("title", slug); author = m.get("author", "")
                except: pass
            build(slug, title, author)
        build_index()
    elif cmd == "new":
        slug = sys.argv[2] if len(sys.argv) > 2 else None
        if slug:
            os.makedirs(os.path.join(ARTICLES_DIR, slug), exist_ok=True)
            print(f"Created articles/{slug}/")
    else:
        print("builder.py v2 — commands: new, translate, build, all")
