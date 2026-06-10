# edu-analytic-geometry · 解析几何交互解题页

> **类型**：收集  
> **上游**：[wy51ai/edulab](https://github.com/wy51ai/edulab) · Apache-2.0  
> **原版路径**：[`skills/edu-analytic-geometry`](https://github.com/wy51ai/edulab/tree/master/skills/edu-analytic-geometry)  
> **推荐安装**：全局 Skill 或数学专题工作区

## 概述

把一道解析几何（圆锥曲线）题解成**自包含的交互教学网页**：左栏题面 + 动态控制台，中栏 KaTeX 分步解析，右栏 2D Canvas 动态几何画板。

支持三种入口：文字题目、上传题目图片、随机出题。

**覆盖题型**：标准方程、弦长、向量数量积范围/定值、三角形面积最值、定点、定值、轨迹、离心率——椭圆/双曲线/抛物线/圆，统一用含参直线联立 + 韦达 + 换元，sympy 精确计算驱动。

**触发词**：解析几何、圆锥曲线、椭圆、双曲线、抛物线、焦点弦、数量积取值范围、定点问题、定值问题……

## 依赖

计算核心 `lib/analytic_kernel.py` 需要 **sympy**：

```bash
python3 -c "import sympy"
python3 -m pip install sympy
```

## 安装到 Inno Agent

本 Skill 含完整计算内核与前端模板，需**打包整个目录**上传：

```bash
cd skill-library
zip -r edu-analytic-geometry.zip edu-analytic-geometry/ \
  -x "*.pyc" -x "*__pycache__*"
```

1. 在 Inno Agent 上传 `edu-analytic-geometry.zip`
2. 新建会话，发送「随机出一道圆锥曲线题」或贴一道解析几何文字题验证

## 使用效果

在 Inno Agent 中安装后，发送解析几何题目，Agent 生成交互解题页。效果动图见 [`assets/edu-analytic-geometry/demo.gif`](../assets/edu-analytic-geometry/demo.gif)。

产出为工作区根目录下的 `solution-<题目简述>.html`。

## 目录说明

| 路径 | 说明 |
|---|---|
| [`SKILL.md`](./SKILL.md) | 技能正文（zip 内必需） |
| `lib/analytic_kernel.py` | sympy 精确求解核心 |
| `lib/conics.py` | 圆锥曲线定义库 |
| `scripts/generate.py` | 模板注入与 6 个 build_* 范本 |
| `template/board.html` | 2D 交互页模板 |
| `references/` | 数据格式与解法配方 |

## 同步上游

```bash
git clone --depth 1 https://github.com/wy51ai/edulab.git /tmp/edulab
cp -R /tmp/edulab/skills/edu-analytic-geometry/* skill-library/edu-analytic-geometry/
# 保留本 README.md，勿覆盖
```
