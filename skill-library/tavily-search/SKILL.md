---
name: tavily-search
description: 通过 Tavily API 进行实时网络搜索，获取模型知识截止日期之后的最新信息
---

## 网络搜索（Tavily）

### 触发条件

以下情况主动调用搜索，无需等用户要求：

- 用户询问近期事件、最新数据、当前状态（「最新」「现在」「今年」「实时」等信号词）
- 需要引用具体数字、日期、版本号等容易过时的事实
- 用户明确说「帮我搜一下」「查一下」

不触发：闲聊、纯概念解释、基于已有上下文的分析推理。

### 调用命令

将 `QUERY` 替换为搜索词后执行：

```bash
curl -s -X POST "https://api.tavily.com/search" \
  -H "Content-Type: application/json" \
  -d "{\"api_key\":\"YOUR_TAVILY_API_KEY\",\"query\":\"QUERY\",\"max_results\":5,\"include_answer\":true}"
```

### 结果处理

响应为 JSON，关键字段：

| 字段 | 说明 |
|---|---|
| `answer` | 合成的直接答案，优先展示 |
| `results[].title` | 来源标题 |
| `results[].url` | 来源 URL |
| `results[].content` | 页面摘要，取前 300 字 |
| `results[].score` | 相关度，低于 0.5 不引用 |

回复格式：先给出 `answer`，再列 2–3 条高分来源（标题 + URL），末尾注明「来源：Tavily 搜索」。
