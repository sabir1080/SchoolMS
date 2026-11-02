// Draws the illustrated student photos used by the "scholars" demo school (apps/tenants/demo_photos).
// Run from the backend folder:  node tools/demo_photos.mjs   (needs the pre-installed Playwright + Chromium)
// Files: <level>_<b|g>_<nn>.jpg, level 0 = youngest class (age ~4) ... level 4 = Class 3 (age ~8).
// No real children are pictured: every face is a drawing made from a fixed random seed.
import { createRequire } from "node:module";
import { mkdirSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const require = createRequire(import.meta.url);
const { chromium } = require("playwright");
const OUT = join(dirname(fileURLToPath(import.meta.url)), "..", "apps", "tenants", "demo_photos");
const LEVELS = 5;
const PER_GROUP = 22; // photos per level and gender

function rng(seed) {
  let s = seed >>> 0; // mulberry32
  return () => {
    s = (s + 0x6d2b79f5) >>> 0;
    let x = Math.imul(s ^ (s >>> 15), 1 | s);
    x = (x + Math.imul(x ^ (x >>> 7), 61 | x)) ^ x;
    return ((x ^ (x >>> 14)) >>> 0) / 2 ** 32;
  };
}
const pick = (r, list) => list[Math.floor(r() * list.length)];
function shade(hex, f) {
  const n = parseInt(hex.slice(1), 16);
  const c = [n >> 16, (n >> 8) & 255, n & 255].map((v) => Math.max(0, Math.min(255, Math.round(f < 0 ? v * (1 + f) : v + (255 - v) * f))));
  return "#" + c.map((v) => v.toString(16).padStart(2, "0")).join("");
}

const SKINS = ["#f3cfae", "#ebbf98", "#e2ad84", "#d69d72", "#c88b60", "#b97a52", "#a8693f"];
const HAIRS = ["#16100c", "#1f1510", "#2a1a12", "#3a2417", "#24170f"];
const RIBBONS = ["#d42a3c", "#ffffff", "#1f3a7a", "#e8559a", "#d42a3c"];
const BACKS = [["#e4ecf4", "#c3d3e3"], ["#e9eef2", "#c9d2db"], ["#e2eaf3", "#bccde0"]];

function portrait(level, gender, n) {
  const r = rng(level * 1000 + (gender === "g" ? 500 : 0) + n * 7 + 11);
  const t = Math.min(1, Math.max(0, (level + (r() - 0.5) * 0.8) / (LEVELS - 1))); // 0 = age 4, 1 = age 8
  const girl = gender === "g";
  const skin = pick(r, SKINS);
  const hair = pick(r, HAIRS);
  const [bg1, bg2] = pick(r, BACKS);
  const cx = 150;
  const rx = 84 - 12 * t + (r() - 0.5) * 4;
  const ry = 92 - 4 * t + (r() - 0.5) * 4;
  const cy = 160 - 12 * t;
  const sy = cy + ry + 4 + 20 * t; // shoulder line
  const sw = 108 + 36 * t; // half shoulder width
  const nw = 25 - 2 * t;
  const k = 0.5523;
  const j1 = 0.62 - 0.1 * t, j2 = 0.62 - 0.2 * t; // rounder chin when young
  const eyeY = cy + ry * (0.14 - 0.12 * t);
  const eyeDx = rx * 0.43;
  const eyeR = 13 - 2.5 * t;
  const noseY = eyeY + ry * 0.3;
  const mouthY = noseY + ry * 0.22;
  const scarf = girl && level >= 3 && r() < 0.3;
  const young = level <= 1;
  const sweater = young ? "#8c1d3c" : "#1e2d5a";
  const shirt = young ? "#a9d4f2" : "#ffffff";
  const id = `p${level}${gender}${n}`;
  const out = [];
  const face = `M ${cx - rx} ${cy} C ${cx - rx} ${cy - k * ry} ${cx - k * rx} ${cy - ry} ${cx} ${cy - ry} C ${cx + k * rx} ${cy - ry} ${cx + rx} ${cy - k * ry} ${cx + rx} ${cy} C ${cx + rx} ${cy + ry * j1} ${cx + rx * j2} ${cy + ry} ${cx} ${cy + ry} C ${cx - rx * j2} ${cy + ry} ${cx - rx} ${cy + ry * j1} ${cx - rx} ${cy} Z`;

  out.push(`<defs>
    <linearGradient id="bg${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${bg1}"/><stop offset="1" stop-color="${bg2}"/></linearGradient>
    <radialGradient id="sk${id}" cx="0.45" cy="0.4" r="0.7"><stop offset="0" stop-color="${shade(skin, 0.12)}"/><stop offset="0.75" stop-color="${skin}"/><stop offset="1" stop-color="${shade(skin, -0.12)}"/></radialGradient>
    <linearGradient id="sw${id}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="${shade(sweater, -0.25)}"/><stop offset="0.5" stop-color="${sweater}"/><stop offset="1" stop-color="${shade(sweater, -0.3)}"/></linearGradient>
    <linearGradient id="hr${id}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${shade(hair, 0.18)}"/><stop offset="1" stop-color="${hair}"/></linearGradient>
  </defs>`);
  out.push(`<rect width="300" height="360" fill="url(#bg${id})"/>`);
  out.push(`<ellipse cx="${cx}" cy="${sy + 70}" rx="${sw + 30}" ry="40" fill="#000" opacity="0.06"/>`);

  // Hair behind the head
  const girlStyle = girl ? pick(r, young ? ["pigtails", "bob", "pigtails", "bob", "long"] : ["long", "braids", "pigtails", "long", "braids", "bob"]) : null;
  const boyStyle = girl ? null : pick(r, ["side", "straight", "short", "side"]);
  if (!scarf) {
    if (girl && (girlStyle === "long" || girlStyle === "braids")) {
      const len = girlStyle === "long" ? sy + 30 : sy - 10;
      out.push(`<path d="M ${cx - rx - 12} ${cy - ry * 0.2} C ${cx - rx - 16} ${cy - ry * 1.25} ${cx + rx + 16} ${cy - ry * 1.25} ${cx + rx + 12} ${cy - ry * 0.2} L ${cx + rx + 16} ${len} Q ${cx} ${len + 18} ${cx - rx - 16} ${len} Z" fill="url(#hr${id})"/>`);
    } else if (girl && girlStyle === "bob") {
      out.push(`<path d="M ${cx - rx - 14} ${cy + ry * 0.5} C ${cx - rx - 22} ${cy - ry * 1.3} ${cx + rx + 22} ${cy - ry * 1.3} ${cx + rx + 14} ${cy + ry * 0.5} Q ${cx + rx} ${cy + ry * 0.62} ${cx + rx - 12} ${cy + ry * 0.5} L ${cx - rx + 12} ${cy + ry * 0.5} Q ${cx - rx} ${cy + ry * 0.62} ${cx - rx - 14} ${cy + ry * 0.5} Z" fill="url(#hr${id})"/>`);
    } else {
      out.push(`<ellipse cx="${cx}" cy="${cy - ry * 0.28}" rx="${rx + (girl ? 9 : 5)}" ry="${ry * 0.86}" fill="url(#hr${id})"/>`);
    }
    if (girl && girlStyle === "pigtails") {
      for (const s of [-1, 1]) {
        const px = cx + s * (rx + 18), py = cy - ry * 0.35;
        out.push(`<ellipse cx="${px + s * 8}" cy="${py + 26}" rx="24" ry="34" transform="rotate(${s * -18} ${px} ${py})" fill="url(#hr${id})"/>`);
      }
    }
  }

  // Neck and uniform
  out.push(`<rect x="${cx - nw}" y="${cy + ry * 0.55}" width="${nw * 2}" height="${sy - cy - ry * 0.55 + 20}" fill="${shade(skin, -0.06)}"/>`);
  out.push(`<ellipse cx="${cx}" cy="${cy + ry * 0.95}" rx="${nw + 4}" ry="12" fill="${shade(skin, -0.22)}" opacity="0.5"/>`);
  out.push(`<path d="M ${cx - sw} 360 C ${cx - sw} ${sy + 24} ${cx - sw + 22} ${sy} ${cx - nw - 34} ${sy - 6} L ${cx + nw + 34} ${sy - 6} C ${cx + sw - 22} ${sy} ${cx + sw} ${sy + 24} ${cx + sw} 360 Z" fill="url(#sw${id})"/>`);
  const vy = sy + (young ? 48 : 64);
  out.push(`<path d="M ${cx - nw - 14} ${sy - 7} L ${cx + nw + 14} ${sy - 7} L ${cx} ${vy} Z" fill="${shirt}"/>`);
  if (!young && !girl) {
    out.push(`<path d="M ${cx - 6} ${sy + 4} L ${cx + 6} ${sy + 4} L ${cx + 8} ${sy + 15} L ${cx - 8} ${sy + 15} Z" fill="#7a1f2b"/>`);
    out.push(`<path d="M ${cx - 7} ${sy + 15} L ${cx + 7} ${sy + 15} L ${cx + 12} ${vy - 6} L ${cx} ${vy + 6} L ${cx - 12} ${vy - 6} Z" fill="#8d2433"/>`);
    out.push(`<path d="M ${cx - 9} ${sy + 28} L ${cx + 9} ${sy + 22} M ${cx - 10} ${sy + 44} L ${cx + 11} ${sy + 37}" stroke="#c9a227" stroke-width="3"/>`);
  }
  if (young) {
    // Rounded (Peter Pan) collar
    for (const s of [-1, 1]) {
      out.push(`<path d="M ${cx} ${sy + 2} Q ${cx + s * (nw + 30)} ${sy - 2} ${cx + s * (nw + 22)} ${sy + 22} Q ${cx + s * 14} ${sy + 28} ${cx} ${sy + 2} Z" fill="#ffffff" stroke="#d6dde6" stroke-width="1.5"/>`);
    }
  } else {
    for (const s of [-1, 1]) {
      out.push(`<path d="M ${cx + s * 3} ${sy + 6} L ${cx + s * (nw + 10)} ${sy - 12} L ${cx + s * (nw + 22)} ${sy + 16} Z" fill="#ffffff" stroke="#cfd6df" stroke-width="1.5"/>`);
    }
  }
  out.push(`<path d="M ${cx - nw - 14} ${sy - 7} L ${cx} ${vy} L ${cx + nw + 14} ${sy - 7}" fill="none" stroke="${shade(sweater, 0.18)}" stroke-width="7" stroke-linejoin="round"/>`);
  const bx = cx + sw * 0.5, by = sy + 62;
  out.push(`<circle cx="${bx}" cy="${by}" r="12" fill="#e2b93b" stroke="#fff3c4" stroke-width="2"/>`);
  out.push(`<path d="M ${bx} ${by - 7} L ${bx + 2.2} ${by - 2} L ${bx + 7} ${by - 2} L ${bx + 3} ${by + 1.5} L ${bx + 4.5} ${by + 6.5} L ${bx} ${by + 3.5} L ${bx - 4.5} ${by + 6.5} L ${bx - 3} ${by + 1.5} L ${bx - 7} ${by - 2} L ${bx - 2.2} ${by - 2} Z" fill="${sweater}"/>`);

  // Head scarf (drawn over the shoulders, the face sits inside it)
  if (scarf) {
    out.push(`<path d="M ${cx - rx - 24} ${cy} C ${cx - rx - 28} ${cy - ry * 1.42} ${cx + rx + 28} ${cy - ry * 1.42} ${cx + rx + 24} ${cy} C ${cx + rx + 26} ${sy - 10} ${cx + sw * 0.75} ${sy + 10} ${cx + sw * 0.62} ${sy + 52} Q ${cx} ${sy + 80} ${cx - sw * 0.62} ${sy + 52} C ${cx - sw * 0.75} ${sy + 10} ${cx - rx - 26} ${sy - 10} ${cx - rx - 24} ${cy} Z" fill="#fbfcfd" stroke="#dfe5ec" stroke-width="2"/>`);
    out.push(`<path d="M ${cx - sw * 0.45} ${sy + 40} Q ${cx} ${sy + 62} ${cx + sw * 0.4} ${sy + 34}" fill="none" stroke="#e3e8ee" stroke-width="2"/>`);
  } else {
    for (const s of [-1, 1]) {
      out.push(`<ellipse cx="${cx + s * rx * 0.97}" cy="${eyeY + 8}" rx="12" ry="17" fill="${shade(skin, -0.04)}"/>`);
      out.push(`<ellipse cx="${cx + s * rx * 0.99}" cy="${eyeY + 8}" rx="6" ry="10" fill="${shade(skin, -0.18)}" opacity="0.6"/>`);
    }
  }

  // Face and features
  out.push(`<path d="${face}" fill="url(#sk${id})"/>`);
  if (scarf) {
    out.push(`<ellipse cx="${cx}" cy="${cy - 6}" rx="${rx + 3}" ry="${ry + 9}" fill="none" stroke="#fbfcfd" stroke-width="14"/>`);
    out.push(`<ellipse cx="${cx}" cy="${cy - 6}" rx="${rx - 4}" ry="${ry + 2}" fill="none" stroke="#e1e6ec" stroke-width="1.5"/>`);
  }
  const blush = 0.32 - 0.14 * t;
  for (const s of [-1, 1]) {
    out.push(`<ellipse cx="${cx + s * rx * 0.56}" cy="${mouthY - 8}" rx="13" ry="9" fill="#f07c78" opacity="${blush.toFixed(2)}"/>`);
  }
  const iris = pick(r, ["#3a2416", "#2b1a10", "#4a2e1a"]);
  const look = (r() - 0.5) * 2;
  for (const s of [-1, 1]) {
    const ex = cx + s * eyeDx;
    out.push(`<ellipse cx="${ex}" cy="${eyeY}" rx="${eyeR + 2}" ry="${eyeR * 0.82}" fill="#ffffff"/>`);
    out.push(`<circle cx="${ex + look}" cy="${eyeY + 0.5}" r="${eyeR * 0.68}" fill="${iris}"/>`);
    out.push(`<circle cx="${ex + look}" cy="${eyeY + 0.5}" r="${eyeR * 0.34}" fill="#0d0806"/>`);
    out.push(`<circle cx="${ex + look - 2.5}" cy="${eyeY - 2.5}" r="${eyeR * 0.22}" fill="#ffffff"/>`);
    out.push(`<path d="M ${ex - eyeR - 3} ${eyeY + 1} Q ${ex} ${eyeY - eyeR * 1.15} ${ex + eyeR + 3} ${eyeY + 1}" fill="none" stroke="#24150e" stroke-width="2.6" stroke-linecap="round"/>`);
    if (girl) {
      out.push(`<path d="M ${ex + s * (eyeR + 2)} ${eyeY - 2} l ${s * 5} -4 M ${ex + s * (eyeR - 1)} ${eyeY - 5} l ${s * 4} -5" stroke="#24150e" stroke-width="1.8" stroke-linecap="round"/>`);
    }
    const by2 = eyeY - eyeR - 9 - 2 * t;
    out.push(`<path d="M ${ex - 12} ${by2 + 2} Q ${ex} ${by2 - 5} ${ex + 12} ${by2 + 1}" fill="none" stroke="${hair}" stroke-width="${girl ? 3 : 4}" stroke-linecap="round"/>`);
  }
  out.push(`<path d="M ${cx - 5} ${noseY} Q ${cx} ${noseY + 5} ${cx + 5} ${noseY}" fill="none" stroke="${shade(skin, -0.3)}" stroke-width="2.4" stroke-linecap="round"/>`);
  out.push(`<ellipse cx="${cx}" cy="${noseY - 6}" rx="5" ry="7" fill="${shade(skin, 0.15)}" opacity="0.5"/>`);
  const mw = 15 + 3 * t + r() * 3;
  const smile = pick(r, ["closed", "open", "open", "closed"]);
  if (smile === "closed") {
    out.push(`<path d="M ${cx - mw} ${mouthY} Q ${cx} ${mouthY + 13} ${cx + mw} ${mouthY}" fill="none" stroke="#8a3a30" stroke-width="3.2" stroke-linecap="round"/>`);
  } else {
    out.push(`<path d="M ${cx - mw} ${mouthY} Q ${cx} ${mouthY + 24} ${cx + mw} ${mouthY} Q ${cx} ${mouthY + 4} ${cx - mw} ${mouthY} Z" fill="#7d2a2a"/>`);
    out.push(`<path d="M ${cx - mw * 0.55} ${mouthY + 11} Q ${cx} ${mouthY + 5} ${cx + mw * 0.55} ${mouthY + 11} Q ${cx} ${mouthY + 18} ${cx - mw * 0.55} ${mouthY + 11} Z" fill="#e2707a"/>`);
    out.push(`<path d="M ${cx - mw + 3} ${mouthY + 1.5} Q ${cx} ${mouthY + 10} ${cx + mw - 3} ${mouthY + 1.5} Q ${cx} ${mouthY + 4} ${cx - mw + 3} ${mouthY + 1.5} Z" fill="#ffffff"/>`);
    if (level >= 2 && level <= 3 && r() < 0.5) {
      out.push(`<rect x="${cx + 1}" y="${mouthY + 2}" width="6" height="6" fill="#7d2a2a"/>`); // a missing milk tooth
    }
  }

  // Hair in front (fringe / hairline)
  if (!scarf) {
    const top = cy - ry - (girl ? 12 : 9);
    if (girl) {
      if (girlStyle === "bob" || (girlStyle === "pigtails" && r() < 0.5)) {
        let d = `M ${cx - rx - 8} ${cy + ry * 0.05} C ${cx - rx - 10} ${top - 4} ${cx + rx + 10} ${top - 4} ${cx + rx + 8} ${cy + ry * 0.05} L ${cx + rx - 4} ${cy - ry * 0.32}`;
        const bangs = 6;
        for (let i = 0; i < bangs; i++) {
          const x1 = cx + rx - 4 - ((i + 0.5) * (2 * rx - 8)) / bangs, x2 = cx + rx - 4 - ((i + 1) * (2 * rx - 8)) / bangs;
          d += ` Q ${x1} ${cy - ry * 0.24} ${x2} ${cy - ry * 0.36}`;
        }
        out.push(`<path d="${d} Z" fill="url(#hr${id})"/>`);
      } else {
        out.push(`<path d="M ${cx - rx - 8} ${cy + ry * 0.15} C ${cx - rx - 10} ${top - 6} ${cx + rx + 10} ${top - 6} ${cx + rx + 8} ${cy + ry * 0.15} C ${cx + rx * 0.9} ${cy - ry * 0.45} ${cx + rx * 0.4} ${cy - ry * 0.62} ${cx + 2} ${cy - ry * 0.66} L ${cx - 2} ${cy - ry * 0.66} C ${cx - rx * 0.4} ${cy - ry * 0.62} ${cx - rx * 0.9} ${cy - ry * 0.45} ${cx - rx - 8} ${cy + ry * 0.15} Z" fill="url(#hr${id})"/>`);
      }
      const ribbon = pick(r, RIBBONS);
      if (girlStyle === "pigtails") {
        for (const s of [-1, 1]) {
          const px = cx + s * (rx + 10), py = cy - ry * 0.42;
          out.push(`<path d="M ${px} ${py} l ${s * 12} -10 l 0 20 Z M ${px} ${py} l ${s * -10} -12 l ${s * -2} 20 Z" fill="${ribbon}" stroke="${shade(ribbon, -0.25)}" stroke-width="1"/>`);
          out.push(`<circle cx="${px}" cy="${py}" r="4" fill="${shade(ribbon, -0.15)}"/>`);
        }
      } else if (girlStyle === "ponytail") {
        out.push(`<path d="M ${cx - rx * 0.8} ${cy - ry * 0.78} Q ${cx} ${cy - ry * 1.18} ${cx + rx * 0.8} ${cy - ry * 0.78}" fill="none" stroke="${ribbon}" stroke-width="7" stroke-linecap="round"/>`);
      } else if (girlStyle === "braids") {
        for (const s of [-1, 1]) {
          const bx2 = cx + s * (rx + 6);
          for (let i = 0; i < 5; i++) {
            out.push(`<ellipse cx="${bx2 + s * (i * 1.5)}" cy="${cy + ry * 0.2 + i * 17}" rx="10" ry="11" fill="${i % 2 ? hair : shade(hair, 0.12)}"/>`);
          }
          out.push(`<circle cx="${bx2 + s * 8}" cy="${cy + ry * 0.2 + 84}" r="6" fill="${ribbon}"/>`);
        }
      } else if (girlStyle === "long" && r() < 0.6) {
        out.push(`<path d="M ${cx - rx - 2} ${cy - ry * 0.4} Q ${cx} ${cy - ry * 1.12} ${cx + rx + 2} ${cy - ry * 0.4}" fill="none" stroke="${ribbon}" stroke-width="6" stroke-linecap="round"/>`);
      }
    } else {
      const side = r() < 0.5 ? 1 : -1;
      if (boyStyle === "side") {
        out.push(`<path d="M ${cx - rx - 5} ${cy - ry * 0.05} C ${cx - rx - 8} ${top - 6} ${cx + rx + 8} ${top - 6} ${cx + rx + 5} ${cy - ry * 0.05} L ${cx + rx - 2} ${cy - ry * 0.22} Q ${cx + side * rx * 0.25} ${cy - ry * 0.75} ${cx - side * rx * 0.55} ${cy - ry * 0.42} Q ${cx - side * rx * 0.85} ${cy - ry * 0.3} ${cx - rx + 1} ${cy - ry * 0.22} Z" fill="url(#hr${id})"/>`);
      } else if (boyStyle === "straight") {
        let d = `M ${cx - rx - 5} ${cy - ry * 0.05} C ${cx - rx - 8} ${top - 6} ${cx + rx + 8} ${top - 6} ${cx + rx + 5} ${cy - ry * 0.05} L ${cx + rx - 3} ${cy - ry * 0.3}`;
        for (let i = 0; i < 7; i++) {
          const x1 = cx + rx - 3 - ((i + 0.5) * (2 * rx - 6)) / 7, x2 = cx + rx - 3 - ((i + 1) * (2 * rx - 6)) / 7;
          d += ` L ${x1} ${cy - ry * 0.4} L ${x2} ${cy - ry * 0.32}`;
        }
        out.push(`<path d="${d} Z" fill="url(#hr${id})"/>`);
      } else {
        out.push(`<path d="M ${cx - rx - 3} ${cy - ry * 0.05} C ${cx - rx - 5} ${top} ${cx + rx + 5} ${top} ${cx + rx + 3} ${cy - ry * 0.05} L ${cx + rx - 4} ${cy - ry * 0.35} Q ${cx} ${cy - ry * 0.72} ${cx - rx + 4} ${cy - ry * 0.35} Z" fill="url(#hr${id})"/>`);
      }
      out.push(`<path d="M ${cx - rx * 0.45} ${cy - ry * 0.85} Q ${cx - rx * 0.1} ${cy - ry * 0.98} ${cx + rx * 0.3} ${cy - ry * 0.9}" fill="none" stroke="${shade(hair, 0.35)}" stroke-width="3" stroke-linecap="round" opacity="0.25"/>`);
    }
  }
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 360" width="240" height="288">${out.join("")}</svg>`;
}

mkdirSync(OUT, { recursive: true });
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 240, height: 288 } });
const only = process.argv[2]; // optional: write a preview sheet instead
if (only === "--sheet") {
  const cells = [];
  for (let level = 0; level < LEVELS; level++) for (const g of ["b", "g"]) for (let n = 0; n < 8; n++) cells.push(portrait(level, g, n));
  await page.setViewportSize({ width: 240 * 8, height: 288 * 10 });
  await page.setContent(`<body style="margin:0;display:grid;grid-template-columns:repeat(8,240px);line-height:0">${cells.join("")}</body>`);
  await page.screenshot({ path: process.argv[3] || "sheet.png" });
} else {
  let count = 0;
  for (let level = 0; level < LEVELS; level++) {
    for (const g of ["b", "g"]) {
      for (let n = 1; n <= PER_GROUP; n++) {
        await page.setContent(`<body style="margin:0;line-height:0">${portrait(level, g, n)}</body>`);
        const jpg = await page.screenshot({ type: "jpeg", quality: 80, clip: { x: 0, y: 0, width: 240, height: 288 } });
        writeFileSync(join(OUT, `${level}_${g}_${String(n).padStart(2, "0")}.jpg`), jpg);
        count++;
      }
    }
  }
  console.log(`wrote ${count} photos to ${OUT}`);
}
await browser.close();
