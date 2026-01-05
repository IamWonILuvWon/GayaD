export const runtime = "nodejs";

import { NextResponse } from "next/server";
import { prisma } from "@/src/server/db/prisma";

export async function GET(_: Request, { params }: { params: { id: string } }) {
  const { id } = await params;

  const job = await prisma.job.findUnique({
    where: {id},
  })

  if (!job) return NextResponse.json({ error: "Not found" }, { status: 404 });
  return NextResponse.json(job);
}
