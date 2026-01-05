from fastapi import FastAPI
from api.stub import router as stub_router

app = FastAPI(title="MVP API", version="0.1.0")
app.include_router(stub_router, prefix="/api")
