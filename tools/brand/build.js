// Builds the AnarchicPsyche logo suite from the mark's geometry.
//
//   node tools/brand/build.js
//
// Needs Playwright with Chromium (to render PNGs). Writes:
//   brand/svg, brand/png        the suite (not published)
//   assets/img/logo.svg         header mark (inline, follows light/dark)
//   assets/img/logo-stacked.svg homepage heading (mark + wordmark)
//   assets/img/social.png       default share image
//   static/favicon*, apple-touch-icon.png, android-chrome-*.png, site.webmanifest
//
// Geometry is measured from the original ap_logo.png (489x452 px, kept in
// brand/original/) and redrawn as strokes on the same grid.

const fs = require("fs");
const path = require("path");
const { chromium } = require("playwright");

const ROOT = path.resolve(__dirname, "../..");
const WORDMARK = require("./wordmark.json");

const INK = "#111111";
const PAPER = "#f6f1e7"; // warm off-white
const SLATE = "#1e293b"; // Blowfish dark background (neutral-800)
const SUN = "#e08a2c"; // amber, for the "sunrise" variant

// --- the mark ---------------------------------------------------------------
const G = {
  horizonY: 310,
  horizon: [0, 489],
  sun: { cx: 246, cy: 168, r: 165.5 },
  apex: [246, 170], // top of the peak = centre of the sun
  knee: [246, 222], // where the two right-hand lines leave the vertical
  stemEnd: 447,
  longLeg: [78, 449],
  innerLeft: [189, 310],
  innerRight: [294, 310],
  outerRight: [330, 310],
  hatch: [
    [286, 30, 368, 114],
    [233.5, 50, 356, 175.5],
    [163, 64.8, 342, 237.4],
  ],
};

// Stroke weights by display size. fine = the original drawing (large uses),
// regular = header, hero and lockups, bold = app icons, tiny = 16-32 px favicons.
// Smaller sizes drop detail: inner legs, then hatch lines, and shorten the horizon.
const WEIGHTS = {
  fine: { sw: 6.6, hw: 4.4 },
  regular: { sw: 16, hw: 11 },
  bold: { sw: 26, hw: 18, hatches: 2, inner: false, horizon: [50, 442] },
  tiny: { sw: 44, hw: 0, hatches: 0, inner: false, horizon: [70, 422] },
};

const f = (n) => +n.toFixed(2);

function shorten([x1, y1, x2, y2], by) {
  const len = Math.hypot(x2 - x1, y2 - y1);
  const [ux, uy] = [(x2 - x1) / len, (y2 - y1) / len];
  return [x1 + ux * by, y1 + uy * by, x2 - ux * by, y2 - uy * by];
}

// Returns { body, box: [x, y, w, h] } in mark units.
function mark(weight, { stroke = "currentColor", sun = stroke } = {}) {
  const { sw, hw, hatches = 3, inner = true, horizon = G.horizon } = weight;
  const { cx, cy, r } = G.sun;
  const dx = Math.sqrt(r * r - (G.horizonY - cy) ** 2);
  const arc = `M${f(cx - dx)} ${G.horizonY}A${r} ${r} 0 1 1 ${f(cx + dx)} ${G.horizonY}`;
  // With two hatches, drop the top one (it would touch the ring) and trim the rest.
  const hatch = (hatches === 3 ? G.hatch : G.hatch.slice(1).map((h) => shorten(h, 14)))
    .slice(0, hatches)
    .map(([a, b, c, d]) => `M${f(a)} ${f(b)}L${f(c)} ${f(d)}`).join("");
  const [ax, ay] = G.apex, [kx, ky] = G.knee;
  const lines = [
    `M${horizon[0]} ${G.horizonY}H${horizon[1]}`,
    `M${ax} ${ay}V${G.stemEnd}`,
    `M${ax} ${ay}L${G.longLeg.join(" ")}`,
    inner ? `M${ax} ${ay}L${G.innerLeft.join(" ")}` : "",
    inner ? `M${kx} ${ky}L${G.innerRight.join(" ")}` : "",
    `M${kx} ${ky}L${G.outerRight.join(" ")}`,
  ].join("");
  const body =
    `<g fill="none" stroke-linecap="round" stroke-linejoin="round">` +
    `<path d="${arc}" stroke="${sun}" stroke-width="${sw}"/>` +
    (hatch ? `<path d="${hatch}" stroke="${sun}" stroke-width="${hw}"/>` : "") +
    `<path d="${lines}" stroke="${stroke}" stroke-width="${sw}"/></g>`;
  const pad = sw / 2;
  const x0 = Math.min(horizon[0], G.longLeg[0], cx - r) - pad, y0 = cy - r - pad;
  const x1 = Math.max(horizon[1], G.outerRight[0], cx + r) + pad, y1 = Math.max(G.longLeg[1], G.stemEnd) + pad;
  return { body, box: [f(x0), f(y0), f(x1 - x0), f(y1 - y0)] };
}

// Wordmark path, scaled so its x-height is `xh` mark units, baseline at (x, y).
function wordmark(weight, x, y, xh, fill) {
  const w = WORDMARK.weights[weight];
  const s = xh / w.xHeight;
  return {
    body: `<path transform="translate(${f(x)} ${f(y)}) scale(${f(s * 1000) / 1000})" fill="${fill}" d="${w.d}"/>`,
    width: w.width * s,
  };
}

// decorative: for copies inlined next to the site name (hidden from screen readers).
function svg(box, body, { size, title = "AnarchicPsyche", extra = "", decorative = false } = {}) {
  const wh = size ? ` width="${size[0]}" height="${size[1]}"` : "";
  const a11y = decorative ? ` aria-hidden="true" focusable="false">` : ` role="img" aria-label="${title}"><title>${title}</title>`;
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${box.join(" ")}"${wh}${a11y}${extra}${body}</svg>\n`;
}

// --- compositions -----------------------------------------------------------
function markSvg(weight, colors, opts) {
  const m = mark(WEIGHTS[weight], colors);
  return svg(m.box, m.body, opts);
}

// Mark + wordmark sitting on the horizon line.
function lockup(weight, ink, fontWeight) {
  const m = mark(WEIGHTS[weight], { stroke: ink });
  const [x, y, w, h] = m.box;
  const gap = 110, xh = 132;
  const t = wordmark(fontWeight, x + w + gap, G.horizonY, xh, ink);
  return svg([x, y, f(w + gap + t.width + 20), h], m.body + t.body);
}

// Mark above a centred wordmark.
function stacked(weight, ink, fontWeight, opts) {
  const m = mark(WEIGHTS[weight], { stroke: ink });
  const [x, y, w, h] = m.box;
  const xh = 62, width = WORDMARK.weights[fontWeight].width * (xh / 460);
  const top = y + h + 175;
  const t = wordmark(fontWeight, x + w / 2 - width / 2, top, xh, ink);
  const left = Math.min(x, x + w / 2 - width / 2) - 10;
  return svg([f(left), y, f(Math.max(w, width) + 20), f(top - y + 32)], m.body + t.body, opts);
}

// Square tile: background + bold mark, inside the maskable safe zone.
function tile(bg, ink, { radius = 0, scale = 0.62, weight = "bold" } = {}) {
  const S = 1024;
  const m = mark(WEIGHTS[weight], { stroke: ink });
  const [x, y, w, h] = m.box;
  const k = (S * scale) / Math.max(w, h);
  const tx = (S - w * k) / 2 - x * k, ty = (S - h * k) / 2 - y * k;
  const rect = `<rect width="${S}" height="${S}" rx="${radius * S}" fill="${bg}"/>`;
  return svg([0, 0, S, S], `${rect}<g transform="translate(${f(tx)} ${f(ty)}) scale(${f(k * 1e4) / 1e4})">${m.body}</g>`);
}

// Transparent favicon that switches colour with the browser theme.
function favicon() {
  const m = mark(WEIGHTS.tiny, { stroke: "var(--ink)" });
  const [x, y, w, h] = m.box;
  const side = Math.max(w, h);
  const box = [f(x - (side - w) / 2), f(y - (side - h) / 2), f(side), f(side)];
  const style = `<style>:root{--ink:${INK}}@media (prefers-color-scheme:dark){:root{--ink:${PAPER}}}</style>`;
  return svg(box, m.body, { extra: style });
}

function social() {
  const W = 1200, H = 630;
  const inner = lockup("regular", INK, 300);
  const vb = inner.match(/viewBox="([^"]+)"/)[1].split(" ").map(Number);
  const k = 960 / vb[2];
  const tx = (W - vb[2] * k) / 2 - vb[0] * k, ty = (H - vb[3] * k) / 2 - vb[1] * k;
  const body = inner.replace(/^<svg[^>]*><title>[^<]*<\/title>/, "").replace(/<\/svg>\n$/, "");
  return svg([0, 0, W, H], `<rect width="${W}" height="${H}" fill="${PAPER}"/><g transform="translate(${f(tx)} ${f(ty)}) scale(${f(k * 1e4) / 1e4})">${body}</g>`);
}

// --- output -----------------------------------------------------------------
const write = (rel, data) => {
  const p = path.join(ROOT, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, data);
  return p;
};

const SVGS = {
  "mark-fine-black": markSvg("fine", { stroke: INK }),
  "mark-fine-white": markSvg("fine", { stroke: PAPER }),
  "mark-regular-black": markSvg("regular", { stroke: INK }),
  "mark-regular-white": markSvg("regular", { stroke: PAPER }),
  "mark-bold-black": markSvg("bold", { stroke: INK }),
  "mark-bold-white": markSvg("bold", { stroke: PAPER }),
  "mark-tiny-black": markSvg("tiny", { stroke: INK }),
  "mark-sunrise": markSvg("fine", { stroke: INK, sun: SUN }),
  "mark-sunrise-regular": markSvg("regular", { stroke: INK, sun: SUN }),
  "lockup-black": lockup("regular", INK, 300),
  "lockup-white": lockup("regular", PAPER, 300),
  "lockup-fine-black": lockup("fine", INK, 200),
  "lockup-fine-white": lockup("fine", PAPER, 200),
  "lockup-stacked-black": stacked("regular", INK, 300),
  "lockup-stacked-white": stacked("regular", PAPER, 300),
  "app-icon-light": tile(PAPER, INK),
  "app-icon-dark": tile(SLATE, PAPER),
  "favicon": favicon(),
  "social": social(),
};

// [svg name, png name, width] — height follows the aspect ratio.
const PNGS = [
  ["mark-fine-black", "brand/png/mark-fine-black.png", 2048],
  ["mark-fine-white", "brand/png/mark-fine-white.png", 2048],
  ["mark-regular-black", "brand/png/mark-regular-black.png", 1024],
  ["mark-regular-white", "brand/png/mark-regular-white.png", 1024],
  ["mark-bold-black", "brand/png/mark-bold-black.png", 512],
  ["mark-bold-white", "brand/png/mark-bold-white.png", 512],
  ["mark-sunrise", "brand/png/mark-sunrise.png", 2048],
  ["lockup-black", "brand/png/lockup-black.png", 2400],
  ["lockup-white", "brand/png/lockup-white.png", 2400],
  ["lockup-stacked-black", "brand/png/lockup-stacked-black.png", 1600],
  ["lockup-stacked-white", "brand/png/lockup-stacked-white.png", 1600],
  ["app-icon-light", "brand/png/app-icon-light.png", 1024],
  ["app-icon-dark", "brand/png/app-icon-dark.png", 1024],
  ["social", "assets/img/social.png", 1200],
  ["app-icon-light", "static/apple-touch-icon.png", 180],
  ["app-icon-light", "static/android-chrome-192x192.png", 192],
  ["app-icon-light", "static/android-chrome-512x512.png", 512],
];

// Small favicons: rounded paper tile so they read on light and dark tabs.
const SMALL = tile(PAPER, INK, { radius: 0.22, scale: 0.84, weight: "tiny" });
const ICO_SIZES = [16, 32, 48];

function ico(pngs) {
  // ICO container with embedded PNGs (supported by every current browser/OS).
  const head = Buffer.alloc(6 + 16 * pngs.length);
  head.writeUInt16LE(0, 0); head.writeUInt16LE(1, 2); head.writeUInt16LE(pngs.length, 4);
  let offset = head.length;
  pngs.forEach(({ size, data }, i) => {
    const e = 6 + 16 * i;
    head.writeUInt8(size % 256, e); head.writeUInt8(size % 256, e + 1);
    head.writeUInt16LE(1, e + 4); head.writeUInt16LE(32, e + 6);
    head.writeUInt32LE(data.length, e + 8); head.writeUInt32LE(offset, e + 12);
    offset += data.length;
  });
  return Buffer.concat([head, ...pngs.map((p) => p.data)]);
}

async function main() {
  for (const [name, data] of Object.entries(SVGS)) write(`brand/svg/${name}.svg`, data);
  // Site copies use currentColor, so they follow the text colour in light and dark mode.
  write("assets/img/logo.svg", markSvg("regular", { stroke: "currentColor" }, { decorative: true }));
  write("assets/img/logo-stacked.svg", stacked("regular", "currentColor", 300, { decorative: true }));
  write("static/favicon.svg", SVGS.favicon);
  write("static/site.webmanifest", JSON.stringify({
    name: "AnarchicPsyche",
    short_name: "AnarchicPsyche",
    icons: [
      { src: "/android-chrome-192x192.png", sizes: "192x192", type: "image/png", purpose: "any maskable" },
      { src: "/android-chrome-512x512.png", sizes: "512x512", type: "image/png", purpose: "any maskable" },
    ],
    theme_color: PAPER,
    background_color: PAPER,
    display: "standalone",
    start_url: "/",
  }, null, 2) + "\n");

  const browser = await chromium.launch();
  const page = await browser.newPage({ deviceScaleFactor: 1 });
  const render = async (svgText, width) => {
    const [, , w, h] = svgText.match(/viewBox="([^"]+)"/)[1].split(" ").map(Number);
    const height = Math.round((width * h) / w);
    const sized = svgText.replace("<svg ", `<svg width="${width}" height="${height}" `);
    await page.setViewportSize({ width, height });
    await page.setContent(`<!doctype html><style>html,body{margin:0;background:transparent}svg{display:block}</style>${sized}`);
    return page.screenshot({ omitBackground: true, clip: { x: 0, y: 0, width, height } });
  };
  for (const [name, out, width] of PNGS) write(out, await render(SVGS[name], width));
  const small = [];
  for (const size of ICO_SIZES) small.push({ size, data: await render(SMALL, size) });
  write("static/favicon-16x16.png", small[0].data);
  write("static/favicon-32x32.png", small[1].data);
  write("static/favicon.ico", ico(small));
  await browser.close();
  console.log(`wrote ${Object.keys(SVGS).length} SVGs, ${PNGS.length + ICO_SIZES.length} PNGs, favicon.ico`);
}

if (require.main === module) main().catch((e) => { console.error(e); process.exit(1); });
module.exports = { G, WEIGHTS, mark, svg };
