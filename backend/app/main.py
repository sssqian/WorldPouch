"""
FastAPI 应用主入口。
启动方式：uvicorn backend.app.main:app --reload
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api.routes.novel import router as novel_router

app = FastAPI(
    title="小说视觉化阅读助手 API",
    description="以章节为时间轴的动态小说沙盒后端服务",
    version="0.1.0",
)

# CORS 配置 — 允许 Streamlit 前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # MVP 阶段允许所有来源
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(novel_router)


@app.get("/health")
async def health_check():
    """健康检查接口。"""
    return {"status": "ok", "message": "小说视觉化阅读助手服务运行中"}
