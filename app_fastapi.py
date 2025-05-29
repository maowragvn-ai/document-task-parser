from fastapi import FastAPI, Request
from contextlib import asynccontextmanager
import uvicorn
from api.routers.document_router import document_router
from api.routers.project_router import project_router
from src.db import initialize_all_databases
from fastapi.middleware.cors import CORSMiddleware

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Code chạy khi ứng dụng khởi động
    initialize_all_databases()
    yield

app = FastAPI(title="Document Parser Service", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Hoặc ["*"] để mở hoàn toàn
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# Include routers
app.include_router(document_router)
app.include_router(project_router)

@app.get("/")
async def home():
    return "hello world"

@app.get("/health")
def health_check():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("fastapi_app:app", host="0.0.0.0", port=8000, reload=True)