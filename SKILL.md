---
name: wechat-article-harvester
slug: wechat-article-harvester
version: 0.1.0
displayName: 微信公众号文章全量归档
summary: 把一个微信公众号的全部文章归档为 Markdown + Obsidian 知识库，并采集阅读/赞/转发/在看/评论/听全文数据。基于 Computer Use 截图管线 + 连通域/模板匹配解析，实测 291 篇互动数据 100% 覆盖。
license: MIT
description: 把一个微信公众号的全部文章归档为 Markdown + Obsidian 知识库，并采集阅读/赞/转发/在看/评论/听全文等互动数据。适用于「下载/备份某个公众号的全部文章」「把公众号存到 Obsidian」「采集公众号文章的阅读数点赞在看」等场景。触发词：公众号归档、公众号下载、公众号备份、采集公众号互动数据、存到 Obsidian。
agent_created: true
---

# 微信公众号文章全量归档

## Trigger

当用户说以下任意一种话时触发：

- "把某个公众号的全部文章下载下来"
- "公众号文章归档 / 备份"
- "把公众号文章存到 Obsidian / Notion"
- "采集公众号文章的阅读数、赞、在看、评论"
- 用户给出 `mp.weixin.qq.com` 链接并希望批量处理

## Instructions

1. **环境确认**（不通过就停下来问用户）
   - 微信 Mac 客户端已登录
   - 公众号文章列表窗口在**内建屏、单窗口**
   - Computer Use 有辅助功能 + 屏幕录制权限
   - 告知用户：采集期间不要切换窗口

2. **采集链接**：按 `docs/01-workflow.md` 阶段 1，每篇 4 步（点标题 → 点 ··· → 复制链接 → 回列表），后台剪贴板监听自动落盘。

3. **下载正文**：优先走 MCP 接口（`scripts/download_via_mcp.mjs`）；没有可用 MCP 时用网页批量下载（每批 10 条）。

4. **清洗**：`scripts/clean_markdown.py` —— 提取 front-matter、截断尾部垃圾、去头像图、保留正文图。

5. **分类**：`scripts/build_index.py` —— 7 类语义 tag（每篇 ≤3 个）+ Obsidian MOC 索引。

6. **互动数据**（用户要求时）：
   - `scripts/capture_screenshots.mjs` 逐篇截图（存 full/bar/hdr 三张，用发布时间命名）
   - `scripts/parse_bar.py` + `scripts/parse_listened.py` 离线解析
   - `scripts/backfill.py` 回填 front-matter

7. **交付**：md 目录 + `_目录.md` + `_互动数据核对表.xlsx`

## 铁律（违反会丢数据）

1. 点击前确认微信在前台（activate + 1.3s），否则点击被静默丢弃
2. 永不点击标签栏最右侧图标（窗口合并、标签全丢）
3. 永不点击菜单里的「关闭全部标签页」
4. 禁用 Cmd+W / Ctrl+Tab / Cmd+Shift+]
5. 每次动作前按 Esc 清残留菜单
6. 每步落盘，不要攒着

## Examples

**用户**：把「ThinkingSlow缓慢思考」这个号的文章都存下来，做成 Obsidian 库

**助手**：
1. 检查微信窗口状态 → 报告"窗口已就绪，共 291 篇，预计 2 小时"
2. 阶段 1 采集链接（后台监听剪贴板，每 10 篇报一次进度）
3. 阶段 2 MCP 下载（限流时退避重试）
4. 阶段 3-4 清洗 + 分类 + 生成索引
5. 交付：291 个 md + `_目录.md` + 核对表

## 参考

- 完整流程：`docs/01-workflow.md`
- 踩坑清单：`docs/02-pitfalls.md`
- 技术架构：`docs/03-architecture.md`
