# edu-solid-geometry · 立体几何交互解题页

> **类型**：收集  
> **上游**：[wy51ai/edulab](https://github.com/wy51ai/edulab) · Apache-2.0  
> **原版路径**：[`skills/edu-solid-geometry`](https://github.com/wy51ai/edulab/tree/master/skills/edu-solid-geometry)  
> **推荐安装**：全局 Skill 或数学专题工作区

## 概述

把一道立体几何题解成**自包含的交互教学网页**：左侧 MathJax 分步解析，右侧 Three.js 可交互 3D 模型（分步高亮 + 镜头切换）。

支持三种入口：文字题目、上传题目图片、随机出题。

**覆盖题型**：线面角、二面角、异面直线夹角、点到平面距离、体积等——正方体/长方体、棱锥/棱柱、圆柱/圆锥，统一用建系 + 向量法，sympy 精确计算驱动。

**触发词**：立体几何、线面角、二面角、异面直线、点到平面距离、正四棱锥、解这道几何题、随机出一道立体几何题……

## 依赖

计算核心 `lib/geometry_kernel.py` 需要 **sympy**：

```bash
python3 -c "import sympy"   # 确认可用
python3 -m pip install sympy  # 缺失时安装
```

## 安装到 Inno Agent

本 Skill 含 `lib/`、`scripts/`、`template/` 等辅助文件，需**打包整个目录**上传，不能只传 `SKILL.md`：

```bash
cd skill-library
zip -r edu-solid-geometry.zip edu-solid-geometry/ \
  -x "*.pyc" -x "*__pycache__*"
```

1. 在 Inno Agent 右侧「技能」面板（或工作区 **✦** 按钮）选择上传
2. 选择 `edu-solid-geometry.zip`
3. 新建会话，发送「随机出一道立体几何题」验证

安装后落盘路径：`~/.inno-agent/skills/edu-solid-geometry/SKILL.md`（全局）或 `workspace/<名>/.skills/edu-solid-geometry/`（工作区）。

## 使用效果

在 Inno Agent 中安装后，发送立体几何题目，Agent 生成交互解题页。效果动图见 [`assets/edu-solid-geometry/demo.gif`](../assets/edu-solid-geometry/demo.gif)。

产出为工作区根目录下的 `solution-<题目简述>.html`，浏览器直接打开即可交互。

## 目录说明

| 路径 | 说明 |
|---|---|
| [`SKILL.md`](./SKILL.md) | 技能正文（zip 内必需） |
| `lib/geometry_kernel.py` | sympy 精确计算核心 |
| `lib/bodies.py` | 几何体棱拓扑库 |
| `scripts/generate.py` | 模板注入与范例构建 |
| `template/lesson.html` | 3D 交互页模板 |
| `references/` | 数据格式与建系约定 |

## 同步上游

```bash
# 从原版仓库拉取最新 skill 包
git clone --depth 1 https://github.com/wy51ai/edulab.git /tmp/edulab
cp -R /tmp/edulab/skills/edu-solid-geometry/* skill-library/edu-solid-geometry/
# 保留本 README.md，勿覆盖
```
