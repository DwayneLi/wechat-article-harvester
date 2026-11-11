import net from "node:net";
import { createHash } from "node:crypto";
import fs from "node:fs";
import path from "node:path";

export const HELPER = "/Users/tg/.dsh/profiles/desktop/node_modules/@deepseek-ai/dsh-experimental-cua-macos/native/bin/darwin-arm64/f0879ec551751eaefd3402b3980575207183f0bf60590e02fb1591e34b740644/DSH Computer Use.app/Contents/MacOS/dsh-cua-native";

export function helperRuntimeKey() {
  const h = createHash("sha256");
  h.update(fs.readFileSync(HELPER));
  return h.digest("hex");
}

const CONFIG = {
  maxRequestBytes: 4 * 1024 * 1024,
  maxResponseBytes: 32 * 1024 * 1024,
  axTimeoutMs: 3000,
  textEventIntervalMs: 0.25,
  maxClickHoldMs: 5000,
  screenshotTimeoutMs: 5000,
  timeoutMs: 30000,
  graceMs: 3000,
};

export class CuaClient {
  constructor(sock) {
    this.sock = sock;
    this.buf = Buffer.alloc(0);
    this.pending = new Map();
    this.seq = 0;
    sock.on("data", (chunk) => this.onData(chunk));
    sock.on("error", (e) => this.failAll(e));
    sock.on("close", () => this.failAll(new Error("socket closed")));
  }

  static connect() {
    const uid = process.getuid();
    const key = helperRuntimeKey();
    const sockPath = path.join("/tmp", "dsh-cua-" + uid, key + ".sock");
    return new Promise((resolve, reject) => {
      const sock = net.createConnection(sockPath);
      const client = new CuaClient(sock);
      let settled = false;
      sock.once("connect", () => {
        sock.write(JSON.stringify({ type: "hello", protocol: 1, runtimeKey: key, config: CONFIG }) + "\n");
      });
      const onFirst = (chunk) => {
        const text = chunk.toString("utf8");
        if (!settled) {
          settled = true;
          sock.removeListener("data", onFirst);
          try {
            const line = text.split("\n")[0];
            const parsed = JSON.parse(line);
            if (parsed.error) { reject(new Error(JSON.stringify(parsed.error))); sock.destroy(); return; }
            client.onData(Buffer.from(text.slice(line.length + 1)));
            resolve(client);
          } catch (e) { reject(e); sock.destroy(); }
        }
      };
      sock.on("data", onFirst);
      sock.once("error", reject);
    });
  }

  onData(chunk) {
    this.buf = Buffer.concat([this.buf, chunk]);
    for (;;) {
      const nl = this.buf.indexOf(10);
      if (nl < 0) return;
      const line = this.buf.subarray(0, nl).toString("utf8");
      this.buf = this.buf.subarray(nl + 1);
      if (!line.trim()) continue;
      let msg;
      try { msg = JSON.parse(line); } catch { continue; }
      if (msg.type === "diagnostic") continue;
      if (msg.id !== undefined && this.pending.has(msg.id)) {
        const p = this.pending.get(msg.id);
        this.pending.delete(msg.id);
        if (msg.error) p.reject(new Error(msg.error.code + ": " + msg.error.message));
        else p.resolve(msg.result);
      }
    }
  }

  failAll(err) {
    for (const [, p] of this.pending) p.reject(err);
    this.pending.clear();
  }

  request(method, params) {
    const id = "c" + ++this.seq;
    return new Promise((resolve, reject) => {
      this.pending.set(id, { resolve, reject });
      this.sock.write(JSON.stringify({ id, method, params }) + "\n", (err) => {
        if (err) { this.pending.delete(id); reject(err); }
      });
      setTimeout(() => {
        if (this.pending.has(id)) { this.pending.delete(id); reject(new Error("timeout " + method)); }
      }, 60000);
    });
  }

  close() { try { this.sock.destroy(); } catch {} }
}
