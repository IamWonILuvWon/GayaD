export const runtime = "nodejs";

import { NextResponse } from "next/server";
import path from "path";
import fs from "fs/promises";
import { prisma } from "@/src/server/db/prisma";

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

    // If jobId was provided, update the job and dispatch to AI asynchronously
    const jobId = url.searchParams.get("jobId");
    if (jobId) {
      try {
        await prisma.job.update({ where: { id: jobId }, data: { inputPath, status: "processing" } });

        const callbackUrl = `${process.env.APP_BASE_URL}/api/jobs/${jobId}/callback`;
        fetch(`${process.env.AI_BASE_URL}/api/stub/submit`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ jobId, inputPath, callbackUrl }),
        }).catch(() => {
          prisma.job.update({ where: { id: jobId }, data: { status: "failed", error: "Failed to dispatch to AI server" } }).catch(() => {});
        });
      } catch (err) {
        if (process.env.NODE_ENV !== "production") {
          console.error("Failed to update job after upload:", err);
        }
      }
    }

    return NextResponse.json({ inputPath }, { status: 201 });
  } catch (err) {
    if (process.env.NODE_ENV !== "production") {
      console.error(err);
    }
    return NextResponse.json({ error: "Internal server error" }, { status: 500 });
  }
}
