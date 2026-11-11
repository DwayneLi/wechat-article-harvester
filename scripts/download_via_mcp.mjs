
import fs from "node:fs";

const CSV = "/Users/tg/WorkBuddy/2026-11-10-22-52-14/公众号文章链接_最终.csv";
const DIR = "/Users/tg/Library/CloudStorage/OneDrive-个人/桌面/公众号写作/他人公众号文章下载/缓慢思考";
const MCP = "https://changfengbox.top/api/mcp";
const LOG = "/tmp/dlall.log";

function log(s) {
  const line = new Date().toISOString().slice(11, 19) + " " + s;
  fs.appendFileSync(LOG, line + "\n");
}

function norm(s) {
  return (s || "").normalize("NFKC").replace(/[^0-9A-Za-z\u4e00-\u9fff]/g, "").toLowerCase();
}

function parseCsv(text) {
  const rows = [];
  let field = "", row = [], inQ = false;
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (inQ) {
      if (c === '"') { if (text[i + 1] === '"') { field += '"'; i++; } else inQ = false; }
      else field += c;
    } else if (c === '"') inQ = true;
    else if (c === ",") { row.push(field); field = ""; }
    else if (c === "\n") { row.push(field); field = ""; rows.push(row); row = []; }
    else if (c !== "\r") field += c;
  }
  if (field.length || row.length) { row.push(field); rows.push(row); }
  return rows;
}

function existingNames() {
  const files = fs.readdirSync(DIR).filter((f) => f.endsWith(".md"));
  return new Set(files.map((f) => norm(f.replace(/\.md$/, ""))));
}

let sid = null;
async function ensureSession() {
  const headers = { "Content-Type": "application/json", "Accept": "application/json, text/event-stream" };
  const res = await fetch(MCP, { method: "POST", headers, body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize", params: { protocolVersion: "2025-06-18", capabilities: {}, clientInfo: { name: "dsh", version: "1.0" } } }) });
  sid = res.headers.get("mcp-session-id");
  await res.text();
  await fetch(MCP, { method: "POST", headers: Object.assign({}, headers, { "Mcp-Session-Id": sid }), body: JSON.stringify({ jsonrpc: "2.0", method: "notifications/initialized" }) });
  log("session " + sid);
}

function parseSse(text) {
  const out = [];
  for (const chunk of text.split("\n\n")) {
    const lines = chunk.split("\n").filter((l) => l.startsWith("data:"));
    if (lines.length) { const d = lines.map((l) => l.slice(5).trim()).join("\n"); try { out.push(JSON.parse(d)); } catch (e) {} }
  }
  if (!out.length) { try { out.push(JSON.parse(text)); } catch (e) {} }
  return out;
}

async function callWechat(url) {
  const headers = { "Content-Type": "application/json", "Accept": "application/json, text/event-stream", "Mcp-Session-Id": sid };
  const res = await fetch(MCP, { method: "POST", headers, body: JSON.stringify({ jsonrpc: "2.0", id: 9, method: "tools/call", params: { name: "wechat", arguments: { url, config: { MD: true } } } }) });
  const txt = await res.text();
  const msgs = parseSse(txt);
  const m = msgs.find((x) => x.id === 9) || msgs[0];
  if (!m || !m.result || !m.result.content) throw new Error("bad response: " + txt.slice(0, 200));
  const inner = JSON.parse(m.result.content[0].text);
  if (!inner.urls || !inner.urls.length) throw new Error("no urls in " + JSON.stringify(inner).slice(0, 200));
  return inner.urls[0];
}

async function saveOne(item) {
  for (let attempt = 1; attempt <= 3; attempt++) {
    try {
      const fileUrl = await callWechat(item.url);
      const name = decodeURIComponent(fileUrl.split("/").pop());
      const res = await fetch(fileUrl);
      if (!res.ok) throw new Error("fetch " + res.status);
      const buf = Buffer.from(await res.arrayBuffer());
      if (buf.length < 200) throw new Error("tiny file " + buf.length);
      const target = DIR + "/" + name.replace(/\//g, "_");
      fs.writeFileSync(target, buf);
      log("OK " + item.i + " " + name + " " + buf.length);
      return true;
    } catch (e) {
      if (attempt === 3) { log("FAIL " + item.i + " " + item.title + " :: " + String(e.message || e).slice(0, 120)); return false; }
      await new Promise((r) => setTimeout(r, 1500 * attempt));
      if (String(e.message || e).includes("session")) { try { await ensureSession(); } catch (e2) {} }
    }
  }
  return false;
}

const csvText = fs.readFileSync(CSV, "utf8").replace(/^\uFEFF/, "");
const rows = parseCsv(csvText).slice(1).filter((r) => r.length >= 3 && r[2] && r[2].startsWith("http"));
const have = existingNames();
const todo = rows.filter((r) => !have.has(norm(r[1]))).map((r) => ({ i: r[0], title: r[1], url: r[2] }));
log("start: rows=" + rows.length + " have=" + have.size + " todo=" + todo.length);

await ensureSession();
let done = 0, ok = 0, fail = 0;
const CONC = 2;
let idx = 0;
async function worker() {
  for (;;) {
    const my = idx++;
    if (my >= todo.length) return;
    const r = await saveOne(todo[my]);
    done++;
    if (r) ok++; else fail++;
    if (done % 10 === 0) log("progress " + done + "/" + todo.length + " ok=" + ok + " fail=" + fail);
  }
}
await Promise.all(Array.from({ length: CONC }, () => worker()));
log("DONE ok=" + ok + " fail=" + fail + " total=" + todo.length);
