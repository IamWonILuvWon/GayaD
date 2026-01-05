from __future__ import annotations

import os
import uuid
import shutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter()

# 백엔드에 넣어둔 테스트 악보
ASSET_TEST_SCORE = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "assets", "test_score.pdf")
)

class StubRequest(BaseModel):
    audio_path: str  # Next.js에서 넘어오는 음원 경로(지금은 사용 안 함)

class StubResponse(BaseModel):
    job_id: str
    received_audio_path: str
    score_path: str  # 로컬 "스토리지" 내 저장 경로

def ensure_dir(path: str) -> None:
    os.makedirs(path, exist_ok=True)

@router.post("/stub/submit", response_model=StubResponse)
def submit_stub(req: StubRequest):
    storage_root = os.getenv("LOCAL_STORAGE_ROOT")
    if not storage_root:
        raise HTTPException(status_code=500, detail="LOCAL_STORAGE_ROOT is not set in env")

    if not os.path.exists(ASSET_TEST_SCORE):
        raise HTTPException(status_code=500, detail=f"Missing asset file: {ASSET_TEST_SCORE}")

    job_id = str(uuid.uuid4())

    # S3의 key 느낌으로: input/{job_id}/score.pdf
    dest_dir = os.path.join(storage_root, "input", job_id)
    ensure_dir(dest_dir)

    dest_path = os.path.join(dest_dir, "score.pdf")

    try:
        shutil.copyfile(ASSET_TEST_SCORE, dest_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to copy test score: {e}")

    return StubResponse(
        job_id=job_id,
        received_audio_path=req.audio_path,
        score_path=dest_path,
    )
