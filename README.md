# 微信公众号全量文章归档 · Computer Use 实战方法论

> 用 **Computer Use（视觉点击）** 把一个微信公众号的 **291 篇文章**完整落地：链接、正文 Markdown、互动数据（阅读/赞/转发/在看/评论/听全文）、语义分类、Obsidian 索引。
>
> 这不是一个"下载器"，而是一套 **在官方接口失效、现有 Agent 都做不了的情况下，如何用视觉操作把活干完** 的工程经验。

---

## 一、为什么会有这个项目

最初的需求很简单：把我长期读的一个公众号（《ThinkingSlow缓慢思考》）全部 291 篇文章下载下来，做成 Obsidian 知识库。

试过的路：

| 方案 | 结果 |
|---|---|
| 公众号历史消息接口 / 第三方下载 API | ❌ 接口已停用，返回验证页 |
| WorkBuddy（腾讯）内置的公众号下载能力 | ❌ 只能单篇，无法批量 |
| Codex / 其他 Computer Use Agent | ❌ 标签栏密集成图标后定位全乱，窗口合并丢标签 |
| 网页版下载站（changfengbox.top）批量粘贴 | ⚠️ 能用，但受限于站点限流与前端状态同步 |
| **WorkBuddy + DeepSeek Harness 的 Computer Use + 自建工具链** | ✅ **291 篇全部落地** |

**结论**：这类"脏"任务（窗口会抖动、标签会压缩、页面会限流）单靠模型点屏幕走不远，必须**自己搭工具**把不稳定环节隔离掉。

---

## 二、最终成果

| 产物 | 数量 |
|---|---|
| 原文链接（去重） | 290 条 |
| 正文 Markdown（清洗 + front-matter） | 291 篇 |
| 互动数据（赞/转发/在看/评论） | **291/291 = 100%** |
| 阅读数 | **291/291 = 100%** |
| 听全文人数 | 275/291 = 95% |
| 语义分类索引（7 类，MOC） | 1 份 |
| 底部栏截图数据集（可复用训练） | 276 篇 × 3 图 |

---

## 三、整体架构（6 个阶段）

```
┌─────────────────────────────────────────────────────────────┐
│ 阶段 1  链接采集      Computer Use 点开每篇 → 复制链接        │
│         工具：原生 socket 直连 CUA helper（免上下文截图）      │
├─────────────────────────────────────────────────────────────┤
│ 阶段 2  正文下载      网页批量粘贴 或 MCP 接口                │
│         工具：changfengbox MCP (JSON-RPC over HTTP)          │
├─────────────────────────────────────────────────────────────┤
│ 阶段 3  正文清洗      去页尾垃圾 / 去头像图 / 保留正文图       │
│         工具：Python 正则 + 结构规则                          │
├─────────────────────────────────────────────────────────────┤
│ 阶段 4  语义分类      7 大类 + 每篇 ≤3 个 tag                 │
│         工具：关键词级联 + 人工校正                           │
├─────────────────────────────────────────────────────────────┤
│ 阶段 5  互动数据      截图 → 连通域 → 图标模板 → 数字 kNN      │
│         工具：传统 CV（无需 GPU、无需训练大模型）              │
├─────────────────────────────────────────────────────────────┤
│ 阶段 6  Obsidian 化   front-matter + MOC 目录 + 双链          │
└─────────────────────────────────────────────────────────────┘
```

详细设计见 [docs/01-workflow.md](docs/01-workflow.md)。

---

## 四、三条最有价值的技术经验

### 1. 不要用 Agent 的截图接口调 UI，直连原生 socket

Agent 框架的 `screenshot` 工具会把图片塞进对话上下文，一张 ~2k token，几百次操作直接爆上下文。

解法：找到 CUA helper 的 **Unix socket**（`/tmp/dsh-cua-<uid>/<runtimeKey>.sock`），用 JSONL 协议自己发请求，截图直接落盘、离线分析，**零上下文开销**。

代码见 [scripts/cua_socket_client.mjs](scripts/cua_socket_client.mjs)。

### 2. 视觉识别不要指望 OCR 整行，要"结构化裁剪 + 部件分类"

微信底部操作栏是「图标 + 数字」紧贴排版，OCR 会把图标读成数字：

```
🎧 71人   → OCR 读成 671人   （耳机图标被读成 6）
👍 3      → OCR 单字符经常失败
在看=0    → 显示「写留言」三个字，不是数字
```

解法（纯传统 CV，CPU 0.15s/张）：

1. **二值化 + 连通域**把每个字形切出来
2. **图标用模板匹配**识别（4 个图标在全数据集里像素级一致，距离 0.0）
3. 图标右侧**间距连续的窄高连通域**才是数字
4. **数字不用 OCR**：把历史已确认的数字字形归一化聚类，建 0–9 模板库，最近邻分类
5. 数字区域若是宽字形（汉字）→ 判定为 0

结果：174 → 276 张截图，**解析成功率 100%**，抽样肉眼核对 29/29 一致。

### 3. 窗口不稳定时，先隔离再自动化

WeChat 窗口会：移动、被遮挡、标签压缩成图标、点错窗口控件导致窗口合并丢标签。

对策：**每次动作前检查窗口几何**（`WINDOW_CHANGED` 自动重试）、**标签操作前用 OCR 确认标签位置**、**永远不点窗口右上角的搜索/合并/关闭控件**。

完整踩坑清单见 [docs/02-pitfalls.md](docs/02-pitfalls.md)（20+ 条，每条都是真金白银）。

---

## 五、给其他模型的提示词

如果你想让别的 Computer Use Agent（Claude Computer Use / OpenAI Operator / 自建）复现这套流程：

- [prompts/agent-main.md](prompts/agent-main.md) —— 主控 Agent 的完整任务提示词
- [prompts/subagent-screenshot-parser.md](prompts/subagent-screenshot-parser.md) —— 截图解析子任务
- [prompts/subagent-attribution.md](prompts/subagent-attribution.md) —— 数据归属/校验子任务

---

## 六、快速开始

### 路径 A：只想要文章正文（推荐，10 分钟）

```bash
# 1. 拿到公众号全部文章链接（任意方式，本仓库 scripts/ 有 Computer Use 采集脚本）
# 2. 用 MCP 批量下载（需自备可用的微信文章下载 MCP 服务）
node scripts/download_via_mcp.mjs links.txt ./output
# 3. 清洗 + 生成 Obsidian front-matter
python3 scripts/clean_markdown.py ./output
python3 scripts/build_index.py ./output
```

### 路径 B：连互动数据一起要（完整复现，约 3 小时）

按 [docs/01-workflow.md](docs/01-workflow.md) 的 6 个阶段走，其中互动数据需要：

1. 逐篇打开截图（`scripts/capture_screenshots.mjs`，约 10s/篇）
2. 离线解析（`scripts/parse_bar.py` + `scripts/parse_listened.py`，秒级/张）
3. 回填 md（`scripts/backfill.py`）

---

## 七、目录结构

```
.
├── README.md
├── SKILL.md                    # WorkBuddy 技能入口（可直接安装）
├── config.yaml                 # WorkBuddy 技能元数据
├── docs/
│   ├── 01-workflow.md          # 六阶段完整工作流
│   ├── 02-pitfalls.md          # 踩坑清单
│   ├── 03-architecture.md      # 技术架构细节
│   └── 04-publishing.md        # 如何发布到各应用市场
├── prompts/                    # 给其他模型用的提示词
├── scripts/                    # 可复用脚本
└── examples/                   # 产物样例
```

---

## 八、合规与边界

- 本仓库只处理**你自己有权访问的公开文章**，不包含任何绕过登录/付费墙的手段
- 下载的正文仅用于个人阅读与知识管理，**请勿二次分发**
- 尊重公众号作者的版权；互动数据是公开可见的页面数字，仅作个人归档
- 脚本中不含任何站点密钥；MCP 服务需自备

---

## License

MIT（脚本代码） / CC BY-NC 4.0（文档）
