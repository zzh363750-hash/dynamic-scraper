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

## 🚀 API 服务部署

### 本地运行

```bash
cd api
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

访问 http://localhost:8000 查看文档和定价页面。

### Docker 部署

```bash
cd api
docker-compose up -d
```

### 云服务部署

推荐平台：
- [Railway](https://railway.app) — 免费额度，一键部署
- [Render](https://render.com) — 免费 tier
- [Fly.io](https://fly.io) — 免费额度

```bash
# Railway 示例
railway init
railway up
```

### API 使用

```bash
# 1. 获取 API Key
curl -X POST https://your-domain.com/api/keys \
  -H "Content-Type: application/json" \
  -d '{"plan": "free"}'

# 2. 调用爬虫 API
curl -X POST https://your-domain.com/api/scrape \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-key-here" \
  -d '{"url": "https://mp.weixin.qq.com/s/xxx"}'

# 3. 查看用量
curl https://your-domain.com/api/usage \
  -H "X-API-Key: your-key-here"
```

### 套餐定价

| 套餐 | 价格 | 限额 |
|------|------|------|
| Free | ¥0 | 10 次/天 |
| Basic | ¥9.9/月 | 1,000 次/月 |
| Pro | ¥49/月 | 无限次 |
