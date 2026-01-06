export const runtime = "nodejs";

import { NextResponse } from "next/server";
import path from "path";
import fs from "fs/promises";

export async function POST(req: Request) {
  try {
    const url = new URL(req.url);
    const rawFilename = url.searchParams.get("filename");

    if (!rawFilename) {
      return NextResponse.json({ error: "filename query parameter is required" }, { status: 400 });
    }

    const filename = path.basename(rawFilename);
    const storageDir = path.resolve(process.cwd(), "storage", "input");
    await fs.mkdir(storageDir, { recursive: true });

    const uniqueName = `${Date.now()}-${filename}`;
    const filePath = path.join(storageDir, uniqueName);

    const buffer = Buffer.from(await req.arrayBuffer());
    await fs.writeFile(filePath, buffer);

    const inputPath = `/storage/input/${uniqueName}`;

    return NextResponse.json({ inputPath }, { status: 201 });
  } catch (err) {
    console.error(err);
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
