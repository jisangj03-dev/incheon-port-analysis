// 시험용 정적 서버 — GitHub Pages 와 같은 모양으로 낸다(2026-10-12).
//   /incheon-port-analysis/…  → astro/dist/…      (기준주소)
//   없는 지면                  → astro/dist/404.html (상태 404)
//   Range 요청                 → 206 부분 응답        (PMTiles 가 쓴다 · 판정 v2 주의 ③ — python http.server 는 못 한다)
//   node tests/serve.mjs [포트] [폴더]
import { createServer } from "node:http";
import { createReadStream, statSync, existsSync, readFileSync } from "node:fs";
import { join, extname, normalize } from "node:path";
import { gzipSync } from "node:zlib";

const port = Number(process.argv[2] || 4173);
const root = process.argv[3] || "astro/dist";
const PREFIX = "/incheon-port-analysis";
const TYPES = { ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript", ".css": "text/css", ".json": "application/json",
  ".svg": "image/svg+xml", ".png": "image/png", ".jpg": "image/jpeg", ".webp": "image/webp", ".avif": "image/avif", ".woff2": "font/woff2", ".mp4": "video/mp4",
  ".webm": "video/webm", ".xml": "application/xml", ".txt": "text/plain; charset=utf-8", ".pmtiles": "application/octet-stream", ".wasm": "application/wasm", ".pf_meta": "application/octet-stream" };

function resolveFile(urlPath) {
  let p = decodeURIComponent(urlPath.split("?")[0]);
  if (!p.startsWith(PREFIX)) return null;
  p = normalize(p.slice(PREFIX.length) || "/");
  if (p.includes("..")) return null;
  let f = join(root, p);
  if (existsSync(f) && statSync(f).isDirectory()) f = join(f, "index.html");
  return existsSync(f) ? f : null;
}

createServer((req, res) => {
  if (req.url === PREFIX) { res.writeHead(301, { Location: `${PREFIX}/` }); return res.end(); }
  let f = resolveFile(req.url);
  let status = 200;
  if (!f) { f = join(root, "404.html"); status = 404; if (!existsSync(f)) { res.writeHead(404); return res.end(); } }
  const size = statSync(f).size;
  const type = TYPES[extname(f)] || "application/octet-stream";
  const range = req.headers.range && /bytes=(\d*)-(\d*)/.exec(req.headers.range);
  if (range && status === 200) {
    const start = range[1] ? Number(range[1]) : size - Number(range[2]);
    const end = range[1] && range[2] ? Math.min(Number(range[2]), size - 1) : size - 1;
    if (start >= size || start > end) { res.writeHead(416, { "Content-Range": `bytes */${size}` }); return res.end(); }
    res.writeHead(206, { "Content-Type": type, "Content-Length": end - start + 1, "Content-Range": `bytes ${start}-${end}/${size}`, "Accept-Ranges": "bytes" });
    return createReadStream(f, { start, end }).pipe(res);
  }
  // GitHub Pages 처럼 글자 자원은 gzip 으로 낸다(Lighthouse 가 압축 없음을 성능에서 깎는다 — 실물과 같은 조건으로 잰다).
  if (/text|javascript|json|xml|svg/.test(type) && /gzip/.test(req.headers["accept-encoding"] || "")) {
    const body = gzipSync(readFileSync(f));
    res.writeHead(status, { "Content-Type": type, "Content-Encoding": "gzip", "Content-Length": body.length, Vary: "Accept-Encoding" });
    return res.end(req.method === "HEAD" ? undefined : body);
  }
  res.writeHead(status, { "Content-Type": type, "Content-Length": size, "Accept-Ranges": "bytes" });
  if (req.method === "HEAD") return res.end();
  createReadStream(f).pipe(res);
}).listen(port, "127.0.0.1", () => console.log(`serve ${root} at http://127.0.0.1:${port}${PREFIX}/`));
