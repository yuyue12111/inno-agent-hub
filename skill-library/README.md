# Skill Library

Inno Agent Skill 集合整理 —— 每个 Skill 是独立目录，可直接下载打包上传到工作区。



---

## 快速使用

从本仓库下载 Skill 目录（或自行打包为 `.zip`），按需求选择**全局**或**工作区**上传入口：

<table>
  <tr>
    <td width="50%" valign="top">
      <h3>工作区 Skill（局部）</h3>
      <p>仅对绑定该工作区的会话生效。在工作区「预览」页，点击文件树工具栏 <strong>✦</strong> 按钮，上传 <code>.md</code> 或 <code>.zip</code>。</p>
      <img src="./assets/upload-workspace-skill.gif" alt="工作区 Skill 上传示意" width="100%">
    </td>
    <td width="50%" valign="top">
      <h3>全局 Skill</h3>
      <p>对所有工作区的会话生效。点击右侧「<strong>技能</strong>」标签页 → 右上角「<strong>上传</strong>」。</p>
      <img src="./assets/upload-global-skill.gif" alt="全局 Skill 上传示意" width="100%">
    </td>
  </tr>
</table>


## Skill 列表

按场景分组，便于按需取用。

### 🌐 工具 · 信息获取

| Skill | 类型 | 一句话 |
|---|---|---|
| [tavily-search](./tavily-search/) | 原创 | 实时网络搜索，补充过时信息（需申请 [Tavily API Key](https://www.tavily.com/)，免费 1000 次/月） |

### 📐 教育 · 数学

| Skill | 类型 | 一句话 | 引用 | 效果 |
|---|---|---|---|---|
| [edu-solid-geometry](./edu-solid-geometry/) | 收集 | 立体几何题 → Three.js 交互 3D 解题页 | [wy51ai/edulab](https://github.com/wy51ai/edulab/tree/master/skills/edu-solid-geometry) | [demo](./assets/edu-solid-geometry/demo.gif) |
| [edu-analytic-geometry](./edu-analytic-geometry/) | 收集 | 圆锥曲线题 → Canvas 2D 动态画板 | [wy51ai/edulab](https://github.com/wy51ai/edulab/tree/master/skills/edu-analytic-geometry) | [demo](./assets/edu-analytic-geometry/demo.gif) |

### 📚 教育 · 备考与刷题

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [Exam2Knowledge](./Exam2Knowledge/) | 收集 |  | 把考题逆向拆成高频考点、解题模板与错题库，构建应试模式识别（理科优先） | [AtomerCore/Exam2Knowledge-skill](https://github.com/AtomerCore/Exam2Knowledge-skill) |

### 📄 文档 · 办公与转换

> 「通过验证」:✅ = 已人工验证可用,留空 = 未验证。

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [xlsx](./xlsx/) | 收集 |  | 处理 .xlsx/.csv/.tsv 表格的读取、编辑、修复、分析与公式计算 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/xlsx) |
| [pdf](./pdf/) | 收集 |  | 处理重排版的 PDF 读取、创建与审阅，借 Poppler 渲染与 Python 库 | [fcakyon/claude-codex-settings](https://github.com/fcakyon/claude-codex-settings/tree/HEAD/plugins/openai-office-skills/skills/pdf) |
| [docx](./docx/) | 收集 |  | 创建、读取与编辑 Word（.docx）文档 | [fcakyon/claude-codex-settings](https://github.com/fcakyon/claude-codex-settings/tree/HEAD/plugins/anthropic-office-skills/skills/docx) |
| [pptx](./pptx/) | 收集 |  | 处理任何涉及 .pptx 的场景：创建、读取、解析或提取幻灯片内容 | [fcakyon/claude-codex-settings](https://github.com/fcakyon/claude-codex-settings/tree/HEAD/plugins/anthropic-office-skills/skills/pptx) |
| [markitdown](./markitdown/) | 收集 |  | 用 MarkItDown 将 PDF、Office 文档、图片、音频等转换为 Markdown | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/HEAD/scientific-skills/markitdown) |

### 🔎 学习 · 研究与笔记

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [paper-lookup](./paper-lookup/) | 收集 |  | 通过 REST API 检索 PubMed、arXiv、OpenAlex 等 10 个学术论文库 | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/HEAD/scientific-skills/paper-lookup) |
| [citation-management](./citation-management/) | 收集 |  | 学术引用管理：检索 Google Scholar 与 PubMed，校验文献并生成 BibTeX | [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills/tree/HEAD/scientific-skills/citation-management) |
| [baoyu-youtube-transcript](./baoyu-youtube-transcript/) | 收集 |  | 按 URL 或视频 ID 下载 YouTube 字幕与封面，支持翻译与分章 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-youtube-transcript) |
| [baoyu-url-to-markdown](./baoyu-url-to-markdown/) | 收集 |  | 用 baoyu-fetch 抓取任意 URL 转为 markdown，内置 X、YouTube 等适配器 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-url-to-markdown) |
| [understand](./understand/) | 收集 |  | 分析代码库生成交互式知识图谱，理解架构、组件与关系 | [Lum1104/Understand-Anything](https://github.com/Lum1104/Understand-Anything/tree/HEAD/understand-anything-plugin/skills/understand) |
| [storm-research](./storm-research/) | 收集 |  | 多视角提问 + 联网检索 + 强制引用，产出维基百科式带来源的深度研究报告 | [openwhat007/storm-research](https://github.com/openwhat007/storm-research) |

### 🎨 创作 · 知识可视化

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [baoyu-comic](./baoyu-comic/) | 收集 |  | 知识漫画创作，支持多种画风与基调，分镜排版并按序生成图像 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-comic) |
| [baoyu-infographic](./baoyu-infographic/) | 收集 |  | 用 21 种布局与 21 种风格生成可发布的专业信息图 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-infographic) |
| [baoyu-slide-deck](./baoyu-slide-deck/) | 收集 |  | 从内容生成专业幻灯片图像，先出带风格的提纲再逐页生图 | [JimLiu/baoyu-skills](https://github.com/JimLiu/baoyu-skills/tree/HEAD/skills/baoyu-slide-deck) |
| [smart-illustrator](./smart-illustrator/) | 收集 |  | 智能配图与 PPT 信息图生成器，三种模式（文章配图 / 批量信息图 / 封面图） | [axtonliu/smart-illustrator](https://github.com/axtonliu/smart-illustrator) |
| [ian-xiaohei-illustrations](./ian-xiaohei-illustrations/) | 收集 |  | 生成 Ian「小黑」风格的中文正文配图（手绘、怪诞、16:9 解释图） | [helloianneo/ian-xiaohei-illustrations](https://github.com/helloianneo/ian-xiaohei-illustrations) |

### 🧩 元能力 · 技能与提示词

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [skill-creator](./skill-creator/) | 收集 |  | 创建、修改、优化 skill 并运行评测衡量其表现（自带 Apache-2.0 LICENSE） | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/skill-creator) |
| [prompt-engineer](./prompt-engineer/) | 收集 |  | 编写、重构与评估 LLM 提示词，产出优化模板、结构化输出 schema 与测试套件 | [Jeffallan/claude-skills](https://github.com/Jeffallan/claude-skills/tree/HEAD/skills/prompt-engineer) |

### 🎨 创作 · 视觉与设计

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [algorithmic-art](./algorithmic-art/) | 收集 |  | 用 p5.js 创作算法生成艺术，支持随机种子与交互式参数探索 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/algorithmic-art) |
| [canvas-design](./canvas-design/) | 收集 |  | 运用设计理念创作海报、艺术品等静态视觉作品，输出 PNG 与 PDF | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/canvas-design) |
| [theme-factory](./theme-factory/) | 收集 |  | 用预设主题为幻灯片、文档、HTML 落地页等产物统一配色与字体 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/theme-factory) |

### 📝 写作 · 文档协作

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [doc-coauthoring](./doc-coauthoring/) | 收集 |  | 引导结构化协作流程，共同撰写技术文档与规范 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/doc-coauthoring) |

### 💻 开发 · 构建与测试

| Skill | 类型 | 通过验证 | 一句话 | 引用 |
|---|---|---|---|---|
| [claude-api](./claude-api/) | 收集 |  | 构建、调试与优化 Claude API / Anthropic SDK 应用，含 prompt caching 与版本迁移 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/claude-api) |
| [mcp-builder](./mcp-builder/) | 收集 |  | 构建高质量 MCP (Model Context Protocol) 服务器以让 LLM 接入外部服务 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/mcp-builder) |
| [web-artifacts-builder](./web-artifacts-builder/) | 收集 |  | 用 React、Tailwind CSS 与 shadcn/ui 构建复杂多组件的 claude.ai HTML artifact | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/web-artifacts-builder) |
| [webapp-testing](./webapp-testing/) | 收集 |  | 用 Playwright 测试本地 Web 应用，验证前端功能、调试 UI 并截图取日志 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/webapp-testing) |
| [frontend-design](./frontend-design/) | 收集 |  | 打造高设计品质的生产级前端界面、页面与作品 | [anthropics/skills](https://github.com/anthropics/skills/tree/HEAD/skills/frontend-design) |








---

## 目录结构

```
skill-library/
├── README.md
├── assets/                          # 文档展示用，不参与上传
│   ├── upload-workspace-skill.gif   # 工作区上传示意
│   ├── upload-global-skill.gif      # 全局上传示意
│   ├── edu-solid-geometry/demo.gif
│   └── edu-analytic-geometry/demo.gif
├── edu-solid-geometry/              # ← 可直接打包上传
│   ├── SKILL.md                     # 含 frontmatter description：用途与效果
│   └── lib/  scripts/  template/  references/
└── edu-analytic-geometry/
    └── ...
```

---

## 贡献新 Skill


