import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const outDir = path.dirname(fileURLToPath(import.meta.url));

const W = 3380;
const H = 2280;
const phoneW = 390;
const phoneH = 844;
const gapX = 74;
const rowGap = 118;
const startX = 80;
const startY = 300;

const C = {
  page: "#F7F5F2",
  surface: "#FFFFFF",
  surface2: "#FBFAF8",
  ink: "#111116",
  muted: "#72727D",
  subtle: "#A4A2AD",
  line: "#E8E5E0",
  lavender: "#8A78FF",
  lavender2: "#B5AAFF",
  lavenderSoft: "#EFECFF",
  blush: "#FFF1F3",
  pearl: "#FAF9F6",
  sage: "#EAF2EC",
  denim: "#DDE9F0",
  blue: "#9EB8C6",
  beige: "#E9E0D3",
  shadow: "rgba(22,20,28,.13)",
};

const screens = [
  ["01", "启动页", drawSplash],
  ["02", "登录欢迎", drawLogin],
  ["03", "风格建档", drawOnboarding],
  ["04", "照片上传", drawPhotoUpload],
  ["05", "特征报告", drawFeatureReport],
  ["06", "首页推荐", drawHome],
  ["07", "灵感社区", drawInspiration],
  ["08", "我的衣橱", drawWardrobe],
  ["09", "单品详情", drawItemDetail],
  ["10", "搭配详情", drawOutfitDetail],
  ["11", "购买清单", drawShoppingList],
  ["12", "AI 试穿", drawTryOn],
  ["13", "收藏日历", drawFavorites],
  ["14", "我的设置", drawProfile],
];

function esc(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function attrs(obj = {}) {
  return Object.entries(obj)
    .filter(([, v]) => v !== undefined && v !== null && v !== false)
    .map(([k, v]) => `${k}="${esc(v)}"`)
    .join(" ");
}

function tag(name, a, content = "") {
  return `<${name}${a ? ` ${attrs(a)}` : ""}>${content}</${name}>`;
}

function rect(x, y, w, h, a = {}) {
  return `<rect ${attrs({ x, y, width: w, height: h, ...a })}/>`;
}

function circle(cx, cy, r, a = {}) {
  return `<circle ${attrs({ cx, cy, r, ...a })}/>`;
}

function line(x1, y1, x2, y2, a = {}) {
  return `<line ${attrs({ x1, y1, x2, y2, ...a })}/>`;
}

function pathD(d, a = {}) {
  return `<path ${attrs({ d, ...a })}/>`;
}

function text(x, y, content, a = {}) {
  const defaults = {
    "font-family": 'Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif',
    "font-size": 14,
    fill: C.ink,
  };
  return tag("text", { x, y, ...defaults, ...a }, esc(content));
}

function tspan(lines, lineHeight = 18) {
  return lines
    .map((l, i) => `<tspan x="0" dy="${i === 0 ? 0 : lineHeight}">${esc(l)}</tspan>`)
    .join("");
}

function multiline(x, y, lines, a = {}, lineHeight = 18) {
  const defaults = {
    "font-family": 'Inter, "SF Pro Display", "PingFang SC", "Microsoft YaHei", sans-serif',
    "font-size": 12,
    fill: C.muted,
  };
  return `<text ${attrs({ x, y, ...defaults, ...a })}>${lines
    .map((l, i) => `<tspan x="${x}" dy="${i === 0 ? 0 : lineHeight}">${esc(l)}</tspan>`)
    .join("")}</text>`;
}

function g(id, content, a = {}) {
  return tag("g", { id, ...a }, content);
}

function card(x, y, w, h, a = {}) {
  return rect(x, y, w, h, {
    rx: a.rx ?? 18,
    fill: a.fill ?? C.surface,
    stroke: a.stroke ?? C.line,
    "stroke-width": a.strokeWidth ?? 1,
    filter: a.filter,
  });
}

function button(x, y, w, h, label, variant = "primary") {
  if (variant === "outline") {
    return [
      rect(x, y, w, h, { rx: h / 2, fill: C.surface, stroke: C.lavender, "stroke-width": 1.4 }),
      text(x + w / 2, y + h / 2 + 5, label, {
        "font-size": 13,
        "font-weight": 650,
        fill: C.lavender,
        "text-anchor": "middle",
      }),
    ].join("");
  }
  if (variant === "black") {
    return [
      rect(x, y, w, h, { rx: h / 2, fill: "#101014" }),
      text(x + w / 2, y + h / 2 + 5, label, {
        "font-size": 14,
        "font-weight": 650,
        fill: "#FFFFFF",
        "text-anchor": "middle",
      }),
    ].join("");
  }
  return [
    rect(x, y, w, h, { rx: h / 2, fill: "url(#cta)" }),
    text(x + w / 2, y + h / 2 + 5, label, {
      "font-size": 14,
      "font-weight": 700,
      fill: "#FFFFFF",
      "text-anchor": "middle",
    }),
  ].join("");
}

function chip(x, y, label, active = false, w = 74) {
  return [
    rect(x, y, w, 30, {
      rx: 15,
      fill: active ? C.lavenderSoft : C.surface,
      stroke: active ? C.lavender : C.line,
      "stroke-width": active ? 1.4 : 1,
    }),
    text(x + w / 2, y + 20, label, {
      "font-size": 12,
      "font-weight": active ? 700 : 500,
      fill: active ? C.lavender : C.muted,
      "text-anchor": "middle",
    }),
  ].join("");
}

function sparkle(x, y, s = 18, fill = C.lavender2, opacity = 0.55) {
  const d = `M${x} ${y - s} C${x + s * 0.16} ${y - s * 0.16} ${x + s} ${y} ${x + s} ${y} C${x + s * 0.16} ${y + s * 0.16} ${x} ${y + s} ${x} ${y + s} C${x - s * 0.16} ${y + s * 0.16} ${x - s} ${y} ${x - s} ${y} C${x - s * 0.16} ${y - s * 0.16} ${x} ${y - s} ${x} ${y - s}Z`;
  return pathD(d, { fill, opacity });
}

function topBar(x, y, title, back = false, right = "") {
  return [
    back
      ? pathD(`M${x + 28} ${y + 36} L${x + 20} ${y + 44} L${x + 28} ${y + 52}`, {
          fill: "none",
          stroke: C.ink,
          "stroke-width": 1.7,
          "stroke-linecap": "round",
          "stroke-linejoin": "round",
        })
      : "",
    text(x + phoneW / 2, y + 48, title, {
      "font-size": 15,
      "font-weight": 750,
      "text-anchor": "middle",
    }),
    right
      ? text(x + phoneW - 28, y + 48, right, {
          "font-size": 18,
          fill: C.ink,
          "text-anchor": "end",
        })
      : "",
  ].join("");
}

function navBar(x, y, active = "首页") {
  const items = [
    ["首页", "M0 7 L8 0 L16 7 V18 H11 V11 H5 V18 H0Z"],
    ["灵感", "M8 1 L10.1 5.8 L15.3 6.2 L11.4 9.6 L12.6 14.8 L8 12.1 L3.4 14.8 L4.6 9.6 L.7 6.2 L5.9 5.8Z"],
    ["衣橱", "M4 3 H12 L15 7 V17 H1 V7Z"],
    ["我的", "M8 8 A4 4 0 1 0 8 0 A4 4 0 0 0 8 8 M1 18 C2.4 13.8 13.6 13.8 15 18Z"],
  ];
  const baseY = y + phoneH - 70;
  return [
    line(x, baseY - 10, x + phoneW, baseY - 10, { stroke: "#F0EDEA" }),
    ...items.map(([label, d], i) => {
      const cx = x + 58 + i * 92;
      const is = label === active;
      return g(`nav-${label}`, [
        pathD(d, {
          transform: `translate(${cx - 8} ${baseY - 1}) scale(.92)`,
          fill: is ? C.lavender : "none",
          stroke: is ? C.lavender : C.subtle,
          "stroke-width": 1.5,
          "stroke-linejoin": "round",
        }),
        text(cx, baseY + 42, label, {
          "font-size": 11,
          "font-weight": is ? 700 : 500,
          fill: is ? C.lavender : C.subtle,
          "text-anchor": "middle",
        }),
      ].join(""));
    }),
  ].join("");
}

function femaleIllustration(x, y, scale = 1, outfit = "light") {
  const skin = "#F3D3C4";
  const hair = "#3C2B27";
  const blazer = outfit === "dark" ? "#1C1B20" : "#EDE4D8";
  const pants = outfit === "skirt" ? "#F1ECE5" : "#C8D8DE";
  return g("fashion-illustration", [
    circle(x + 78 * scale, y + 42 * scale, 26 * scale, { fill: skin }),
    pathD(
      `M${x + 47 * scale} ${y + 38 * scale} C${x + 44 * scale} ${y + 8 * scale} ${x + 94 * scale} ${y + 3 * scale} ${x + 105 * scale} ${y + 40 * scale} C${x + 112 * scale} ${y + 72 * scale} ${x + 100 * scale} ${y + 88 * scale} ${x + 110 * scale} ${y + 120 * scale} C${x + 84 * scale} ${y + 105 * scale} ${x + 52 * scale} ${y + 102 * scale} ${x + 40 * scale} ${y + 122 * scale} C${x + 47 * scale} ${y + 83 * scale} ${x + 36 * scale} ${y + 68 * scale} ${x + 47 * scale} ${y + 38 * scale}Z`,
      { fill: hair, opacity: 0.93 }
    ),
    pathD(`M${x + 52 * scale} ${y + 80 * scale} L${x + 103 * scale} ${y + 80 * scale} L${x + 120 * scale} ${y + 214 * scale} L${x + 33 * scale} ${y + 214 * scale}Z`, {
      fill: "#F9F7F3",
      stroke: "#C9BDB2",
      "stroke-width": 1 * scale,
    }),
    pathD(`M${x + 34 * scale} ${y + 82 * scale} L${x + 63 * scale} ${y + 78 * scale} L${x + 62 * scale} ${y + 213 * scale} L${x + 21 * scale} ${y + 222 * scale}Z`, {
      fill: blazer,
      stroke: "#C7BDB2",
      "stroke-width": 1 * scale,
    }),
    pathD(`M${x + 94 * scale} ${y + 78 * scale} L${x + 122 * scale} ${y + 84 * scale} L${x + 134 * scale} ${y + 222 * scale} L${x + 96 * scale} ${y + 213 * scale}Z`, {
      fill: blazer,
      stroke: "#C7BDB2",
      "stroke-width": 1 * scale,
    }),
    outfit === "skirt"
      ? pathD(`M${x + 44 * scale} ${y + 214 * scale} L${x + 112 * scale} ${y + 214 * scale} L${x + 138 * scale} ${y + 390 * scale} L${x + 16 * scale} ${y + 390 * scale}Z`, {
          fill: pants,
          stroke: "#B9B2AD",
          "stroke-width": 1 * scale,
        })
      : [
          pathD(`M${x + 43 * scale} ${y + 214 * scale} L${x + 76 * scale} ${y + 214 * scale} L${x + 69 * scale} ${y + 410 * scale} L${x + 28 * scale} ${y + 410 * scale}Z`, {
            fill: pants,
            stroke: "#A6B6BE",
            "stroke-width": 1 * scale,
          }),
          pathD(`M${x + 81 * scale} ${y + 214 * scale} L${x + 113 * scale} ${y + 214 * scale} L${x + 128 * scale} ${y + 410 * scale} L${x + 89 * scale} ${y + 410 * scale}Z`, {
            fill: pants,
            stroke: "#A6B6BE",
            "stroke-width": 1 * scale,
          }),
        ].join(""),
    rect(x + 22 * scale, y + 408 * scale, 49 * scale, 11 * scale, { rx: 5 * scale, fill: "#F4EFE7", stroke: "#C7BDB2", "stroke-width": 1 * scale }),
    rect(x + 88 * scale, y + 408 * scale, 49 * scale, 11 * scale, { rx: 5 * scale, fill: "#F4EFE7", stroke: "#C7BDB2", "stroke-width": 1 * scale }),
  ].join(""));
}

function itemMini(x, y, type = "blazer", scale = 1) {
  if (type === "top") {
    return pathD(`M${x + 24 * scale} ${y} L${x + 72 * scale} ${y} L${x + 86 * scale} ${y + 52 * scale} L${x + 62 * scale} ${y + 58 * scale} L${x + 59 * scale} ${y + 18 * scale} L${x + 37 * scale} ${y + 18 * scale} L${x + 34 * scale} ${y + 58 * scale} L${x + 10 * scale} ${y + 52 * scale}Z`, {
      fill: "#FBF8F1",
      stroke: "#D1C7BD",
    });
  }
  if (type === "pants") {
    return [
      pathD(`M${x + 32 * scale} ${y} H${x + 53 * scale} L${x + 48 * scale} ${y + 78 * scale} H${x + 22 * scale}Z`, { fill: "#CBDCE3", stroke: "#A8BBC5" }),
      pathD(`M${x + 55 * scale} ${y} H${x + 76 * scale} L${x + 86 * scale} ${y + 78 * scale} H${x + 60 * scale}Z`, { fill: "#CBDCE3", stroke: "#A8BBC5" }),
    ].join("");
  }
  if (type === "shoe") {
    return pathD(`M${x + 18 * scale} ${y + 45 * scale} C${x + 45 * scale} ${y + 60 * scale} ${x + 70 * scale} ${y + 40 * scale} ${x + 91 * scale} ${y + 58 * scale} C${x + 102 * scale} ${y + 68 * scale} ${x + 89 * scale} ${y + 76 * scale} ${x + 53 * scale} ${y + 74 * scale} H${x + 14 * scale} C${x + 4 * scale} ${y + 73 * scale} ${x + 3 * scale} ${y + 62 * scale} ${x + 18 * scale} ${y + 45 * scale}Z`, {
      fill: "#F3EFE8",
      stroke: "#CFC6BC",
    });
  }
  return pathD(`M${x + 32 * scale} ${y} H${x + 78 * scale} L${x + 96 * scale} ${y + 82 * scale} H${x + 14 * scale}Z M${x + 55 * scale} ${y + 8 * scale} V${y + 80 * scale}`, {
    fill: "#EDE4D8",
    stroke: "#C7BDB2",
  });
}

function drawPhone(index, code, title, draw) {
  const col = index % 7;
  const row = Math.floor(index / 7);
  const x = startX + col * (phoneW + gapX);
  const y = startY + row * (phoneH + rowGap);
  return g(`screen-${code}-${title}`, [
    text(x + 4, y - 34, `${code}  ${title}`, { "font-size": 18, "font-weight": 760 }),
    rect(x + 10, y + 14, phoneW, phoneH, { rx: 44, fill: C.shadow, opacity: 0.4, filter: "url(#phoneShadow)" }),
    rect(x, y, phoneW, phoneH, { rx: 44, fill: C.surface, stroke: "#FFFFFF", "stroke-width": 5 }),
    rect(x + 1.5, y + 1.5, phoneW - 3, phoneH - 3, { rx: 42, fill: C.surface }),
    draw(x, y),
  ].join(""));
}

function drawHeader() {
  return g("cover-title", [
    text(80, 90, "clozAi iOS App UI Kit", { "font-size": 42, "font-weight": 780 }),
    text(80, 130, "女性用户 · AI 穿搭 · 简约有质感 · 可导入 Figma 的完整产品界面", { "font-size": 18, fill: C.muted }),
    rect(80, 162, 660, 80, { rx: 20, fill: C.surface, stroke: C.line, filter: "url(#softShadow)" }),
    text(108, 195, "核心流程", { "font-size": 15, "font-weight": 760 }),
    text(108, 222, "建档 → 上传照片 → 特征报告 → 今日推荐 → 试穿 → 购买/收藏 → 衣橱沉淀", { "font-size": 14, fill: C.muted }),
    rect(780, 162, 440, 80, { rx: 20, fill: C.surface, stroke: C.line, filter: "url(#softShadow)" }),
    text(808, 195, "视觉关键词", { "font-size": 15, "font-weight": 760 }),
    text(808, 222, "象牙白 / 薰衣草紫 / 轻阴影 / 细线图标 / 温柔留白", { "font-size": 14, fill: C.muted }),
    ...[
      [1260, C.ink, "Ink"],
      [1324, C.lavender, "Lavender"],
      [1388, C.lavenderSoft, "Mist"],
      [1452, C.pearl, "Pearl"],
      [1516, C.beige, "Linen"],
      [1580, C.denim, "Denim"],
    ].flatMap(([x, color, name]) => [
      rect(x, 168, 44, 44, { rx: 12, fill: color, stroke: color === C.pearl ? C.line : "none" }),
      text(x + 22, 228, name, { "font-size": 11, fill: C.muted, "text-anchor": "middle" }),
    ]),
    sparkle(3160, 94, 34, C.lavender2, 0.42),
    sparkle(3238, 178, 18, C.lavender, 0.5),
    pathD("M2870 72 C3030 8 3204 44 3270 132 C3112 118 2976 158 2868 252", {
      fill: "none",
      stroke: "#DAD5FF",
      "stroke-width": 1.2,
      opacity: 0.65,
    }),
  ].join(""));
}

function drawSplash(x, y) {
  return [
    rect(x + 12, y + 12, phoneW - 24, phoneH - 24, { rx: 34, fill: "url(#splashBg)" }),
    pathD(`M${x + 84} ${y + 172} C${x + 176} ${y + 76} ${x + 340} ${y + 80} ${x + 318} ${y + 228} C${x + 304} ${y + 330} ${x + 140} ${y + 420} ${x + 78} ${y + 560}`, {
      fill: "none",
      stroke: "#D8D2FF",
      "stroke-width": 1,
      opacity: 0.8,
    }),
    sparkle(x + 104, y + 178, 22),
    sparkle(x + 296, y + 294, 18),
    sparkle(x + 300, y + 515, 14),
    text(x + 194, y + 360, "cloz", { "font-size": 54, "font-weight": 500, "text-anchor": "end" }),
    text(x + 194, y + 360, "Ai", { "font-size": 54, "font-weight": 500, fill: C.lavender, "text-anchor": "start" }),
    multiline(x + 78, y + 424, ["AI 洞察你的独特特征", "生成最适合你的流行穿搭"], {
      "font-size": 18,
      fill: C.ink,
      "font-weight": 520,
    }, 30),
    button(x + 54, y + 665, 282, 54, "开始体验", "black"),
    circle(x + 92, y + 757, 7, { fill: "none", stroke: C.subtle }),
    pathD(`M${x + 88} ${y + 756} L${x + 91} ${y + 759} L${x + 97} ${y + 752}`, { fill: "none", stroke: C.subtle, "stroke-width": 1 }),
    text(x + 110, y + 762, "我已阅读并同意《用户协议》与《隐私政策》", { "font-size": 10.5, fill: C.subtle }),
  ].join("");
}

function drawLogin(x, y) {
  return [
    topBar(x, y, "", false, "跳过"),
    text(x + 42, y + 108, "cloz", { "font-size": 32, "font-weight": 520 }),
    text(x + 111, y + 108, "Ai", { "font-size": 32, "font-weight": 520, fill: C.lavender }),
    text(x + 42, y + 162, "欢迎回来", { "font-size": 26, "font-weight": 760 }),
    multiline(x + 42, y + 194, ["登录后保存你的身形档案、衣橱和试穿记录"], { "font-size": 13, fill: C.muted }),
    card(x + 48, y + 232, 294, 220, { rx: 26, fill: "url(#portraitBg)" }),
    femaleIllustration(x + 116, y + 250, 0.42),
    rect(x + 42, y + 490, 306, 52, { rx: 18, fill: C.surface2, stroke: C.line }),
    text(x + 62, y + 523, "+86  请输入手机号", { "font-size": 14, fill: C.subtle }),
    rect(x + 42, y + 558, 306, 52, { rx: 18, fill: C.surface2, stroke: C.line }),
    text(x + 62, y + 591, "验证码", { "font-size": 14, fill: C.subtle }),
    text(x + 320, y + 591, "获取", { "font-size": 13, "font-weight": 700, fill: C.lavender, "text-anchor": "end" }),
    button(x + 42, y + 638, 306, 52, "登录 / 注册"),
    button(x + 42, y + 706, 306, 48, "微信一键登录", "outline"),
    text(x + 195, y + 794, "登录即代表同意服务条款与隐私政策", { "font-size": 10.5, fill: C.subtle, "text-anchor": "middle" }),
  ].join("");
}

function drawOnboarding(x, y) {
  return [
    topBar(x, y, "风格建档", true),
    text(x + 42, y + 112, "今天想为你优化什么？", { "font-size": 24, "font-weight": 760 }),
    text(x + 42, y + 142, "选择你的场景和身体特征，推荐会更准确", { "font-size": 13, fill: C.muted }),
    rect(x + 42, y + 170, 210, 5, { rx: 3, fill: C.lavender }),
    rect(x + 252, y + 170, 96, 5, { rx: 3, fill: C.lavenderSoft }),
    text(x + 42, y + 222, "穿搭目标", { "font-size": 15, "font-weight": 720 }),
    chip(x + 42, y + 242, "通勤", true),
    chip(x + 126, y + 242, "约会"),
    chip(x + 210, y + 242, "旅行"),
    chip(x + 42, y + 284, "显高显瘦", true, 92),
    chip(x + 144, y + 284, "温柔气质", false, 92),
    chip(x + 246, y + 284, "松弛感", false, 78),
    card(x + 42, y + 350, 306, 230, { rx: 22 }),
    text(x + 64, y + 386, "身体信息", { "font-size": 16, "font-weight": 760 }),
    ...[
      ["身高", "168 cm", 416],
      ["体重", "52 kg", 462],
      ["肤色", "暖白皮", 508],
      ["发色", "深棕色", 554],
    ].map(([label, value, yy]) => [
      text(x + 64, y + yy, label, { "font-size": 13, fill: C.muted }),
      text(x + 326, y + yy, value, { "font-size": 14, "font-weight": 650, "text-anchor": "end" }),
      yy < 554 ? line(x + 64, y + yy + 16, x + 326, y + yy + 16, { stroke: "#F0EDEA" }) : "",
    ].join("")).join(""),
    text(x + 42, y + 632, "喜欢的感觉", { "font-size": 15, "font-weight": 720 }),
    chip(x + 42, y + 654, "清新", true),
    chip(x + 126, y + 654, "优雅", true),
    chip(x + 210, y + 654, "简约", true),
    button(x + 42, y + 736, 306, 52, "生成我的风格档案"),
  ].join("");
}

function drawPhotoUpload(x, y) {
  return [
    topBar(x, y, "上传照片", true),
    text(x + 42, y + 116, "上传全身照", { "font-size": 24, "font-weight": 760 }),
    text(x + 42, y + 146, "用于分析比例与肤色，不会公开展示", { "font-size": 13, fill: C.muted }),
    card(x + 42, y + 180, 140, 190, { rx: 22, fill: C.surface2 }),
    card(x + 208, y + 180, 140, 190, { rx: 22, fill: C.surface2 }),
    text(x + 112, y + 278, "+", { "font-size": 42, fill: C.lavender, "text-anchor": "middle" }),
    text(x + 112, y + 324, "正面照", { "font-size": 13, fill: C.muted, "text-anchor": "middle" }),
    pathD(`M${x + 266} ${y + 236} C${x + 292} ${y + 238} ${x + 310} ${y + 272} ${x + 278} ${y + 320} C${x + 252} ${y + 286} ${x + 254} ${y + 258} ${x + 266} ${y + 236}Z`, {
      fill: "none",
      stroke: C.lavender,
      "stroke-width": 1.4,
      "stroke-dasharray": "5 5",
    }),
    text(x + 278, y + 324, "侧面照", { "font-size": 13, fill: C.muted, "text-anchor": "middle" }),
    card(x + 42, y + 404, 306, 170, { rx: 22, fill: C.lavenderSoft, stroke: "#E3DEFF" }),
    text(x + 64, y + 440, "拍摄建议", { "font-size": 16, "font-weight": 760 }),
    multiline(x + 64, y + 472, ["站在明亮背景前，露出肩线和鞋子", "避免宽松外套遮挡身体轮廓", "照片仅用于 AI 分析，可随时删除"], { "font-size": 13, fill: C.muted }, 25),
    text(x + 42, y + 626, "AI 分析进度", { "font-size": 15, "font-weight": 720 }),
    rect(x + 42, y + 650, 306, 10, { rx: 5, fill: "#EEEAFB" }),
    rect(x + 42, y + 650, 214, 10, { rx: 5, fill: C.lavender }),
    text(x + 42, y + 684, "正在识别身形比例、肤色和风格关键词", { "font-size": 12, fill: C.muted }),
    button(x + 42, y + 736, 306, 52, "开始分析"),
  ].join("");
}

function drawFeatureReport(x, y) {
  return [
    topBar(x, y, "我的特征分析", true),
    card(x + 28, y + 96, 334, 456, { rx: 24 }),
    text(x + 52, y + 134, "基础特征", { "font-size": 17, "font-weight": 760 }),
    pathD(`M${x + 106} ${y + 196} C${x + 134} ${y + 160} ${x + 180} ${y + 166} ${x + 200} ${y + 196} M${x + 153} ${y + 200} L${x + 153} ${y + 436}`, {
      fill: "none",
      stroke: "#B9B7C0",
      "stroke-width": 1.3,
    }),
    pathD(`M${x + 116} ${y + 244} C${x + 94} ${y + 312} ${x + 106} ${y + 380} ${x + 130} ${y + 442} M${x + 190} ${y + 244} C${x + 212} ${y + 312} ${x + 202} ${y + 380} ${x + 176} ${y + 442}`, {
      fill: "none",
      stroke: "#B9B7C0",
      "stroke-width": 1.3,
    }),
    rect(x + 82, y + 228, 144, 218, { fill: "none", stroke: "#DAD5FF", "stroke-dasharray": "4 4" }),
    ...[
      ["身形", "梨形", 184],
      ["身高", "168cm", 248],
      ["肤色", "暖白皮", 312],
      ["发色", "深棕色", 376],
      ["风格", "清新 · 优雅 · 简约", 440],
    ].map(([label, value, yy]) => [
      circle(x + 254, y + yy - 5, 13, { fill: C.lavenderSoft }),
      sparkle(x + 254, y + yy - 5, 6, C.lavender, 0.9),
      text(x + 278, y + yy - 8, label, { "font-size": 11, fill: C.muted }),
      text(x + 278, y + yy + 13, value, { "font-size": 13, "font-weight": 650 }),
    ].join("")).join(""),
    text(x + 42, y + 600, "推荐策略", { "font-size": 16, "font-weight": 760 }),
    card(x + 42, y + 620, 306, 78, { rx: 18, fill: C.surface2 }),
    multiline(x + 64, y + 650, ["上半身使用浅色外套提亮", "裤装选择垂坠直筒，拉长比例"], { "font-size": 13, fill: C.muted }, 23),
    button(x + 42, y + 736, 306, 52, "进入今日推荐"),
  ].join("");
}

function drawHome(x, y) {
  return [
    text(x + 38, y + 86, "cloz", { "font-size": 30, "font-weight": 520 }),
    text(x + 104, y + 86, "Ai", { "font-size": 30, "font-weight": 520, fill: C.lavender }),
    circle(x + 342, y + 78, 17, { fill: C.surface, stroke: C.line }),
    pathD(`M${x + 342} ${y + 68} C${x + 335} ${y + 74} ${x + 335} ${y + 84} ${x + 342} ${y + 90} C${x + 349} ${y + 84} ${x + 349} ${y + 74} ${x + 342} ${y + 68}Z`, { fill: "none", stroke: C.ink, "stroke-width": 1.2 }),
    text(x + 42, y + 150, "你好，今天想尝试", { "font-size": 13, fill: C.muted }),
    text(x + 42, y + 180, "什么风格的穿搭呢？", { "font-size": 24, "font-weight": 780 }),
    button(x + 250, y + 154, 96, 36, "上传照片", "outline"),
    card(x + 28, y + 222, 334, 316, { rx: 22 }),
    text(x + 48, y + 254, "我的特征分析", { "font-size": 15, "font-weight": 760 }),
    text(x + 314, y + 254, "查看全部 ›", { "font-size": 11, fill: C.muted, "text-anchor": "end" }),
    pathD(`M${x + 91} ${y + 318} C${x + 120} ${y + 276} ${x + 176} ${y + 278} ${x + 196} ${y + 318} M${x + 143} ${y + 318} L${x + 143} ${y + 496} M${x + 106} ${y + 358} C${x + 86} ${y + 406} ${x + 94} ${y + 456} ${x + 118} ${y + 500} M${x + 182} ${y + 358} C${x + 202} ${y + 406} ${x + 198} ${y + 456} ${x + 168} ${y + 500}`, {
      fill: "none",
      stroke: "#AFAEB7",
      "stroke-width": 1.2,
    }),
    rect(x + 84, y + 346, 128, 154, { fill: "none", stroke: "#DAD5FF", "stroke-dasharray": "4 4" }),
    ...[
      ["身形", "梨形", 296],
      ["身高", "168cm", 354],
      ["肤色", "暖白皮", 412],
      ["风格", "清新 · 优雅", 470],
    ].map(([label, value, yy]) => [
      circle(x + 240, y + yy, 12, { fill: C.lavenderSoft }),
      text(x + 262, y + yy - 5, label, { "font-size": 10.5, fill: C.muted }),
      text(x + 262, y + yy + 14, value, { "font-size": 12, "font-weight": 650 }),
    ].join("")).join(""),
    text(x + 42, y + 586, "为你推荐的穿搭", { "font-size": 16, "font-weight": 760 }),
    text(x + 322, y + 586, "查看更多 ›", { "font-size": 11, fill: C.muted, "text-anchor": "end" }),
    ...[
      [42, "今日推荐", "light"],
      [154, "通勤", "dark"],
      [266, "约会", "skirt"],
    ].map(([xx, label, outfit]) => [
      card(x + xx, y + 612, 100, 168, { rx: 10, fill: C.surface2, stroke: label === "今日推荐" ? C.lavender : C.line }),
      label === "今日推荐" ? rect(x + xx + 4, y + 616, 70, 20, { rx: 10, fill: C.lavender }) : "",
      label === "今日推荐" ? text(x + xx + 39, y + 630, label, { "font-size": 10, fill: "#fff", "text-anchor": "middle" }) : "",
      femaleIllustration(x + xx + 24, y + 638, 0.28, outfit),
    ].join("")).join(""),
    navBar(x, y, "首页"),
  ].join("");
}

function drawInspiration(x, y) {
  return [
    topBar(x, y, "灵感", false, "⌕"),
    text(x + 42, y + 112, "今日灵感", { "font-size": 25, "font-weight": 780 }),
    chip(x + 42, y + 136, "通勤", true),
    chip(x + 126, y + 136, "浅色系"),
    chip(x + 210, y + 136, "显高"),
    card(x + 30, y + 196, 150, 230, { rx: 22, fill: "url(#portraitBg)" }),
    femaleIllustration(x + 58, y + 214, 0.42, "light"),
    text(x + 46, y + 460, "米色西装的温柔通勤", { "font-size": 14, "font-weight": 700 }),
    text(x + 46, y + 484, "1280 人收藏", { "font-size": 11, fill: C.subtle }),
    card(x + 210, y + 196, 150, 190, { rx: 22, fill: C.surface2 }),
    femaleIllustration(x + 242, y + 216, 0.34, "skirt"),
    text(x + 226, y + 420, "周末约会轻法式", { "font-size": 14, "font-weight": 700 }),
    text(x + 226, y + 444, "暖白皮友好", { "font-size": 11, fill: C.subtle }),
    card(x + 30, y + 524, 330, 160, { rx: 22, fill: C.surface }),
    text(x + 54, y + 562, "本周色彩趋势", { "font-size": 15, "font-weight": 760 }),
    text(x + 54, y + 588, "低饱和蓝 + 奶油白", { "font-size": 18, "font-weight": 760, fill: C.lavender }),
    multiline(x + 54, y + 620, ["适合清爽通勤、轻熟休闲和夏季旅行"], { "font-size": 12.5, fill: C.muted }),
    circle(x + 290, y + 598, 34, { fill: C.denim }),
    circle(x + 320, y + 626, 24, { fill: C.beige }),
    navBar(x, y, "灵感"),
  ].join("");
}

function drawWardrobe(x, y) {
  return [
    topBar(x, y, "衣橱", false, "+"),
    text(x + 42, y + 112, "我的 32 件单品", { "font-size": 24, "font-weight": 780 }),
    text(x + 42, y + 142, "按季节、颜色和搭配频率管理", { "font-size": 13, fill: C.muted }),
    chip(x + 32, y + 174, "上衣", true),
    chip(x + 112, y + 174, "外套"),
    chip(x + 192, y + 174, "裤装"),
    chip(x + 272, y + 174, "鞋包"),
    ...[
      [36, 232, "blazer", "米色西装"],
      [206, 232, "top", "白色挂脖"],
      [36, 424, "pants", "浅蓝牛仔"],
      [206, 424, "shoe", "小白鞋"],
      [36, 616, "top", "黑色针织"],
      [206, 616, "blazer", "风衣外套"],
    ].map(([xx, yy, type, label]) => [
      card(x + xx, y + yy, 148, 150, { rx: 18, fill: C.surface2 }),
      itemMini(x + xx + 28, y + yy + 24, type, 0.92),
      text(x + xx + 14, y + yy + 128, label, { "font-size": 12.5, "font-weight": 650 }),
    ].join("")).join(""),
    navBar(x, y, "衣橱"),
  ].join("");
}

function drawItemDetail(x, y) {
  return [
    topBar(x, y, "单品详情", true, "♡"),
    card(x + 42, y + 100, 306, 250, { rx: 26, fill: C.surface2 }),
    itemMini(x + 126, y + 142, "blazer", 1.55),
    text(x + 42, y + 396, "米色西装外套", { "font-size": 24, "font-weight": 780 }),
    text(x + 42, y + 425, "UR 官方旗舰店 · 春夏通勤", { "font-size": 13, fill: C.muted }),
    text(x + 42, y + 474, "属性", { "font-size": 16, "font-weight": 760 }),
    ...[
      ["颜色", "米白"],
      ["材质", "轻薄西装料"],
      ["季节", "春 / 夏 / 秋"],
      ["适配", "通勤、约会"],
    ].map(([label, value], i) => [
      card(x + 42 + (i % 2) * 158, y + 500 + Math.floor(i / 2) * 72, 148, 54, { rx: 16, fill: C.surface }),
      text(x + 58 + (i % 2) * 158, y + 523 + Math.floor(i / 2) * 72, label, { "font-size": 11, fill: C.subtle }),
      text(x + 58 + (i % 2) * 158, y + 543 + Math.floor(i / 2) * 72, value, { "font-size": 13, "font-weight": 650 }),
    ].join("")).join(""),
    card(x + 42, y + 660, 306, 54, { rx: 16, fill: C.lavenderSoft, stroke: "#E3DEFF" }),
    text(x + 64, y + 694, "可搭配 18 套方案", { "font-size": 14, "font-weight": 700, fill: C.lavender }),
    button(x + 42, y + 736, 306, 52, "生成搭配"),
  ].join("");
}

function drawOutfitDetail(x, y) {
  return [
    topBar(x, y, "今日推荐", true, "♡  ⤴"),
    text(x + 42, y + 130, "综合适配度", { "font-size": 11, fill: C.muted }),
    text(x + 42, y + 164, "92%", { "font-size": 28, "font-weight": 760, fill: C.lavender }),
    rect(x + 42, y + 174, 150, 5, { rx: 3, fill: C.lavender }),
    rect(x + 192, y + 174, 46, 5, { rx: 3, fill: C.lavenderSoft }),
    card(x + 42, y + 204, 306, 456, { rx: 24, fill: "url(#portraitBg)" }),
    femaleIllustration(x + 126, y + 228, 0.92, "light"),
    sparkle(x + 318, y + 246, 17, "#fff", 0.9),
    card(x + 296, y + 456, 50, 178, { rx: 25, fill: "rgba(255,255,255,.82)", stroke: "none" }),
    ...["换背景", "换姿势", "3D 预览"].map((label, i) => [
      circle(x + 321, y + 486 + i * 52, 8, { fill: "none", stroke: C.ink, "stroke-width": 1 }),
      text(x + 321, y + 510 + i * 52, label, { "font-size": 10, fill: C.ink, "text-anchor": "middle" }),
    ].join("")).join(""),
    text(x + 42, y + 706, "穿搭亮点", { "font-size": 15, "font-weight": 760 }),
    multiline(x + 42, y + 734, ["浅色系清新温柔，拉长身形比例，简约优雅又不失时尚感。"], { "font-size": 12, fill: C.muted }, 18),
    button(x + 42, y + 790, 270, 48, "一键购买整套"),
    circle(x + 340, y + 814, 24, { fill: C.surface, stroke: C.line }),
    pathD(`M${x + 332} ${y + 808} H${x + 348} V${y + 822} H${x + 332}Z M${x + 336} ${y + 808} C${x + 336} ${y + 798} ${x + 344} ${y + 798} ${x + 344} ${y + 808}`, { fill: "none", stroke: C.ink, "stroke-width": 1.2 }),
  ].join("");
}

function drawShoppingList(x, y) {
  return [
    topBar(x, y, "搭配详情", true),
    text(x + 108, y + 112, "单品（4）", { "font-size": 15, "font-weight": 760, fill: C.lavender, "text-anchor": "middle" }),
    text(x + 280, y + 112, "套装信息", { "font-size": 15, fill: C.muted, "text-anchor": "middle" }),
    rect(x + 66, y + 128, 84, 3, { rx: 2, fill: C.lavender }),
    ...[
      ["blazer", "米色西装外套", "UR 官方旗舰店", "¥ 299", 160],
      ["top", "白色挂脖背心", "MANGO 官方旗舰店", "¥ 159", 288],
      ["pants", "浅蓝色直筒牛仔裤", "MO&Co. 官方旗舰店", "¥ 299", 416],
      ["shoe", "白色厚底小白鞋", "百丽官方旗舰店", "¥ 239", 544],
    ].map(([type, title, store, price, yy]) => [
      card(x + 28, y + yy, 334, 104, { rx: 18 }),
      itemMini(x + 52, y + yy + 22, type, 0.72),
      text(x + 150, y + yy + 38, title, { "font-size": 13.5, "font-weight": 700 }),
      text(x + 150, y + yy + 62, store, { "font-size": 11, fill: C.subtle }),
      text(x + 150, y + yy + 88, price, { "font-size": 14, "font-weight": 760 }),
      button(x + 278, y + yy + 56, 62, 30, "去购买", "outline"),
    ].join("")).join(""),
    card(x + 42, y + 706, 306, 74, { rx: 18, fill: C.lavenderSoft, stroke: "none" }),
    sparkle(x + 66, y + 734, 9, C.lavender),
    text(x + 86, y + 734, "更多相似推荐", { "font-size": 14, "font-weight": 760 }),
    text(x + 86, y + 758, "根据你的特征和偏好，发现更多适合你的单品", { "font-size": 11, fill: C.muted }),
    text(x + 326, y + 748, "›", { "font-size": 30, fill: C.ink }),
  ].join("");
}

function drawTryOn(x, y) {
  return [
    topBar(x, y, "AI 试穿", true, "保存"),
    card(x + 42, y + 104, 306, 436, { rx: 26, fill: "url(#portraitBg)" }),
    line(x + 195, y + 122, x + 195, y + 522, { stroke: "#FFFFFF", "stroke-width": 2, opacity: 0.88 }),
    text(x + 118, y + 148, "原图", { "font-size": 12, fill: C.muted, "text-anchor": "middle" }),
    text(x + 272, y + 148, "试穿后", { "font-size": 12, fill: C.lavender, "font-weight": 700, "text-anchor": "middle" }),
    femaleIllustration(x + 68, y + 178, 0.62, "dark"),
    femaleIllustration(x + 222, y + 178, 0.62, "light"),
    text(x + 42, y + 592, "已选择套装", { "font-size": 16, "font-weight": 760 }),
    card(x + 42, y + 614, 306, 86, { rx: 18 }),
    itemMini(x + 58, y + 634, "blazer", 0.58),
    itemMini(x + 122, y + 634, "pants", 0.58),
    text(x + 198, y + 652, "清新通勤套装", { "font-size": 14, "font-weight": 760 }),
    text(x + 198, y + 678, "适配度 92% · 4 件单品", { "font-size": 12, fill: C.muted }),
    button(x + 42, y + 736, 144, 52, "重新生成", "outline"),
    button(x + 204, y + 736, 144, 52, "保存试穿"),
  ].join("");
}

function drawFavorites(x, y) {
  return [
    topBar(x, y, "收藏", false, "日历"),
    text(x + 42, y + 112, "已收藏 16 套", { "font-size": 24, "font-weight": 780 }),
    card(x + 42, y + 148, 306, 82, { rx: 20, fill: C.lavenderSoft, stroke: "#E3DEFF" }),
    text(x + 64, y + 184, "明天 24°C 多云", { "font-size": 15, "font-weight": 760, fill: C.lavender }),
    text(x + 64, y + 208, "建议轻薄外套 + 直筒裤，适合通勤", { "font-size": 12, fill: C.muted }),
    ...[
      [42, 268, "通勤", "light"],
      [206, 268, "约会", "skirt"],
      [42, 502, "旅行", "dark"],
      [206, 502, "周末", "light"],
    ].map(([xx, yy, label, outfit]) => [
      card(x + xx, y + yy, 142, 186, { rx: 20, fill: C.surface2 }),
      femaleIllustration(x + xx + 33, y + yy + 20, 0.34, outfit),
      text(x + xx + 14, y + yy + 158, label, { "font-size": 13, "font-weight": 760 }),
      text(x + xx + 14, y + yy + 178, "92% 适配", { "font-size": 11, fill: C.lavender }),
    ].join("")).join(""),
    navBar(x, y, "灵感"),
  ].join("");
}

function drawProfile(x, y) {
  return [
    topBar(x, y, "我的", false, "⚙"),
    circle(x + 78, y + 122, 34, { fill: C.lavenderSoft }),
    text(x + 78, y + 135, "Z", { "font-size": 28, "font-weight": 760, fill: C.lavender, "text-anchor": "middle" }),
    text(x + 128, y + 116, "zhihao", { "font-size": 21, "font-weight": 780 }),
    text(x + 128, y + 144, "暖白皮 · 梨形 · 清新简约", { "font-size": 12, fill: C.muted }),
    rect(x + 42, y + 184, 306, 112, { rx: 24, fill: "url(#member)" }),
    text(x + 66, y + 224, "clozAi Plus", { "font-size": 19, "font-weight": 780, fill: "#FFFFFF" }),
    text(x + 66, y + 252, "无限试穿 · 优先生成 · 高级衣橱分析", { "font-size": 12, fill: "rgba(255,255,255,.84)" }),
    text(x + 304, y + 252, "续费 ›", { "font-size": 13, "font-weight": 700, fill: "#FFFFFF", "text-anchor": "end" }),
    card(x + 42, y + 330, 306, 104, { rx: 22 }),
    ...[
      ["身高", "168cm", 78],
      ["体型", "梨形", 156],
      ["肤色", "暖白", 234],
    ].map(([label, value, xx]) => [
      text(x + xx, y + 372, value, { "font-size": 18, "font-weight": 780, fill: C.lavender, "text-anchor": "middle" }),
      text(x + xx, y + 400, label, { "font-size": 11, fill: C.muted, "text-anchor": "middle" }),
    ].join("")).join(""),
    ...[
      ["身体数据", 482],
      ["订单记录", 536],
      ["隐私与照片授权", 590],
      ["通知设置", 644],
      ["帮助与反馈", 698],
    ].map(([label, yy]) => [
      card(x + 42, y + yy, 306, 44, { rx: 14, fill: C.surface }),
      text(x + 64, y + yy + 28, label, { "font-size": 14, "font-weight": 600 }),
      text(x + 326, y + yy + 29, "›", { "font-size": 20, fill: C.subtle, "text-anchor": "end" }),
    ].join("")).join(""),
    navBar(x, y, "我的"),
  ].join("");
}

function buildSvg() {
  const defs = `
    <defs>
      <linearGradient id="splashBg" x1="0" x2="1" y1="0" y2="1">
        <stop offset="0%" stop-color="#F7F3FF"/>
        <stop offset="48%" stop-color="#FFFFFF"/>
        <stop offset="100%" stop-color="#F0EDFF"/>
      </linearGradient>
      <linearGradient id="portraitBg" x1="0" x2="1" y1="0" y2="1">
        <stop offset="0%" stop-color="#F7F6F3"/>
        <stop offset="58%" stop-color="#FFFFFF"/>
        <stop offset="100%" stop-color="#F0EEFF"/>
      </linearGradient>
      <linearGradient id="cta" x1="0" x2="1" y1="0" y2="0">
        <stop offset="0%" stop-color="#8C75FF"/>
        <stop offset="100%" stop-color="#6E5BFF"/>
      </linearGradient>
      <linearGradient id="member" x1="0" x2="1" y1="0" y2="1">
        <stop offset="0%" stop-color="#9E8BFF"/>
        <stop offset="100%" stop-color="#6D58F0"/>
      </linearGradient>
      <filter id="softShadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="16" stdDeviation="18" flood-color="#19161F" flood-opacity=".08"/>
      </filter>
      <filter id="phoneShadow" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="18" stdDeviation="22" flood-color="#19161F" flood-opacity=".10"/>
      </filter>
    </defs>`;
  const body = [
    rect(0, 0, W, H, { fill: C.page }),
    circle(3080, 380, 260, { fill: "#F1EFFF", opacity: 0.45 }),
    circle(420, 1980, 320, { fill: "#FFF1F3", opacity: 0.55 }),
    drawHeader(),
    screens.map(([code, title, draw], i) => drawPhone(i, code, title, draw)).join(""),
  ].join("");
  return `<?xml version="1.0" encoding="UTF-8"?>\n<svg width="${W}" height="${H}" viewBox="0 0 ${W} ${H}" fill="none" xmlns="http://www.w3.org/2000/svg">\n${defs}\n${body}\n</svg>\n`;
}

const svg = buildSvg();
const svgPath = path.join(outDir, "clozai-ios-ui-kit.figma-import.svg");
fs.writeFileSync(svgPath, svg, "utf8");

const html = `<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>clozAi iOS UI Kit</title>
  <style>
    body { margin: 0; background: #f7f5f2; font-family: Inter, "PingFang SC", "Microsoft YaHei", sans-serif; }
    header { position: sticky; top: 0; z-index: 2; display: flex; gap: 16px; align-items: center; justify-content: space-between; padding: 14px 20px; background: rgba(255,255,255,.86); backdrop-filter: blur(16px); border-bottom: 1px solid #ebe7e2; }
    h1 { margin: 0; font-size: 18px; line-height: 24px; }
    p { margin: 2px 0 0; color: #72727d; font-size: 13px; }
    a { color: #7b68ff; text-decoration: none; font-weight: 700; }
    .stage { padding: 24px; overflow: auto; }
    img { display: block; width: ${W}px; height: ${H}px; max-width: none; border-radius: 18px; box-shadow: 0 24px 70px rgba(17,17,22,.12); }
  </style>
</head>
<body>
  <header>
    <div>
      <h1>clozAi iOS UI Kit</h1>
      <p>14 个完整 App 页面，可将 SVG 拖入 Figma 作为可编辑设计板继续拆分。</p>
    </div>
    <a href="./clozai-ios-ui-kit.figma-import.svg">打开 SVG</a>
  </header>
  <main class="stage">
    <img src="./clozai-ios-ui-kit.figma-import.svg" alt="clozAi iOS UI Kit" />
  </main>
</body>
</html>
`;
fs.writeFileSync(path.join(outDir, "clozai-ios-ui-kit.preview.html"), html, "utf8");

const spec = `# clozAi iOS App UI Kit

Figma 文件已创建，但当前 Figma MCP 在 Starter 方案下返回调用额度限制，暂时无法继续用 API 直接写入画布。

- Figma 文件：<https://www.figma.com/design/pzELrAOqY7Y2QwLZOHfwu4>
- 可导入 Figma 的设计板：\`design/clozai-ios-ui-kit.figma-import.svg\`
- 浏览器预览：\`design/clozai-ios-ui-kit.preview.html\`

## 页面范围

1. 启动页
2. 登录欢迎
3. 风格建档
4. 照片上传
5. 特征报告
6. 首页推荐
7. 灵感社区
8. 我的衣橱
9. 单品详情
10. 搭配详情
11. 购买清单
12. AI 试穿
13. 收藏日历
14. 我的设置

## iOS 设计 Token

- Background: \`#F7F5F2\`
- Surface: \`#FFFFFF\`
- Pearl: \`#FAF9F6\`
- Ink: \`#111116\`
- Muted: \`#72727D\`
- Divider: \`#E8E5E0\`
- Primary Lavender: \`#8A78FF\`
- Lavender Soft: \`#EFECFF\`
- Denim Accent: \`#DDE9F0\`
- Linen Accent: \`#E9E0D3\`
- Corner radius: cards \`16-24\`, phone \`44\`, CTA \`26\`
- Typography: SF Pro / PingFang SC, title 24-28, section 15-17, body 12-14, caption 10-11

## Figma 导入建议

将 \`design/clozai-ios-ui-kit.figma-import.svg\` 拖进 Figma 文件即可得到完整设计板。额度恢复后，建议再用 Figma API 重建为 native frame/component：

- 建立 \`Colors\`, \`Typography\`, \`Spacing\`, \`Radius\`, \`Shadow\` 变量集合
- 抽出 \`Button / Chip / Card / Phone Frame / Product Row / Bottom Tab\` 组件
- 将 14 个 screen frame 按 iOS 390 x 844 拆分并命名
- 为 iOS 客户端保留每屏主要状态：empty/loading/filled/error
`;
fs.writeFileSync(path.join(outDir, "clozai-ios-ui-kit.spec.md"), spec, "utf8");

console.log(JSON.stringify({
  svg: "design/clozai-ios-ui-kit.figma-import.svg",
  preview: "design/clozai-ios-ui-kit.preview.html",
  spec: "design/clozai-ios-ui-kit.spec.md",
}, null, 2));
