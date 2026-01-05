export const runtime = "nodejs";

import { NextResponse } from "next/server";
import { prisma } from "@/src/server/db/prisma";

export async function POST(req: Request) {
  const body = await req.json();
  const { inputPath } = body;

  // Case A: inputPath provided -> create and dispatch to AI immediately
  if (inputPath && typeof inputPath === "string") {
    const job = await prisma.job.create({
      data: { inputPath, status: "queued" },
    });

    await prisma.job.update({
      where: { id: job.id },
      data: { status: "processing" },
    });

    const callbackUrl = `${process.env.APP_BASE_URL}/api/jobs/${job.id}/callback`;

    fetch(`${process.env.AI_BASE_URL}/api/stub/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jobId: job.id, inputPath: job.inputPath, callbackUrl }),
    }).catch(() => {
      prisma.job.update({ where: { id: job.id }, data: { status: "failed", error: "Failed to dispatch to AI server" } }).catch(() => {});
    });

    return NextResponse.json({ jobId: job.id }, { status: 201 });
  }

  // Case B: no inputPath -> create job in 'uploading' state and return jobId for client to upload
  const job = await prisma.job.create({ data: { status: "uploading", inputPath: "" } });
  return NextResponse.json({ jobId: job.id }, { status: 201 });
}

export async function GET() {
  const jobs = await prisma.job.findMany({
    orderBy: { createdAt: "desc" },
    take: 50,
  });
  return NextResponse.json(jobs);
}
