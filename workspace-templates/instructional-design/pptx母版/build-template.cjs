/*
 * InnoSpark 风格教学课件母版生成器
 * 运行：NODE_PATH="$(npm root -g)" node build-template.cjs
 * 产物：InnoSpark教学课件母版.pptx
 * 内容示例课题：一次函数（与《学情CSV字段规范》样例对齐；阶段三可整体套改为实际课题）
 */
const pptxgen = require("pptxgenjs");

// ── InnoSpark 品牌色（无 # 前缀）──
const C = {
  primary: "555AFF",   // 主色 靛蓝
  second:  "7C5CFF",   // 辅助 紫
  soft:    "EDEEFF",   // 浅靛底
  bgLight: "FBFBFF",   // 内容页浅背景
  dark:    "191922",   // 深色页 / 正文
  darker:  "26264F",   // 深靛（备用）
  text:    "191922",
  muted:   "545469",
  subtle:  "9D9DA9",
  border:  "E5E4F4",
  ok:      "22A06B",
  warn:    "D99A08",
  bad:     "DC2626",
  white:   "FFFFFF",
};
const FONT = "微软雅黑";      // CJK；如环境有思源黑体可改 "Source Han Sans SC"
const FONT_LAT = "Calibri";  // 拉丁/数字

const pres = new pptxgen();
pres.layout = "LAYOUT_WIDE"; // 13.33 x 7.5
pres.author = "InnoAgent";
pres.title = "《一次函数》教学课件（InnoSpark 母版）";
const W = 13.33, H = 7.5, M = 0.6;

const shadow = () => ({ type: "outer", color: "555AFF", blur: 10, offset: 3, angle: 135, opacity: 0.12 });

// 顶部靛→紫渐变带（用分段矩形近似渐变）
function gradientBand(slide, y, h, segs = 16) {
  const a = [0x55, 0x5a, 0xff], b = [0x7c, 0x5c, 0xff];
  const segW = W / segs;
  for (let i = 0; i < segs; i++) {
    const t = i / (segs - 1);
    const hex = [0, 1, 2].map(k => Math.round(a[k] + (b[k] - a[k]) * t).toString(16).padStart(2, "0")).join("");
    slide.addShape(pres.shapes.RECTANGLE, { x: i * segW, y, w: segW + 0.02, h, fill: { color: hex }, line: { type: "none" } });
  }
}

// 内容页统一页头：渐变带 + kicker + 标题
function header(slide, kicker, title) {
  gradientBand(slide, 0, 0.16);
  slide.addText(kicker, { x: M, y: 0.4, w: 8, h: 0.3, fontSize: 12, color: C.primary, bold: true, fontFace: FONT, charSpacing: 2, margin: 0 });
  slide.addText(title, { x: M, y: 0.7, w: W - 2 * M, h: 0.9, fontSize: 30, bold: true, color: C.text, fontFace: FONT, margin: 0 });
}

// 页脚
function footer(slide, n) {
  slide.addText("InnoAgent · 教学工程演示", { x: M, y: H - 0.42, w: 6, h: 0.3, fontSize: 9, color: C.subtle, fontFace: FONT, margin: 0 });
  slide.addText(String(n), { x: W - 1.0, y: H - 0.42, w: 0.4, h: 0.3, fontSize: 9, color: C.subtle, align: "right", fontFace: FONT_LAT, margin: 0 });
}

/* ── Slide 1 · 封面（深色页）── */
(() => {
  const s = pres.addSlide();
  s.background = { color: C.dark };
  gradientBand(s, 0, 0.22);
  gradientBand(s, H - 0.22, 0.22);
  s.addText("InnoAgent · 教学工程", { x: M, y: 1.5, w: 8, h: 0.4, fontSize: 14, color: C.second, bold: true, fontFace: FONT, charSpacing: 3, margin: 0 });
  s.addText("《一次函数》教学课件", { x: M, y: 2.5, w: W - 2 * M, h: 1.4, fontSize: 48, bold: true, color: C.white, fontFace: FONT, margin: 0 });
  s.addText("基于核心素养导向的课堂设计", { x: M, y: 4.0, w: W - 2 * M, h: 0.6, fontSize: 20, color: "C9C9E6", fontFace: FONT, margin: 0 });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 5.1, w: 3.9, h: 0.62, fill: { color: C.primary }, rectRadius: 0.08 });
  s.addText("初中数学 · 数与代数领域", { x: M, y: 5.1, w: 3.9, h: 0.62, fontSize: 14, color: C.white, align: "center", valign: "middle", fontFace: FONT, margin: 0 });
})();

/* ── Slide 2 · 学习目标（浅色页 + 素养徽章）── */
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bgLight };
  header(s, "学习目标 · LEARNING OBJECTIVES", "本节课要达成什么");
  // 左：目标列表
  s.addText([
    { text: "能从现实情境中抽象出一次函数关系，理解 y = kx + b 的意义", options: { bullet: true, breakLine: true, paraSpaceAfter: 12 } },
    { text: "会画一次函数图象，并说出 k、b 对图象的影响", options: { bullet: true, breakLine: true, paraSpaceAfter: 12 } },
    { text: "能用待定系数法求解析式，规范书写运算步骤", options: { bullet: true, breakLine: true, paraSpaceAfter: 12 } },
    { text: "能用一次函数模型解决简单实际问题", options: { bullet: true } },
  ], { x: M, y: 2.0, w: 7.2, h: 4.2, fontSize: 16, color: C.text, fontFace: FONT, valign: "top" });
  // 右：核心素养徽章卡
  const chips = [["抽象能力", C.primary], ["几何直观", C.second], ["运算能力", C.primary], ["模型观念", C.second]];
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.4, y: 1.95, w: 4.3, h: 4.25, fill: { color: C.soft }, line: { color: C.border, width: 1 }, rectRadius: 0.1 });
  s.addText("对应核心素养", { x: 8.7, y: 2.2, w: 3.7, h: 0.4, fontSize: 14, bold: true, color: C.text, fontFace: FONT, margin: 0 });
  chips.forEach(([txt, col], i) => {
    const y = 2.85 + i * 0.75;
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.7, y, w: 3.7, h: 0.55, fill: { color: C.white }, line: { color: col, width: 1.25 }, rectRadius: 0.27 });
    s.addShape(pres.shapes.OVAL, { x: 8.9, y: y + 0.16, w: 0.22, h: 0.22, fill: { color: col } });
    s.addText(txt, { x: 9.3, y, w: 3.0, h: 0.55, fontSize: 14, color: C.text, valign: "middle", fontFace: FONT, margin: 0 });
  });
  footer(s, 2);
})();

/* ── Slide 3 · 情境导入（两栏）── */
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bgLight };
  header(s, "情境导入 · CONTEXT", "从共享单车计费说起");
  // 左：情境卡
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 2.05, w: 6.1, h: 4.1, fill: { color: C.white }, line: { color: C.border, width: 1 }, rectRadius: 0.1, shadow: shadow() });
  s.addText([
    { text: "某共享单车：起步价 1.5 元（前 30 分钟），", options: { breakLine: true, paraSpaceAfter: 8 } },
    { text: "此后每分钟 0.5 元。", options: { breakLine: true, paraSpaceAfter: 14 } },
    { text: "骑行时间越长，费用怎样变化？", options: { bold: true, color: C.primary } },
  ], { x: 0.95, y: 2.4, w: 5.35, h: 3.4, fontSize: 17, color: C.text, fontFace: FONT, valign: "top" });
  // 右：一次函数图象（LINE chart，示意 y = 0.5x - 13.5）
  s.addText("费用 y 随时间 x 变化", { x: 7.1, y: 2.05, w: 5.6, h: 0.35, fontSize: 13, bold: true, color: C.muted, fontFace: FONT, margin: 0 });
  s.addChart(pres.charts.LINE, [{ name: "费用(元)", labels: ["30", "40", "50", "60", "70", "80"], values: [1.5, 6.5, 11.5, 16.5, 21.5, 26.5] }], {
    x: 7.0, y: 2.5, w: 5.8, h: 3.6, lineSize: 3, lineSmooth: false, chartColors: [C.primary],
    chartArea: { fill: { color: C.white } }, catAxisLabelColor: C.muted, valAxisLabelColor: C.muted,
    valGridLine: { color: C.border, size: 0.5 }, catGridLine: { style: "none" }, showLegend: false,
    showValue: false, catAxisTitle: "时间/分钟", showCatAxisTitle: true, catAxisTitleColor: C.subtle,
  });
  footer(s, 3);
})();

/* ── Slide 4 · 核心概念 ── */
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bgLight };
  header(s, "核心概念 · CONCEPT", "什么是一次函数");
  // 定义大卡
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: M, y: 2.05, w: W - 2 * M, h: 1.5, fill: { color: C.soft }, line: { color: C.border, width: 1 }, rectRadius: 0.1 });
  s.addText([
    { text: "一般地，形如 ", options: {} },
    { text: "y = kx + b", options: { bold: true, color: C.primary, fontFace: FONT_LAT } },
    { text: "（k、b 为常数，k ≠ 0）的函数，叫做一次函数。", options: {} },
  ], { x: 0.95, y: 2.05, w: W - 2 * M - 0.7, h: 1.5, fontSize: 20, color: C.text, valign: "middle", fontFace: FONT, margin: 0 });
  // 三要素小卡
  const cards = [
    ["k ≠ 0", "一次项系数", "决定倾斜方向与快慢"],
    ["b", "常数项", "图象与 y 轴交点 (0, b)"],
    ["b = 0", "正比例函数", "y = kx 是特殊的一次函数"],
  ];
  cards.forEach(([big, t, d], i) => {
    const x = M + i * ((W - 2 * M - 0.6) / 3 + 0.3);
    const w = (W - 2 * M - 0.6) / 3;
    s.addShape(pres.shapes.RECTANGLE, { x, y: 3.95, w, h: 2.1, fill: { color: C.white }, line: { color: C.border, width: 1 }, shadow: shadow() });
    s.addShape(pres.shapes.RECTANGLE, { x, y: 3.95, w: 0.1, h: 2.1, fill: { color: i === 1 ? C.second : C.primary } });
    s.addText(big, { x: x + 0.25, y: 4.15, w: w - 0.4, h: 0.7, fontSize: 26, bold: true, color: i === 1 ? C.second : C.primary, fontFace: FONT_LAT, margin: 0 });
    s.addText(t, { x: x + 0.25, y: 4.9, w: w - 0.4, h: 0.4, fontSize: 15, bold: true, color: C.text, fontFace: FONT, margin: 0 });
    s.addText(d, { x: x + 0.25, y: 5.3, w: w - 0.4, h: 0.6, fontSize: 12, color: C.muted, fontFace: FONT, margin: 0 });
  });
  footer(s, 4);
})();

/* ── Slide 5 · 例题 / 探究（流程步骤）── */
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bgLight };
  header(s, "例题探究 · INQUIRY", "用待定系数法求解析式");
  const steps = [
    ["1", "读情境", "找出两组对应值 (x, y)"],
    ["2", "设模型", "设 y = kx + b"],
    ["3", "列方程", "代入两点得方程组"],
    ["4", "解方程", "求出 k、b"],
    ["5", "反思迁移", "回代检验并解释含义"],
  ];
  const n = steps.length, gap = 0.3;
  const w = (W - 2 * M - gap * (n - 1)) / n;
  steps.forEach(([num, t, d], i) => {
    const x = M + i * (w + gap);
    s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.4, w, h: 3.0, fill: { color: C.white }, line: { color: C.border, width: 1 }, rectRadius: 0.08, shadow: shadow() });
    s.addShape(pres.shapes.OVAL, { x: x + w / 2 - 0.35, y: 2.7, w: 0.7, h: 0.7, fill: { color: i % 2 ? C.second : C.primary } });
    s.addText(num, { x: x + w / 2 - 0.35, y: 2.7, w: 0.7, h: 0.7, fontSize: 22, bold: true, color: C.white, align: "center", valign: "middle", fontFace: FONT_LAT, margin: 0 });
    s.addText(t, { x: x + 0.1, y: 3.55, w: w - 0.2, h: 0.5, fontSize: 15, bold: true, color: C.text, align: "center", fontFace: FONT, margin: 0 });
    s.addText(d, { x: x + 0.12, y: 4.05, w: w - 0.24, h: 1.2, fontSize: 11.5, color: C.muted, align: "center", fontFace: FONT, margin: 0 });
  });
  footer(s, 5);
})();

/* ── Slide 6 · 课堂小结 ── */
(() => {
  const s = pres.addSlide();
  s.background = { color: C.bgLight };
  header(s, "课堂小结 · SUMMARY", "这节课我们收获了什么");
  s.addText([
    { text: "概念：y = kx + b（k ≠ 0）是一次函数，b = 0 时为正比例函数", options: { bullet: { code: "2713" }, breakLine: true, paraSpaceAfter: 14 } },
    { text: "图象：一条直线，k 定斜向、b 定截距", options: { bullet: { code: "2713" }, breakLine: true, paraSpaceAfter: 14 } },
    { text: "方法：待定系数法——设、代、解、验四步", options: { bullet: { code: "2713" }, breakLine: true, paraSpaceAfter: 14 } },
    { text: "应用：把实际问题抽象成一次函数模型", options: { bullet: { code: "2713" } } },
  ], { x: M, y: 2.1, w: 7.4, h: 4.0, fontSize: 17, color: C.text, fontFace: FONT, valign: "top" });
  // 右侧提示卡
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 8.5, y: 2.1, w: 4.2, h: 3.2, fill: { color: C.dark }, rectRadius: 0.12 });
  s.addText("下节预告", { x: 8.8, y: 2.4, w: 3.6, h: 0.4, fontSize: 14, bold: true, color: C.second, fontFace: FONT, margin: 0 });
  s.addText("一次函数与一元一次方程、不等式的关系", { x: 8.8, y: 2.95, w: 3.6, h: 2.0, fontSize: 18, color: C.white, fontFace: FONT, valign: "top", margin: 0 });
  footer(s, 6);
})();

pres.writeFile({ fileName: "InnoSpark教学课件母版.pptx" }).then(f => console.log("生成成功：" + f));
