# Bilingual Reader Template

Single-file HTML (~8KB), zero dependencies, GitHub Pages ready.

## Features

- **50/50 flex columns** — `flex: 0 0 50%` strict equal width
- **Click highlight** — toggle pair highlighting, Esc to clear
- **EN⇄ZH swap** — CSS `order` swap, addEventListener binding
- **Dark mode** — `body.dark` CSS variables + localStorage persistence
- **Mobile responsive** — stacked layout ≤768px
- **Zero build** — just `index.html` + `data.json`

## Quick start

1. Create `data.json`:

```json
{
  "title": "Your Title · 你的标题",
  "author": "Author",
  "sections": [
    {
      "id": "intro",
      "title": "Section Title",
      "pairs": [
        { "en": "English text.", "zh": "中文翻译。" }
      ]
    }
  ]
}
```

2. Copy `index.html` from this repo
3. Open in browser or deploy to GitHub Pages

## Design

CSS variable-driven, two themes:

```css
:root {
  --bg: #ffffff;
  --text-primary: #1a1a2e;
  --accent: #4f46e5;
  --highlight-bg: rgba(79,70,229,0.06);
}
body.dark {
  --bg: #0f0f13;
  --text-primary: #e4e4ec;
  --accent: #818cf8;
  --highlight-bg: rgba(129,140,248,0.08);
}
```

## Pitfalls

- Use `flex: 0 0 50%`, NOT `flex: 1 1 50%` (content affects width with grow/shrink)
- `.swapped` order: en=1, zh=2 (NOT 2/1, which is identical to default)
- `.pair:hover` use `var(--highlight-bg)`, not hardcoded rgba
- Buttons use `addEventListener`, not onclick (`type="module"` scope)

## Demo

https://guocongcongcong.github.io/bilingual-reader/
