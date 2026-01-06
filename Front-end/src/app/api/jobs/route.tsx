export const runtime = "nodejs";

import { NextResponse } from "next/server";
import { prisma } from "@/src/server/db/prisma";

export async function POST(req: Request) {
  const body = await req.json();
  const { inputPath } = body;

  if (!inputPath || typeof inputPath !== "string") {
    return NextResponse.json({ error: "inputPath is required" }, { status: 400 });
  }

  const job = await prisma.job.create({
    data: { inputPath, status: "queued" },
  });

  return NextResponse.json(job, { status: 201 });
}

export async function GET() {
  const jobs = await prisma.job.findMany({
    orderBy: { createdAt: "desc" },
    take: 50,
  });
  return NextResponse.json(jobs);
}
