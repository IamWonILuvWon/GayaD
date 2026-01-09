from fastapi import FastAPI
from dotenv import load_dotenv
from api.stub import router as stub_router

load_dotenv()

app = FastAPI(title="MVP API", version="0.1.0")
app.include_router(stub_router, prefix="/api")
