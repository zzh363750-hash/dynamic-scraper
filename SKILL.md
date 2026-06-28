---
name: dynamic-scraper
description: "Scrape dynamically rendered web pages (WeChat, Zhihu, Bilibili, Juejin, CSDN, etc.) and extract clean text, images, links, or metadata."
---

# Dynamic Scraper

Extract content from JavaScript-rendered pages that `curl`/`web_fetch` can't handle.

## Supported sites

| Site | Config |
|------|--------|
| 微信公众号 (mp.weixin.qq.com) | ✅ auto |
| 知乎专栏 (zhuanlan.zhihu.com) | ✅ auto |
| 知乎回答 (www.zhihu.com) | ✅ auto |
| B站专栏 (www.bilibili.com) | ✅ auto |
| 掘金 (juejin.cn) | ✅ auto |
| CSDN (blog.csdn.net) | ✅ auto |
| SegmentFault (segmentfault.com) | ✅ auto |
| 其他SPA网站 | ✅ fallback |

## Usage

```bash
SCRIPT=~/.openclaw/skills/dynamic-scraper/scripts/scrape.py

# Default: smart extract (text)
python3 "$SCRIPT" "https://mp.weixin.qq.com/s/xxx"

# Force Chrome headless (for complex SPAs)
python3 "$SCRIPT" "https://example.com" --chrome

# Extract images only
python3 "$SCRIPT" "https://example.com" --images

# Extract links only
python3 "$SCRIPT" "https://example.com" --links

# Extract metadata (author, date, description)
python3 "$SCRIPT" "https://example.com" --meta

# JSON output (combines all)
python3 "$SCRIPT" "https://example.com" --json

# Extract specific element
python3 "$SCRIPT" "https://example.com" --select "#article-content"

# Raw HTML output
python3 "$SCRIPT" "https://example.com" --raw
```

## How it works

1. **Mobile UA fetch** — Many Chinese sites (WeChat, Zhihu) serve pre-rendered HTML to mobile clients
2. **Desktop UA fallback** — Try desktop UA if mobile fails
3. **Chrome headless** — Last resort for fully client-rendered SPAs
4. **Site-specific selectors** — Each supported site has optimized extraction patterns

## Tips

- WeChat articles: mobile UA almost always works, no Chrome needed
- Zhihu/Bilibili: mobile UA returns cleaner HTML
- Unknown sites: try without `--chrome` first, add it if content is empty
- Use `--json` for structured output when piping to other tools
