from __future__ import annotations

import os
import httpx

NEXT_BASE_URL = os.getenv("NEXT_BASE_URL", "http://localhost:3000")

async def notify_next(job_id: str, callbackUrl: str, payload: dict) -> None:
    """
    Next.js callback API에 작업 상태를 알려줌.
    payload 예: {"status":"completed","outputPath":"input/..../score.pdf"}
    """

    headers = {"Content-Type": "application/json"}
    # Next에서 토큰 체크를 켠다면:
    # if AI_CALLBACK_TOKEN:
    #     headers["x-ai-callback-token"] = AI_CALLBACK_TOKEN

    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(callbackUrl, json=payload, headers=headers)
        r.raise_for_status()
