# Dynamic Scraper 🔍

[![GitHub stars](https://img.shields.io/github/stars/zzh363750-hash/dynamic-scraper?style=social)](https://github.com/zzh363750-hash/dynamic-scraper/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/zzh363750-hash/dynamic-scraper?style=social)](https://github.com/zzh363750-hash/dynamic-scraper/network/members)
[![GitHub issues](https://img.shields.io/github/issues/zzh363750-hash/dynamic-scraper)](https://github.com/zzh363750-hash/dynamic-scraper/issues)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)

> 从动态渲染的网页中提取内容，支持微信公众号、知乎、B站、掘金等主流中文网站。

## ✨ 特性

- 🚀 无需浏览器，纯 Python 实现
- 📱 移动端 UA 伪装，绕过客户端渲染
- 🔧 支持 7+ 主流中文网站
- 🖼️ 提取文本、图片、链接、元数据
- 📤 JSON 格式输出，方便管道处理

## 支持网站

| 网站 | 域名 | 状态 |
|------|------|------|
| 微信公众号 | mp.weixin.qq.com | ✅ |
| 知乎专栏 | zhuanlan.zhihu.com | ✅ |
| 知乎回答 | www.zhihu.com | ✅ |
| B站专栏 | www.bilibili.com | ✅ |
| 掘金 | juejin.cn | ✅ |
| CSDN | blog.csdn.net | ✅ |
| SegmentFault | segmentfault.com | ✅ |
| 其他SPA网站 | - | ✅ 通用fallback |

## 🚀 安装

```bash
# 克隆到 OpenClaw skills 目录
cd ~/.openclaw/skills
git clone https://github.com/zzh363750-hash/dynamic-scraper.git
```

## 📖 使用方法

```bash
SCRIPT=~/.openclaw/skills/dynamic-scraper/scripts/scrape.py

# 提取文本内容
python3 "$SCRIPT" "https://mp.weixin.qq.com/s/xxx"

# 提取图片URL
python3 "$SCRIPT" "https://example.com" --images

# 提取链接
python3 "$SCRIPT" "https://example.com" --links

# 提取元数据（作者、日期等）
python3 "$SCRIPT" "https://example.com" --meta

# JSON格式输出
python3 "$SCRIPT" "https://example.com" --json

# 指定选择器提取
python3 "$SCRIPT" "https://example.com" --select "#article-content"

# 强制使用Chrome无头模式
python3 "$SCRIPT" "https://example.com" --chrome
```

## 🔍 工作原理

```
请求 → 移动端UA → 成功? → 提取内容
              ↓ 失败
          桌面端UA → 成功? → 提取内容
                      ↓ 失败
                  Chrome无头 → 渲染 → 提取内容
```

1. **移动端UA请求** - 大多数中文网站对移动端返回预渲染的HTML
2. **桌面端UA降级** - 移动端失败时尝试桌面端
3. **Chrome无头模式** - 兜底方案，完全渲染JS后提取DOM
4. **站点专属规则** - 每个支持的网站都有优化的提取规则

## ❓ 为什么不用 curl/web_fetch？

很多现代网站（特别是微信公众号）使用客户端渲染，`curl` 拿到的是空壳HTML，内容由JavaScript动态加载。这个工具通过UA伪装和浏览器渲染来获取完整内容。

## 🤝 Contributing

欢迎提交 Issue 和 Pull Request！

## 📄 License

[MIT](LICENSE)
