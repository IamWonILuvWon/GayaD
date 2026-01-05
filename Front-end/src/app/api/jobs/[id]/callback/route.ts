export const runtime = "nodejs";

import { NextResponse } from "next/server";
import { prisma } from "@/src/server/db/prisma";

export async function POST(req: Request, { params }: { params: { id: string } }) {
  // (권장) 간단 인증: 공유 토큰 확인
//   const token = req.headers.get("x-ai-callback-token");
//   if (token !== process.env.AI_CALLBACK_TOKEN) {
//     return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
//   }

  const {id } = await params;
  const body = await req.json();

  // body 예시:
  // { status: "completed", outputPath: "...", error: "..." }

  if (body.status === "completed") {
    await prisma.job.update({
      where: { id: id },
      data: {
        status: "completed",
        outputPath: body.outputPath ?? null,
        error: null,
      },
    });
    return NextResponse.json({ ok: true });
  }

  if (body.status === "failed") {
    await prisma.job.update({
      where: { id: id },
      data: {
        status: "failed",
        error: body.error ?? "AI processing failed",
      },
    });
    return NextResponse.json({ ok: true });
  }

  // 진행률 업데이트까지 받고 싶으면:
  // if (body.status === "processing") { progress 필드 추가해서 update }

  return NextResponse.json({ error: "Invalid status" }, { status: 400 });
}
