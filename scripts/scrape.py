#!/usr/bin/env python3
"""
Dynamic page scraper — extracts content from JS-rendered pages.
Supports: WeChat, Zhihu, Bilibili, Juejin, CSDN, 知乎, and general SPAs.

Usage:
  python3 scrape.py <URL>                    # smart extract (text)
  python3 scrape.py <URL> --chrome           # force Chrome headless
  python3 scrape.py <URL> --raw              # output raw HTML
  python3 scrape.py <URL> --images          # extract image URLs
  python3 scrape.py <URL> --links           # extract all links
  python3 scrape.py <URL> --meta            # extract metadata only
  python3 scrape.py <URL> --json            # output as JSON
  python3 scrape.py <URL> --select "div.content"  # CSS-like selector
"""

import sys
import re
import html
import json
import urllib.request
import subprocess
import shutil
import argparse
from typing import Optional, Dict, List, Any
from urllib.parse import urlparse, urljoin


# ─── Site-specific configs ────────────────────────────────────────────

SITE_CONFIGS = {
    'mp.weixin.qq.com': {
        'name': 'WeChat',
        'selectors': [
            r'id="js_content"[^>]*>(.*?)</div>',
            r'class="rich_media_content[^"]*"[^>]*>(.*?)</div>',
        ],
        'title_patterns': [
            r'var msg_title\s*=\s*["\'](.+?)["\']',
            r'<h1[^>]*class="[^"]*rich_media_title[^"]*"[^>]*>(.*?)</h1>',
        ],
        'meta_patterns': {
            'author': r'var nickname\s*=\s*["\'](.+?)["\']',
            'date': r'var ct\s*=\s*["\'](\d+)["\']',
            'description': r'var msg_desc\s*=\s*["\'](.+?)["\']',
        },
    },
    'zhuanlan.zhihu.com': {
        'name': 'Zhihu',
        'selectors': [
            r'class="Post-RichTextContainer[^"]*"[^>]*>(.*?)</div>',
            r'class="RichText[^"]*"[^>]*>(.*?)</div>',
        ],
        'title_patterns': [
            r'<h1[^>]*class="[^"]*Post-Title[^"]*"[^>]*>(.*?)</h1>',
        ],
        'meta_patterns': {
            'author': r'class="AuthorInfo-name[^"]*"[^>]*>.*?<a[^>]*>(.*?)</a>',
        },
    },
    'www.zhihu.com': {
        'name': 'Zhihu',
        'selectors': [
            r'class="RichContent-inner[^"]*"[^>]*>(.*?)</div>',
        ],
        'title_patterns': [
            r'<h1[^>]*class="[^"]*QuestionHeader-title[^"]*"[^>]*>(.*?)</h1>',
        ],
    },
    'www.bilibili.com': {
        'name': 'Bilibili',
        'selectors': [
            r'class="desc-info-text[^"]*"[^>]*>(.*?)</div>',
            r'class="basic-desc-info[^"]*"[^>]*>(.*?)</div>',
        ],
        'title_patterns': [
            r'<h1[^>]*class="[^"]*video-title[^"]*"[^>]*>(.*?)</h1>',
        ],
    },
    'juejin.cn': {
        'name': 'Juejin',
        'selectors': [
            r'class="article-content[^"]*"[^>]*>(.*?)</div>',
            r'id="article-root"[^>]*>(.*?)</div>',
        ],
        'title_patterns': [
            r'<h1[^>]*class="[^"]*article-title[^"]*"[^>]*>(.*?)</h1>',
        ],
        'meta_patterns': {
            'author': r'class="author-name[^"]*"[^>]*>(.*?)</span>',
        },
    },
    'blog.csdn.net': {
        'name': 'CSDN',
        'selectors': [
            r'id="article_content"[^>]*>(.*?)</article>',
            r'class="article_content[^"]*"[^>]*>(.*?)</div>',
        ],
        'title_patterns': [
            r'<h1[^>]*class="[^"]*title-article[^"]*"[^>]*>(.*?)</h1>',
        ],
        'meta_patterns': {
            'author': r'class="follow-nickName[^"]*"[^>]*>(.*?)</a>',
            'date': r'class="time[^"]*"[^>]*>(.*?)</span>',
        },
    },
    'segmentfault.com': {
        'name': 'SegmentFault',
        'selectors': [
            r'class="article-content[^"]*"[^>]*>(.*?)</div>',
        ],
        'title_patterns': [
            r'<h1[^>]*class="[^"]*title[^"]*"[^>]*>(.*?)</h1>',
        ],
    },
    'mp.weixin.qq.com/s/': {
        'name': 'WeChat Article',
        'inherit': 'mp.weixin.qq.com',
    },
}


# ─── Scraping engines ─────────────────────────────────────────────────

def scrape_mobile_ua(url: str) -> Optional[str]:
    """Try mobile UA to get server-rendered HTML."""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Linux; Android 10; Pixel 3) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/91.0.4472.120 Mobile Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'identity',
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode('utf-8', errors='ignore')
    except Exception:
        return None


def scrape_desktop_ua(url: str) -> Optional[str]:
    """Try desktop UA."""
    headers = {
        'User-Agent': (
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/120.0.0.0 Safari/537.36'
        ),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
        'Accept-Encoding': 'identity',
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        resp = urllib.request.urlopen(req, timeout=15)
        return resp.read().decode('utf-8', errors='ignore')
    except Exception:
        return None


def scrape_chrome(url: str) -> Optional[str]:
    """Use Chrome headless --dump-dom."""
    chrome_paths = [
        '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
        shutil.which('google-chrome'),
        shutil.which('chromium'),
        shutil.which('chrome'),
    ]
    chrome = next((p for p in chrome_paths if p), None)
    if not chrome:
        print("Warning: Chrome not found", file=sys.stderr)
        return None

    try:
        result = subprocess.run(
            [chrome, '--headless=new', '--disable-gpu', '--no-sandbox',
             '--dump-dom', '--virtual-time-budget=5000', url],
            capture_output=True, text=True, timeout=25,
        )
        if result.returncode == 0 and len(result.stdout) > 500:
            return result.stdout
        return None
    except (subprocess.TimeoutExpired, Exception):
        return None


# ─── Content extraction ───────────────────────────────────────────────

def get_site_config(url: str) -> Optional[Dict]:
    """Get site-specific config based on URL."""
    parsed = urlparse(url)
    host = parsed.netloc

    # Exact match first
    if host in SITE_CONFIGS:
        cfg = SITE_CONFIGS[host]
        if 'inherit' in cfg:
            cfg = SITE_CONFIGS.get(cfg['inherit'], cfg)
        return cfg

    # Path-based match (e.g., mp.weixin.qq.com/s/xxx)
    for pattern, cfg in SITE_CONFIGS.items():
        if pattern in host or pattern in url:
            if 'inherit' in cfg:
                cfg = SITE_CONFIGS.get(cfg['inherit'], cfg)
            return cfg

    return None


def extract_title(html_text: str, config: Optional[Dict]) -> str:
    """Extract page title."""
    # Try site-specific patterns first
    if config:
        for pat in config.get('title_patterns', []):
            match = re.search(pat, html_text, re.DOTALL)
            if match:
                return clean_text(match.group(1))

    # Generic patterns
    generic_patterns = [
        r'<h1[^>]*>(.*?)</h1>',
        r'<title[^>]*>(.*?)</title>',
        r'var msg_title\s*=\s*["\'](.+?)["\']',
    ]
    for pat in generic_patterns:
        match = re.search(pat, html_text, re.DOTALL)
        if match:
            text = clean_text(match.group(1))
            if text and len(text) > 2:
                return text

    return ''


def extract_content(html_text: str, config: Optional[Dict]) -> str:
    """Extract main content from HTML."""
    # Try site-specific selectors
    if config:
        for pat in config.get('selectors', []):
            match = re.search(pat, html_text, re.DOTALL)
            if match:
                content = match.group(1)
                cleaned = clean_html(content)
                if len(cleaned) > 50:
                    return cleaned

    # Generic fallback selectors
    generic_selectors = [
        r'id="js_content"[^>]*>(.*?)</div>',
        r'class="rich_media_content[^"]*"[^>]*>(.*?)</div>',
        r'<article[^>]*>(.*?)</article>',
        r'class="post-content[^"]*"[^>]*>(.*?)</div>',
        r'class="article-content[^"]*"[^>]*>(.*?)</div>',
        r'class="content[^"]*"[^>]*>(.*?)</div>',
    ]
    for pat in generic_selectors:
        match = re.search(pat, html_text, re.DOTALL)
        if match:
            content = match.group(1)
            cleaned = clean_html(content)
            if len(cleaned) > 50:
                return cleaned

    # Last resort: strip scripts/styles and get all text
    cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html_text, flags=re.DOTALL)
    cleaned = re.sub(r'<style[^>]*>.*?</style>', '', cleaned, flags=re.DOTALL)
    return clean_html(cleaned)


def extract_meta(html_text: str, config: Optional[Dict]) -> Dict[str, str]:
    """Extract metadata (author, date, description)."""
    meta = {}

    if config:
        for key, pat in config.get('meta_patterns', {}).items():
            match = re.search(pat, html_text, re.DOTALL)
            if match:
                meta[key] = clean_text(match.group(1))

    # Generic meta extraction
    if 'author' not in meta:
        match = re.search(r'<meta[^>]*name="author"[^>]*content="([^"]*)"', html_text)
        if match:
            meta['author'] = match.group(1)

    if 'description' not in meta:
        match = re.search(r'<meta[^>]*name="description"[^>]*content="([^"]*)"', html_text)
        if match:
            meta['description'] = match.group(1)

    return meta


def extract_images(html_text: str, base_url: str) -> List[str]:
    """Extract all image URLs from HTML."""
    images = set()
    for match in re.finditer(r'<img[^>]*(?:src|data-src)=["\']([^"\']+)["\']', html_text):
        url = match.group(1)
        if url.startswith(('http://', 'https://')):
            images.add(url)
        elif url.startswith('//'):
            images.add('https:' + url)
        elif url.startswith('/'):
            parsed = urlparse(base_url)
            images.add(f"{parsed.scheme}://{parsed.netloc}{url}")

    # Also check for background-image URLs
    for match in re.finditer(r'background-image:\s*url\(["\']?([^"\')]+)["\']?\)', html_text):
        url = match.group(1)
        if url.startswith(('http://', 'https://')):
            images.add(url)

    return sorted(images)


def extract_links(html_text: str, base_url: str) -> List[Dict[str, str]]:
    """Extract all links from HTML."""
    links = []
    seen = set()

    for match in re.finditer(r'<a[^>]*href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', html_text, re.DOTALL):
        url, text = match.group(1), match.group(2)
        text = clean_text(text)

        if not url or url.startswith(('#', 'javascript:')):
            continue

        # Normalize URL
        if url.startswith('//'):
            url = 'https:' + url
        elif url.startswith('/'):
            parsed = urlparse(base_url)
            url = f"{parsed.scheme}://{parsed.netloc}{url}"

        if url not in seen and text:
            seen.add(url)
            links.append({'text': text[:100], 'url': url})

    return links


def extract_text_from_selector(html_text: str, selector: str) -> str:
    """Extract content using a simple CSS-like selector (tag, id, class)."""
    # Convert simple selectors to regex
    if selector.startswith('#'):
        # ID selector: #content -> id="content"
        pat = rf'id="{selector[1:]}"[^>]*>(.*?)</'
    elif selector.startswith('.'):
        # Class selector: .content -> class="content"
        pat = rf'class="[^"]*{selector[1:]}[^"]*"[^>]*>(.*?)</'
    else:
        # Tag selector: article -> <article>...</article>
        pat = rf'<{selector}[^>]*>(.*?)</{selector}>'

    match = re.search(pat, html_text, re.DOTALL)
    if match:
        return clean_html(match.group(1))
    return ''


# ─── Utility functions ────────────────────────────────────────────────

def clean_text(text: str) -> str:
    """Clean text content."""
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def clean_html(content: str) -> str:
    """Clean HTML to readable text."""
    text = re.sub(r'<br\s*/?>', '\n', content)
    text = re.sub(r'<p[^>]*>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<div[^>]*>', '\n', text)
    text = re.sub(r'<h[1-6][^>]*>', '\n## ', text)
    text = re.sub(r'</h[1-6]>', '\n', text)
    text = re.sub(r'<li[^>]*>', '\n- ', text)
    text = re.sub(r'<[^>]+>', '', text)
    text = html.unescape(text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [l.strip() for l in text.split('\n') if l.strip()]
    return '\n'.join(lines)


def detect_site(url: str) -> str:
    """Detect which site this URL belongs to."""
    config = get_site_config(url)
    if config:
        return config.get('name', 'Unknown')
    return urlparse(url).netloc


# ─── Main ─────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description='Dynamic page scraper — extract content from JS-rendered pages',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "https://mp.weixin.qq.com/s/xxx"           # WeChat article
  %(prog)s "https://zhuanlan.zhihu.com/p/xxx"         # Zhihu article
  %(prog)s "https://juejin.cn/post/xxx"               # Juejin post
  %(prog)s "https://example.com" --images             # Extract images
  %(prog)s "https://example.com" --meta               # Extract metadata
  %(prog)s "https://example.com" --json               # JSON output
        """,
    )
    parser.add_argument('url', help='URL to scrape')
    parser.add_argument('--chrome', action='store_true', help='Force Chrome headless mode')
    parser.add_argument('--raw', action='store_true', help='Output raw HTML')
    parser.add_argument('--images', action='store_true', help='Extract image URLs')
    parser.add_argument('--links', action='store_true', help='Extract all links')
    parser.add_argument('--meta', action='store_true', help='Extract metadata only')
    parser.add_argument('--json', action='store_true', dest='json_output', help='Output as JSON')
    parser.add_argument('--select', help='Extract from specific selector (e.g., div.content)')
    args = parser.parse_args()

    url = args.url
    config = get_site_config(url)
    site_name = detect_site(url)

    # Fetch HTML
    html_text = None
    if not args.chrome:
        html_text = scrape_mobile_ua(url)
        if not html_text:
            html_text = scrape_desktop_ua(url)
    if not html_text:
        html_text = scrape_chrome(url)
    if not html_text:
        print("Error: Could not fetch page content", file=sys.stderr)
        sys.exit(1)

    # Raw HTML output
    if args.raw:
        print(html_text)
        return

    # JSON output
    if args.json_output:
        result = {
            'url': url,
            'site': site_name,
            'title': extract_title(html_text, config),
            'content': extract_content(html_text, config) if not args.meta else '',
            'meta': extract_meta(html_text, config),
        }
        if args.images:
            result['images'] = extract_images(html_text, url)
        if args.links:
            result['links'] = extract_links(html_text, url)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return

    # Selector-based extraction
    if args.select:
        content = extract_text_from_selector(html_text, args.select)
        if content:
            print(content)
        else:
            print(f"Warning: selector '{args.select}' matched nothing", file=sys.stderr)
        return

    # Images only
    if args.images:
        images = extract_images(html_text, url)
        if images:
            print(f"Found {len(images)} images:\n")
            for img in images:
                print(img)
        else:
            print("No images found")
        return

    # Links only
    if args.links:
        links = extract_links(html_text, url)
        if links:
            print(f"Found {len(links)} links:\n")
            for link in links:
                print(f"[{link['text']}] {link['url']}")
        else:
            print("No links found")
        return

    # Meta only
    if args.meta:
        meta = extract_meta(html_text, config)
        title = extract_title(html_text, config)
        if title:
            print(f"Title: {title}")
        for key, value in meta.items():
            print(f"{key.capitalize()}: {value}")
        if not meta and not title:
            print("No metadata found")
        return

    # Default: extract content
    title = extract_title(html_text, config)
    content = extract_content(html_text, config)

    if title:
        print(f"# {title}\n")
    print(content)


if __name__ == '__main__':
    main()
