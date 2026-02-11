import os
import sys

from fastapi import FastAPI
from dotenv import load_dotenv

from api.stub import router as stub_router


# AI/fastAPI/app 기준으로 상위(AI) 디렉토리를 import 경로에 추가
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(os.path.dirname(CURRENT_DIR))  # .../AI
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)


load_dotenv()

app = FastAPI(title="MVP API", version="0.1.0")
app.include_router(stub_router, prefix="/api")
