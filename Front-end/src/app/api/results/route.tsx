export const runtime = "nodejs";

import { NextResponse } from "next/server";
import fs from "node:fs/promises";
import path from "node:path";

export async function GET(req: Request) {
  const url = new URL(req.url);
  const p = url.searchParams.get("path");
  if (!p) return NextResponse.json({ error: "path is required" }, { status: 400 });

  // ⚠️ 보안: 디렉토리 탈출 방지 (storage/output 내부만 허용)
  const baseDir = path.resolve(process.cwd(), "storage");
  const resolved = path.resolve(baseDir, p.replace(/^\/+/, "")); // 절대경로化
  if (!resolved.startsWith(baseDir)) {
    return NextResponse.json({ error: "invalid path" }, { status: 400 });
  }

  const buf = await fs.readFile(resolved);

  // 확장자에 따라 content-type 간단히
  const ext = path.extname(resolved).toLowerCase();
  const contentType =
    ext === ".xml" || ext === ".musicxml" ? "application/xml" :
    ext === ".mid" || ext === ".midi" ? "audio/midi" :
    ext === ".pdf" ? "application/pdf" :
    "application/octet-stream";

  return new NextResponse(buf, {
    headers: {
      "Content-Type": contentType,
      "Content-Disposition": `attachment; filename="${path.basename(resolved)}"`,
    },
  });
}
