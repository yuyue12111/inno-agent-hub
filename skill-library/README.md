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


