# Workspace Templates

按场景整理的工作区模板，每个模板包含 `agent.md`（工作区上下文）和 `.skills/`（专项能力）。

## 模板列表

| 目录 | 场景 | 包含 Skill |
|---|---|---|
| [ielts-prep/](./ielts-prep/) | 雅思英语备考 | card-maker（词汇卡片生成器）|

## 使用方法

1. 在 Inno Agent 新建一个工作区
2. 将模板目录下的 `agent.md` 上传到工作区根目录（让 Agent 创建，或拖拽到文件树空白区域）
3. 将模板 `.skills/` 下每个技能的 `SKILL.md`（或自行打包的 `.zip`）通过工作区文件树的 **✦ 按钮**上传，上传后落到工作区的 `.skills/<名称>/SKILL.md`
4. 新建会话绑定该工作区即可

> 详细操作步骤参见 [`how-to/skill-tutorial.md`](../how-to/skill-tutorial.md)
