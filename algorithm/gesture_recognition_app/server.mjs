import { createReadStream, existsSync, mkdirSync, readFileSync, statSync, writeFileSync } from "node:fs";
import { createHash } from "node:crypto";
import { createServer } from "node:http";
import { dirname, extname, join, normalize, resolve } from "node:path";
import {
  cancelRecording,
  clearPrototypes,
  createRecognitionEngine,
  deletePrototype,
  getRecordingStatus,
  getVehicleState,
  processFrame,
  recognizeOnce,
  startRecording,
  summarizePrototypes,
  updateEngineConfig
} from "./src/gesture-engine.js";

const host = process.env.HOST || "127.0.0.1";
const basePort = Number(process.env.PORT || 5173);
const distDir = resolve("dist");
const dataPath = resolve("data/prototypes.json");
const configPath = resolve("config/gesture-config.json");
const engine = createRecognitionEngine(loadPrototypes(), loadConfig());

const mimeTypes = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".wasm": "application/wasm",
  ".task": "application/octet-stream",
  ".png": "image/png",
  ".jpg": "image/jpeg",
  ".jpeg": "image/jpeg",
  ".svg": "image/svg+xml",
  ".ico": "image/x-icon"
};

if (!existsSync(distDir)) {
  console.error("dist 目录不存在，请先运行 npm run build。");
  process.exit(1);
}

const server = createServer(async (request, response) => {
  try {
    const url = new URL(request.url || "/", `http://${host}:${basePort}`);
    if (url.pathname.startsWith("/api/")) {
      await handleApi(request, response, url);
      return;
    }
    serveStatic(url, response);
  } catch (error) {
    console.error(error);
    sendJson(response, 500, { error: "internal_error", message: error.message });
  }
});

server.on("upgrade", (request, socket) => {
  const url = new URL(request.url || "/", `http://${host}:${basePort}`);
  if (url.pathname !== "/api/recognition/stream") {
    socket.destroy();
    return;
  }
  acceptWebSocket(request, socket);
});

async function handleApi(request, response, url) {
  if (request.method === "GET" && url.pathname === "/api/health") {
    sendJson(response, 200, {
      ok: true,
      service: "owner-gesture-recognition",
      prototypes: engine.prototypes.length,
      recording: getRecordingStatus(engine)
    });
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/state") {
    sendJson(response, 200, serviceState());
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/config") {
    sendJson(response, 200, { config: engine.config });
    return;
  }

  if ((request.method === "PATCH" || request.method === "PUT") && url.pathname === "/api/config") {
    const body = await readJsonBody(request);
    const nextConfig = request.method === "PUT" ? body : deepMerge(engine.config, body);
    updateEngineConfig(engine, nextConfig);
    persistConfig();
    sendJson(response, 200, serviceState());
    return;
  }

  if (request.method === "GET" && url.pathname === "/api/prototypes") {
    sendJson(response, 200, { prototypes: summarizePrototypes(engine.prototypes) });
    return;
  }

  if (request.method === "DELETE" && url.pathname === "/api/prototypes") {
    clearPrototypes(engine);
    persistPrototypes();
    sendJson(response, 200, serviceState());
    return;
  }

  const prototypeMatch = url.pathname.match(/^\/api\/prototypes\/([^/]+)$/);
  if (request.method === "DELETE" && prototypeMatch) {
    deletePrototype(engine, decodeURIComponent(prototypeMatch[1]));
    persistPrototypes();
    sendJson(response, 200, serviceState());
    return;
  }

  if (request.method === "POST" && url.pathname === "/api/recordings/start") {
    const body = await readJsonBody(request);
    if (!body.name || !body.action || !body.kind) {
      sendJson(response, 400, { error: "missing_fields" });
      return;
    }
    startRecording(engine, body);
    sendJson(response, 200, serviceState());
    return;
  }

  if (request.method === "POST" && url.pathname === "/api/recordings/cancel") {
    cancelRecording(engine);
    sendJson(response, 200, serviceState());
    return;
  }

  if (request.method === "POST" && url.pathname === "/api/recognize") {
    const body = await readJsonBody(request);
    if (!Array.isArray(body.vector)) {
      sendJson(response, 400, { error: "missing_vector" });
      return;
    }
    const recognition = recognizeOnce(engine.prototypes, body.vector, body.sequence || [], engine.config);
    sendJson(response, 200, { recognition });
    return;
  }

  sendJson(response, 404, { error: "not_found" });
}

function serviceState(extra = {}) {
  return {
    prototypes: summarizePrototypes(engine.prototypes),
    recording: getRecordingStatus(engine),
    vehicle: getVehicleState(engine),
    config: engine.config,
    ...extra
  };
}

function serveStatic(url, response) {
  const decodedPath = decodeURIComponent(url.pathname);
  const safePath = normalize(decodedPath).replace(/^(\.\.[/\\])+/, "");
  let filePath = join(distDir, safePath);

  if (!filePath.startsWith(distDir)) {
    response.writeHead(403);
    response.end("Forbidden");
    return;
  }

  if (!existsSync(filePath) || statSync(filePath).isDirectory()) {
    filePath = join(distDir, "index.html");
  }

  const contentType = mimeTypes[extname(filePath)] || "application/octet-stream";
  response.writeHead(200, {
    "Content-Type": contentType,
    "Cache-Control": "no-cache"
  });
  createReadStream(filePath).pipe(response);
}

function acceptWebSocket(request, socket) {
  const key = request.headers["sec-websocket-key"];
  if (!key) {
    socket.destroy();
    return;
  }

  const accept = createHash("sha1")
    .update(`${key}258EAFA5-E914-47DA-95CA-C5AB0DC85B11`)
    .digest("base64");

  socket.write(
    [
      "HTTP/1.1 101 Switching Protocols",
      "Upgrade: websocket",
      "Connection: Upgrade",
      `Sec-WebSocket-Accept: ${accept}`,
      "",
      ""
    ].join("\r\n")
  );

  socket.on("data", (buffer) => {
    for (const message of decodeWebSocketFrames(buffer)) {
      handleSocketMessage(socket, message);
    }
  });

  socket.on("error", () => {});
  sendWebSocketJson(socket, serviceState());
}

function handleSocketMessage(socket, message) {
  try {
    const payload = JSON.parse(message);
    if (payload.type !== "frame" || !Array.isArray(payload.vector)) return;
    const result = processFrame(engine, payload.vector);
    if (result.recordingComplete) {
      persistPrototypes();
    }
    sendWebSocketJson(socket, result);
  } catch (error) {
    sendWebSocketJson(socket, { error: "bad_message", message: error.message });
  }
}

function decodeWebSocketFrames(buffer) {
  const messages = [];
  let offset = 0;

  while (offset + 2 <= buffer.length) {
    const firstByte = buffer[offset++];
    const opcode = firstByte & 0x0f;
    const secondByte = buffer[offset++];
    const masked = Boolean(secondByte & 0x80);
    let length = secondByte & 0x7f;

    if (length === 126) {
      if (offset + 2 > buffer.length) break;
      length = buffer.readUInt16BE(offset);
      offset += 2;
    } else if (length === 127) {
      if (offset + 8 > buffer.length) break;
      const high = buffer.readUInt32BE(offset);
      const low = buffer.readUInt32BE(offset + 4);
      length = high * 2 ** 32 + low;
      offset += 8;
    }

    const mask = masked ? buffer.subarray(offset, offset + 4) : null;
    if (masked) offset += 4;
    if (offset + length > buffer.length) break;

    const payload = Buffer.from(buffer.subarray(offset, offset + length));
    offset += length;

    if (masked && mask) {
      for (let index = 0; index < payload.length; index += 1) {
        payload[index] ^= mask[index % 4];
      }
    }

    if (opcode === 0x8) {
      messages.push(null);
    } else if (opcode === 0x1) {
      messages.push(payload.toString("utf8"));
    }
  }

  return messages.filter(Boolean);
}

function sendWebSocketJson(socket, payload) {
  if (socket.destroyed) return;
  const data = Buffer.from(JSON.stringify(payload));
  let header;

  if (data.length < 126) {
    header = Buffer.from([0x81, data.length]);
  } else if (data.length < 65536) {
    header = Buffer.alloc(4);
    header[0] = 0x81;
    header[1] = 126;
    header.writeUInt16BE(data.length, 2);
  } else {
    header = Buffer.alloc(10);
    header[0] = 0x81;
    header[1] = 127;
    header.writeUInt32BE(0, 2);
    header.writeUInt32BE(data.length, 6);
  }

  socket.write(Buffer.concat([header, data]));
}

async function readJsonBody(request) {
  const chunks = [];
  for await (const chunk of request) {
    chunks.push(chunk);
  }
  if (!chunks.length) return {};
  return JSON.parse(Buffer.concat(chunks).toString("utf8"));
}

function sendJson(response, status, payload) {
  response.writeHead(status, {
    "Content-Type": "application/json; charset=utf-8",
    "Cache-Control": "no-cache"
  });
  response.end(JSON.stringify(payload));
}

function loadPrototypes() {
  try {
    if (!existsSync(dataPath)) return [];
    const parsed = JSON.parse(readFileSync(dataPath, "utf8"));
    return Array.isArray(parsed) ? parsed : [];
  } catch (error) {
    console.warn("无法读取原型库，使用空原型库。", error);
    return [];
  }
}

function persistPrototypes() {
  mkdirSync(dirname(dataPath), { recursive: true });
  writeFileSync(dataPath, JSON.stringify(engine.prototypes, null, 2));
}

function loadConfig() {
  return JSON.parse(readFileSync(configPath, "utf8"));
}

function persistConfig() {
  mkdirSync(dirname(configPath), { recursive: true });
  writeFileSync(configPath, JSON.stringify(engine.config, null, 2));
}

function deepMerge(target, patch) {
  if (!patch || typeof patch !== "object" || Array.isArray(patch)) return target;
  const output = Array.isArray(target) ? [...target] : { ...target };
  for (const [key, value] of Object.entries(patch)) {
    if (value && typeof value === "object" && !Array.isArray(value) && target?.[key] && typeof target[key] === "object") {
      output[key] = deepMerge(target[key], value);
    } else {
      output[key] = value;
    }
  }
  return output;
}

function listen(port, attemptsLeft = 10) {
  server.once("error", (error) => {
    if (error.code === "EADDRINUSE" && attemptsLeft > 0) {
      listen(port + 1, attemptsLeft - 1);
      return;
    }

    console.error(error);
    process.exit(1);
  });

  server.listen(port, host, () => {
    console.log(`本地服务已启动：http://${host}:${port}/`);
    console.log("REST API: /api/health /api/state /api/prototypes /api/recognize");
    console.log("WebSocket: /api/recognition/stream");
    console.log("按 Ctrl+C 停止服务。");
  });
}

process.on("SIGINT", () => {
  server.close(() => process.exit(0));
});

process.on("SIGTERM", () => {
  server.close(() => process.exit(0));
});

listen(basePort);
