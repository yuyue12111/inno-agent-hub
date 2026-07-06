# Workspace Templates

按场景整理的**工作区模板**(预设)。每个模板是一个目录,把一个学习/创作场景所需的 **Agent 人格 + 专项技能**打包在一起,让你开箱即用。

Inno Agent 的「简单模式」会直接把这些模板渲染成欢迎页的**预设卡片**,点一下就进入一个配好的工作区开始对话。你也可以手动把模板内容上传到任意工作区(见下文)。

---

## 目录结构

每个模板目录包含:

```
<模板 id>/
├── preset.json        # 元数据:id / name / description / icon(App 预设卡片读它)
├── agent.md           # 工作区上下文:每次对话注入到 Agent 系统提示
└── .skills/           # 可选,工作区私有技能
    └── <技能名>/
        └── SKILL.md   # 技能定义(name 与目录名一致)
```

### `preset.json` 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | ✅ | 唯一标识,**必须与目录名完全一致**(防路径穿越)。只用字母/数字/`._-`。 |
| `name` | ✅ | 显示名,出现在预设卡片标题。 |
| `description` | | 一句话说明这个模板帮用户做什么,显示在卡片副标题。 |
| `category` | ✅ | 分类标签,客户端按此分组与筛选。当前可用: `教学` / `演示`。**缺失会落到「未分类」组**,详见仓库根目录 [README.md 的「分类标签 (必填)」](../README.md#分类标签-必填)。 |
| `icon` | | [lucide](https://lucide.dev/icons/) 图标名,如 `presentation` / `book-open` / `lightbulb`。 |

---

## 模板列表

| 目录 | 场景 | 包含 Skill | 状态 |
|---|---|---|---|
| [ielts-prep/](./ielts-prep/) | 雅思英语备考 | card-maker(词汇卡片生成器)| ✅ 可用 |
| [ielts-coach/](./ielts-coach/) | 雅思备考(英文闭环版) | card-maker / essay-grader / reading-trainer / weekly-review | ✅ 可用 |
| [ppt-creation/](./ppt-creation/) | PPT / 演示文稿制作 | ppt-builder(结构化幻灯片生成)| ✅ 可用 |
| [lesson-plan/](./lesson-plan/) | 结构化教案生成 | — | 🚧 骨架(工作流待细化)|
| [scenario-explain/](./scenario-explain/) | 情景化讲题 | — | 🚧 骨架(工作流待细化)|
| [_template/](./_template/) | **新模板起点** | example-skill(示例)| 📋 模板 |

---

## 怎么用

### 方式一:简单模式预设卡片(推荐)

Inno Agent 默认从本仓库的 `workspace-templates/` 拉取模板。打开「简单模式」,欢迎页会列出上面这些预设,点卡片即创建并绑定一个配好的工作区。

> 拉取源可在 App 设置 →「内容源」中切换(公共仓库 / 私有 GitHub 仓库 / 自托管服务)。

### 方式二:手动上传到工作区

1. 在 Inno Agent 新建一个工作区。
2. 把模板的 `agent.md` 放到工作区根目录(让 Agent 创建,或拖拽到文件树空白区域)。
3. 把模板 `.skills/` 下每个技能的 `SKILL.md`(或自行打包的 `.zip`)通过文件树工具栏 **✦ 按钮**上传,落到工作区的 `.skills/<名称>/SKILL.md`。
4. 新建会话绑定该工作区即可。

> 详细操作步骤参见 [`how-to/skill-tutorial.md`](../how-to/skill-tutorial.md)。

---

## 贡献一个新模板

1. 复制 [`_template/`](./_template/),重命名为你的模板 id(如 `my-template`)。
2. 编辑 `preset.json`:把 `id` 改成新目录名,填好 `name` / `description` / **`category`**(必填,见下) / `icon`。
3. 编辑 `agent.md`:定义这个工作区的 Agent 人格与工作流程。
4. 按需在 `.skills/` 下增删技能(每个技能一个目录,内含 `SKILL.md`)。
5. 在上面的「模板列表」表格里加一行。
6. 提交 PR。

> **`category` 必填** —— 客户端按 `category` 分组显示预设卡片,缺失会落到「未分类」组。当前可用: `教学` / `演示`(从这两个里挑,不要新造)。新增分类请先提 issue。详见仓库根目录 [README.md 的「分类标签 (必填)」](../README.md#分类标签-必填)。

> 命名约定:`id` 用小写连字符(`kebab-case`);以 `_` 或 `.` 开头的目录(如 `_template`)不会被当作可用预设拉取,适合放骨架/草稿。
