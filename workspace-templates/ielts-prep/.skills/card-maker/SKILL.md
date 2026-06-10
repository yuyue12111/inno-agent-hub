---
name: card-maker
description: 把英语学习材料中的生词整理成 Anki 兼容的词汇卡片
---

## 词汇卡片生成器

### 触发条件

用户说「做成卡片」「整理生词」「生成单词卡」「Anki 卡片」时，进入卡片生成模式。

### 卡片格式

每张卡片格式：`单词或短语;词性 中文释义 | 原文例句;标签`

示例行：

```
ubiquitous;adj. 无处不在的 | Smartphones have become ubiquitous in daily life.;ielts academic
```

规则：
- 例句优先取自用户提供的原文；无原文时自造贴近雅思语境的句子
- 标签固定含 `ielts`，再加内容标签（如 `technology`、`environment`）
- 单次最多 20 张；短语正面写完整短语，不拆开

### 文件操作

写入 `cards/<来源主题>.csv`，文件头固定为：

```
#separator:Semicolon
#html:false
单词或短语;释义与例句;标签
```

生成后告知路径、卡片数，以及 Anki 导入方法（File → Import，分隔符「;」）。

### 记忆联动

- 来源文章调用 `l2_archive` 归档，标题格式 `[雅思阅读] 文章主题`
- 调用 `record_learning_event` 记录 `concept_explained` 事件，`mastery_delta` 设为 0.01
