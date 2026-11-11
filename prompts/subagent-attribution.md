# 子任务：数据归属与校验

```
# 任务
把三份独立采集的数据合并到每篇 md 的 front-matter 里，并输出核对表。

# 输入
1. ./md/*.md            每篇 front-matter 含 publish（YYYY-MM-DD HH:MM）
2. /tmp/bar_parse.json  {publish: [赞, 转发, 在看, 评论]}
3. /tmp/listened.json   {publish: N人}
4. ./links.csv          序号,链接,采集时间（列表顺序）

# 对齐键（重要）
统一用 **publish**（发布时间）做外键，不要用标题：
标题 OCR 每次可能差一个冒号/省略号/首字，会导致错配。

# 输出
1. 更新每个 md 的 front-matter 六个字段：
   listened / reads / likes / shares / wows / comments
2. 生成核对表 xlsx：
   序号 | 标题 | 发布时间 | 听全文 | 阅读 | 赞 | 转发 | 在看 | 评论 | 文件名 | 完整度 | 链接
   完整度 = 完整（6 项齐）/ 部分 / 缺失
3. 打印：总数 / 完整 / 部分 / 缺失，以及缺失清单

# 规则
- 用户手工提供的值**优先级最高**，不得被自动结果覆盖
- 缺失 ≠ 0：只有截图明确显示 0 才算 0，没采到的留空
- 每个写入都要幂等：重复跑脚本结果不变
```
