# 技术架构细节

本文讲三件事：**怎么绕过框架限制拿截图**、**怎么用传统 CV 稳定解析 UI**、**怎么让整条链路可复现**。

---

## 一、直连 CUA 原生 socket（绕过上下文爆炸）

### 原理

Computer Use 插件并不是在进程内截图，而是启动/复用一个 **helper app**（本项目里是 `DSH Computer Use.app`），通过 **Unix domain socket** 通信，协议是 **JSONL（一行一个 JSON）**。

找 socket：

```bash
ls /tmp/dsh-cua-<uid>/          # 里面有 <runtimeKey>.sock
# runtimeKey = sha256(helper 可执行文件)
shasum -a 256 "/Applications/.../DSH Computer Use.app/Contents/MacOS/dsh-cua-native"
```

### 握手

```js
socket.write(JSON.stringify({
  type: "hello", protocol: 1, runtimeKey,
  config: { maxRequestBytes, maxResponseBytes, axTimeoutMs,
            textEventIntervalMs, maxClickHoldMs,
            screenshotTimeoutMs, timeoutMs, graceMs }
}) + "\n");
// 服务端回一行 Ready（含 runtimeKey），之后即可发请求
```

### 请求格式

```js
{ id: "c1", method: "screenshot", params: { appHandle, windowId } }
{ id: "c2", method: "click",      params: { appHandle, windowId, x, y } }
{ id: "c3", method: "scroll",     params: { appHandle, windowId, x, y, deltaLinesX, deltaLinesY } }
{ id: "c4", method: "getApp",     params: { selector: "com.tencent.xinWeChat" } }
```

**关键**：坐标是 **window points**（窗口内坐标），不是屏幕坐标；截图返回的是像素图（可能被缩放），需要 `scale = bounds.width / pixelWidth` 换算。

### 收益

| | 框架 screenshot 工具 | 直连 socket |
|---|---|---|
| 上下文开销 | ~2000 token/张 | 0 |
| 速度 | 慢（序列化 + 注入） | 快（纯 socket） |
| 可控性 | 受限于工具封装 | 任意方法可调 |

---

## 二、用传统 CV 解析 UI（以微信底部操作栏为例）

### 输入

`bar.png`：窗口底部约 125px 高的条带，内容是：

```
[头像] AccountName        👍 13   ↗ 5   ♡ 2   💬 9
```

### 处理流水线

```
1. 灰度 → 二值化（阈值 140）
2. 8 邻接连通域（行游程 + 并查集），得到每个字形的 bbox
3. 字形过滤：14 ≤ h ≤ 60，4 ≤ w ≤ 80
4. 图标识别（4 类）：
     模板来自任一截图中的 4 个图标，归一化到 32×32
     对所有"图标尺寸"(28≤h≤48, w≥22) 的连通域做最近邻
     → 实测距离 0.0（图标在 UI 里像素级一致）
5. 数字分组：
     对每个图标，向右取**间距 ≤26px** 的连续连通域
     宽度 ≤22 的视为数字；宽度 >22 的视为文字（如「写留言」）
6. 数字识别：
     归一化到 20×20 → 与已标注字形库（1000+ 样本）最近邻
     （标注来源：多位数整体 OCR 成功的结果，逐位切分）
7. 缺失指标：图标后没有任何数字 → 0
```

### 为什么不用现成 OCR

| 场景 | OCR 表现 | 模板分类 |
|---|---|---|
| 单字符 `3`/`5` | 经常返回空 | 100% |
| `71` 前有耳机图标 | 读成 `671` | 正确 |
| `6` vs `9` | 常互反 | 正确 |
| `在看=0` 显示「写留言」 | 当成数字失败 | 识别为文字 → 0 |

### 顶部行（听全文）

```
原创 戴汨 ThinkingSlow缓慢思考  2026年4月16日 11:05  北京  🎧 71人  AI摘要
```

同样的连通域思路：
- 深蓝字形（数字+图标）与灰色字形（日期/地区）灰度不同，天然分组
- 找 `[耳机图标][数字...][人][AI摘要]` 这组
- `人` 字形尺寸固定（约 27×28），作为终止符
- 耳机图标与数字粘连 → 用模板定位图标，取其后、`人` 之前的窄高连通域
- 若图标后直接是 `人` → 无人收听 → 0

---

## 三、数据对齐模型

三类数据分开采集，最终用 **发布时间** 做外键：

| 数据 | 采集源 | 对齐键 |
|---|---|---|
| 正文 | 下载站 MD | `publish`（md front-matter） |
| 互动数据 | 底部栏截图 | 文件名 `2026-04-16_11-05` |
| 听全文 | 顶部行截图 | 同上 |
| 阅读数 | 列表页卡片 | 卡片标题 → 归一化标题匹配 |

**为什么用 publish 而不是标题**：标题 OCR 每次可能略有差异（冒号、省略号、首字被裁），发布时间是唯一的、可精确解析的。

---

## 四、可复现性设计

1. **所有中间产物落盘**：截图、解析 JSON、manifest，随时可离线重跑
2. **解析器与采集器解耦**：采集一次（~1h），解析可以迭代 20 次（每次 2 分钟）
3. **解析器自带校验集**：人工确认过的样本单独存，回归测试时先跑它们
4. **失败可跳过不可污染**：任何不确定的格子宁可留空（`None`），不猜
