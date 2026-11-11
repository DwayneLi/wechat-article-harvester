# 脚本说明

> ⚠️ 所有脚本里的路径都是原作者机器上的（`/Users/tg/...`），使用前替换成你自己的。
> 建议先读 `docs/01-workflow.md` 了解每个脚本在流程中的位置。

| 脚本 | 作用 | 阶段 | 依赖 |
|---|---|---|---|
| `cua_socket_client.mjs` | 直连 CUA 原生 Unix socket 取截图/点击，零上下文开销 | 1 / 5 | 无（Node 18+） |
| `wx_control.mjs` | 在 socket 客户端上封装微信窗口操作（截图/点击/滚动/按键 + 自动重试） | 1 / 5 | 上者 |
| `capture_screenshots.mjs` | 逐篇打开文章，保存 full/bar/hdr 三张截图 | 5 | 上两者 |
| `parse_bar.py` | 底部栏解析：连通域 + 图标模板 + 数字 kNN → 赞/转发/在看/评论 | 5 | Pillow |
| `parse_listened.py` | 顶部行解析：「🎧 N人」→ 听全文人数 | 5 | Pillow + numpy |
| `download_via_mcp.mjs` | MCP JSON-RPC 批量下载正文 md | 2 | Node 18+（fetch） |
| `clean_markdown.py` | 提取 front-matter、截断尾部垃圾、去头像图 | 3 | Python |
| `classify.py` | 关键词级联分类，输出 tags.json | 4 | Python |
| `build_index.py` | 写入 tags、生成 Obsidian MOC 目录 | 4 / 6 | Python |
| `backfill.py` | 按 publish 把解析结果回填 front-matter | 5 | Python |
| `build_report.py` | 生成核对表 xlsx | 6 | openpyxl |

## 使用顺序

```bash
# 阶段 1：采集链接（需要微信前台）
node scripts/capture_screenshots.mjs        # 先跑通单篇，确认能截图
# 链接采集脚本需要按 docs/01-workflow.md 阶段 1 自行组装（每篇 4 步）

# 阶段 2：下载正文
node scripts/download_via_mcp.mjs links.txt ./md

# 阶段 3：清洗
python3 scripts/clean_markdown.py

# 阶段 4：分类 + 索引
python3 scripts/classify.py && python3 scripts/build_index.py

# 阶段 5：互动数据
node scripts/capture_screenshots.mjs        # 逐篇截图（约 10s/篇）
python3 scripts/parse_bar.py                # 底部栏 → bar_parse.json
python3 scripts/parse_listened.py           # 顶部行 → listened.json
python3 scripts/backfill.py                 # 回填 md

# 阶段 6：核对表
python3 scripts/build_report.py
```

## 关键调参点

| 参数 | 位置 | 说明 |
|---|---|---|
| 二值化阈值 `140` | parse_bar.py / parse_listened.py | 深色 UI 主题需调低 |
| 图标尺寸 `28≤h≤48, w≥22` | parse_bar.py | 换分辨率/缩放比例要改 |
| 数字最大宽 `22` | parse_bar.py | 用于区分数字与汉字 |
| 图标-数字最大间距 `26px` | parse_bar.py | 防止把右边的小箭头算进来 |
| 点击前等待 `1300ms` | wx_control.mjs | 前台切换太慢时加大 |
| 页面加载等待 `3300ms` | capture_screenshots.mjs | 网络慢时加大到 6000 |
| 去重标题前缀长度 `4` | capture_screenshots.mjs | OCR 标题不稳定时用前缀去重 |
