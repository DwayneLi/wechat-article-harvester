# 发布指南：把这项技能发出去

三种发布路径，按**投入产出比**排序：

| 路径 | 能触达谁 | 工作量 | 推荐度 |
|---|---|---|---|
| 1. WorkBuddy 技能市场 | WorkBuddy 用户（国内为主） | 半天 | ⭐⭐⭐⭐⭐ |
| 2. GitHub 开源仓库 | 全球开发者 / 其他 Agent 用户 | 1 小时（已就绪） | ⭐⭐⭐⭐⭐ |
| 3. MCP Registry / 技能聚合站 | MCP 生态用户 | 半天 | ⭐⭐⭐ |

---

## 路径 1：WorkBuddy 技能市场（官方）

### 技能结构

```
my-skill/
├── SKILL.md      # 指令本体（Markdown）：触发条件 + 步骤 + 示例
├── config.yaml   # 元数据：name / version / description / triggers / category
└── assets/       # 可选：图片、模板、脚本
```

`SKILL.md` 示例（本项目的 `SKILL.md` 就是可直接用的）：

```markdown
# 微信公众号文章归档

## Trigger
当用户说"下载某个公众号的全部文章"、"把这个号的文章存到 Obsidian"时触发。

## Instructions
1. 先确认微信客户端在前台、公众号文章列表窗口可见
2. 按 docs/01-workflow.md 的阶段 1 采集链接（每篇 4 步）
3. ...
```

`config.yaml` 示例：

```yaml
name: wechat-article-harvester
version: 0.1.0
description: 把一个微信公众号的全部文章（链接/正文/互动数据）归档成 Obsidian 知识库
triggers:
  - "下载公众号全部文章"
  - "公众号文章归档"
  - "把公众号存到 Obsidian"
category: research
```

### 发布流程（官方 CLI）

```bash
# 1. 本地加载测试
workbuddy skills add ./wechat-article-harvester
workbuddy skills list

# 2. 本地安全扫描（必过，否则不能上架）
workbuddy skills scan ./wechat-article-harvester

# 3. 发布到市场
workbuddy skills publish ./wechat-article-harvester
```

发布时会要求确认：技能名与版本、市场展示描述、分类、是否依赖第三方 API Key。

### 安全扫描会卡什么

- 硬编码密钥 / API Key
- 会让 Agent 把用户数据外传的指令
- 超出技能范围的系统命令（`rm -rf`、修改系统设置）
- 已废弃/不安全的 API 调用

> 本项目已规避：所有站点地址与密钥都在用户自己的配置里，脚本不含任何 token。

参考：
- [How to Develop and Publish WorkBuddy Skills（腾讯云官方指南）](https://www.tencentcloud.com/techpedia/144344?lang=en)
- [WorkBuddy 专家/技能发布完全指南](https://cloud.tencent.com.cn/developer/article/2776760)
- [从设计稿到上架：WorkBuddy 技能开发全流程实录](https://cloud.tencent.com.cn/developer/article/2737751)

### 额外：WorkBuddy 的 MCP 能力

如果想让技能更"重"（比如内置下载能力），可以把下载逻辑做成 **MCP server**，在 `SKILL.md` 里声明依赖，WorkBuddy 运行时可以调用 MCP。

本项目实测的下载站 MCP 配置形式：

```json
{
  "mcpServers": {
    "download-mcp": {
      "type": "streamableHttp",
      "url": "https://<站点>/api/mcp"
    }
  }
}
```

---

## 路径 2：GitHub 开源仓库（已就绪）

本目录就是一个可以直接 push 的仓库。

```bash
cd wechat-article-harvester
git init
git add .
git commit -m "feat: 微信公众号全量归档 Computer Use 方法论 + 工具链"
git branch -M main
git remote add origin git@github.com:<你的账号>/wechat-article-harvester.git
git push -u origin main
```

### 建议的仓库设置

| 项 | 建议 |
|---|---|
| About | `WeChat MP archive with Computer Use · 291 articles · CV-based UI parsing` |
| Topics | `computer-use`, `wechat`, `obsidian`, `computer-vision`, `agent`, `automation`, `mcp` |
| License | MIT（代码）+ CC BY-NC 4.0（文档） |
| Release | 打 `v0.1.0` tag，附 `docs/` 单文件打包 |
| English README | 在 README 顶部加一行英文摘要，便于海外读者（`README.en.md`） |

> 如果没有本地 git 凭据，可以先 `brew install gh && gh auth login`，或直接在网页上新建仓库后 upload 目录。

---

## 路径 3：MCP Registry / 技能聚合站

如果你把下载/解析能力封装成 **MCP server**（而不是纯技能），可以投递到这些目录：

| 目录 | 说明 | 入口 |
|---|---|---|
| **Smithery** | 最大的 MCP server 目录，支持 CLI 一键发布 | `npx @smithery/cli publish` |
| **Glama** | MCP 目录，自动从 GitHub 索引 | 在 glama.ai 提交仓库 |
| **mcp.so** | 社区 MCP 目录 | 网页提交 |
| **GitHub MCP Registry** | 官方注册表（需 `server.json` + 仓库公开） | 见官方 docs |
| **ClawHub（腾讯）** | 腾讯系技能/插件市场 | 与 WorkBuddy 生态互通，见[教程](https://cloud.tencent.com.cn/developer/article/2716327) |

### 提交前检查清单

- [ ] `README` 写明：能力边界、依赖、隐私说明（会不会上传用户数据）
- [ ] `LICENSE` 明确
- [ ] 有可运行的最小示例
- [ ] 无硬编码密钥
- [ ] 版本号语义化，带 CHANGELOG
- [ ] 在 `server.json` / `config.yaml` 里写清 transport（stdio / streamableHttp）

---

## 给发布稿的措辞建议

> 这是一个**方法论 + 工具链**仓库，不是"破解工具"。
>
> 它解决的是：当官方接口失效、通用 Computer Use Agent 又因为 UI 抖动/标签压缩/上下文爆炸而失败时，如何通过**自建截图管线 + 传统 CV 解析 + 幂等状态机**把活干完。
>
> 代码可复用到任何"信息只存在于原生客户端 UI 里"的归档场景（企业微信、飞书、钉钉、内部工具）。

这样定位可以避免被当成爬虫工具，也更容易被技能市场接受。
