import fs from "node:fs";
import { CuaClient } from "/tmp/cuaclient.mjs";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
async function retry(fn, attempts = 4) {
  let last;
  for (let i = 0; i < attempts; i++) {
    try { return await fn(); } catch (e) {
      last = e;
      const msg = String(e && e.message || e);
      if (!/WINDOW_CHANGED|NATIVE_BUSY|TIMEOUT/.test(msg)) throw e;
      await sleep(1200 + i * 800);
    }
  }
  throw last;
}


export class Wx {
  constructor(client, appHandle, win) {
    this.client = client;
    this.appHandle = appHandle;
    this.win = win;
    this.scale = null;
  }

  static async create(selector = "com.tencent.xinWeChat") {
    const client = await CuaClient.connect();
    const app = await client.request("getApp", { selector });
    const wins = await client.request("listWindows", { appHandle: app.appHandle });
    const cands = wins.filter((w) => w.isOnScreen && w.bounds && w.bounds.width > 1000);
    cands.sort((a, b) => b.bounds.width * b.bounds.height - a.bounds.width * a.bounds.height);
    let win = cands[0];
    for (let i = 0; !win && i < 10; i++) {
      await new Promise((r) => setTimeout(r, 800));
      const again = await client.request("listWindows", { appHandle: app.appHandle });
      const c2 = again.filter((w) => w.isOnScreen && w.bounds && w.bounds.width > 1000);
      c2.sort((a, b) => b.bounds.width * b.bounds.height - a.bounds.width * a.bounds.height);
      win = c2[0];
    }
    if (!win) {
      const all = wins.filter((w) => w.bounds).sort((a, b) => b.bounds.width * b.bounds.height - a.bounds.width * a.bounds.height);
      win = all[0];
    }
    return new Wx(client, app.appHandle, win);
  }

  async refreshWindows() {
    const wins = await this.client.request("listWindows", { appHandle: this.appHandle });
    const cands = wins.filter((w) => w.isOnScreen && w.bounds && w.bounds.width > 1000);
    cands.sort((a, b) => b.bounds.width * b.bounds.height - a.bounds.width * a.bounds.height);
    if (cands[0]) this.win = cands[0];
    return wins;
  }

  async shot(file = "/tmp/wxshot.png") {
    const res = await retry(() => this.client.request("screenshot", { appHandle: this.appHandle, windowId: this.win.windowId }));
    fs.writeFileSync(file, Buffer.from(res.data, "base64"));
    const bounds = res.bounds || this.win.bounds;
    this.win = Object.assign({}, this.win, { bounds });
    this.scale = bounds.width / res.pixelWidth;
    this.pxW = res.pixelWidth;
    this.pxH = res.pixelHeight;
    return { file, w: res.pixelWidth, h: res.pixelHeight, scale: this.scale, bounds };
  }

  pt(x, y) {
    if (!this.scale) throw new Error("no screenshot scale yet");
    return { x: x * this.scale, y: y * this.scale };
  }

  async clickPx(x, y, opts = {}) {
    const p = this.pt(x, y);
    return retry(() => this.client.request("click", Object.assign({
      appHandle: this.appHandle,
      windowId: this.win.windowId,
      x: p.x,
      y: p.y,
    }, opts)));
  }

  async movePx(x, y) {
    const p = this.pt(x, y);
    return this.client.request("hover", {
      appHandle: this.appHandle,
      windowId: this.win.windowId,
      x: p.x,
      y: p.y,
    });
  }

  async scrollPx(x, y, dx, dy) {
    const p = this.pt(x, y);
    return this.client.request("scroll", {
      appHandle: this.appHandle,
      windowId: this.win.windowId,
      x: p.x,
      y: p.y,
      deltaLinesX: dx,
      deltaLinesY: dy,
    });
  }

  async key(key, modifiers = []) {
    return this.client.request("pressKey", { appHandle: this.appHandle, key, modifiers });
  }

  async activate() {
    return this.client.request("activate", { appHandle: this.appHandle });
  }
}
