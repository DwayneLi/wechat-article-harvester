import fs from "node:fs";
import { execFileSync } from "node:child_process";
import { SP } from "/tmp/statpass2.mjs";

const PY = "/Users/tg/.dsh/dsh-runtimes/dsh-primary-runtime/dependencies/python/bin/python3";
const DS = "/tmp/dataset";
const MAN = "/tmp/dataset_manifest.json";
const LOG = "/tmp/capture4.log";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const norm = (s) => (s || "").replace(/[^0-9A-Za-z\u4e00-\u9fff]/g, "").toLowerCase();
function log(s) { fs.appendFileSync(LOG, new Date().toISOString().slice(11, 19) + " " + s + "\n"); }
fs.mkdirSync(DS, { recursive: true });
let man = fs.existsSync(MAN) ? JSON.parse(fs.readFileSync(MAN, "utf8")) : {};
const done = new Set(Object.values(man).map((v) => norm(v.title)));
const donePrefix = new Set([...done].map((t) => t.slice(0, 4)));
function isDone(title) { const k = norm(title); return done.has(k) || donePrefix.has(k.slice(0, 4)); }
log("start have=" + Object.keys(man).length);

const sp = await SP.create();
try { await sp.wx.activate(); } catch (e) {}
await sleep(600);
// ensure we are on the LIST: close article tabs
for (let i = 0; i < 5; i++) {
  const tb = await sp.page("/tmp/c4_tab.png");
  if (!sp.articleTabs(tb).length) break;
  await sp.closeLastArticleTab();
  await sleep(350);
}
// scroll to list top
for (let i = 0; i < 30; i++) { try { for (let j = 0; j < 10; j++) await sp.wx.scrollPx(sp.W * 0.5, sp.H * 0.5, 0, 10); } catch (e) {} await sleep(180); }
await sleep(1000);
log("at top");

let captured = 0, idle = 0;
const fails = {};
const start = Date.now();
while (Date.now() - start < 70 * 60 * 1000) {
  let cards;
  try { cards = await sp.cardsWithMeta(); } catch (e) { log("ERR cards"); await sleep(1000); continue; }
  if (!cards.length) {
    try {
      const tb = await sp.page("/tmp/c4_tab2.png");
      if (sp.articleTabs(tb).length) { await sp.closeLastArticleTab(); await sleep(500); continue; }
    } catch (e) {}
    try { await sp.wx.scrollPx(sp.W * 0.5, sp.H * 0.5, 0, -10); } catch (e) {}
    await sleep(1200); idle++;
    if (idle > 20) { log("no cards stop"); break; }
    continue;
  }
  idle = 0;
  const card = cards.find((c) => !isDone(c.title));
  if (!card) {
    try { await sp.wx.scrollPx(sp.W * 0.5, sp.H * 0.5, 0, -10); } catch (e) {}
    await sleep(1300);
    continue;
  }
  done.add(norm(card.title));
  try {
    try { await sp.wx.activate(); } catch (e) {}
    await sp.wx.clickPx(card.x, card.y);
    await sleep(3000);
    try { await sp.wx.activate(); } catch (e) {}
    await sleep(3500);
    await sp.wx.shot("/tmp/c4_shot.png");
    const boxes = await sp.ocr("/tmp/c4_shot.png");
    const hdr = boxes.find((b) => /\d{4}年\d{1,2}月\d{1,2}日\s*\d{2}:\d{2}/.test(b.txt) && b.cy < sp.H * 0.3);
    let pub = "", pubHuman = "";
    if (hdr) {
      const m = hdr.txt.match(/(\d{4})年(\d{1,2})月(\d{1,2})日\s*(\d{2}:\d{2})/);
      if (m) { pubHuman = m[1] + "-" + String(m[2]).padStart(2, "0") + "-" + String(m[3]).padStart(2, "0") + " " + m[4]; pub = pubHuman.replace(" ", "_").replace(":", "-"); }
    }
    if (pub) {
      const base = pub;
      fs.copyFileSync("/tmp/c4_shot.png", DS + "/" + base + "_full.png");
      execFileSync(PY, ["/tmp/crop_ds.py", "/tmp/c4_shot.png", DS + "/" + base], { encoding: "utf8" });
      man[base] = { title: card.title, publish: pubHuman, file: base };
      fs.writeFileSync(MAN, JSON.stringify(man, null, 1));
      captured++;
      log("cap " + base + " total=" + Object.keys(man).length);
    } else {
      const kk = norm(card.title);
      fails[kk] = (fails[kk] || 0) + 1;
      log("nopub " + card.title.slice(0, 16) + " try=" + fails[kk]);
      if (fails[kk] >= 2) done.add(kk); else done.delete(kk);
    }
  } catch (e) { log("ERR proc " + String(e.message || e).slice(0, 60)); }
  try { await sp.closeLastArticleTab(); } catch (e) {}
  await sleep(250);
  if (process.env.MAXCAP && captured >= Number(process.env.MAXCAP)) { log("MAXCAP"); break; }
}
log("DONE captured=" + captured + " total=" + Object.keys(man).length);
