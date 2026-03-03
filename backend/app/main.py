import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import resume, match

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="AI 智能简历分析系统",
    description=(
        "自动解析 PDF 简历，利用 AI 模型提取关键信息，"
        "并对简历与岗位需求进行智能匹配评分。"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS — allow frontend origins
ALLOWED_ORIGINS = os.getenv(
    "ALLOWED_ORIGINS",
    "http://localhost:3000,http://localhost:5173,http://127.0.0.1:5500",
).split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Tighten in production using ALLOWED_ORIGINS
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"success": False, "message": "服务器内部错误", "detail": str(exc)},
    )


# Register routers
app.include_router(resume.router, prefix="/api/resume", tags=["简历解析"])
app.include_router(match.router, prefix="/api/match", tags=["匹配评分"])


@app.get("/", tags=["健康检查"])
async def root():
    return {
        "service": "AI 智能简历分析系统",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["健康检查"])
async def health_check():
    return {"status": "healthy"}
