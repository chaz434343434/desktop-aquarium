// Desktop Aquarium's tank server: short codes for shared tanks.
//   POST   /v1/tanks              {code}  -> {id, key}   share a tank, get its 6-digit code and a secret key
//   GET    /v1/tanks/:id                  -> {code, updated}
//   PUT    /v1/tanks/:id          {code}  (needs the key) newer version of your tank
//   POST   /v1/tanks/:id/close            (needs the key) close it: the tank's data goes, the code stays yours
//   DELETE /v1/tanks/:id                  (needs the key) give the code up completely
//   POST   /v1/tanks/:id/report           someone reported it; enough different people hides it
// The game checks every tank it downloads, so nothing here has to be trusted by players.
// No accounts, and IP addresses are never stored (reports and limits keep only a one-way hash).

const ID = /^[1-9][0-9]{5}$/;
const CODE = /^DA1:[A-Za-z0-9_-]+$/;
const MAX_CODE = 16000;
const REPORTS_TO_HIDE = 5;
const KEEP_FOR_MS = 365 * 24 * 3600 * 1000; // tanks nobody has updated for a year are cleared out
const HOUR_MS = 3600 * 1000;
// Per internet address, per hour. Stored in the database because the rate limit bindings are only approximate.
const MAX_WRONG_CODES = 60; // what stops someone walking through every code
const MAX_NEW_TANKS = 20;
const MAX_REPORTS = 20;

function reply(data, status = 200) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "content-type": "application/json", "cache-control": "no-store" },
  });
}

async function sha256(text) {
  const bytes = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(bytes)].map((b) => b.toString(16).padStart(2, "0")).join("");
}

function randomId() {
  // 100000-999999, evenly
  const box = new Uint32Array(1);
  const limit = Math.floor(0x100000000 / 900000) * 900000;
  do {
    crypto.getRandomValues(box);
  } while (box[0] >= limit);
  return String(100000 + (box[0] % 900000));
}

function randomKey() {
  const bytes = crypto.getRandomValues(new Uint8Array(32));
  return [...bytes].map((b) => b.toString(16).padStart(2, "0")).join("");
}

async function allowed(limiter, ip) {
  if (!limiter) return true;
  const { success } = await limiter.limit({ key: ip });
  return success;
}

function counterName(kind, ip, env) {
  return sha256(`${kind}:${ip}:${env.REPORT_SALT || ""}`); // the address itself is never stored
}

async function overLimit(env, kind, ip, max) {
  const row = await env.DB.prepare("SELECT n FROM limits WHERE who = ? AND hour = ?")
    .bind(await counterName(kind, ip, env), Math.floor(Date.now() / HOUR_MS)).first();
  return !!row && row.n >= max;
}

async function count(env, kind, ip) {
  await env.DB.prepare(
    "INSERT INTO limits (who, hour, n) VALUES (?, ?, 1) ON CONFLICT (who, hour) DO UPDATE SET n = n + 1",
  ).bind(await counterName(kind, ip, env), Math.floor(Date.now() / HOUR_MS)).run();
}

async function readCode(request) {
  const size = Number(request.headers.get("content-length") || 0);
  if (size > MAX_CODE + 200) return null;
  let body;
  try {
    const text = await request.text();
    if (text.length > MAX_CODE + 200) return null;
    body = JSON.parse(text);
  } catch {
    return null;
  }
  const code = body && body.code;
  return typeof code === "string" && code.length <= MAX_CODE && CODE.test(code) ? code : null;
}

async function ownerCheck(request, env, id) {
  const auth = request.headers.get("authorization") || "";
  const key = auth.startsWith("Bearer ") ? auth.slice(7) : "";
  if (!/^[0-9a-f]{64}$/.test(key)) return "denied";
  const row = await env.DB.prepare("SELECT key_hash FROM tanks WHERE id = ?").bind(id).first();
  if (!row) return "gone";
  return row.key_hash === (await sha256(key)) ? "ok" : "denied";
}

async function handle(request, env) {
  const url = new URL(request.url);
  const ip = request.headers.get("cf-connecting-ip") || "local";
  const parts = url.pathname.split("/").filter(Boolean);
  if (parts.length === 0 && request.method === "GET") {
    // anyone can open this in a browser to see whether their network can reach the server
    return new Response("Desktop Aquarium's tank server is working, and this network can reach it.\n", {
      headers: { "content-type": "text/plain; charset=utf-8", "cache-control": "no-store" },
    });
  }
  if (parts[0] !== "v1" || parts[1] !== "tanks" || parts.length > 4) return reply({ error: "not found" }, 404);
  const id = parts[2];
  if (id !== undefined && !ID.test(id)) return reply({ error: "not found" }, 404);
  const now = Date.now();

  if (parts.length === 2 && request.method === "POST") {
    if (!(await allowed(env.LIMIT_CREATE, ip)) || (await overLimit(env, "new", ip, MAX_NEW_TANKS))) {
      return reply({ error: "slow down" }, 429);
    }
    const code = await readCode(request);
    if (!code) return reply({ error: "bad tank" }, 400);
    const key = randomKey();
    const keyHash = await sha256(key);
    for (let tries = 0; tries < 8; tries++) {
      const newId = randomId();
      const done = await env.DB.prepare(
        "INSERT OR IGNORE INTO tanks (id, code, key_hash, updated, hidden) VALUES (?, ?, ?, ?, 0)",
      ).bind(newId, code, keyHash, now).run();
      if (done.meta.changes) {
        await count(env, "new", ip);
        return reply({ id: newId, key }, 201);
      }
    }
    return reply({ error: "full" }, 503);
  }

  if (parts.length === 3 && request.method === "GET") {
    // this limit is what stops someone walking through every code
    if (!(await allowed(env.LIMIT_READ, ip)) || (await overLimit(env, "wrong", ip, MAX_WRONG_CODES))) {
      return reply({ error: "slow down" }, 429);
    }
    const row = await env.DB.prepare("SELECT code, updated FROM tanks WHERE id = ? AND hidden = 0 AND code != ''").bind(id).first();
    if (row) return reply({ code: row.code, updated: row.updated });
    await count(env, "wrong", ip);
    return reply({ error: "not found" }, 404);
  }

  if (parts.length === 3 && (request.method === "PUT" || request.method === "DELETE")) {
    if (!(await allowed(env.LIMIT_WRITE, ip))) return reply({ error: "slow down" }, 429);
    const owner = await ownerCheck(request, env, id);
    if (owner === "gone") return reply({ error: "not found" }, 404);
    if (owner !== "ok") return reply({ error: "not yours" }, 403);
    if (request.method === "DELETE") {
      await env.DB.batch([
        env.DB.prepare("DELETE FROM tanks WHERE id = ?").bind(id),
        env.DB.prepare("DELETE FROM reports WHERE tank = ?").bind(id),
      ]);
      return reply({ ok: true });
    }
    const code = await readCode(request);
    if (!code) return reply({ error: "bad tank" }, 400);
    await env.DB.prepare("UPDATE tanks SET code = ?, updated = ? WHERE id = ?").bind(code, now, id).run();
    return reply({ ok: true });
  }

  if (parts.length === 4 && parts[3] === "close" && request.method === "POST") {
    if (!(await allowed(env.LIMIT_WRITE, ip))) return reply({ error: "slow down" }, 429);
    const owner = await ownerCheck(request, env, id);
    if (owner === "gone") return reply({ error: "not found" }, 404);
    if (owner !== "ok") return reply({ error: "not yours" }, 403);
    await env.DB.prepare("UPDATE tanks SET code = '', updated = ? WHERE id = ?").bind(now, id).run();
    return reply({ ok: true });
  }

  if (parts.length === 4 && parts[3] === "report" && request.method === "POST") {
    if (!(await allowed(env.LIMIT_WRITE, ip)) || (await overLimit(env, "report", ip, MAX_REPORTS))) {
      return reply({ error: "slow down" }, 429);
    }
    await count(env, "report", ip);
    const who = await sha256(`${id}:${ip}:${env.REPORT_SALT || ""}`);
    const tank = await env.DB.prepare("SELECT id FROM tanks WHERE id = ? AND code != ''").bind(id).first();
    if (!tank) return reply({ error: "not found" }, 404);
    await env.DB.prepare("INSERT OR IGNORE INTO reports (tank, who) VALUES (?, ?)").bind(id, who).run();
    const row = await env.DB.prepare("SELECT COUNT(*) AS n FROM reports WHERE tank = ?").bind(id).first();
    if (row.n >= REPORTS_TO_HIDE) await env.DB.prepare("UPDATE tanks SET hidden = 1 WHERE id = ?").bind(id).run();
    return reply({ ok: true });
  }

  return reply({ error: "not found" }, 404);
}

export default {
  async fetch(request, env) {
    try {
      return await handle(request, env);
    } catch (err) {
      console.error(err);
      return reply({ error: "server trouble" }, 500);
    }
  },
  async scheduled(controller, env) {
    const cutoff = Date.now() - KEEP_FOR_MS;
    await env.DB.batch([
      env.DB.prepare("DELETE FROM reports WHERE tank IN (SELECT id FROM tanks WHERE updated < ?)").bind(cutoff),
      env.DB.prepare("DELETE FROM tanks WHERE updated < ?").bind(cutoff),
      env.DB.prepare("DELETE FROM limits WHERE hour < ?").bind(Math.floor(Date.now() / HOUR_MS) - 48),
    ]);
  },
};
