# Inno Agent Hub

> Inno Agent 的文档、Skill 与工作区模板合集 —— 一个让你**快速上手、按场景取用、随时贡献**的资源仓库。

[![主项目](https://img.shields.io/badge/main--repo-inno--agent-blue)](https://github.com/hhyqhh/inno-agent)
[![文档](https://img.shields.io/badge/docs-quickstart-green)](./product-docs/quickstart.md)
[![Skills](https://img.shields.io/badge/skills-library-orange)](./skill-library/)

---

## 这是什么

[Inno Agent](https://github.com/hhyqhh/inno-agent) 是一个**本地运行、有长期记忆**的个人学习助手。它通过「工作区上下文 + Skill 包」组合，把通用 LLM 变成贴合具体学习场景的专属 Agent。

本仓库收集围绕 Inno Agent 的全部**外部资源**：

- **怎么用** —— 官方文档、入门教程、专题指南
- **能做什么** —— 自研 / 收集的 Skill 包，开箱即用
- **怎么搭** —— 按场景准备好的工作区模板（agent.md + skills 组合）

主项目代码在 [`hhyqhh/inno-agent`](https://github.com/hhyqhh/inno-agent)；本仓库**不含运行时代码**，纯文档与资源。

---

## 仓库导航

| 目录 | 内容 | 适合谁 |
|---|---|---|
| 📘 [`product-docs/`](./product-docs/) | 官方文档：5 分钟上手 + 完整说明书 | 第一次接触 Inno Agent |
| 🛠 [`how-to/`](./how-to/) | 专题教程：Skill 编写、工作区配置等 | 想做点定制 |
| 🎨 [`skill-library/`](./skill-library/) | Skill 收集库，含说明 + 效果展示 | 想直接拿来用 |
| 📦 [`workspace-templates/`](./workspace-templates/) | 工作区模板：agent.md + .skills 组合 | 想一键搭建场景 |

---

## 快速开始

按你的角色选择入口：

**🚀 我是新用户** —— 从 [`product-docs/quickstart.md`](./product-docs/quickstart.md) 开始，5 分钟跑通安装与第一次对话。

**🎯 我想试试现成 Skill** —— 浏览 [`skill-library/`](./skill-library/)，挑一个 Skill 包下载，按教程上传到工作区。当前已收录：

- [`edu-solid-geometry`](./skill-library/edu-solid-geometry/) — 立体几何题 → Three.js 交互解题页
- [`edu-analytic-geometry`](./skill-library/edu-analytic-geometry/) — 圆锥曲线题 → Canvas 交互解题页

**📦 我想按场景一键搭建工作区** —— 去 [`workspace-templates/`](./workspace-templates/) 选模板，复制 `agent.md` + `.skills/` 即可。当前已收录：

- [`ielts-prep`](./workspace-templates/ielts-prep/) — 雅思英语备考工作区

**🧑‍🏫 我想自己写 Skill** —— 读 [`how-to/skill-tutorial.md`](./how-to/skill-tutorial.md)，看 `agent.md` 与 SKILL 包的设计与上传方式。

---

## Skill 与 Workspace 的关系

```
┌──────────────────────────────────────────────────────────┐
│  Inno Agent 工作区                                       │
│                                                          │
│   agent.md             ← 工作区上下文（学习背景/偏好）   │
│   .skills/             ← 专项能力（触发条件/格式/流程）  │
│     └─ xxx/SKILL.md                                      │
│   files/               ← 你的学习资料                    │
│                                                          │
└──────────────────────────────────────────────────────────┘
              ▲                       ▲
              │                       │
   workspace-templates/        skill-library/
   （拿走整套工作区）          （单挑某个能力）
```

详见 [`how-to/skill-tutorial.md`](./how-to/skill-tutorial.md) 的「设计思路」一节。

---

## 贡献

欢迎提交你自己的 Skill 或工作区模板：

1. **新 Skill** → 在 `skill-library/` 下新建目录，包含 `SKILL.md` + 必要的 `lib/scripts/template/references/`，外加一份 `README.md` 介绍用途与效果。效果图请放到 `skill-library/assets/<skill-name>/`。
2. **新 Workspace 模板** → 在 `workspace-templates/` 下新建目录，包含 `agent.md` 与 `.skills/`，并在该目录的 `README.md` 描述适用场景。
3. **教程或文档勘误** → 直接 PR 到 `how-to/` 或 `product-docs/`。

提交前请确认：
- 不要把 `.DS_Store`、屏幕录像（`*.mov`）等本地文件入库（已在 `.gitignore` 中忽略）
- 效果展示用 GIF / PNG，不要直接放视频文件
- 中文文档优先，必要时附英文说明

---

## 关联项目

- [`hhyqhh/inno-agent`](https://github.com/hhyqhh/inno-agent) — 主项目（Inno Agent 运行时）
- [`wy51ai/edulab`](https://github.com/wy51ai/edulab) — 教育领域 Skill 上游来源

---

## License

文档与 Skill 内容按各子目录所注协议提供；如未单独标注，默认遵循主项目协议。
